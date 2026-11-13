"""HP license boundaries without provider credentials or deployed resources."""
import io
import json
import unittest
from unittest.mock import Mock, patch

from licensing import EntitlementResolver, LicenseUnavailable
from mcp_adapter import App, TOOL_FIELDS
from service import Rejected, Service
from store import MemoryStore


ORG = 'f4dbf297-4526-41f5-bd7b-2ba20b4736d9'
OTHER_ORG = '65a63523-8d2b-46ac-b01d-3b34f3f6d277'
SUBJECT = 'google-subject'


class LicenseTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.store.put('principal:' + SUBJECT, {'sites': {'paid-site': ['read', 'edit'], 'legacy-site': ['read']}})
        site = {'name': 'Example', 'dev_url': 'https://dev.example.invalid', 'prod_url': 'https://example.invalid'}
        self.store.put('site:paid-site', {**site, 'direct_transfer_enabled': True, 'license_policy': {'mode': 'simy', 'org_id': ORG}})
        self.store.put('site:legacy-site', site)
        self.resolve = Mock(return_value=False)
        self.service = Service(self.store, license_resolver=self.resolve)
        self.claims = {'sub': SUBJECT, 'scope': 'hp:read hp:write'}
        self.token = 'a' * 32
        self.app = App(None, self.service, None, None, None, preflight_token=lambda: self.token)

    def request(self, body, token='a' * 32, transfer_ready=True):
        event = {'rawPath': '/internal/license/preflight', 'httpMethod': 'POST',
            'headers': {'authorization': 'Bearer ' + token, 'content-type': 'application/json'},
            'body': json.dumps(body)}
        transfer = {'hp_download_workspace': (), 'hp_prepare_upload': ()} if transfer_ready else {}
        with patch.dict(TOOL_FIELDS, transfer):
            response = self.app(event)
        return response['statusCode'], json.loads(response['body'])

    def test_preflight_unavailable_without_registered_direct_transfer_tools(self):
        body = {'org_id': ORG, 'google_subject': SUBJECT}
        with patch.dict(TOOL_FIELDS, {}, clear=True):
            self.assertEqual(self.request(body, transfer_ready=False), (503, {'error': 'hp_license_unavailable'}))
            TOOL_FIELDS['hp_download_workspace'] = ()
            self.assertEqual(self.request(body, transfer_ready=False), (503, {'error': 'hp_license_unavailable'}))
        self.resolve.assert_not_called()

    def test_preflight_is_readonly_and_payment_independent(self):
        body = {'org_id': ORG, 'google_subject': SUBJECT}
        snapshot = json.dumps(self.store.rows, sort_keys=True)
        self.assertEqual(self.request(body), (200, {'ready': True}))
        self.resolve.assert_called_once_with(ORG, SUBJECT)
        self.assertEqual(json.dumps(self.store.rows, sort_keys=True), snapshot)
        self.assertEqual(self.request({**body, 'org_id': OTHER_ORG}),
                         (200, {'ready': False, 'status': 'site_setup_required'}))
        self.assertEqual(self.request({**body, 'google_subject': 'other-subject'}),
                         (200, {'ready': False, 'status': 'connection_required'}))
        self.assertEqual(self.request(body, token='b' * 32), (401, {'error': 'invalid_token'}))
        self.assertEqual(self.request({**body, 'email': 'irrelevant@example.invalid'})[0], 400)
        self.resolve.side_effect = LicenseUnavailable('hp_license_unavailable')
        self.assertEqual(self.request(body), (503, {'error': 'hp_license_unavailable'}))

    def test_only_licensed_and_authorized_managed_sites_are_available(self):
        self.assertEqual(self.service.profile(self.claims)['sites'], ['legacy-site'])
        with self.assertRaisesRegex(Rejected, 'hp_license_required'):
            self.service.authorized(self.claims, 'paid-site', 'edit')
        self.resolve.return_value = True
        self.assertEqual(self.service.profile(self.claims)['sites'], ['legacy-site', 'paid-site'])
        self.service.authorized(self.claims, 'paid-site', 'edit')
        with self.assertRaisesRegex(Rejected, 'site_access_denied'):
            self.service.authorized(self.claims, 'paid-site', 'publish')
        self.service.license_resolver = None
        with self.assertRaises(LicenseUnavailable):
            self.service.authorized(self.claims, 'paid-site')
        self.service.authorized(self.claims, 'legacy-site')

    def test_invalid_site_policy_never_falls_back_to_existing_grants(self):
        site = self.store.get('site:paid-site')
        self.store.put('site:paid-site', {**site, 'license_policy': None}, site['_version'])
        self.assertEqual(self.request({'org_id': ORG, 'google_subject': SUBJECT})[0], 503)
        with self.assertRaises(LicenseUnavailable):
            self.service.authorized(self.claims, 'paid-site')

    def test_preflight_requires_an_existing_editor_and_explicit_org_binding(self):
        member = self.store.get('principal:' + SUBJECT)
        self.store.put('principal:' + SUBJECT, {'sites': {'paid-site': ['read'], 'legacy-site': ['read', 'edit']}}, member['_version'])
        self.assertEqual(self.request({'org_id': ORG, 'google_subject': SUBJECT}),
                         (200, {'ready': False, 'status': 'site_setup_required'}))
        self.resolve.assert_not_called()

    def test_resolver_accepts_loopback_http_only_when_explicitly_allowed(self):
        local = 'http://127.0.0.1:54321/functions/v1/hp-control-entitlement'
        with self.assertRaises(LicenseUnavailable):
            EntitlementResolver(local, lambda: self.token)
        EntitlementResolver(local, lambda: self.token, allow_loopback=True)
        for endpoint in ('http://api.example.invalid/functions/v1/hp-control-entitlement',
                         'http://127.0.0.1.example.invalid:54321/functions/v1/hp-control-entitlement',
                         'http://127.0.0.1:54321/functions/v1/other'):
            with self.subTest(endpoint=endpoint), self.assertRaises(LicenseUnavailable):
                EntitlementResolver(endpoint, lambda: self.token, allow_loopback=True)

    def test_resolver_uses_only_service_credentials_and_exact_boolean_response(self):
        resolver = EntitlementResolver('https://api.example.invalid/functions/v1/hp-control-entitlement', lambda: self.token)
        resolver.opener = Mock()

        def response(payload):
            stream = io.BytesIO(payload)
            stream.status = 200
            resolver.opener.open.return_value = stream

        response(b'{"allowed":false}')
        self.assertIs(resolver(ORG, SUBJECT), False)
        request = resolver.opener.open.call_args.args[0]
        self.assertEqual(request.get_header('Authorization'), 'Bearer ' + self.token)
        self.assertEqual(json.loads(request.data), {'org_id': ORG, 'google_subject': SUBJECT})
        for payload in (b'{"allowed":"true"}', b'{"allowed":true,"extra":1}', b'{}', b' ' * 1025):
            with self.subTest(payload=payload[:50]), self.assertRaises(LicenseUnavailable):
                response(payload)
                resolver(ORG, SUBJECT)
