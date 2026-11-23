import io
import json
import unittest
import zipfile

import test_clinic_onboarding as onboarding
from clinic_ready import ClinicReady
from clinic_slots import (POOL_KEY, PENDING_KEY, SlotAssigner, SlotError, enqueue, publishable_files,
                          valid_slot_site)
from hp_control import copy_clinic_sites
from provision_slot import add_slot
from test_stripe_billing import SESSION, SUB

ACCOUNT = '209300895845'
CLINIC_URL = 'https://clinic.example.jp'
COPY_KEY = 'intake/' + 'a' * 64 + '/' + 'b' * 64 + '/site.zip'


def archive(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zf:
        for path, data in files.items():
            zf.writestr(path, data)
        zf.writestr('manifest.json', '{}')
    return buffer.getvalue()


class Buckets:
    def __init__(self, contents):
        self.objects = {bucket: dict(files) for bucket, files in contents.items()}
        self.puts = []

    def list(self, bucket):
        return list(self.objects.get(bucket, {}))

    def put(self, bucket, key, data, content_type):
        self.puts.append((bucket, key, content_type))
        self.objects.setdefault(bucket, {})[key] = data


class ClinicSlotsTest(unittest.TestCase):
    """A paid clinic with an unknown domain gets a prepared slot, is claimed and mailed, with no operator step."""

    cookie = onboarding.ClinicOnboardingTest.cookie
    call = onboarding.ClinicOnboardingTest.call
    sign_in = onboarding.ClinicOnboardingTest.sign_in

    def setUp(self):
        onboarding.ClinicOnboardingTest.setUp(self)
        self.sent = []
        self.ready = ClinicReady(self.store, self.service, lambda *mail: self.sent.append(mail),
                                 onboarding.ISSUER, clock=lambda: 3000)
        self.slots = {name: self.slot_site(name, 100 + i) for i, name in enumerate(('slot-a', 'slot-b'))}
        # The operator deployed both slots' claim targets with clinic_sites.
        self.service.claim_targets = {**self.service.claim_targets, **{
            name: {env: {'bucket': t['bucket'], 'distribution': t['distribution_id']}
                   for env, t in site['deployment'].items()} for name, site in self.slots.items()}}
        self.buckets = Buckets({t['bucket']: {'index.html': b'placeholder'}
                                for site in self.slots.values() for t in site['deployment'].values()})
        self.copy = archive({'site/index.html': b'<h1>clinic</h1>', 'site/access.html': b'a',
                             'site/img/a.png': b'png', 'site/search__0123456789ab': b'query page',
                             'site/.git/config': b'x'})
        self.notified = []

        def notify(subscription_id):
            self.notified.append(subscription_id)
            return self.ready.notify(subscription_id)
        self.assigner = SlotAssigner(self.store, lambda key: self.copy, self.buckets, notify, clock=lambda: 3000)

    def slot_site(self, name, repo_id):
        return {**self.site, 'site_id': name, 'prod_url': f'https://{name}.hp.simy.one',
                'github_repository_id': repo_id, 'github_repository': 'hp-' + name,
                'deployment': {env: {**target, 'bucket': f'simy-hp-site-{name}-{env}-{ACCOUNT}',
                                     'distribution_id': f'E{name.upper().replace("-", "")}{env.upper()}',
                                     'initial_file_paths': ['index.html']}
                               for env, target in self.site['deployment'].items()}}

    def paid_clinic_copied(self, sub=SUB):
        self.sign_in()
        self.call('POST', '/start/site', form={'session_id': SESSION, 'site_url': CLINIC_URL, 'auth_code': ''})
        key = 'clinic-intake:' + sub
        intake = self.store.get(key)
        self.store.put(key, {**{k: v for k, v in intake.items() if k != '_version'}, 'copy_state': 'done',
                             'copy_key': COPY_KEY, 'copy_files': 5, 'copy_truncated': False}, intake['_version'])
        enqueue(self.store, sub)

    def add_slots(self, *names):
        for name in names:
            add_slot(self.store, self.slots[name])

    def test_copied_clinic_is_given_a_slot_claimed_and_mailed(self):
        self.add_slots('slot-a', 'slot-b')
        self.paid_clinic_copied()
        self.assertEqual(self.assigner.run_one(), (SUB, 'ready'))

        intake = self.store.get('clinic-intake:' + SUB)
        self.assertEqual((intake['status'], intake['slot_site_id'], intake['slot_state'], intake['ready_mail']),
                         ('claimed', 'slot-a', 'ready', 'sent'))
        self.assertEqual(intake['copy_skipped'], 2)  # the query page and .git are not publishable
        # Only publishable files reach both slot buckets, at the bucket root.
        for env in ('dev', 'prod'):
            bucket = f'simy-hp-site-slot-a-{env}-{ACCOUNT}'
            self.assertEqual(sorted(self.buckets.objects[bucket]), ['access.html', 'img/a.png', 'index.html'])
            self.assertEqual(self.store.get('site:slot-a')['deployment'][env]['initial_file_paths'],
                             ['access.html', 'img/a.png', 'index.html'])
        self.assertIn((f'simy-hp-site-slot-a-prod-{ACCOUNT}', 'index.html', 'text/html'), self.buckets.puts)
        # The clinic can edit and publish exactly that site under its own subscription.
        claims = {'sub': 'google-subject', 'scope': 'hp:read hp:write'}
        self.assertEqual([(s['site_id'], s['roles']) for s in self.service.list_sites(claims)],
                         [('slot-a', ['read', 'edit', 'publish'])])
        self.assertEqual(self.store.get('site:slot-a')['license_policy'], {'mode': 'stripe', 'subscription_id': SUB})
        self.assertEqual(self.store.get('site:slot-a')['recipient'], 'owner@example.test')
        [(to, subject, _)] = self.sent
        self.assertEqual(to, 'owner@example.test')
        self.assertEqual(self.store.get(POOL_KEY)['free'], ['slot-b'])
        self.assertEqual(self.store.get('site-slot:slot-a')['subscription_id'], SUB)
        self.assertEqual(self.store.get(PENDING_KEY)['subscriptions'], [])
        page = self.call('GET', '/start', {'session_id': SESSION})['body']
        self.assertIn('HP編集を始める', page)
        self.assertIn('https://slot-a.hp.simy.one', page)

    def test_no_free_slot_waits_and_resumes_when_one_is_added(self):
        self.paid_clinic_copied()
        self.assertEqual(self.assigner.run_one(), (SUB, 'no_free_slot'))
        self.assertEqual(self.store.get('clinic-intake:' + SUB)['slot_state'], 'waiting')
        self.assertIn('編集用の環境を準備中です', self.call('GET', '/start', {'session_id': SESSION})['body'])
        self.assertEqual(self.store.get(PENDING_KEY)['subscriptions'], [SUB])
        self.assertEqual(self.sent, [])

        self.add_slots('slot-b')
        self.assertEqual(self.assigner.run_one(), (SUB, 'ready'))
        self.assertEqual(self.store.get('clinic-intake:' + SUB)['slot_site_id'], 'slot-b')

    def test_domain_the_operator_registered_is_left_to_the_existing_flow(self):
        from provision_site import enable_domain_registration
        self.add_slots('slot-a')
        self.paid_clinic_copied()
        prepared = {**self.slots['slot-b'], 'prod_url': CLINIC_URL}
        enable_domain_registration(self.store, prepared, owner_email='owner@example.test')
        self.assertEqual(self.assigner.run_one(), (SUB, 'operator_registered'))
        self.assertEqual(self.store.get(POOL_KEY)['free'], ['slot-a'])
        self.assertEqual(self.buckets.puts, [])

    def test_used_slot_bucket_is_refused(self):
        self.add_slots('slot-a')
        self.buckets.objects[f'simy-hp-site-slot-a-prod-{ACCOUNT}']['releases/x/index.html'] = b'old'
        self.paid_clinic_copied()
        self.assertEqual(self.assigner.run_one(), (SUB, 'slot_not_empty'))
        intake = self.store.get('clinic-intake:' + SUB)
        self.assertEqual((intake['status'], intake['slot_state']), ('received', 'failed'))
        self.assertIsNone(self.store.get('registration-site:clinic.example.jp'))
        self.assertIn('担当者が確認します', self.call('GET', '/start', {'session_id': SESSION})['body'])

    def test_interrupted_run_resumes_without_a_second_slot(self):
        self.add_slots('slot-a', 'slot-b')
        self.paid_clinic_copied()
        broken = SlotAssigner(self.store, lambda key: self.copy, self.buckets, lambda sub: {'status': 'retry'})
        self.assertEqual(broken.run_one(), (SUB, 'claim_pending'))
        self.assertEqual(self.store.get(PENDING_KEY)['subscriptions'], [SUB])
        self.assertEqual(self.assigner.run_one(), (SUB, 'ready'))
        self.assertEqual(self.store.get('clinic-intake:' + SUB)['slot_site_id'], 'slot-a')
        self.assertEqual(self.store.get(POOL_KEY)['free'], ['slot-b'])
        self.assertEqual(len(self.sent), 1)

    def test_wordpress_and_unfinished_copies_are_not_assigned(self):
        self.add_slots('slot-a')
        self.sign_in()
        self.call('POST', '/start/site', form={'session_id': SESSION, 'site_url': CLINIC_URL, 'auth_code': ''})
        enqueue(self.store, SUB)
        self.assertEqual(self.assigner.run_one(), (SUB, 'not_applicable'))  # copy still pending
        self.assertEqual(self.store.get(POOL_KEY)['free'], ['slot-a'])

    def test_partial_copy_is_shown(self):
        self.paid_clinic_copied()
        key = 'clinic-intake:' + SUB
        intake = self.store.get(key)
        self.store.put(key, {**{k: v for k, v in intake.items() if k != '_version'}, 'copy_truncated': True},
                       intake['_version'])
        self.assertIn('一部のページ・ファイルのみ', self.call('GET', '/start', {'session_id': SESSION})['body'])

    def test_finished_copy_queues_slot_assignment(self):
        from site_copy import run_one
        self.add_slots('slot-a')
        self.sign_in()
        self.call('POST', '/start/site', form={'session_id': SESSION, 'site_url': CLINIC_URL, 'auth_code': ''})
        queued = []
        run_one(self.store, lambda key, data: None, copier=lambda host: (self.copy, {'files': [1], 'truncated': False}),
                on_done=queued.append)
        self.assertEqual(queued, [SUB])
        self.assertEqual(self.store.get('clinic-intake:' + SUB)['copy_state'], 'done')

    def test_copier_handler_assigns_after_copying(self):
        self.add_slots('slot-a')
        self.paid_clinic_copied()
        pending = self.store.get('clinic-copy-pending')
        self.store.put('clinic-copy-pending', {'subscriptions': []}, pending['_version'])
        result = copy_clinic_sites({}, None, store=self.store, put_object=lambda *a: None, assigner=self.assigner)
        self.assertEqual(result, {'handled': False, 'slot': 'ready', 'cutover': None})

    def test_resubmitting_the_same_url_keeps_the_reserved_slot(self):
        self.add_slots('slot-a', 'slot-b')
        self.paid_clinic_copied()
        broken = SlotAssigner(self.store, lambda key: self.copy, self.buckets, lambda sub: {'status': 'retry'})
        self.assertEqual(broken.run_one(), (SUB, 'claim_pending'))
        self.call('POST', '/start/site', form={'session_id': SESSION, 'site_url': CLINIC_URL, 'auth_code': ''})
        self.assertEqual(self.store.get('clinic-intake:' + SUB)['slot_site_id'], 'slot-a')
        self.assertEqual(self.assigner.run_one(), (SUB, 'ready'))
        self.assertEqual(self.store.get('clinic-intake:' + SUB)['slot_site_id'], 'slot-a')
        self.assertEqual(self.store.get(POOL_KEY)['free'], ['slot-b'])

    def test_url_cannot_change_once_a_slot_is_reserved(self):
        self.add_slots('slot-a')
        self.paid_clinic_copied()
        SlotAssigner(self.store, lambda key: self.copy, self.buckets, lambda sub: {'status': 'retry'}).run_one()
        response = self.call('POST', '/start/site', form={'session_id': SESSION, 'site_url': 'https://other.example.jp',
                                                          'auth_code': ''})
        self.assertIn('notice=site_locked', response['headers']['location'])
        intake = self.store.get('clinic-intake:' + SUB)
        self.assertEqual((intake['host'], intake['slot_site_id']), ('clinic.example.jp', 'slot-a'))

    def test_ready_mail_is_retried_after_the_claim(self):
        self.add_slots('slot-a')
        self.paid_clinic_copied()
        failing = ClinicReady(self.store, self.service, lambda *mail: (_ for _ in ()).throw(RuntimeError('ses')),
                              onboarding.ISSUER, clock=lambda: 3000)
        SlotAssigner(self.store, lambda key: self.copy, self.buckets, failing.notify).run_one()
        intake = self.store.get('clinic-intake:' + SUB)
        self.assertEqual((intake['status'], intake['ready_mail']), ('claimed', 'failed'))
        self.assertEqual(self.store.get(PENDING_KEY)['subscriptions'], [SUB])
        self.assertEqual(self.assigner.run_one(), (SUB, 'ready'))
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.store.get(PENDING_KEY)['subscriptions'], [])

    def test_copy_follow_up_survives_a_run_that_ends_after_the_copy(self):
        from site_copy import run_one
        self.sign_in()
        self.call('POST', '/start/site', form={'session_id': SESSION, 'site_url': CLINIC_URL, 'auth_code': ''})

        def lost(subscription_id):
            raise TimeoutError('lambda ended')
        with self.assertRaises(TimeoutError):
            run_one(self.store, lambda key, data: None,
                    copier=lambda host: (self.copy, {'files': [1], 'truncated': False}), on_done=lost)
        self.assertEqual(self.store.get('clinic-intake:' + SUB)['copy_state'], 'done')
        queued = []
        run_one(self.store, lambda key, data: None, on_done=queued.append)
        self.assertEqual(queued, [SUB])
        self.assertEqual(self.store.get('clinic-copy-pending')['subscriptions'], [])


class SlotRulesTest(unittest.TestCase):
    def test_publishable_files_need_index(self):
        with self.assertRaisesRegex(SlotError, 'copy_without_index'):
            publishable_files(archive({'site/a.html': b'a'}))

    def test_slot_site_must_be_its_own_hp_subdomain_and_buckets(self):
        good = {'site_id': 'slot-a', 'prod_url': 'https://slot-a.hp.simy.one',
                'deployment': {env: {'bucket': f'simy-hp-site-slot-a-{env}-{ACCOUNT}'} for env in ('dev', 'prod')}}
        self.assertTrue(valid_slot_site(good))
        self.assertFalse(valid_slot_site({**good, 'prod_url': 'https://slot-b.hp.simy.one'}))
        self.assertFalse(valid_slot_site({**good, 'license_policy': {'mode': 'stripe'}}))
        swapped = json.loads(json.dumps(good))
        swapped['deployment']['dev']['bucket'] = f'simy-hp-site-slot-a-prod-{ACCOUNT}'
        self.assertFalse(valid_slot_site(swapped))
        other = json.loads(json.dumps(good))
        other['deployment']['prod']['bucket'] = f'simy-sample-clinic-prod-{ACCOUNT}'
        self.assertFalse(valid_slot_site(other))
        # Another slot whose id merely starts with this one is not this slot.
        longer = json.loads(json.dumps(good))
        longer['deployment']['prod']['bucket'] = f'simy-hp-site-slot-a-extra-prod-{ACCOUNT}'
        self.assertFalse(valid_slot_site(longer))


if __name__ == '__main__':
    unittest.main()
