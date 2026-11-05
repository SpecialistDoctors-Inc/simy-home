"""Pure Lambda route tests: no network, provider credentials, or real tokens."""
import base64
import hashlib
import json
import unittest
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import uuid4

from identity import Identity
from mcp_adapter import App, MAX_BODY, UI_URI
from service import Service, Rejected
from store import MemoryStore


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.now = 10000
        self.claims = {'sub': 'sample-subject', 'email': 'member@example.invalid', 'email_verified': True, 'scope': 'hp:read hp:write'}
        self.store.put('principal:sample-subject', {'sites': {'sample-site': ['read', 'edit', 'publish']}})
        self.preview_id = str(uuid4())
        self.store.put('site:sample-site', {'name': 'Sample Site', 'config_version': 1, 'initial_main_commit': 'a' * 40, 'dev_url': 'https://preview.example.invalid', 'prod_url': 'https://public.example.invalid', 'current_preview': self.preview_id})
        self.store.put('preview:' + self.preview_id, {'site_id': 'sample-site', 'status': 'verified', 'source_commit': 'a' * 40, 'artifact_sha256': 'b' * 64, 'url': 'https://preview.example.invalid/current', 'summary': 'Opening hours'})
        self.identity = Identity(self.store, 'https://control.example.invalid', 'fake-google-client', lambda claims: 'signed:' + json.dumps(claims), lambda *args: dict(self.claims), clock=lambda: self.now)
        self.service = Service(self.store, clock=lambda: self.now, publication_enabled=True)
        def verify(token):
            if token != 'fake-access':
                raise ValueError('token secret must never escape')
            return dict(self.claims)
        self.app = App(self.identity, self.service, verify, {'keys': [{'kty': 'RSA', 'kid': 'example-public-key'}]}, '<!doctype html><title>Confirmation</title>')

    def http(self, path, method='GET', body='', auth=False, content_type='application/json', query=None, encoded=False):
        headers = {'content-type': content_type}
        if auth:
            headers['authorization'] = 'Bearer fake-access'
        event = {'rawPath': path, 'requestContext': {'http': {'method': method}}, 'headers': headers, 'body': body, 'rawQueryString': urlencode(query or {}), 'isBase64Encoded': encoded}
        response = self.app(event)
        value = json.loads(response['body']) if response['body'] else None
        return response, value

    def rpc(self, method, params=None, auth=True):
        return self.http('/mcp', 'POST', json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}}), auth=auth)

    def tool(self, name, arguments=None):
        return self.rpc('tools/call', {'name': name, 'arguments': arguments or {}})

    def test_health_metadata_and_public_jwks(self):
        response, value = self.http('/health')
        self.assertEqual((response['statusCode'], value), (200, {'status': 'ok'}))
        for path in ['/.well-known/oauth-authorization-server', '/.well-known/openid-configuration']:
            response, value = self.http(path)
            self.assertEqual(response['statusCode'], 200)
            self.assertEqual(value['issuer'], self.identity.issuer)
            self.assertEqual(value['code_challenge_methods_supported'], ['S256'])
        for path in ['/.well-known/oauth-protected-resource', '/.well-known/oauth-protected-resource/mcp']:
            response, value = self.http(path)
            self.assertEqual(value['resource'], self.identity.resource)
        response, value = self.http('/oauth/jwks')
        self.assertEqual(value['keys'][0]['kid'], 'example-public-key')

    def test_every_mcp_operation_including_resource_and_initialize_requires_auth(self):
        for method, params in [('initialize', {}), ('ping', {}), ('tools/list', {}), ('tools/call', {'name': 'hp_profile'}), ('resources/list', {}), ('resources/read', {'uri': UI_URI})]:
            with self.subTest(method=method):
                response, value = self.rpc(method, params, auth=False)
                self.assertEqual(response['statusCode'], 401)
                self.assertEqual(value, {'error': 'invalid_token'})
                self.assertIn('/.well-known/oauth-protected-resource/mcp', response['headers']['www-authenticate'])
        response, value = self.http('/oauth/userinfo')
        self.assertEqual(response['statusCode'], 401)
        response, value = self.http('/mcp')
        self.assertEqual(response['statusCode'], 401)

    def test_profile_claims_and_tool_annotations_do_not_expose_internals(self):
        response, value = self.tool('hp_profile')
        self.assertEqual(value['result']['structuredContent']['subject'], self.claims['sub'])
        self.assertNotIn('_version', json.dumps(value))
        response, value = self.rpc('tools/list')
        tools = {tool['name']: tool for tool in value['result']['tools']}
        self.assertEqual(len(tools), 9)
        self.assertTrue(tools['hp_profile']['annotations']['readOnlyHint'])
        self.assertFalse(tools['hp_save_draft']['annotations']['readOnlyHint'])
        self.assertTrue(tools['hp_confirm_publish']['annotations']['destructiveHint'])
        self.assertEqual(tools['hp_confirm_publish']['_meta']['ui']['visibility'], ['app'])
        self.assertEqual(tools['hp_prepare_publish']['_meta']['ui']['resourceUri'], UI_URI)
        self.assertEqual(tools['hp_profile']['securitySchemes'][0]['scopes'], ['hp:read'])

    def test_initialize_notification_ping_and_resources(self):
        response, value = self.rpc('initialize', {'protocolVersion': '2025-11-25', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}})
        self.assertEqual(value['result']['protocolVersion'], '2025-11-25')
        response, value = self.rpc('ping')
        self.assertEqual(value['result'], {})
        response, value = self.http('/mcp', 'POST', json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'}), auth=True)
        self.assertEqual(response['statusCode'], 202)
        self.assertIsNone(value)
        response, value = self.rpc('resources/list')
        self.assertEqual(value['result']['resources'][0]['uri'], UI_URI)
        response, value = self.rpc('resources/read', {'uri': UI_URI})
        content = value['result']['contents'][0]
        self.assertEqual(content['mimeType'], 'text/html;profile=mcp-app')
        self.assertIn('<title>Confirmation</title>', content['text'])
        self.assertEqual(content['_meta']['ui']['csp']['resourceDomains'], [])

    def test_queue_receipt_and_cancellation_are_public_projection(self):
        arguments = {'operation_id': str(uuid4()), 'site_id': 'sample-site'}
        response, value = self.tool('hp_open_workspace', arguments)
        receipt = value['result']['structuredContent']
        self.assertEqual(receipt['status'], 'queued')
        self.assertNotIn('input', receipt)
        self.assertNotIn('member_version', receipt)
        response, value = self.tool('hp_get_operation', {'operation_id': arguments['operation_id']})
        self.assertEqual(value['result']['structuredContent'], receipt)
        response, value = self.tool('hp_cancel_operation', {'operation_id': arguments['operation_id']})
        self.assertEqual(value['result']['structuredContent']['status'], 'cancelled')

    def test_prepare_nonce_is_private_and_model_call_without_nonce_is_denied(self):
        response, value = self.tool('hp_prepare_publish', {'site_id': 'sample-site', 'preview_id': self.preview_id})
        result = value['result']
        nonce = result['_meta']['confirmation_nonce']
        approval_id = result['structuredContent']['approval_id']
        self.assertNotIn(nonce, json.dumps(result['content']))
        self.assertNotIn(nonce, json.dumps(result['structuredContent']))
        self.assertEqual(result['_meta']['ui']['resourceUri'], UI_URI)
        response, value = self.tool('hp_confirm_publish', {'approval_id': approval_id})
        self.assertEqual(response['statusCode'], 400)
        response, value = self.tool('hp_confirm_publish', {'approval_id': approval_id, 'confirmation_nonce': 'guessed'})
        self.assertTrue(value['result']['isError'])
        self.assertEqual(value['result']['structuredContent']['error'], 'confirmation_invalid')
        self.assertFalse(any(key.startswith('operation:') for key in self.store.rows))
        # The app channel supplies the private nonce. This is NOT a forged-client
        # protection test: an authorized raw client still acts as the same user.
        response, value = self.tool('hp_confirm_publish', {'approval_id': approval_id, 'confirmation_nonce': nonce})
        self.assertEqual(value['result']['structuredContent']['status'], 'queued')
        self.assertNotIn(nonce, json.dumps(value))

    def test_publication_disabled_remains_fail_closed(self):
        self.service.publication_enabled = False
        response, value = self.tool('hp_prepare_publish', {'site_id': 'sample-site', 'preview_id': self.preview_id})
        self.assertTrue(value['result']['isError'])
        self.assertEqual(value['result']['structuredContent']['error'], 'publication_not_enabled')

    def test_strict_bounded_body_duplicate_keys_and_form_values(self):
        for body in ['[]', '{bad', '{"jsonrpc":"2.0","jsonrpc":"2.0"}', '{"jsonrpc":"2.0","id":1,"method":"ping","params":{"x":NaN}}']:
            with self.subTest(body=body):
                response, value = self.http('/mcp', 'POST', body, auth=True)
                self.assertEqual(response['statusCode'], 400)
                self.assertEqual(value, {'error': 'invalid_request'})
        response, value = self.http('/mcp', 'POST', 'x' * (MAX_BODY + 1), auth=True)
        self.assertEqual(response['statusCode'], 413)
        body = base64.b64encode(b'x' * (MAX_BODY + 1)).decode()
        response, value = self.http('/mcp', 'POST', body, auth=True, encoded=True)
        self.assertEqual(response['statusCode'], 413)
        response, value = self.http('/oauth/token', 'POST', 'grant_type=a&grant_type=b', content_type='application/x-www-form-urlencoded')
        self.assertEqual(response['statusCode'], 400)
        response, value = self.http('/mcp', 'POST', '%%%%', auth=True, encoded=True)
        self.assertEqual(response['statusCode'], 400)

    def test_malformed_tool_name_and_registration_are_rejected_as_inputs(self):
        response, value = self.rpc('tools/call', {'name': [], 'arguments': {}})
        self.assertEqual(response['statusCode'], 400)
        for body in [{'redirect_uris': 1}, {'redirect_uris': ['http://localhost:invalid/callback']}, {'redirect_uris': ['http://127.0.0.1:43123/callback\r\nX-Example: injected']}]:
            with self.subTest(body=body):
                response, value = self.http('/oauth/register', 'POST', json.dumps(body))
                self.assertEqual(response['statusCode'], 400)
                self.assertNotIn('Traceback', json.dumps(response))

    def test_fixed_errors_never_expose_exception_or_token(self):
        self.app.verify = lambda token: (_ for _ in ()).throw(RuntimeError('secret-provider-token-example'))
        response, value = self.rpc('ping')
        self.assertEqual(value, {'error': 'invalid_token'})
        self.assertNotIn('secret-provider-token-example', json.dumps(response))
        self.app.verify = lambda token: self.claims
        self.service.profile = lambda claims: (_ for _ in ()).throw(RuntimeError('private table/stack/provider-token'))
        response, value = self.tool('hp_profile')
        self.assertEqual(value, {'error': 'internal_error'})
        self.service.profile = lambda claims: (_ for _ in ()).throw(Rejected('untrusted database text'))
        response, value = self.tool('hp_profile')
        self.assertEqual(value['result']['structuredContent'], {'error': 'request_rejected'})

    def test_revoked_membership_invalidates_all_mcp_reads(self):
        row = self.store.get('principal:sample-subject')
        self.store.put('principal:sample-subject', dict(row, disabled=True), row['_version'])
        response, value = self.rpc('tools/list')
        self.assertEqual(response['statusCode'], 401)

    def test_wrong_tool_inputs_do_not_allow_subject_or_config_override(self):
        response, value = self.tool('hp_profile', {'sub': 'other-subject'})
        self.assertEqual(response['statusCode'], 400)
        response, value = self.tool('hp_open_workspace', {'operation_id': str(uuid4()), 'site_id': 'sample-site', 'repository': 'other-repository'})
        self.assertEqual(response['statusCode'], 400)
        self.assertFalse(any(key.startswith('operation:') for key in self.store.rows))
        response, value = self.rpc('unknown/method')
        self.assertEqual(value['error']['code'], -32601)

    def test_oauth_registration_authorization_callback_token_and_userinfo(self):
        redirect = 'http://127.0.0.1:43123/callback'
        response, registered = self.http('/oauth/register', 'POST', json.dumps({'redirect_uris': [redirect]}))
        self.assertEqual(response['statusCode'], 201)
        verifier = 'v' * 43
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        response, value = self.http('/oauth/authorize', query={'client_id': registered['client_id'], 'redirect_uri': redirect, 'response_type': 'code', 'resource': self.identity.resource, 'code_challenge': challenge, 'code_challenge_method': 'S256', 'state': 'client-state'})
        self.assertEqual(response['statusCode'], 302)
        login = parse_qs(urlsplit(response['headers']['location']).query)
        response, value = self.http('/oauth/google/callback', query={'state': login['state'][0], 'code': 'fake-google-code'})
        self.assertEqual(response['statusCode'], 302)
        callback = parse_qs(urlsplit(response['headers']['location']).query)
        self.assertEqual(callback['state'], ['client-state'])
        form = urlencode({'grant_type': 'authorization_code', 'client_id': registered['client_id'], 'redirect_uri': redirect, 'code': callback['code'][0], 'code_verifier': verifier, 'resource': self.identity.resource})
        response, value = self.http('/oauth/token', 'POST', form, content_type='application/x-www-form-urlencoded')
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(value['token_type'], 'Bearer')
        self.assertIn('access_token', value)
        self.assertEqual(response['headers']['cache-control'], 'no-store')
        response, value = self.http('/oauth/userinfo', auth=True)
        self.assertEqual(value['sub'], self.claims['sub'])
        self.assertNotIn('scope', value)

    def test_google_callback_accepts_known_issuer_and_rejects_issuer_substitution(self):
        calls = []
        def callback(state, code):
            calls.append((state, code))
            return 'http://127.0.0.1:43123/callback?code=hp-code'
        self.identity.callback = callback
        query = {'state': 'state', 'code': 'google-code', 'iss': 'https://accounts.google.com',
                 'scope': 'openid email', 'authuser': '0', 'hd': 'example.invalid', 'prompt': 'none'}
        response, _ = self.http('/oauth/google/callback', query=query)
        self.assertEqual(response['statusCode'], 302)
        self.assertEqual(calls, [('state', 'google-code')])
        for issuer in ('https://attacker.invalid', 'https://accounts.google.com.attacker.invalid',
                       'http://accounts.google.com', ''):
            with self.subTest(issuer=issuer):
                response, value = self.http('/oauth/google/callback', query={**query, 'iss': issuer})
                self.assertEqual((response['statusCode'], value), (400, {'error': 'invalid_request'}))
        self.assertEqual(calls, [('state', 'google-code')])


if __name__ == '__main__':
    unittest.main()
