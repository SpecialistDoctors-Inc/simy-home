"""Credential recovery boundaries using only fake Google transports."""
from contextlib import nullcontext
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from gmail_provider import GMAIL_API, GMAIL_READONLY_SCOPE, GMAIL_SEND_SCOPE, Gmail
from google_provider import EMAIL_SCOPE, EVENT_FIELDS, FIELDS, GoogleSheets, OPENID_SCOPE, SHEETS_SCOPE, USERINFO_URL
from provider_errors import AuthenticationRequired, EffectNotStarted, safe_provider_code


class Response:
    def __init__(self, payload=None, status=200):
        self.status_code = status
        self.payload = {} if payload is None else payload

    def json(self):
        return self.payload


class Credentials:
    valid = True
    expired = False
    scopes = [SHEETS_SCOPE, OPENID_SCOPE, EMAIL_SCOPE, GMAIL_SEND_SCOPE, GMAIL_READONLY_SCOPE]

    def apply(self, headers):
        headers['Authorization'] = 'Bearer not-a-real-token'


class SheetsTransport:
    def __init__(self, *, post_status=None, read_status=None):
        self.calls = []
        self.post_status = post_status
        self.read_status = read_status
        self.requests = [list(FIELDS)]
        self.events = [list(EVENT_FIELDS)]

    def request(self, method, url, *, params=None, json=None):
        self.calls.append((method, url, params, json))
        if self.read_status is not None:
            return Response(status=self.read_status)
        if url == USERINFO_URL:
            return Response({'sub': 'sub', 'email': 'operator@example.com', 'email_verified': True})
        if method == 'GET':
            return Response({'valueRanges': [{'values': self.requests}, {'values': self.events}]})
        if method == 'POST':
            if self.post_status is not None:
                return Response(status=self.post_status)
            self.events.append(json['values'][0])
            return Response({'updates': {'updatedRows': 1}})
        raise AssertionError((method, url))


class GmailTransport:
    def __init__(self, status):
        self.status = status
        self.calls = []

    def request(self, method, url, *, params=None, json=None):
        self.calls.append((method, url, params, json))
        if url == USERINFO_URL:
            return Response({'sub': 'sub', 'email': 'operator@example.com', 'email_verified': True})
        if method == 'GET' and url == GMAIL_API:
            return Response({'messages': []})
        if method == 'POST' and url == f'{GMAIL_API}/send':
            return Response(status=self.status)
        raise AssertionError((method, url))


def caused(error):
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        if isinstance(error, AuthenticationRequired):
            return error
        error = error.__cause__
    return None


class ProviderRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.event = {
            'event_id': 'event', 'request_id': '11111111-1111-4111-8111-111111111111', 'revision': '1',
            'occurred_at': '2026-11-03T00:00:00Z', 'actor': 'operator',
            'kind': 'test_result', 'body': 'body', 'reply_to_event_id': '', 'event_idempotency_key': 'event-key',
        }

    def tearDown(self):
        self.temp.cleanup()

    def sheets(self, transport, credentials=None):
        return GoogleSheets({'sheet_id': 'sheet'}, Path(self.temp.name) / 'credentials.json', 'sub', 'operator@example.com',
                            transport=transport, credentials=credentials or Credentials(), event_admission=lambda *_: nullcontext())

    def test_sheets_http_auth_failure_is_safe_and_prewrite_is_not_started(self):
        for status in (401, 403):
            with self.subTest(status=status):
                transport = SheetsTransport(read_status=status)
                adapter = self.sheets(transport)
                with self.assertRaises(AuthenticationRequired) as raised:
                    adapter.snapshot()
                error = raised.exception
                self.assertEqual({'provider': 'google', 'code': f'google_http_{status}', 'status': status}, safe_provider_code(error))
                self.assertNotIn('not-a-real-token', str(error))
                with self.assertRaises(EffectNotStarted) as wrapped:
                    adapter.append_event(self.event)
                self.assertEqual(status, caused(wrapped.exception).status)
                self.assertEqual(0, len([call for call in transport.calls if call[0] == 'POST']))

    def test_sheets_post_auth_failure_is_ambiguous_not_not_started(self):
        transport = SheetsTransport(post_status=401)
        with self.assertRaisesRegex(RuntimeError, '^event append outcome is uncertain; reconcile before retry$') as raised:
            self.sheets(transport).append_event(self.event)
        self.assertNotIsInstance(raised.exception, EffectNotStarted)
        self.assertEqual(1, len([call for call in transport.calls if call[0] == 'POST']))
        self.assertEqual(401, caused(raised.exception).status)

    def test_gmail_post_auth_failure_is_ambiguous_without_resend(self):
        transport = GmailTransport(403)
        adapter = Gmail({'recipient': 'clinic@example.com'}, Path(self.temp.name) / 'credentials.json', 'sub', 'operator@example.com',
                        transport=transport, credentials=Credentials(), notice_admission=lambda *_: nullcontext())
        envelope = {'to': 'clinic@example.com', 'subject': 'Ready', 'body': 'body\nHP-NOTICE-key'}
        with self.assertRaisesRegex(RuntimeError, '^notice send outcome is uncertain; reconcile before retry$') as raised:
            adapter.send_notice(envelope, 'key')
        self.assertNotIsInstance(raised.exception, EffectNotStarted)
        self.assertEqual(1, len([call for call in transport.calls if call[0] == 'POST']))
        self.assertEqual({'provider': 'google', 'code': 'google_http_403', 'status': 403}, safe_provider_code(caused(raised.exception)))

    def test_refresh_failure_is_classified_without_provider_text(self):
        class ExpiredCredentials(Credentials):
            valid = False
            expired = True
        with self.assertRaises(AuthenticationRequired) as raised:
            self.sheets(SheetsTransport(), ExpiredCredentials()).snapshot()
        self.assertEqual('google_auth_refresh_required', raised.exception.code)
        self.assertNotIn('credentials.json', str(raised.exception))
        self.assertNotIn('not-a-real-token', str(raised.exception))

    def test_codex_auth_is_typed_without_a_provider_status_or_cli_output(self):
        error = AuthenticationRequired('codex', 'codex_auth_required')
        self.assertEqual({'provider': 'codex', 'code': 'codex_auth_required', 'status': None}, safe_provider_code(error))
        with self.assertRaisesRegex(ValueError, 'invalid authentication status'):
            AuthenticationRequired('codex', 'codex_auth_required', 401)


if __name__ == '__main__':
    unittest.main()
