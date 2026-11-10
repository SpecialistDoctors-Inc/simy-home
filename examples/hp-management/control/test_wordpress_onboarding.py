import json
import unittest

from cryptography.fernet import Fernet

from mcp_adapter import App
from service import Service
from store import MemoryStore
import test_wordpress_provider
from wordpress_onboarding import WordPressOnboarding


ORG = 'f4dbf297-4526-41f5-bd7b-2ba20b4736d9'
SUBJECT = 'google-subject'


class WordPressOnboardingTest(unittest.TestCase):
    def test_oauth_completion_binds_mac_listing_to_the_correct_account_and_entitlement(self):
        fixture = test_wordpress_provider.WordPressProviderTest()
        fixture.setUp()
        store = MemoryStore()
        paid = False
        service = Service(store, license_resolver=lambda org, sub: paid and (org, sub) == (ORG, SUBJECT))
        connection = WordPressOnboarding(store, {'credential_key': Fernet.generate_key().decode()},
                                         provider=fixture.provider)
        app = App(None, service, lambda _: {'sub': SUBJECT, 'scope': 'hp:read'}, None, None,
                  preflight_token=lambda: 's' * 32, wordpress=lambda: connection)

        def post(path, body, token='s' * 32):
            reply = app({'rawPath': path, 'httpMethod': 'POST',
                         'headers': {'authorization': 'Bearer ' + token, 'content-type': 'application/json'},
                         'body': json.dumps(body)})
            return reply['statusCode'], json.loads(reply['body'])

        actor = {'org_id': ORG, 'google_subject': SUBJECT}
        start = {**actor, 'action': 'wordpress_start', 'site_url': 'https://clinic.wordpress.com'}
        self.assertEqual(post('/internal/site/claim', start, token='wrong')[0], 401)
        status, started = post('/internal/site/claim', start)
        self.assertEqual(status, 200)
        self.assertEqual(started['status'], 'authorization_required')
        finish = {**actor, 'action': 'wordpress_finish', 'state': started['state'], 'code': 'fixture'}
        self.assertEqual(post('/internal/site/claim', {**finish, 'google_subject': 'other-subject'})[0], 409)
        self.assertEqual(fixture.calls, [])
        self.assertEqual(post('/internal/site/claim', finish), (200, {'status': 'wordpress_connected'}))
        self.assertEqual(post('/internal/site/claim', finish)[0], 409)
        self.assertNotIn('fake-wordpress-token', json.dumps(store.rows))
        self.assertEqual(service.license_preflight(ORG, SUBJECT), {'ready': False, 'status': 'site_setup_required'})

        def mac_sites():
            status, result = post('/mcp', {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                                'params': {'name': 'hp_list_sites', 'arguments': {}}}, token='mac-test')
            self.assertEqual(status, 200)
            return result['result']['structuredContent']['sites']

        self.assertEqual(mac_sites(), [])
        paid = True
        self.assertEqual(mac_sites(), [{'site_id': 'wordpress-123', 'name': 'clinic.wordpress.com',
            'roles': ['read'], 'preview_url': None, 'production_url': 'https://clinic.wordpress.com',
            'deployments': {
                'dev': {'updated_at': None, 'version': None, 'url': None},
                'production': {'updated_at': None, 'version': None, 'url': 'https://clinic.wordpress.com'},
            }}])
