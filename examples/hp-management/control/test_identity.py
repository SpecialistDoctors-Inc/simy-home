"""OAuth issuer behavior with fake Google verification and no provider/network access."""
import base64
import hashlib
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from identity import Identity, AuthError, sha
from store import MemoryStore, Conflict


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.now = 10000
        self.signed = []
        self.exchanges = []
        self.profile = {'sub': 'google-subject-example', 'email': 'member@example.invalid', 'email_verified': True}
        self.exchange_nonce = None
        self.issuer = Identity(self.store, 'https://editor.example.invalid', 'google-client-example', self.sign, self.exchange, clock=lambda: self.now)
        self.redirect = 'http://127.0.0.1:43123/callback'
        self.client = self.issuer.register({'redirect_uris': [self.redirect]})['client_id']
        self.verifier = 'v' * 43
        self.challenge = base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).rstrip(b'=').decode()
        self.member()

    def member(self, **updates):
        key = 'principal:' + self.profile['sub']
        old = self.store.get(key)
        value = {'sites': ['example-site'], 'disabled': False}
        value.update(updates)
        self.store.put(key, value, old['_version'] if old else None)

    def sign(self, claims):
        self.signed.append(dict(claims))
        return json.dumps(claims, sort_keys=True)

    def exchange(self, code, redirect, nonce):
        self.exchanges.append((code, redirect, nonce))
        if self.exchange_nonce is not None and nonce != self.exchange_nonce:
            raise AuthError('invalid_google_nonce')
        return dict(self.profile)

    def login(self, **overrides):
        query = dict(client_id=self.client, redirect_uri=self.redirect, response_type='code', resource=self.issuer.resource, code_challenge=self.challenge, code_challenge_method='S256', scope='openid email hp:read hp:write', state='client-state', nonce='client-oidc-nonce')
        query.update(overrides)
        url = self.issuer.authorize(query)
        values = parse_qs(urlsplit(url).query)
        return values['state'][0], values['nonce'][0]

    def code(self, **overrides):
        state, nonce = self.login(**overrides)
        self.exchange_nonce = nonce
        url = self.issuer.callback(state, 'fake-google-code')
        query = parse_qs(urlsplit(url).query)
        self.assertEqual(query['state'], ['client-state'])
        self.assertEqual(query['iss'], [self.issuer.issuer])
        return query['code'][0]

    def form(self, code, **overrides):
        value = dict(grant_type='authorization_code', code=code, client_id=self.client, redirect_uri=self.redirect, code_verifier=self.verifier, resource=self.issuer.resource)
        value.update(overrides)
        return value

    def test_operator_invitation_binds_verified_mailbox_once(self):
        self.store.rows.pop('principal:' + self.profile['sub'])
        key = 'invitation:' + sha(self.profile['email'].casefold())
        roles = {'example-site': ['read', 'edit']}
        self.store.put(key, {'email': self.profile['email'], 'sites': roles, 'expires_at': self.now + 600})
        code = self.code()
        self.assertEqual(self.store.get('principal:' + self.profile['sub'])['sites'], roles)
        self.assertEqual(self.store.get(key)['claimed_subject'], self.profile['sub'])
        self.issuer.token(self.form(code))
        self.profile = {**self.profile, 'sub': 'different-subject-same-mailbox'}
        with self.assertRaises(AuthError):
            self.code()

    def test_expired_invitation_and_revoked_principal_cannot_reenroll(self):
        key = 'invitation:' + sha(self.profile['email'].casefold())
        self.store.put(key, {'email': self.profile['email'], 'sites': {'example-site': ['publish']}, 'expires_at': self.now + 600})
        self.member(disabled=True)
        with self.assertRaises(AuthError):
            self.code()
        self.store.rows.pop('principal:' + self.profile['sub'])
        old = self.store.get(key)
        self.store.put(key, {**old, 'expires_at': self.now}, old['_version'])
        with self.assertRaises(AuthError):
            self.code()
        self.assertIsNone(self.store.get('principal:' + self.profile['sub']))

    def test_pkce_required_and_wrong_verifier_does_not_consume_code(self):
        for overrides in [dict(code_challenge_method='plain'), dict(code_challenge='short')]:
            with self.subTest(overrides=overrides), self.assertRaises(AuthError):
                self.login(**overrides)
        code = self.code()
        for verifier in ['short', 'z' * 43, '!' * 43]:
            with self.subTest(verifier=verifier), self.assertRaises(AuthError):
                self.issuer.token(self.form(code, code_verifier=verifier))
        token = self.issuer.token(self.form(code))
        self.assertEqual(json.loads(token['access_token'])['sub'], self.profile['sub'])

    def test_redirect_allowlist_and_exact_registered_binding(self):
        for redirect in ['https://attacker.example.invalid/callback', 'https://chatgpt.com.evil.invalid/connector_platform_oauth_redirect', 'https://chatgpt.com/other', 'https://user@chatgpt.com/connector_platform_oauth_redirect', 'http://localhost/callback', self.redirect + '#fragment']:
            with self.subTest(redirect=redirect), self.assertRaises(AuthError):
                self.issuer.register({'redirect_uris': [redirect]})
        for redirect in ['https://chatgpt.com/connector_platform_oauth_redirect', 'https://chatgpt.com/connector/oauth/example', 'http://[::1]:43123/callback']:
            with self.subTest(redirect=redirect):
                self.assertTrue(self.issuer.register({'redirect_uris': [redirect]})['client_id'])
        with self.assertRaises(AuthError):
            self.login(redirect_uri='http://127.0.0.1:43124/callback')
        code = self.code()
        with self.assertRaises(AuthError):
            self.issuer.token(self.form(code, redirect_uri=self.redirect + '?different'))

    def test_unknown_state_and_consumed_state_cannot_issue_another_code(self):
        with self.assertRaises(AuthError):
            self.issuer.callback('unknown-state', 'fake-google-code')
        self.assertEqual(self.exchanges, [])
        state, nonce = self.login()
        self.exchange_nonce = nonce
        self.issuer.callback(state, 'fake-google-code')
        with self.assertRaises(AuthError):
            self.issuer.callback(state, 'fake-google-code')
        self.assertEqual(len(self.exchanges), 1)

    def test_browser_input_cannot_choose_subject(self):
        code = self.code(subject='attacker-subject', sub='attacker-subject', email='attacker@example.invalid')
        token = self.issuer.token(self.form(code, subject='attacker-subject', sub='attacker-subject'))
        claims = json.loads(token['access_token'])
        self.assertEqual(claims['sub'], self.profile['sub'])
        self.assertEqual(claims['email'], self.profile['email'])
        self.assertEqual(claims['aud'], self.issuer.resource)

    def test_google_nonce_passed_to_verifier_and_bad_nonce_leaves_login_unconsumed(self):
        state, nonce = self.login()
        self.exchange_nonce = 'different-google-nonce'
        with self.assertRaisesRegex(AuthError, 'nonce'):
            self.issuer.callback(state, 'fake-google-code')
        self.assertIsNotNone(self.store.get('login:' + sha(state)))
        self.exchange_nonce = nonce
        self.issuer.callback(state, 'fake-google-code')
        self.assertEqual(self.exchanges[-1], ('fake-google-code', self.issuer.issuer + '/oauth/google/callback', nonce))

    def test_oidc_id_token_preserves_client_nonce(self):
        code = self.code()
        token = self.issuer.token(self.form(code))
        claims = json.loads(token['id_token'])
        self.assertEqual(claims['aud'], self.client)
        self.assertEqual(claims['nonce'], 'client-oidc-nonce')

    def test_callback_requires_verified_invited_member(self):
        for profile_update, member_update in [({'email_verified': False}, {}), ({}, {'disabled': True}), ({}, {'sites': []})]:
            with self.subTest(profile_update=profile_update, member_update=member_update):
                self.member(**member_update)
                original = dict(self.profile)
                self.profile.update(profile_update)
                state, nonce = self.login()
                self.exchange_nonce = nonce
                with self.assertRaises(AuthError):
                    self.issuer.callback(state, 'fake-google-code')
                self.profile = original
        self.member()
        state, nonce = self.login()
        self.exchange_nonce = nonce
        del self.store.rows['principal:' + self.profile['sub']]
        with self.assertRaises(AuthError):
            self.issuer.callback(state, 'fake-google-code')

    def test_revoked_or_unbound_member_cannot_redeem_or_refresh(self):
        for update in [dict(disabled=True), dict(sites=[])]:
            with self.subTest(update=update, grant='code'):
                self.member()
                code = self.code()
                self.member(**update)
                with self.assertRaises(AuthError):
                    self.issuer.token(self.form(code))
            with self.subTest(update=update, grant='refresh'):
                self.member()
                token = self.issuer.token(self.form(self.code()))
                self.member(**update)
                with self.assertRaises(AuthError):
                    self.issuer.token(dict(grant_type='refresh_token', client_id=self.client, resource=self.issuer.resource, refresh_token=token['refresh_token']))

    def test_cross_client_and_cross_resource_rejected(self):
        other = self.issuer.register({'redirect_uris': [self.redirect]})['client_id']
        with self.assertRaises(AuthError):
            self.login(resource='https://other.example.invalid/mcp')
        code = self.code()
        for changes in [dict(client_id=other), dict(resource='https://other.example.invalid/mcp')]:
            with self.subTest(changes=changes), self.assertRaises(AuthError):
                self.issuer.token(self.form(code, **changes))
        token = self.issuer.token(self.form(code))
        form = dict(grant_type='refresh_token', client_id=self.client, resource=self.issuer.resource, refresh_token=token['refresh_token'])
        for changes in [dict(client_id=other), dict(resource='https://other.example.invalid/mcp')]:
            with self.subTest(changes=changes), self.assertRaises(AuthError):
                self.issuer.token(dict(form, **changes))
        self.issuer.token(form)

    def test_login_code_refresh_and_access_expiry(self):
        state, nonce = self.login()
        self.now += 600
        with self.assertRaises(AuthError):
            self.issuer.callback(state, 'fake-google-code')
        code = self.code()
        self.now += 120
        with self.assertRaises(AuthError):
            self.issuer.token(self.form(code))
        token = self.issuer.token(self.form(self.code()))
        claims = json.loads(token['access_token'])
        self.assertEqual(claims['iat'], self.now)
        self.assertEqual(claims['exp'], self.now + 600)
        self.now += 30 * 86400
        with self.assertRaises(AuthError):
            self.issuer.token(dict(grant_type='refresh_token', client_id=self.client, resource=self.issuer.resource, refresh_token=token['refresh_token']))

    def test_code_and_refresh_replay_do_not_sign_more_tokens(self):
        code = self.code()
        token = self.issuer.token(self.form(code))
        count = len(self.signed)
        with self.assertRaises(AuthError):
            self.issuer.token(self.form(code))
        self.assertEqual(len(self.signed), count)
        form = dict(grant_type='refresh_token', client_id=self.client, resource=self.issuer.resource, refresh_token=token['refresh_token'])
        refreshed = self.issuer.token(form)
        count = len(self.signed)
        self.assertNotEqual(refreshed['refresh_token'], token['refresh_token'])
        with self.assertRaises(AuthError):
            self.issuer.token(form)
        self.assertEqual(len(self.signed), count)

    def test_concurrent_stale_code_redemption_has_one_winner(self):
        code = self.code()
        original = self.store.transact
        winner = []
        replaying = False
        def race(writes):
            nonlocal replaying
            if not replaying and any(write.key == 'code:' + sha(code) for write in writes):
                replaying = True
                winner.append(self.issuer.token(self.form(code)))
            original(writes)
        self.store.transact = race
        with self.assertRaises(Conflict):
            self.issuer.token(self.form(code))
        self.assertEqual(len(winner), 1)
        self.assertEqual(len(self.signed), 2)  # One access token and one ID token.


if __name__ == '__main__':
    unittest.main()
