import os
import unittest
from unittest.mock import patch

from clinic_ready import ClinicReady, readiness
from hp_control import handler, operator_task
from provision_site import enable_domain_registration
from service import Service
import test_clinic_onboarding as onboarding
from test_stripe_billing import SESSION, SUB

CLINIC_URL = 'https://clinic.example.jp'
ISSUER = onboarding.ISSUER


class ClinicReadyTest(unittest.TestCase):
    """The operator prepares a site after the clinic paid and gave an unknown URL."""

    # Reuse the onboarding fixture without rerunning its tests here.
    cookie = onboarding.ClinicOnboardingTest.cookie
    call = onboarding.ClinicOnboardingTest.call
    sign_in = onboarding.ClinicOnboardingTest.sign_in

    def setUp(self):
        onboarding.ClinicOnboardingTest.setUp(self)
        self.sent = []
        self.ready = ClinicReady(self.store, self.service, lambda *mail: self.sent.append(mail), ISSUER,
                                 clock=lambda: 3000)
        self.clinic_site = {**self.site, 'site_id': 'clinic-site', 'prod_url': CLINIC_URL,
                            'github_repository_id': 99, 'github_repository': 'clinic-site',
                            'deployment': {env: {**target, 'bucket': 'simy-hp-site-clinic-' + env,
                                                 'distribution_id': 'ECLINIC' + env.upper()}
                                           for env, target in self.site['deployment'].items()}}
        self.targets = {**self.service.claim_targets, 'clinic-site': {
            env: {'bucket': t['bucket'], 'distribution': t['distribution_id']}
            for env, t in self.clinic_site['deployment'].items()}}

    def submit_unknown_url(self):
        self.sign_in()
        self.call('POST', '/start/site', form={'session_id': SESSION, 'site_url': CLINIC_URL})
        self.assertEqual(self.store.get('clinic-intake:' + SUB)['status'], 'received')

    def deploy_targets(self):
        self.service.claim_targets = self.targets

    def test_prepared_site_is_claimed_and_the_clinic_is_told_once(self):
        self.submit_unknown_url()
        self.assertEqual(self.ready.notify(SUB), {'status': 'site_not_registered'})

        enable_domain_registration(self.store, self.clinic_site, owner_email='Owner@Example.test')
        # Registered but its claim targets are not deployed yet: nothing is granted.
        self.assertEqual(readiness(self.store, SUB, self.service.claim_targets)['claim_targets'], 'missing')
        self.assertEqual(self.ready.notify(SUB), {'status': 'site_unavailable'})
        self.assertIsNone(self.store.get('site:clinic-site'))
        self.assertEqual(self.sent, [])

        self.deploy_targets()
        self.assertEqual(readiness(self.store, SUB, self.targets), {
            'subscription': 'active', 'intake': 'received', 'site_url': CLINIC_URL, 'ready_mail': None,
            'registration': 'present', 'site_id': 'clinic-site', 'owner_matches': True, 'claim_targets': 'deployed'})
        self.assertEqual(self.ready.notify(SUB), {'status': 'notified', 'site_url': CLINIC_URL,
                                                 'host': 'clinic.example.jp'})
        intake = self.store.get('clinic-intake:' + SUB)
        self.assertEqual((intake['status'], intake['ready_mail'], intake['ready_notified_at']),
                         ('claimed', 'sent', 3000))
        claims = {'sub': 'google-subject', 'scope': 'hp:read hp:write'}
        self.assertEqual([(s['site_id'], s['roles']) for s in self.service.list_sites(claims)],
                         [('clinic-site', ['read', 'edit', 'publish'])])
        self.assertEqual(self.store.get('site:clinic-site')['license_policy'],
                         {'mode': 'stripe', 'subscription_id': SUB})

        [(to, subject, body)] = self.sent
        self.assertEqual(to, 'owner@example.test')
        self.assertIn('準備ができました', subject)
        self.assertIn(ISSUER + '/start?session_id=' + SESSION, body)
        self.assertIn(CLINIC_URL, body)
        # The clinic's own page now shows the editing guide.
        self.assertIn('HP編集を始める', self.call('GET', '/start', {'session_id': SESSION})['body'])

        self.assertEqual(self.ready.notify(SUB)['status'], 'already_notified')
        self.assertEqual(len(self.sent), 1)

    def test_clinic_who_already_claimed_through_start_still_gets_one_mail(self):
        self.submit_unknown_url()
        enable_domain_registration(self.store, self.clinic_site, owner_email='owner@example.test')
        self.deploy_targets()
        self.call('GET', '/start', {'session_id': SESSION})
        self.assertEqual(self.store.get('clinic-intake:' + SUB)['status'], 'claimed')
        self.assertEqual(self.ready.notify(SUB)['status'], 'notified')
        self.assertEqual(self.ready.notify(SUB)['status'], 'already_notified')
        self.assertEqual(len(self.sent), 1)

    def test_another_owner_email_is_not_claimed_or_mailed(self):
        self.submit_unknown_url()
        enable_domain_registration(self.store, self.clinic_site, owner_email='someone@example.test')
        self.deploy_targets()
        self.assertFalse(readiness(self.store, SUB, self.targets)['owner_matches'])
        self.assertEqual(self.ready.notify(SUB), {'status': 'owner_mismatch'})
        self.assertIsNone(self.store.get('site:clinic-site'))
        self.assertEqual(self.store.get('clinic-intake:' + SUB)['status'], 'received')
        self.assertEqual(self.sent, [])

    def prepare(self):
        self.submit_unknown_url()
        enable_domain_registration(self.store, self.clinic_site, owner_email='owner@example.test')
        self.deploy_targets()

    def test_failed_mail_can_be_retried_even_if_the_intake_changed_meanwhile(self):
        self.prepare()
        key = 'clinic-intake:' + SUB

        def fail(*mail):
            # The background copier touches the same row while SES fails.
            row = self.store.get(key)
            self.store.put(key, {**row, 'copy_attempts': 1}, row['_version'])
            raise RuntimeError('ses down')
        failing = ClinicReady(self.store, self.service, fail, ISSUER, clock=lambda: 3000)
        self.assertEqual(failing.notify(SUB)['status'], 'mail_failed')
        intake = self.store.get(key)
        self.assertEqual((intake['status'], intake['ready_mail'], intake['copy_attempts']), ('claimed', 'failed', 1))
        self.assertEqual(self.ready.notify(SUB)['status'], 'notified')
        self.assertEqual(len(self.sent), 1)

    def test_interrupted_send_is_retried_once_stale(self):
        self.prepare()
        key = 'clinic-intake:' + SUB
        self.ready.claim(self.store.get('stripe-subscription:' + SUB), self.store.get(key))
        row = self.store.get(key)
        # A Lambda timed out after marking the send, before recording it.
        self.store.put(key, {**row, 'ready_mail': 'sending', 'ready_mail_at': 2900}, row['_version'])
        self.assertEqual(self.ready.notify(SUB)['status'], 'mail_in_progress')
        later = ClinicReady(self.store, self.service, lambda *mail: self.sent.append(mail), ISSUER,
                            clock=lambda: 2900 + 301)
        self.assertEqual(later.notify(SUB)['status'], 'notified')
        self.assertEqual(len(self.sent), 1)

    def test_url_changed_during_the_claim_is_not_marked_claimed(self):
        self.prepare()
        key = 'clinic-intake:' + SUB
        register = self.service.register_by_owner_email

        def resubmitted_meanwhile(*args):
            row = self.store.get(key)
            self.store.put(key, {**row, 'site_url': 'https://other.example.jp', 'host': 'other.example.jp'},
                           row['_version'])
            return register(*args)
        self.service.register_by_owner_email = resubmitted_meanwhile
        self.assertEqual(self.ready.notify(SUB), {'status': 'intake_changed'})
        intake = self.store.get(key)
        self.assertEqual((intake['status'], intake['host']), ('received', 'other.example.jp'))
        self.assertEqual(self.sent, [])
        # The clinic can still correct the URL; the next run evaluates it.
        self.service.register_by_owner_email = register
        self.assertEqual(self.ready.notify(SUB), {'status': 'site_not_registered'})

    def test_inactive_or_unknown_purchases_are_not_notified(self):
        self.assertEqual(self.ready.notify('not-a-sub'), {'status': 'invalid_subscription'})
        self.assertEqual(self.ready.notify(SUB), {'status': 'subscription_not_found'})
        self.submit_unknown_url()
        row = self.store.get('stripe-subscription:' + SUB)
        self.store.put('stripe-subscription:' + SUB, {**row, 'status': 'canceled'}, row['_version'])
        enable_domain_registration(self.store, self.clinic_site, owner_email='owner@example.test')
        self.deploy_targets()
        self.assertEqual(self.ready.notify(SUB), {'status': 'subscription_inactive'})
        self.assertIsNone(self.store.get('site:clinic-site'))

    def test_without_a_mail_sender_the_site_is_still_claimed(self):
        self.submit_unknown_url()
        enable_domain_registration(self.store, self.clinic_site, owner_email='owner@example.test')
        self.deploy_targets()
        quiet = ClinicReady(self.store, self.service, None, ISSUER)
        self.assertEqual(quiet.notify(SUB)['mail'], 'not_configured')
        self.assertEqual(self.store.get('clinic-intake:' + SUB)['status'], 'claimed')
        self.assertIsNone(self.store.get('clinic-intake:' + SUB).get('ready_mail'))

    def test_operator_task_runs_only_for_direct_invocations(self):
        self.submit_unknown_url()
        enable_domain_registration(self.store, self.clinic_site, owner_email='owner@example.test')
        self.deploy_targets()
        task = {'hp_operator_task': 'clinic_ready', 'subscription_id': SUB}
        with patch.dict(os.environ, {'HP_PUBLIC_BASE_URL': ISSUER}):
            self.assertEqual(operator_task({**task, 'extra': 1}, store=self.store, service=self.service,
                                           send=lambda *m: None), {'status': 'invalid_task'})
            result = operator_task(task, store=self.store, service=self.service,
                                   send=lambda *mail: self.sent.append(mail))
        self.assertEqual(result['status'], 'notified')
        self.assertEqual(len(self.sent), 1)
        # An HTTP API event never takes the operator path, whatever else it carries.
        with patch('hp_control.operator_task') as direct, patch('hp_control.application',
                                                                 return_value=lambda e, c: {'statusCode': 404}):
            self.assertEqual(handler({**task, 'requestContext': {}, 'rawPath': '/x'}, None), {'statusCode': 404})
            direct.assert_not_called()


class MultipleClaimTargetsTest(unittest.TestCase):
    def test_service_checks_each_site_against_its_own_targets(self):
        from store import MemoryStore
        import test_provision_site
        store = MemoryStore()
        base = test_provision_site.ProvisionTest().site()
        sites = [{**base, 'site_id': name, 'prod_url': 'https://%s.example.jp' % name, 'github_repository_id': i,
                  'github_repository': name,
                  'deployment': {env: {**t, 'bucket': f'{name}-{env}', 'distribution_id': f'E{name.upper()}{env.upper()}'}
                                 for env, t in base['deployment'].items()}}
                 for i, name in ((10, 'alpha'), (11, 'beta'))]
        targets = {s['site_id']: {env: {'bucket': t['bucket'], 'distribution': t['distribution_id']}
                                  for env, t in s['deployment'].items()} for s in sites}
        service = Service(store, publication_enabled=True, claim_targets=targets)
        for site in sites:
            service._check_claim_targets(site)
        from licensing import LicenseUnavailable
        swapped = {**sites[0], 'deployment': sites[1]['deployment']}
        with self.assertRaises(LicenseUnavailable):
            service._check_claim_targets(swapped)


if __name__ == '__main__':
    unittest.main()
