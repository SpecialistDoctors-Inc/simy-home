"""Sign-in with an emailed one-time code: issuer, HTTP pages and clinic onboarding."""
import base64
import hashlib
import json
import re
import unittest
from html import unescape
from urllib.parse import parse_qs, urlencode, urlsplit

from cryptography.fernet import Fernet

from clinic_onboarding import ClinicOnboarding
from email_login import (MAX_ATTEMPTS, EmailCodes, SesSender, email_subject, normalize_email)
from identity import AuthError, Identity, sha
from mcp_adapter import App
from provision_site import enable_domain_registration
from service import Service
from store import MemoryStore
from stripe_billing import StripeBilling
import test_provision_site
from test_clinic_onboarding import FakeApi
from test_stripe_billing import LINK, SECRET, SESSION, SUB

ISSUER = 'https://hp-control.example.test'
REDIRECT = 'http://127.0.0.1:43123/callback'
MAILBOX = 'clinic@example.test'


class Outbox:
    def __init__(self):
        self.sent = []

    def __call__(self, to, code):
        self.sent.append((to, code))

    def last(self):
        return self.sent[-1][1]


class EmailCodesTest(unittest.TestCase):
    def setUp(self):
        self.store, self.outbox, self.now = MemoryStore(), Outbox(), 100_000
        self.codes = EmailCodes(self.store, self.outbox, clock=lambda: self.now)
        self.challenge = 'c' * 43

    def test_code_is_stored_hashed_and_redeemable_once(self):
        self.assertTrue(self.codes.issue(self.challenge, ' Clinic@Example.TEST ', context={'k': 'v'}))
        to, code = self.outbox.sent[0]
        self.assertEqual(to, MAILBOX)
        self.assertRegex(code, r'^[0-9]{6}$')
        self.assertNotIn(code, json.dumps(self.store.rows))
        self.assertEqual(self.codes.verify(self.challenge, code), (MAILBOX, {'k': 'v'}))
        with self.assertRaisesRegex(AuthError, 'email_code'):
            self.codes.verify(self.challenge, code)

    def test_code_is_bound_to_its_challenge_and_expires(self):
        self.codes.issue(self.challenge, MAILBOX)
        code = self.outbox.last()
        with self.assertRaises(AuthError):
            self.codes.verify('d' * 43, code)
        self.now += 600
        with self.assertRaisesRegex(AuthError, 'expired_email_code'):
            self.codes.verify(self.challenge, code)

    def test_wrong_guesses_exhaust_the_code(self):
        self.codes.issue(self.challenge, MAILBOX)
        code = self.outbox.last()
        wrong = '000000' if code != '000000' else '111111'
        for attempt in range(1, MAX_ATTEMPTS + 1):
            expected = 'invalid_email_code' if attempt < MAX_ATTEMPTS else 'expired_email_code'
            with self.subTest(attempt=attempt), self.assertRaisesRegex(AuthError, expected):
                self.codes.verify(self.challenge, wrong)
        with self.assertRaisesRegex(AuthError, 'expired_email_code'):
            self.codes.verify(self.challenge, code)
        for malformed in ['12345', '1234567', 'abcdef', None]:
            self.codes.issue('e' * 43, MAILBOX)
            with self.subTest(malformed=malformed), self.assertRaisesRegex(AuthError, 'invalid_email_code'):
                self.codes.verify('e' * 43, malformed)

    def test_resend_replaces_the_code_and_is_limited(self):
        for _ in range(3):
            self.assertTrue(self.codes.issue(self.challenge, MAILBOX))
        first, last = self.outbox.sent[0][1], self.outbox.last()
        self.assertFalse(self.codes.issue(self.challenge, MAILBOX))
        self.assertEqual(len(self.outbox.sent), 3)
        if first != last:
            with self.assertRaises(AuthError):
                self.codes.verify(self.challenge, first)
        self.assertEqual(self.codes.verify(self.challenge, last)[0], MAILBOX)

    def test_mailbox_and_ip_hourly_limits(self):
        for index in range(5):
            self.assertTrue(self.codes.issue(f'{index:02d}' + 'x' * 41, MAILBOX))
        self.assertFalse(self.codes.issue('y' * 43, MAILBOX))
        self.assertTrue(self.codes.issue('y' * 43, 'other@example.test'))
        self.now += 3600
        self.assertTrue(self.codes.issue('y' * 43, MAILBOX))
        for index in range(20):
            self.assertTrue(self.codes.issue(f'{index:02d}' + 'z' * 41, f'm{index}@example.test', source_ip='192.0.2.1'))
        self.assertFalse(self.codes.issue('w' * 43, 'fresh@example.test', source_ip='192.0.2.1'))
        self.assertTrue(self.codes.issue('w' * 43, 'fresh@example.test', source_ip='192.0.2.2'))

    def test_stale_wrong_guess_cannot_restore_a_consumed_code(self):
        self.codes.issue(self.challenge, MAILBOX)
        code = self.outbox.last()
        key = 'email-code:' + sha(self.challenge)
        stale = self.store.get(key)
        self.assertEqual(self.codes.verify(self.challenge, code)[0], MAILBOX)
        self.codes.issue(self.challenge, MAILBOX)  # a resend for the same challenge
        # The wrong-guess write prepared from the pre-consumption row must not apply.
        from store import Conflict, Write
        value = {k: v for k, v in stale.items() if k != '_version'}
        with self.assertRaises(Conflict):
            self.store.transact([Write(key, {**value, 'attempts': 1}, stale['_version'])])
        with self.assertRaises(AuthError):
            self.codes.verify(self.challenge, code if code != self.outbox.last() else '------')

    def test_resend_limit_is_identical_for_unregistered_addresses(self):
        results = {}
        for deliver in (True, False):
            codes = EmailCodes(MemoryStore(), Outbox(), clock=lambda: self.now)
            results[deliver] = [codes.issue(self.challenge, MAILBOX, deliver=deliver) for _ in range(4)]
        self.assertEqual(results[True], results[False])
        self.assertEqual(results[True], [True, True, True, False])

    def test_undeliverable_address_spends_limits_but_sends_nothing(self):
        for index in range(5):
            self.assertTrue(self.codes.issue(f'{index:02d}' + 'x' * 41, MAILBOX, deliver=False))
        self.assertEqual(self.outbox.sent, [])
        self.assertIsNone(self.store.get('email-code:' + sha('00' + 'x' * 41))['code'])
        with self.assertRaisesRegex(AuthError, 'invalid_email_code'):
            self.codes.verify('00' + 'x' * 41, '123456')
        self.assertFalse(self.codes.issue('y' * 43, MAILBOX, deliver=False))

    def test_address_validation_and_subject_shape(self):
        for bad in ['', 'no-at-sign', 'a@b', 'a b@example.test', 'x' * 250 + '@e.jp', None]:
            with self.subTest(bad=bad):
                self.assertIsNone(normalize_email(bad))
        subject = email_subject(MAILBOX)
        self.assertRegex(subject, r'^email-[0-9a-f]{64}$')
        self.assertEqual(subject, email_subject(normalize_email('CLINIC@example.test')))

    def test_ses_message(self):
        class Client:
            def send_email(self, **kwargs):
                self.kwargs = kwargs
        client = Client()
        SesSender('no-reply@simy.one', client)(MAILBOX, '123456')
        self.assertEqual(client.kwargs['FromEmailAddress'], 'no-reply@simy.one')
        self.assertEqual(client.kwargs['Destination'], {'ToAddresses': [MAILBOX]})
        self.assertIn('123456', client.kwargs['Content']['Simple']['Body']['Text']['Data'])
        with self.assertRaises(ValueError):
            SesSender('', client)


class PluginEmailLoginTest(unittest.TestCase):
    def setUp(self):
        self.store, self.outbox, self.now = MemoryStore(), Outbox(), 100_000
        self.codes = EmailCodes(self.store, self.outbox, clock=lambda: self.now)
        self.google_profile = None
        self.identity = Identity(self.store, ISSUER, 'google-client', lambda claims: json.dumps(claims, sort_keys=True),
                                 self.exchange, clock=lambda: self.now, email_codes=self.codes)
        self.service = Service(self.store)
        self.app = App(self.identity, self.service, json.loads, {'keys': []}, '<!doctype html>')
        self.sleeps = []
        self.app.sleep = self.sleeps.append
        self.client = self.identity.register({'redirect_uris': [REDIRECT]})['client_id']
        self.verifier = 'v' * 43
        self.challenge = base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).rstrip(b'=').decode()
        self.invite(MAILBOX, {'example-site': ['read', 'edit']})

    def exchange(self, code, redirect, nonce):
        return dict(self.google_profile)

    def invite(self, email, sites):
        self.store.put('invitation:' + sha(email.casefold()),
                       {'email': email, 'sites': sites, 'created_at': self.now, 'expires_at': self.now + 7 * 86400})

    def call(self, method, path, query=None, form=None, origin=ISSUER, ip='198.51.100.7'):
        headers = {}
        if form is not None:
            headers = {'content-type': 'application/x-www-form-urlencoded', 'origin': origin}
        return self.app({'requestContext': {'http': {'method': method, 'sourceIp': ip}}, 'rawPath': path,
                         'rawQueryString': urlencode(query or {}), 'headers': headers,
                         'body': urlencode(form) if form is not None else ''})

    def authorize(self):
        response = self.call('GET', '/oauth/authorize', {
            'client_id': self.client, 'redirect_uri': REDIRECT, 'response_type': 'code',
            'resource': self.identity.resource, 'code_challenge': self.challenge, 'code_challenge_method': 'S256',
            'scope': 'openid email hp:read hp:write', 'state': 'client-state'})
        self.assertEqual(response['statusCode'], 302)
        location = urlsplit(response['headers']['location'])
        self.assertEqual(f'{location.scheme}://{location.netloc}{location.path}', ISSUER + '/oauth/login')
        return parse_qs(location.query)['state'][0]

    def sign_in(self, email=MAILBOX):
        state = self.authorize()
        page = self.call('GET', '/oauth/login', {'state': state})
        self.assertEqual(page['statusCode'], 200)
        self.assertIn('メールアドレスでログイン', page['body'])
        self.assertIn("form-action 'self'", page['headers']['content-security-policy'])
        sent = self.call('POST', '/oauth/login/email', form={'state': state, 'email': email})
        self.assertEqual(sent['statusCode'], 200)
        self.assertIn('確認コードを入力', sent['body'])
        return state

    def redeem(self, state, code, email=MAILBOX):
        return self.call('POST', '/oauth/login/email/verify', form={'state': state, 'email': email, 'code': code})

    def redirect_of(self, response):
        self.assertEqual(response['statusCode'], 200, response['body'])
        self.assertIn('ログインしました', response['body'])
        match = re.search(r'content="0;url=([^"]+)"', response['body'])
        return urlsplit(unescape(match.group(1)))

    def tokens(self, code):
        response = self.call('POST', '/oauth/token', form={
            'grant_type': 'authorization_code', 'code': code, 'client_id': self.client, 'redirect_uri': REDIRECT,
            'code_verifier': self.verifier, 'resource': self.identity.resource})
        return json.loads(response['body'])

    def test_invited_mailbox_signs_in_without_google_and_again_later(self):
        state = self.sign_in('  Clinic@Example.test ')
        self.assertEqual(self.outbox.sent[0][0], MAILBOX)
        redirect = self.redirect_of(self.redeem(state, self.outbox.last()))
        self.assertEqual(f'{redirect.scheme}://{redirect.netloc}{redirect.path}', REDIRECT)
        query = parse_qs(redirect.query)
        self.assertEqual(query['state'], ['client-state'])
        self.assertEqual(query['iss'], [ISSUER])
        subject = email_subject(MAILBOX)
        self.assertEqual(self.store.get('principal:' + subject)['sites'], {'example-site': ['read', 'edit']})
        self.assertEqual(self.store.get('invitation:' + sha(MAILBOX))['claimed_subject'], subject)

        result = self.tokens(query['code'][0])
        claims = json.loads(result['access_token'])
        self.assertEqual((claims['sub'], claims['email']), (subject, MAILBOX))
        self.assertEqual(self.service.principal(claims)['sites'], {'example-site': ['read', 'edit']})
        refreshed = self.call('POST', '/oauth/token', form={
            'grant_type': 'refresh_token', 'refresh_token': result['refresh_token'], 'client_id': self.client,
            'resource': self.identity.resource})
        self.assertEqual(json.loads(json.loads(refreshed['body'])['access_token'])['sub'], subject)

        # A new computer: the claimed invitation is gone, the mailbox principal remains.
        state = self.sign_in()
        self.assertEqual(len(self.outbox.sent), 2)
        query = parse_qs(self.redirect_of(self.redeem(state, self.outbox.last())).query)
        self.assertEqual(json.loads(self.tokens(query['code'][0])['access_token'])['sub'], subject)

    def test_unregistered_mailbox_gets_the_same_page_and_no_mail(self):
        state = self.sign_in('stranger@example.test')
        self.assertEqual(self.outbox.sent, [])
        response = self.redeem(state, '123456', 'stranger@example.test')
        self.assertIn('確認コードが正しくないか', unescape(response['body']))
        self.assertIsNone(self.store.get('principal:' + email_subject('stranger@example.test')))

    def test_revoked_mailbox_principal_gets_no_code(self):
        state = self.sign_in()
        self.redeem(state, self.outbox.last())
        key = 'principal:' + email_subject(MAILBOX)
        row = self.store.get(key)
        self.store.put(key, {**{k: v for k, v in row.items() if k != '_version'}, 'disabled': True}, row['_version'])
        self.sign_in()
        self.assertEqual(len(self.outbox.sent), 1)

    def test_wrong_code_reprompts_and_correct_code_still_works(self):
        state = self.sign_in()
        code = self.outbox.last()
        wrong = '000000' if code != '000000' else '111111'
        self.assertIn('確認コードが正しくないか', self.redeem(state, wrong)['body'])
        self.redirect_of(self.redeem(state, code))
        # The login state is single use.
        self.assertIn('有効期限', self.redeem(state, code)['body'])

    def test_posts_require_our_origin_and_a_live_login(self):
        state = self.authorize()
        response = self.call('POST', '/oauth/login/email', form={'state': state, 'email': MAILBOX},
                             origin='https://evil.example')
        self.assertEqual(response['statusCode'], 403)
        self.assertEqual(self.outbox.sent, [])
        response = self.call('POST', '/oauth/login/email', form={'state': 'x' * 43, 'email': MAILBOX})
        self.assertIn('有効期限', response['body'])
        self.assertEqual(self.outbox.sent, [])
        self.now += 600
        self.assertIn('有効期限', self.call('GET', '/oauth/login', {'state': state})['body'])
        bad = self.call('POST', '/oauth/login/email', form={'state': self.authorize(), 'email': 'not-an-address'})
        self.assertIn('メールアドレスを確認してください', bad['body'])

    def test_mail_failure_shows_a_retry_page(self):
        def broken(to, code):
            raise RuntimeError('ses down')
        self.codes.send = broken
        state = self.authorize()
        failed = self.call('POST', '/oauth/login/email', form={'state': state, 'email': MAILBOX})
        unknown = self.call('POST', '/oauth/login/email', form={'state': state, 'email': 'stranger@example.test'})
        # A registered address whose mail failed looks exactly like an unregistered one.
        self.assertEqual(failed['statusCode'], 200)
        self.assertEqual(failed['body'].replace(MAILBOX, 'X'), unknown['body'].replace('stranger@example.test', 'X'))
        self.assertEqual(len(self.sleeps), 2)
        self.assertTrue(all(0 < value <= 1.5 for value in self.sleeps))

    def test_google_remains_available_from_the_sign_in_page(self):
        state = self.authorize()
        response = self.call('GET', '/oauth/login/google', {'state': state})
        self.assertEqual(response['statusCode'], 302)
        google = parse_qs(urlsplit(response['headers']['location']).query)
        self.assertEqual(google['state'], [state])
        self.google_profile = {'sub': '1234567890', 'email': 'g@example.test', 'email_verified': True}
        self.invite('g@example.test', {'example-site': ['read']})
        callback = self.call('GET', '/oauth/google/callback', {'state': state, 'code': 'google-code'})
        self.assertEqual(callback['statusCode'], 302)
        self.assertEqual(self.store.get('principal:1234567890')['sites'], {'example-site': ['read']})

    def test_google_cannot_reach_mailbox_principals(self):
        state = self.authorize()
        self.google_profile = {'sub': email_subject(MAILBOX), 'email': MAILBOX, 'email_verified': True}
        with self.assertRaisesRegex(AuthError, 'invalid_google_identity'):
            self.identity.callback(state, 'google-code')

    def test_disabled_without_sender_keeps_google_only(self):
        identity = Identity(self.store, ISSUER, 'google-client', str, self.exchange, clock=lambda: self.now)
        app = App(identity, self.service, json.loads, {'keys': []}, '<!doctype html>')
        location = identity.authorize({
            'client_id': self.client, 'redirect_uri': REDIRECT, 'response_type': 'code',
            'resource': identity.resource, 'code_challenge': self.challenge, 'code_challenge_method': 'S256'})
        self.assertTrue(location.startswith('https://accounts.google.com/'))
        response = app({'requestContext': {'http': {'method': 'GET'}}, 'rawPath': '/oauth/login',
                        'rawQueryString': 'state=' + 'x' * 43, 'headers': {}, 'body': ''})
        self.assertEqual(response['statusCode'], 404)


class OnboardingEmailLoginTest(unittest.TestCase):
    def setUp(self):
        self.store, self.outbox = MemoryStore(), Outbox()
        self.site = test_provision_site.ProvisionTest().site()
        targets = {env: {'bucket': item['bucket'], 'distribution': item['distribution_id']}
                   for env, item in self.site['deployment'].items()}
        self.service = Service(self.store, publication_enabled=True, claim_targets={self.site['site_id']: targets})
        enable_domain_registration(self.store, self.site, owner_email='Owner@Example.test')
        codes = EmailCodes(self.store, self.outbox, clock=lambda: 2000)
        identity = Identity(self.store, ISSUER, 'google-client', lambda claims: 'signed',
                            lambda code, redirect, nonce: {}, email_codes=codes)
        self.billing = StripeBilling(self.store, FakeApi(), {LINK: 'basic'}, clock=lambda: 2000)
        self.onboarding = ClinicOnboarding(self.store, self.billing, self.service, identity,
                                           Fernet.generate_key().decode())
        self.app = App(identity, self.service, None, {}, '', onboarding=self.onboarding,
                       stripe_webhook=lambda payload, signature: self.billing.webhook(payload, signature, SECRET))
        self.jar = {}

    def call(self, method, path, query=None, form=None, origin=ISSUER, jar=None):
        jar = self.jar if jar is None else jar
        headers = {'cookie': '; '.join(f'{k}={v}' for k, v in jar.items())}
        if form is not None:
            headers.update({'content-type': 'application/x-www-form-urlencoded', 'origin': origin})
        response = self.app({'requestContext': {'http': {'method': method, 'sourceIp': '198.51.100.9'}},
                             'rawPath': path, 'rawQueryString': urlencode(query or {}), 'headers': headers,
                             'body': urlencode(form) if form is not None else ''})
        for line in response.get('cookies', []):
            name, _, value = line.split(';')[0].partition('=')
            if 'Max-Age=0' in line:
                jar.pop(name, None)
            else:
                jar[name] = value
        return response

    def test_paid_clinic_signs_in_by_email_and_claims_its_site(self):
        page = self.call('GET', '/start', {'session_id': SESSION})
        self.assertIn('メールアドレスでログイン', page['body'])
        self.assertIn('Googleでログイン', page['body'])
        sent = self.call('POST', '/start/email', form={'session_id': SESSION, 'email': 'Owner@Example.test'})
        self.assertEqual(sent['statusCode'], 200)
        self.assertIn('確認コードを入力', sent['body'])
        self.assertIn('Owner@Example.test に確認コードを送信しました', sent['body'].replace('owner@example.test', 'Owner@Example.test'))
        self.assertIn('Secure', sent['cookies'][0])
        self.assertEqual(self.outbox.sent[0][0], 'owner@example.test')

        # Another browser cannot redeem the code sent to this one.
        other = {}
        stolen = self.call('POST', '/start/email/verify', form={
            'session_id': SESSION, 'email': 'owner@example.test', 'code': self.outbox.last()}, jar=other)
        self.assertEqual(stolen['statusCode'], 400)
        self.assertNotIn('hp_start', other)

        done = self.call('POST', '/start/email/verify', form={
            'session_id': SESSION, 'email': 'owner@example.test', 'code': self.outbox.last()})
        self.assertEqual(done['statusCode'], 302)
        self.assertIn('hp_start', self.jar)
        self.assertNotIn('hp_start_email', self.jar)
        subject = email_subject('owner@example.test')
        self.assertEqual(self.store.get('stripe-subscription:' + SUB)['subject'], subject)

        self.call('POST', '/start/site', form={'session_id': SESSION, 'site_url': self.site['prod_url'], 'auth_code': ''})
        self.assertEqual(self.store.get('clinic-intake:' + SUB)['status'], 'claimed')
        claims = {'sub': subject, 'scope': 'hp:read hp:write'}
        self.assertEqual(self.service.list_sites(claims)[0]['roles'], ['read', 'edit', 'publish'])
        self.assertIn('owner@example.test で接続', self.call('GET', '/start', {'session_id': SESSION})['body'])

    def test_email_post_needs_our_origin_and_a_paid_session(self):
        response = self.call('POST', '/start/email', form={'session_id': SESSION, 'email': MAILBOX},
                             origin='https://evil.example')
        self.assertEqual(response['statusCode'], 403)
        response = self.call('POST', '/start/email', form={'session_id': 'cs_test_' + 'X' * 40, 'email': MAILBOX})
        self.assertEqual(response['statusCode'], 403)
        self.assertEqual(self.outbox.sent, [])
        response = self.call('POST', '/start/email', form={'session_id': SESSION, 'email': 'nope'})
        self.assertIn('メールアドレスを確認してください', response['body'])

    def test_purchase_stays_bound_to_the_first_account(self):
        self.call('POST', '/start/email', form={'session_id': SESSION, 'email': MAILBOX})
        self.call('POST', '/start/email/verify', form={'session_id': SESSION, 'email': MAILBOX, 'code': self.outbox.last()})
        self.jar = {}
        self.call('POST', '/start/email', form={'session_id': SESSION, 'email': 'other@example.test'})
        response = self.call('POST', '/start/email/verify', form={
            'session_id': SESSION, 'email': 'other@example.test', 'code': self.outbox.last()})
        self.assertEqual(response['statusCode'], 403)
        self.assertIn(MAILBOX, response['body'])
        self.assertNotIn('hp_start', self.jar)


if __name__ == '__main__':
    unittest.main()
