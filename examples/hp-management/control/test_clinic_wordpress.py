import json
import unittest
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet

from clinic_onboarding import ClinicOnboarding
from identity import Identity
from mcp_adapter import App
from service import Rejected, Service
from store import MemoryStore
from stripe_billing import StripeBilling
import test_clinic_onboarding
from test_clinic_onboarding import ISSUER, FakeApi
from test_stripe_billing import LINK, SECRET, SESSION, SUB, signed
import test_wordpress_provider
from wordpress_onboarding import WordPressOnboarding
from wordpress_provider import WordPressConnectionError

WORDPRESS_SITE = 'https://clinic.wordpress.com'
CLAIMS = {'sub': 'google-subject', 'scope': 'hp:read hp:write'}


class ClinicWordPressTest(unittest.TestCase):
    """A paid clinic connects its WordPress.com homepage from the start page."""

    # Reuse the clinic test's browser helpers without re-running its tests here.
    call = test_clinic_onboarding.ClinicOnboardingTest.call
    sign_in = test_clinic_onboarding.ClinicOnboardingTest.sign_in
    cookie = test_clinic_onboarding.ClinicOnboardingTest.cookie

    def setUp(self, wordpress=True):
        self.store = MemoryStore()
        # Edit and publish on WordPress sites are enabled only for the dedicated test origin.
        self.service = Service(self.store, publication_enabled=True, wordpress_test_origin=WORDPRESS_SITE)
        self.profile = {'sub': 'google-subject', 'email': 'owner@example.test', 'email_verified': True}
        identity = Identity(self.store, ISSUER, 'google-client', lambda claims: 'signed',
                            lambda code, redirect, nonce: self.profile)
        self.billing = StripeBilling(self.store, FakeApi(), {LINK: 'basic'}, clock=lambda: 2000)
        fixture = test_wordpress_provider.WordPressProviderTest()
        fixture.setUp()
        self.fixture = fixture
        self.credential_key = Fernet.generate_key().decode()
        self.connector = WordPressOnboarding(self.store, {'credential_key': self.credential_key},
                                             provider=fixture.provider)
        self.onboarding = ClinicOnboarding(self.store, self.billing, self.service, identity,
                                           Fernet.generate_key().decode(),
                                           wordpress=(lambda: self.connector) if wordpress else None)
        self.app = App(identity, self.service, None, {}, '', onboarding=self.onboarding,
                       stripe_webhook=lambda payload, signature: self.billing.webhook(payload, signature, SECRET))
        self.jar = {}

    def start_wordpress(self, url=WORDPRESS_SITE):
        response = self.call('POST', '/start/wordpress', form={'session_id': SESSION, 'wordpress_url': url})
        self.assertEqual(response['statusCode'], 303)
        location = urlsplit(response['headers']['location'])
        self.assertEqual((location.scheme, location.hostname, location.path),
                         ('https', 'public-api.wordpress.com', '/oauth2/authorize'))
        query = parse_qs(location.query)
        self.assertEqual(query['blog'], ['clinic.wordpress.com'])
        self.assertIn('hp_start_wordpress', self.jar)
        return query['state'][0]

    def test_clinic_connects_wordpress_and_edits_under_the_subscription(self):
        self.sign_in()
        page = self.call('GET', '/start', {'session_id': SESSION})['body']
        self.assertIn('WordPress.comで接続する', page)
        state = self.start_wordpress()
        self.assertEqual(self.fixture.calls, [])

        done = self.call('GET', '/start/wordpress/callback', {'code': 'fixture', 'state': state})
        self.assertEqual(done['statusCode'], 303)
        self.assertEqual(done['headers']['location'], '/start?session_id=' + SESSION)
        self.assertNotIn('hp_start_wordpress', self.jar)

        site = self.store.get('site:wordpress-123')
        self.assertEqual(site['license_policy'], {'mode': 'stripe', 'subscription_id': SUB})
        self.assertEqual(site['owner_subject'], 'google-subject')
        self.assertNotIn('fake-wordpress-token', json.dumps(self.store.rows))
        intake = self.store.get('clinic-intake:' + SUB)
        self.assertEqual((intake['status'], intake['provider'], intake['site_url']),
                         ('claimed', 'wordpress', WORDPRESS_SITE))
        self.assertIn('登録が完了しました', self.call('GET', '/start', {'session_id': SESSION})['body'])

        sites = self.service.list_sites(CLAIMS)
        self.assertEqual([(s['site_id'], s['roles']) for s in sites],
                         [('wordpress-123', ['read', 'edit', 'publish'])])
        # The editor can open the stored grant under the same subscription license.
        self.assertEqual(self.connector.load(site, 'google-subject').content, '<h1>Clinic</h1>')
        with self.assertRaises(WordPressConnectionError):
            self.connector.load(site, 'other-subject')

        # The state is single use; replaying the callback connects nothing new.
        replay = self.call('GET', '/start/wordpress/callback', {'code': 'fixture', 'state': state})
        self.assertEqual(replay['statusCode'], 400)

        cancel = {'id': 'evt_cancel', 'type': 'customer.subscription.deleted', 'created': 3000,
                  'data': {'object': {'id': SUB, 'status': 'canceled'}}}
        payload, signature = signed(cancel)
        self.assertEqual(self.billing.webhook(payload, signature, SECRET), 200)
        self.assertEqual(self.service.list_sites(CLAIMS), [])
        with self.assertRaisesRegex(Rejected, 'hp_license_required'):
            self.service.authorized(CLAIMS, 'wordpress-123', 'edit')

    def test_callback_needs_the_starting_browser_and_the_same_signed_in_account(self):
        self.sign_in()
        state = self.start_wordpress()
        # A callback URL opened in another browser lacks the binding cookie.
        stolen = self.call('GET', '/start/wordpress/callback', {'code': 'fixture', 'state': state},
                           cookie='hp_start=' + self.jar['hp_start'])
        self.assertEqual(stolen['statusCode'], 400)
        # Without the start session (signed out), the purchase cannot be used either.
        signed_out = self.call('GET', '/start/wordpress/callback', {'code': 'fixture', 'state': state},
                               cookie='hp_start_wordpress=' + self.jar['hp_start_wordpress'])
        self.assertEqual(signed_out['statusCode'], 403)
        self.assertIsNone(self.store.get('site:wordpress-123'))
        self.assertEqual(self.fixture.calls, [])

    def test_declined_or_failed_consent_returns_to_the_start_page(self):
        self.sign_in()
        state = self.start_wordpress()
        declined = self.call('GET', '/start/wordpress/callback', {'error': 'access_denied', 'state': state})
        self.assertEqual(declined['statusCode'], 303)
        self.assertIn('notice=wordpress_declined', declined['headers']['location'])
        self.assertIsNone(self.store.get('site:wordpress-123'))

        self.fixture.replies['/wp/v2/sites/123/users/me?context=edit'] = {
            'capabilities': {'edit_pages': True, 'publish_pages': False}}
        state = self.start_wordpress()
        failed = self.call('GET', '/start/wordpress/callback', {'code': 'fixture', 'state': state})
        self.assertIn('notice=wordpress_publish_permission_required', failed['headers']['location'])
        page = self.call('GET', '/start', {'session_id': SESSION, 'notice': 'wordpress_publish_permission_required'})
        self.assertIn('編集・公開権限がありません', page['body'])
        self.assertIsNone(self.store.get('site:wordpress-123'))
        self.assertIsNone(self.store.get('clinic-intake:' + SUB))

    def test_start_requires_our_origin_a_session_and_a_valid_url(self):
        self.sign_in()
        form = {'session_id': SESSION, 'wordpress_url': WORDPRESS_SITE}
        self.assertEqual(self.call('POST', '/start/wordpress', form=form, origin='https://evil.example')['statusCode'], 403)
        self.assertEqual(self.call('POST', '/start/wordpress', form=form, cookie='')['statusCode'], 403)
        bad = self.call('POST', '/start/wordpress', form={**form, 'wordpress_url': 'not a url'})
        self.assertIn('notice=invalid_url', bad['headers']['location'])

    def test_wordpress_option_is_absent_without_a_configured_app(self):
        self.setUp(wordpress=False)
        self.sign_in()
        self.assertNotIn('WordPress.com', self.call('GET', '/start', {'session_id': SESSION})['body'])
        form = {'session_id': SESSION, 'wordpress_url': WORDPRESS_SITE}
        self.assertEqual(self.call('POST', '/start/wordpress', form=form)['statusCode'], 403)

    def test_a_site_connected_under_another_license_is_not_taken_over(self):
        org = 'f4dbf297-4526-41f5-bd7b-2ba20b4736d9'
        started = self.connector.start(org, 'google-subject', WORDPRESS_SITE)
        self.connector.finish(org, 'google-subject', started['state'], 'fixture')
        self.sign_in()
        state = self.start_wordpress()
        refused = self.call('GET', '/start/wordpress/callback', {'code': 'fixture', 'state': state})
        self.assertIn('notice=wordpress_site_unavailable', refused['headers']['location'])
        self.assertEqual(self.store.get('site:wordpress-123')['license_policy'], {'mode': 'simy', 'org_id': org})

    def test_credentials_sealed_before_stripe_licensing_still_load(self):
        org = 'f4dbf297-4526-41f5-bd7b-2ba20b4736d9'
        legacy = Fernet(self.credential_key.encode()).encrypt(json.dumps({
            'site_id': 'wordpress-123', 'page_id': 456, 'origin': WORDPRESS_SITE, 'org_id': org,
            'subject': 'google-subject', 'access_token': 'legacy-token'}).encode()).decode()
        site = {'site_id': 'wordpress-123', 'prod_url': WORDPRESS_SITE, 'credential': legacy,
                'license_policy': {'mode': 'simy', 'org_id': org}}
        self.assertEqual(self.connector.load(site, 'google-subject').access_token, 'legacy-token')
        with self.assertRaises(WordPressConnectionError):
            self.connector.load({**site, 'license_policy': {'mode': 'stripe', 'subscription_id': SUB}},
                                'google-subject')


class ClinicBillingWiringTest(unittest.TestCase):
    def test_wordpress_client_uses_this_origin_and_the_editor_credential_key(self):
        import os
        from unittest.mock import patch
        import hp_control
        key = Fernet.generate_key().decode()
        secrets = {
            'billing': json.dumps({'secret_key': 'rk_test_' + 'a' * 20, 'webhook_secret': SECRET,
                                   'payment_links': {LINK: 'basic'}, 'intake_key': Fernet.generate_key().decode(),
                                   'wordpress_client': {'client_id': 'clinic-app', 'client_secret': 'clinic-secret'}}),
            'wordpress': json.dumps({'client_id': 'simy-app', 'client_secret': 'x', 'callback': 'https://simy.example/cb',
                                     'credential_key': key}),
        }
        env = {'HP_CLINIC_BILLING_SECRET_ARN': 'billing', 'HP_WORDPRESS_SECRET_ARN': 'wordpress',
               'HP_PUBLIC_BASE_URL': 'https://hp-control-acceptance.example.test/'}
        with patch.dict(os.environ, env):
            onboarding, _ = hp_control.clinic_billing(MemoryStore(), None, Identity(
                MemoryStore(), ISSUER, 'google-client', lambda claims: 'signed', lambda *a: {}), secrets.__getitem__)
            connector = onboarding.wordpress()
        self.assertEqual((connector.provider.client_id, connector.provider.callback),
                         ('clinic-app', 'https://hp-control-acceptance.example.test/start/wordpress/callback'))
        self.assertEqual(connector.cipher.decrypt(Fernet(key.encode()).encrypt(b'x')), b'x')

    def test_wordpress_option_stays_off_without_a_clinic_client(self):
        import os
        from unittest.mock import patch
        import hp_control
        billing = json.dumps({'secret_key': 'rk_test_' + 'a' * 20, 'webhook_secret': SECRET,
                              'payment_links': {LINK: 'basic'}, 'intake_key': Fernet.generate_key().decode()})
        with patch.dict(os.environ, {'HP_CLINIC_BILLING_SECRET_ARN': 'billing', 'HP_WORDPRESS_SECRET_ARN': 'wordpress',
                                     'HP_PUBLIC_BASE_URL': ISSUER}):
            onboarding, _ = hp_control.clinic_billing(MemoryStore(), None, Identity(
                MemoryStore(), ISSUER, 'google-client', lambda claims: 'signed', lambda *a: {}), {'billing': billing}.__getitem__)
        self.assertIsNone(onboarding.wordpress)


if __name__ == '__main__':
    unittest.main()
