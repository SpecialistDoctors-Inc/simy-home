import json
import unittest
from urllib.parse import parse_qs, urlencode, urlsplit

from cryptography.fernet import Fernet

from clinic_onboarding import ClinicOnboarding
from identity import Identity
from mcp_adapter import App
from provision_site import enable_domain_registration
from service import Rejected, Service
from store import MemoryStore
from stripe_billing import StripeBilling
import test_provision_site
from test_stripe_billing import LINK, SECRET, SESSION, SUB, session, signed

ISSUER = 'https://hp-control.example.test'
AUTH_CODE = 'Ab3$xY9!kQ'


class FakeApi:
    def __init__(self):
        self.session = session(subscription={'id': SUB, 'status': 'active'})
        self.status = 'active'

    def subscription(self, subscription_id):
        return {'id': subscription_id, 'status': self.status}

    def checkout_session(self, session_id):
        if session_id != SESSION:
            from stripe_billing import BillingRejected
            raise BillingRejected('payment_not_confirmed')
        return self.session


class ClinicOnboardingTest(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.dns = False
        self.site = test_provision_site.ProvisionTest().site()
        targets = {env: {'bucket': item['bucket'], 'distribution': item['distribution_id']}
                   for env, item in self.site['deployment'].items()}
        self.service = Service(self.store, publication_enabled=True,
                               claim_targets={self.site['site_id']: targets}, dns_check=lambda *_: self.dns)
        enable_domain_registration(self.store, self.site)
        self.profile = {'sub': 'google-subject', 'email': 'owner@example.test', 'email_verified': True}
        identity = Identity(self.store, ISSUER, 'google-client', lambda claims: 'signed',
                            lambda code, redirect, nonce: self.profile)
        self.billing = StripeBilling(self.store, FakeApi(), {LINK: 'basic'}, clock=lambda: 2000)
        self.onboarding = ClinicOnboarding(self.store, self.billing, self.service, identity,
                                           Fernet.generate_key().decode())
        self.app = App(identity, self.service, None, {}, '', onboarding=self.onboarding,
                       stripe_webhook=lambda payload, signature: self.billing.webhook(payload, signature, SECRET))
        self.jar = {}

    @property
    def cookie(self):
        return '; '.join(f'{k}={v}' for k, v in self.jar.items())

    @cookie.setter
    def cookie(self, value):
        self.jar = dict(part.split('=', 1) for part in value.split('; ') if '=' in part)

    def call(self, method, path, query=None, form=None, origin=ISSUER, cookie=None):
        headers = {'cookie': self.cookie if cookie is None else cookie}
        if form is not None:
            headers.update({'content-type': 'application/x-www-form-urlencoded', 'origin': origin})
        response = self.app({'requestContext': {'http': {'method': method}}, 'rawPath': path,
                             'rawQueryString': urlencode(query or {}), 'headers': headers,
                             'body': urlencode(form) if form is not None else ''})
        for cookie_line in response.get('cookies', []):
            name, _, value = cookie_line.split(';')[0].partition('=')
            if 'Max-Age=0' in cookie_line:
                self.jar.pop(name, None)
            else:
                self.jar[name] = value
        return response

    def sign_in(self):
        start = self.call('GET', '/start/google', {'session_id': SESSION})
        self.assertEqual(start['statusCode'], 302)
        google = parse_qs(urlsplit(start['headers']['location']).query)
        self.assertEqual(google['redirect_uri'], [ISSUER + '/oauth/google/callback'])
        callback = self.call('GET', '/oauth/google/callback', {'state': google['state'][0], 'code': 'google-code'})
        self.assertEqual(callback['statusCode'], 302)
        self.assertIn('HttpOnly', callback['cookies'][0])
        self.assertNotIn('hp_start_login', self.jar)
        return callback

    def test_paid_clinic_signs_in_registers_site_and_gets_edit_access(self):
        self.assertEqual(self.call('GET', '/start', {'session_id': 'cs_test_' + 'X' * 40})['statusCode'], 403)
        page = self.call('GET', '/start', {'session_id': SESSION})
        self.assertEqual(page['statusCode'], 200)
        self.assertIn('Googleでログイン', page['body'])
        self.assertIn('基本保守', page['body'])
        # Under no-referrer, browsers send "Origin: null" on form POSTs, which the
        # origin check would refuse. Keep referrers same-origin only.
        self.assertEqual(page['headers']['referrer-policy'], 'same-origin')

        self.sign_in()
        self.assertEqual(self.store.get('stripe-subscription:' + SUB)['subject'], 'google-subject')
        self.assertIn('ホームページを登録します', self.call('GET', '/start', {'session_id': SESSION})['body'])

        submitted = self.call('POST', '/start/site', form={
            'session_id': SESSION, 'site_url': self.site['prod_url'], 'auth_code': AUTH_CODE})
        self.assertEqual(submitted['statusCode'], 303)
        intake = self.store.get('clinic-intake:' + SUB)
        self.assertEqual(intake['status'], 'verification_required')
        self.assertNotIn(AUTH_CODE, json.dumps(self.store.rows))
        self.assertEqual(self.onboarding.cipher.decrypt(intake['auth_code'].encode()).decode(), AUTH_CODE)
        page = self.call('GET', '/start', {'session_id': SESSION})['body']
        self.assertIn(intake['dns']['value'], page)
        self.assertNotIn(AUTH_CODE, page)

        pending = self.call('POST', '/start/verify', form={'session_id': SESSION})
        self.assertIn('notice=verification_pending', pending['headers']['location'])
        self.assertIsNone(self.store.get('site:' + self.site['site_id']))
        self.dns = True
        self.call('POST', '/start/verify', form={'session_id': SESSION})
        self.assertEqual(self.store.get('clinic-intake:' + SUB)['status'], 'claimed')
        self.assertIn('HP編集を始める', self.call('GET', '/start', {'session_id': SESSION})['body'])

        claims = {'sub': 'google-subject', 'scope': 'hp:read hp:write'}
        self.assertEqual(self.service.list_sites(claims)[0]['roles'], ['read', 'edit', 'publish'])
        self.assertEqual(self.store.get('site:' + self.site['site_id'])['license_policy'],
                         {'mode': 'stripe', 'subscription_id': SUB})

        cancel = {'id': 'evt_cancel', 'type': 'customer.subscription.deleted', 'created': 3000,
                  'data': {'object': {'id': SUB, 'status': 'canceled'}}}
        payload, signature = signed(cancel)
        response = self.app({'requestContext': {'http': {'method': 'POST'}}, 'rawPath': '/stripe/webhook',
                             'headers': {'stripe-signature': signature}, 'body': payload.decode()})
        self.assertEqual(response['statusCode'], 200)
        with self.assertRaisesRegex(Rejected, 'hp_license_required'):
            self.service.authorized(claims, self.site['site_id'], 'edit')

    def test_posts_need_our_origin_and_the_bound_account(self):
        self.sign_in()
        form = {'session_id': SESSION, 'site_url': self.site['prod_url'], 'auth_code': ''}
        self.assertEqual(self.call('POST', '/start/site', form=form, origin='https://evil.example')['statusCode'], 403)
        self.assertEqual(self.call('POST', '/start/site', form=form, cookie='')['statusCode'], 403)
        self.assertIsNone(self.store.get('clinic-intake:' + SUB))

        self.profile = {'sub': 'other-subject', 'email': 'other@example.test', 'email_verified': True}
        self.cookie = ''
        start = self.call('GET', '/start/google', {'session_id': SESSION})
        state = parse_qs(urlsplit(start['headers']['location']).query)['state'][0]
        callback = self.call('GET', '/oauth/google/callback', {'state': state, 'code': 'google-code'})
        self.assertEqual(callback['statusCode'], 403)
        self.assertNotIn('cookies', callback)

    def test_google_callback_completed_in_another_browser_is_refused(self):
        # An attacker starts sign-in, completes Google with their own account and
        # sends the callback URL to the clinic. The clinic's browser lacks the
        # login cookie, so nothing is bound and no session is issued.
        self.profile = {'sub': 'attacker-subject', 'email': 'attacker@example.test', 'email_verified': True}
        start = self.call('GET', '/start/google', {'session_id': SESSION})
        state = parse_qs(urlsplit(start['headers']['location']).query)['state'][0]
        self.jar = {}
        callback = self.call('GET', '/oauth/google/callback', {'state': state, 'code': 'attacker-code'})
        self.assertEqual(callback['statusCode'], 400)
        self.assertNotIn('cookies', callback)
        self.assertIsNone(self.store.get('stripe-subscription:' + SUB)['subject'])

    def test_unprepared_site_is_kept_for_the_operator_and_invalid_codes_are_refused(self):
        self.sign_in()
        bad = self.call('POST', '/start/site', form={'session_id': SESSION, 'site_url': 'https://clinic.example.jp',
                                                      'auth_code': 'has space'})
        self.assertIn('notice=invalid_auth_code', bad['headers']['location'])
        self.call('POST', '/start/site', form={'session_id': SESSION, 'site_url': 'https://clinic.example.jp',
                                               'auth_code': AUTH_CODE})
        intake = self.store.get('clinic-intake:' + SUB)
        self.assertEqual((intake['status'], intake['host']), ('received', 'clinic.example.jp'))
        self.assertIn('移管の準備を進めます', self.call('GET', '/start', {'session_id': SESSION})['body'])
        self.assertIsNone(self.store.get('principal:google-subject'))

    def test_lambda_cookie_list_is_read(self):
        self.sign_in()
        token = self.jar['hp_start']
        response = self.app({'requestContext': {'http': {'method': 'GET'}}, 'rawPath': '/start',
                             'rawQueryString': urlencode({'session_id': SESSION}), 'headers': {},
                             'cookies': ['other=1', 'hp_start=' + token]})
        self.assertIn('ホームページを登録します', response['body'])


if __name__ == '__main__':
    unittest.main()
