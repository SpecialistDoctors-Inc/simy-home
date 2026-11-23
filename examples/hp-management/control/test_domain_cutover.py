import unittest
from copy import deepcopy

import test_clinic_slots as slots
from domain_cutover import (PENDING_KEY, CutoverRejected, DomainCutover, allowed_host, cutover_key,
                            request)
from publisher import config_sha256, destination
from test_stripe_billing import SUB

ACCOUNT = slots.ACCOUNT
ARN = 'arn:aws:acm:us-east-1:209300895845:certificate/11111111-1111-1111-1111-111111111111'
ZONE = 'Z0008232OGBGLDBHC41G'


class Acm:
    def __init__(self):
        self.requests, self.status, self.ready = [], 'PENDING_VALIDATION', True

    def request_certificate(self, **kwargs):
        self.requests.append(kwargs)
        return {'CertificateArn': ARN}

    def describe_certificate(self, CertificateArn):
        names = [self.requests[-1]['DomainName'], *self.requests[-1]['SubjectAlternativeNames']]
        options = [{'DomainName': n, **({'ResourceRecord': {'Name': f'_v.{n}.', 'Type': 'CNAME',
                                                              'Value': f'_x.{n}.acm-validations.aws.'}}
                                          if self.ready else {})} for n in names]
        return {'Certificate': {'Status': self.status, 'DomainValidationOptions': options}}


class Route53:
    def __init__(self):
        self.changes = []

    def change_resource_record_sets(self, HostedZoneId, ChangeBatch):
        self.changes.append((HostedZoneId, ChangeBatch['Changes']))


class CloudFront:
    def __init__(self, config, origin_id):
        self.config, self.origin_id, self.status, self.updates = config, origin_id, 'Deployed', []

    def get_distribution(self, Id):
        return {'Distribution': {'Id': Id, 'DomainName': 'dslota.cloudfront.net', 'Status': self.status,
                                 'DistributionConfig': deepcopy(self.config)}}

    def get_distribution_config(self, Id):
        return {'DistributionConfig': deepcopy(self.config), 'ETag': 'E1'}

    lose_response = False
    reject = None

    def update_distribution(self, Id, IfMatch, DistributionConfig):
        if self.reject:
            error = Exception(self.reject)
            error.response = {'Error': {'Code': self.reject}}
            raise error
        self.updates.append(DistributionConfig)
        self.config, self.status = deepcopy(DistributionConfig), 'InProgress'
        if self.lose_response:
            raise TimeoutError('read timed out')  # applied, but the caller never hears
        return {'Distribution': {'DistributionConfig': deepcopy(DistributionConfig)}}


def distribution_config(bucket):
    return {'Origins': {'Quantity': 1, 'Items': [{'Id': 'clinic-site-s3', 'DomainName': f'{bucket}.s3.amazonaws.com',
                                                   'OriginPath': '', 'S3OriginConfig': {}}]},
            'Aliases': {'Quantity': 1, 'Items': ['slot-a.hp.simy.one']},
            'ViewerCertificate': {'ACMCertificateArn': 'arn:wildcard', 'SSLSupportMethod': 'sni-only'}}


class DomainCutoverTest(slots.ClinicSlotsTest):
    """A clinic on a slot moves to its own domain by adding two DNS records."""

    def setUp(self):
        super().setUp()
        config = distribution_config(f'simy-hp-site-slot-a-prod-{ACCOUNT}')
        # The slot's binding pins the prod distribution as provisioned.
        for name in ('slot-a', 'slot-b'):
            self.slots[name]['deployment']['prod']['expected_config_sha256'] = config_sha256(config, 'clinic-site-s3')
            self.slots[name]['deployment']['prod']['origin_id'] = 'clinic-site-s3'
        self.add_slots('slot-a')
        self.paid_clinic_copied()
        self.assertEqual(self.assigner.run_one(), (SUB, 'ready'))
        self.acm, self.route53 = Acm(), Route53()
        self.cloudfront = CloudFront(config, 'clinic-site-s3')
        self.objects, self.dns_moved = {}, False
        self.mails = []
        self.cutover = DomainCutover(self.store, self.acm, self.route53, self.cloudfront, self.probe, ZONE,
                                     mail=lambda *m: self.mails.append(m), clock=lambda: 5000,
                                     put_object=lambda b, k, d, t: self.objects.__setitem__((b, k), d))

    def probe(self, url):
        # The distribution serves its bucket; the clinic host is the old
        # homepage until its DNS moves. The old site copies our homepage and
        # even sends a CloudFront header, but cannot know a fresh token.
        host, _, path = url[len('https://'):].partition('/')
        if host == 'dslota.cloudfront.net' or (host == 'www.clinic.example.jp' and self.dns_moved):
            data = self.objects.get((f'simy-hp-site-slot-a-prod-{ACCOUNT}', path))
            return (200, {}, data) if data is not None else (404, {}, b'')
        if path.startswith('.well-known/simy-cutover/'):
            # A hostile old host echoes whatever the file name says.
            return 200, {'X-Amz-Cf-Id': 'forged'}, path.rsplit('/', 1)[1].removesuffix('.txt').encode()
        return 200, {'X-Amz-Cf-Id': 'forged'}, b'<h1>clinic</h1>'

    def intake(self):
        return self.store.get('clinic-intake:' + SUB)

    def test_two_records_then_everything_else_is_automatic(self):
        request(self.store, self.intake(), 'www.clinic.example.jp')
        self.assertEqual(self.cutover.run_one(), ('slot-a', 'awaiting_dns'))
        [req] = self.acm.requests
        self.assertEqual((req['DomainName'], req['SubjectAlternativeNames']),
                         ('www.clinic.example.jp', ['slot-a.hp.simy.one']))
        # We validate our own name; the clinic adds exactly two records, never MX.
        [(zone, [change])] = self.route53.changes
        self.assertEqual((zone, change['ResourceRecordSet']['Name']), (ZONE, '_v.slot-a.hp.simy.one.'))
        records = self.store.get(cutover_key('slot-a'))['records']
        self.assertEqual([(r['name'], r['type'], r['value']) for r in records], [
            ('_v.www.clinic.example.jp.', 'CNAME', '_x.www.clinic.example.jp.acm-validations.aws.'),
            ('www.clinic.example.jp.', 'CNAME', 'dslota.cloudfront.net.')])

        self.assertEqual(self.cutover.run_one(), ('slot-a', 'awaiting_dns'))  # not issued yet
        self.acm.status = 'ISSUED'
        self.assertEqual(self.cutover.run_one(), ('slot-a', 'attaching'))
        [desired] = self.cloudfront.updates
        self.assertEqual(desired['Aliases']['Items'], ['slot-a.hp.simy.one', 'www.clinic.example.jp'])
        self.assertEqual(desired['ViewerCertificate']['ACMCertificateArn'], ARN)
        self.assertEqual(self.store.get('lease:site:slot-a')['owner'], 'domain-cutover')

        self.assertEqual(self.cutover.run_one(), ('slot-a', 'attaching'))  # CloudFront still deploying
        self.cloudfront.status = 'Deployed'
        self.assertEqual(self.cutover.run_one(), ('slot-a', 'attached'))
        site = self.store.get('site:slot-a')
        self.assertEqual(site['deployment']['prod']['expected_config_sha256'],
                         config_sha256(self.cloudfront.config, 'clinic-site-s3'))
        self.assertEqual(site['prod_url'], 'https://slot-a.hp.simy.one')  # still publishing on the slot name
        self.assertEqual(self.store.get('lease:site:slot-a')['until'], 0)

        # The old homepage, even copying our page and a CloudFront header, does not pass.
        self.assertEqual(self.cutover.run_one(), ('slot-a', 'attached'))
        row = self.store.get(cutover_key('slot-a'))
        self.assertNotEqual(row['challenge_name'], row['challenge'])
        self.assertEqual(self.objects[(f'simy-hp-site-slot-a-prod-{ACCOUNT}',
                                       f'.well-known/simy-cutover/{row["challenge_name"]}.txt')], row['challenge'].encode())
        self.dns_moved = True
        self.assertEqual(self.cutover.run_one(), ('slot-a', 'live'))
        self.assertEqual(self.store.get('site:slot-a')['prod_url'], 'https://www.clinic.example.jp')
        self.assertEqual(self.store.get(PENDING_KEY)['sites'], [])
        [(to, subject, _)] = self.mails
        self.assertEqual(to, 'owner@example.test')
        self.assertIn('ご自身のドメイン', subject)

    def test_only_the_clinics_own_domain(self):
        self.assertEqual(allowed_host('clinic.example.jp', 'WWW.clinic.example.jp.'), 'www.clinic.example.jp')
        self.assertEqual(allowed_host('www.clinic.example.jp', 'clinic.example.jp'), 'clinic.example.jp')
        self.assertIsNone(allowed_host('clinic.example.jp', 'other.example.jp'))
        self.assertIsNone(allowed_host('clinic.example.jp', 'slot-b.hp.simy.one'))
        with self.assertRaisesRegex(CutoverRejected, 'invalid_cutover_host'):
            request(self.store, self.intake(), 'evil.example.jp')

    def test_busy_site_waits_for_its_publication(self):
        request(self.store, self.intake(), 'www.clinic.example.jp')
        self.cutover.run_one()
        self.acm.status = 'ISSUED'
        self.store.put('lease:site:slot-a', {'owner': 'op', 'epoch': 3, 'until': 9999, 'blocked_operation': None})
        self.assertEqual(self.cutover.run_one(), ('slot-a', 'awaiting_dns'))
        self.assertEqual(self.cloudfront.updates, [])

    def test_changed_distribution_stops_for_the_operator(self):
        request(self.store, self.intake(), 'www.clinic.example.jp')
        self.cutover.run_one()
        self.acm.status = 'ISSUED'
        self.cloudfront.config['Comment'] = 'edited by hand'
        self.assertEqual(self.cutover.run_one(), ('slot-a', 'failed'))
        self.assertEqual(self.store.get(cutover_key('slot-a'))['error'], 'cloudfront_unexpected_config_drift')
        self.assertEqual(self.cloudfront.updates, [])
        self.assertEqual(self.store.get('lease:site:slot-a')['until'], 0)

    def test_lost_update_response_is_reconciled_not_stranded(self):
        request(self.store, self.intake(), 'www.clinic.example.jp')
        self.cutover.run_one()
        self.acm.status = 'ISSUED'
        self.cloudfront.lose_response = True
        self.assertEqual(self.cutover.run_one(), ('slot-a', 'retry'))
        self.assertEqual(self.store.get(cutover_key('slot-a'))['state'], 'attaching')
        self.assertEqual(self.store.get('lease:site:slot-a')['owner'], 'domain-cutover')  # publications stay out
        self.cloudfront.lose_response = False
        self.cloudfront.status = 'Deployed'
        self.assertEqual(self.cutover.run_one(), ('slot-a', 'attached'))
        self.assertEqual(len(self.cloudfront.updates), 1)  # recognized as applied, not sent twice
        self.assertEqual(self.store.get('site:slot-a')['deployment']['prod']['expected_config_sha256'],
                         config_sha256(self.cloudfront.config, 'clinic-site-s3'))

    def test_other_changes_made_during_the_attach_are_never_pinned(self):
        request(self.store, self.intake(), 'www.clinic.example.jp')
        self.cutover.run_one()
        self.acm.status = 'ISSUED'
        self.cloudfront.lose_response = True
        self.cutover.run_one()
        self.cloudfront.lose_response = False
        # Someone also changed the origin while our update was in flight.
        self.cloudfront.config['Origins']['Items'][0]['DomainName'] = 'evil.s3.amazonaws.com'
        self.cloudfront.status = 'Deployed'
        self.assertEqual(self.cutover.run_one(), ('slot-a', 'failed'))
        self.assertEqual(self.store.get(cutover_key('slot-a'))['error'], 'cloudfront_unexpected_config_drift')
        self.assertEqual(self.store.get('site:slot-a')['deployment']['prod']['expected_config_sha256'],
                         self.slots['slot-a']['deployment']['prod']['expected_config_sha256'])

    def test_update_that_never_landed_is_sent_again(self):
        request(self.store, self.intake(), 'www.clinic.example.jp')
        self.cutover.run_one()
        self.acm.status = 'ISSUED'
        original = self.cloudfront.update_distribution

        def lost_before_applying(**kwargs):
            raise TimeoutError('connect timed out')
        self.cloudfront.update_distribution = lost_before_applying
        self.assertEqual(self.cutover.run_one(), ('slot-a', 'retry'))
        self.cloudfront.update_distribution = original
        self.assertEqual(self.cutover.run_one(), ('slot-a', 'attaching'))
        self.assertEqual(len(self.cloudfront.updates), 1)

    def test_domain_used_by_another_distribution_fails_for_the_operator(self):
        request(self.store, self.intake(), 'www.clinic.example.jp')
        self.cutover.run_one()
        self.acm.status = 'ISSUED'
        self.cloudfront.reject = 'CNAMEAlreadyExists'
        self.assertEqual(self.cutover.run_one(), ('slot-a', 'failed'))
        self.assertEqual(self.store.get(cutover_key('slot-a'))['error'], 'cloudfront_update_failed:CNAMEAlreadyExists')
        self.assertEqual(self.store.get('lease:site:slot-a')['until'], 0)

    def test_expired_certificate_fails_visibly(self):
        request(self.store, self.intake(), 'www.clinic.example.jp')
        self.cutover.run_one()
        self.acm.status = 'VALIDATION_TIMED_OUT'
        self.assertEqual(self.cutover.run_one(), ('slot-a', 'failed'))
        self.assertEqual(self.store.get(PENDING_KEY)['sites'], [])

    def test_transient_errors_keep_the_job(self):
        request(self.store, self.intake(), 'www.clinic.example.jp')

        def throttled(**kwargs):
            raise RuntimeError('throttled')
        self.acm.request_certificate = throttled
        self.assertEqual(self.cutover.run_one(), ('slot-a', 'retry'))
        self.assertEqual(self.store.get(PENDING_KEY)['sites'], ['slot-a'])

    def test_unclaimed_or_non_slot_sites_are_refused(self):
        with self.assertRaisesRegex(CutoverRejected, 'slot_site_required'):
            request(self.store, {**self.intake(), 'slot_site_id': None}, 'www.clinic.example.jp')

    def test_clinic_page_walks_through_the_cutover(self):
        from test_stripe_billing import SESSION
        page = lambda: self.call('GET', '/start', {'session_id': SESSION})['body']
        self.assertIn('action="/start/domain"', page())
        self.assertIn('value="clinic.example.jp"', page())
        refused = self.call('POST', '/start/domain', form={'session_id': SESSION, 'host': 'evil.example.jp'})
        self.assertIn('notice=invalid_cutover_host', refused['headers']['location'])
        self.assertIsNone(self.store.get(cutover_key('slot-a')))

        self.assertEqual(self.call('POST', '/start/domain', form={'session_id': SESSION, 'host': 'www.clinic.example.jp'})['statusCode'], 303)
        self.assertIn('準備中です', page())
        self.cutover.run_one()
        body = page()
        # The two records, and a message the clinic can forward to its DNS vendor.
        self.assertIn('_v.www.clinic.example.jp.', body)
        self.assertIn('dslota.cloudfront.net.', body)
        self.assertIn('管理会社に送る文面', body)
        self.assertIn('MXなど、ほかのレコードは変更しないでください', body)
        self.assertNotIn('action="/start/domain"', body)

        self.acm.status = 'ISSUED'
        self.cutover.run_one()
        self.cloudfront.status = 'Deployed'
        self.cutover.run_one()
        self.assertIn('2件目（ホームページ）が反映されると自動で切り替わり', page())
        self.dns_moved = True
        self.cutover.run_one()
        self.assertIn('https://www.clinic.example.jp で公開中です', page())

    def test_foreign_origin_cannot_start_a_cutover(self):
        from test_stripe_billing import SESSION
        response = self.call('POST', '/start/domain', form={'session_id': SESSION, 'host': 'www.clinic.example.jp'},
                             origin='https://evil.example')
        self.assertNotEqual(response['statusCode'], 303)
        self.assertIsNone(self.store.get(cutover_key('slot-a')))

    # The slot tests themselves already ran in the parent class.
    test_copied_clinic_is_given_a_slot_claimed_and_mailed = None
    test_no_free_slot_waits_and_resumes_when_one_is_added = None
    test_domain_the_operator_registered_is_left_to_the_existing_flow = None
    test_used_slot_bucket_is_refused = None
    test_interrupted_run_resumes_without_a_second_slot = None
    test_wordpress_and_unfinished_copies_are_not_assigned = None
    test_partial_copy_is_shown = None
    test_finished_copy_queues_slot_assignment = None
    test_copier_handler_assigns_after_copying = None
    test_resubmitting_the_same_url_keeps_the_reserved_slot = None
    test_url_cannot_change_once_a_slot_is_reserved = None
    test_ready_mail_is_retried_after_the_claim = None
    test_copy_follow_up_survives_a_run_that_ends_after_the_copy = None


class PublisherDestinationTest(unittest.TestCase):
    def test_repinned_binding_keeps_its_destination(self):
        binding = {'site_id': 's', 'environment': 'prod', 'role_arn': 'r', 'url': 'https://slot-a.hp.simy.one',
                   'target': {'bucket': 'b', 'distribution_id': 'D', 'origin_id': 'o', 'expected_config_sha256': 'a' * 64}}
        moved = deepcopy(binding)
        moved['url'], moved['target']['expected_config_sha256'] = 'https://www.clinic.example.jp', 'b' * 64
        self.assertEqual(destination(binding), destination(moved))
        other = deepcopy(binding)
        other['target']['bucket'] = 'another'
        self.assertNotEqual(destination(binding), destination(other))
        self.assertIsNone(destination(None))


if __name__ == '__main__':
    unittest.main()
