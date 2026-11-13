import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from local_bridge import SITE_ID, build

ORG = 'a4c654e6-89d7-423c-87d8-cc3d26bf496a'
SUBJECT = '123456789012345678901'
ENTITLEMENT_TOKEN = 'entitlement_fixture_token_example_0001'
PREFLIGHT_TOKEN = 'preflight_fixture_token_example_000001'


class LocalBridgeTest(unittest.TestCase):
    def setUp(self):
        self.allowed = False
        self.seen = []
        test = self

        class Entitlement(BaseHTTPRequestHandler):
            def do_POST(self):
                test.seen.append((self.headers['authorization'],
                                  json.loads(self.rfile.read(int(self.headers['content-length'])))))
                payload = json.dumps({'allowed': test.allowed}).encode()
                self.send_response(200)
                self.send_header('content-length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Entitlement)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        endpoint = f'http://127.0.0.1:{self.server.server_port}/functions/v1/hp-control-entitlement'
        self.app, self.access_token = build(endpoint, ENTITLEMENT_TOKEN, PREFLIGHT_TOKEN, ORG, SUBJECT, 8787)

    def call(self, path, body, token):
        result = self.app({'rawPath': path, 'requestContext': {'http': {'method': 'POST'}}, 'body': json.dumps(body),
                           'headers': {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}})
        return result['statusCode'], json.loads(result['body'])

    def list_sites(self):
        status, body = self.call('/mcp', {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                                          'params': {'name': 'hp_list_sites', 'arguments': {}}}, self.access_token)
        self.assertEqual(status, 200)
        return [site['site_id'] for site in body['result']['structuredContent']['sites']]

    def test_prepared_site_becomes_usable_only_after_simy_entitlement(self):
        self.assertEqual(self.call('/internal/license/preflight', {'org_id': ORG, 'google_subject': SUBJECT},
                                   PREFLIGHT_TOKEN), (200, {'ready': True}))
        self.assertEqual(self.list_sites(), [])
        self.allowed = True
        self.assertEqual(self.list_sites(), [SITE_ID])
        self.assertEqual({(auth, json.dumps(body, sort_keys=True)) for auth, body in self.seen},
                         {('Bearer ' + ENTITLEMENT_TOKEN,
                           json.dumps({'org_id': ORG, 'google_subject': SUBJECT}, sort_keys=True))})

    def test_preflight_rejects_a_different_credential(self):
        status, _ = self.call('/internal/license/preflight', {'org_id': ORG, 'google_subject': SUBJECT},
                              'x' * 40)
        self.assertEqual(status, 401)
        self.assertEqual(self.seen, [])

    def test_rejects_invalid_identity_inputs(self):
        with self.assertRaises(SystemExit):
            build('http://127.0.0.1:1/functions/v1/hp-control-entitlement', ENTITLEMENT_TOKEN, PREFLIGHT_TOKEN,
                  'not-a-uuid', SUBJECT, 8787)


if __name__ == '__main__':
    unittest.main()


class ClinicBridgeTest(unittest.TestCase):
    def test_clinic_mode_requires_test_keys_and_grants_the_prepared_site_after_payment(self):
        from urllib.parse import parse_qs, urlencode, urlsplit
        from local_bridge import build_clinic, dev_google_page
        from test_clinic_onboarding import FakeApi
        from test_stripe_billing import LINK, SECRET, SESSION
        with self.assertRaises(SystemExit):
            build_clinic('sk_live_' + 'x' * 24, SECRET, {LINK: 'basic'}, SUBJECT, 'o@example.test',
                         'sakura-clinic.example', 8787)
        app, token = build_clinic('sk_test_' + 'x' * 24, SECRET, {LINK: 'basic'}, SUBJECT, 'o@example.test',
                                  'sakura-clinic.example', 8787, stripe_api=FakeApi())
        cookie = {}

        def call(method, path, query=None, form=None):
            headers = {'cookie': '; '.join(cookie.values()), 'origin': 'http://127.0.0.1:8787'}
            if form is not None:
                headers['content-type'] = 'application/x-www-form-urlencoded'
            result = app({'rawPath': path, 'rawQueryString': urlencode(query or {}), 'headers': headers,
                          'body': urlencode(form or {}), 'requestContext': {'http': {'method': method}}})
            for line in result.get('cookies', []):
                name = line.split('=', 1)[0]
                if 'Max-Age=0' in line:
                    cookie.pop(name, None)
                else:
                    cookie[name] = line.split(';')[0]
            return result

        google = call('GET', '/start/google', {'session_id': SESSION})['headers']['location']
        self.assertTrue(google.startswith('http://127.0.0.1:8787/dev/google?'))
        state = parse_qs(urlsplit(google).query)['state'][0]
        self.assertIn('ローカル検証用', dev_google_page({'state': state}, 'o@example.test')['body'])
        call('GET', '/oauth/google/callback', {'state': state, 'code': 'local-google-code'})
        call('POST', '/start/site', form={'session_id': SESSION, 'site_url': 'https://sakura-clinic.example',
                                          'auth_code': 'Ab3$xY9!kQ'})
        call('POST', '/start/verify', form={'session_id': SESSION})
        self.assertIn('HP編集を始める', call('GET', '/start', {'session_id': SESSION})['body'])
        result = app({'rawPath': '/mcp', 'requestContext': {'http': {'method': 'POST'}},
                      'headers': {'Authorization': 'Bearer ' + token(), 'Content-Type': 'application/json'},
                      'body': json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                                          'params': {'name': 'hp_list_sites', 'arguments': {}}})})
        sites = json.loads(result['body'])['result']['structuredContent']['sites']
        self.assertEqual([(s['site_id'], s['roles']) for s in sites], [(SITE_ID, ['read', 'edit', 'publish'])])
