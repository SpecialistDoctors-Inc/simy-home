"""No-network behavioral tests for the direct Google Sheets adapter."""
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from google_provider import (
    EMAIL_SCOPE, EVENT_FIELDS, FIELDS, GoogleSheets, OPENID_SCOPE,
    SHEETS_SCOPE, USERINFO_URL,
)
from provider_errors import EffectNotStarted


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class FakeCredentials:
    valid = True
    expired = False
    scopes = [SHEETS_SCOPE, OPENID_SCOPE, EMAIL_SCOPE]

    def apply(self, headers):
        headers['Authorization'] = 'Bearer fake'


class FakeTransport:
    def __init__(self, *, subject='123', email='clinic@example.com'):
        self.subject = subject
        self.email = email
        self.requests = [list(FIELDS)]
        self.events = [list(EVENT_FIELDS)]
        self.calls = []
        self.append_error = False
        self.append_without_write = False

    def request(self, method, url, *, params=None, json=None):
        self.calls.append((method, url, params, json))
        if url == USERINFO_URL:
            return FakeResponse({'sub': self.subject, 'email': self.email, 'email_verified': True})
        if method == 'GET' and url.endswith('/values:batchGet'):
            return FakeResponse({'valueRanges': [{'values': self.requests}, {'values': self.events}]})
        if method == 'POST' and url.endswith(':append'):
            if self.append_error:
                raise OSError('transport unavailable')
            if not self.append_without_write:
                self.events.append(json['values'][0])
            return FakeResponse({'updates': {'updatedRows': 1}})
        raise AssertionError(f'unexpected request: {method} {url}')


class GoogleSheetsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.directory.name, 'private.json')
        self.transport = FakeTransport()
        self.admission_lock = threading.Lock()
        self.adapter = self.make_adapter()

    def tearDown(self):
        self.directory.cleanup()

    def make_adapter(self, *, transport=None, credentials=None, config=None, subject='123', email='clinic@example.com'):
        return GoogleSheets(
            config or {'sheet_id': 'sheet-id'},
            self.path,
            subject,
            email,
            max_rows=20,
            transport=transport or self.transport,
            credentials=credentials or FakeCredentials(),
            event_admission=lambda _sheet, _key: self.admission_lock,
        )

    def event(self, **overrides):
        return {
            'event_id': 'event-1',
            'request_id': '11111111-1111-4111-8111-111111111111',
            'revision': '1',
            'occurred_at': '2026-11-02T00:00:00Z',
            'actor': 'clinic:google-sub:123',
            'kind': 'ready_for_dev',
            'body': 'exact acceptance',
            'reply_to_event_id': '',
            'event_idempotency_key': 'hp-ready:11111111-1111-4111-8111-111111111111:1',
            **overrides,
        }

    def test_snapshot_requires_verified_expected_identity_and_exact_headers(self):
        snapshot = self.adapter.snapshot()
        self.assertEqual([], snapshot['requests'])
        self.assertEqual([], snapshot['events'])

        wrong_identity = self.make_adapter(subject='wrong')
        with self.assertRaisesRegex(ValueError, '^Google subject mismatch$'):
            wrong_identity.snapshot()

        self.transport.events[0][0] = 'unexpected'
        with self.assertRaisesRegex(ValueError, '^Events header mismatch$'):
            self.adapter.snapshot()

    def test_snapshot_fails_closed_when_bounded_range_overflows(self):
        self.transport.events.extend([[''] * len(EVENT_FIELDS) for _ in range(21)])
        with self.assertRaisesRegex(ValueError, '^Events exceeds max_rows$'):
            self.adapter.snapshot()

    def test_service_account_requires_trusted_config_and_matching_identity(self):
        credentials = FakeCredentials()
        credentials.service_account_email = 'service@example.iam.gserviceaccount.com'
        adapter = self.make_adapter(
            credentials=credentials,
            config={
                'sheet_id': 'sheet-id',
                'trusted_service_account_email': credentials.service_account_email,
            },
            subject=credentials.service_account_email,
            email=credentials.service_account_email,
        )
        self.assertEqual(
            {'sub': credentials.service_account_email, 'email': credentials.service_account_email},
            adapter.authorized_user(),
        )
        untrusted = self.make_adapter(credentials=credentials)
        with self.assertRaisesRegex(ValueError, '^service account identity mismatch$'):
            untrusted.authorized_user()

    def test_append_uses_raw_once_and_returns_exact_readback(self):
        result = self.adapter.append_event(self.event())
        self.assertTrue(result['created'])
        self.assertTrue(result['readback_verified'])
        self.assertEqual(self.event(), result['event'])
        append_calls = [call for call in self.transport.calls if call[0] == 'POST']
        self.assertEqual(1, len(append_calls))
        _, url, params, payload = append_calls[0]
        self.assertIn('/values/Events%21A5%3AI:append', url)
        self.assertEqual('RAW', params['valueInputOption'])
        self.assertEqual('INSERT_ROWS', params['insertDataOption'])
        self.assertEqual([[self.event()[field] for field in EVENT_FIELDS]], payload['values'])

        replay = self.adapter.append_event(self.event())
        self.assertFalse(replay['created'])
        self.assertEqual(1, len([call for call in self.transport.calls if call[0] == 'POST']))

    def test_duplicate_or_conflicting_key_never_appends(self):
        first = self.event()
        self.transport.events.append([first[field] for field in EVENT_FIELDS])
        conflict = self.event(body='different text')
        with self.assertRaisesRegex(EffectNotStarted, '^append_event_preflight_failed$') as error:
            self.adapter.append_event(conflict)
        self.assertEqual('event key conflicts with existing row', str(error.exception.__cause__))
        self.assertEqual(0, len([call for call in self.transport.calls if call[0] == 'POST']))

    def test_ambiguous_append_does_not_retry(self):
        self.transport.append_error = True
        with self.assertRaisesRegex(RuntimeError, '^event append outcome is uncertain; reconcile before retry$'):
            self.adapter.append_event(self.event())
        self.assertEqual(1, len([call for call in self.transport.calls if call[0] == 'POST']))

        second_transport = FakeTransport()
        second_transport.append_without_write = True
        second = self.make_adapter(transport=second_transport)
        with self.assertRaisesRegex(RuntimeError, '^event append outcome is uncertain; reconcile before retry$'):
            second.append_event(self.event())
        self.assertEqual(1, len([call for call in second_transport.calls if call[0] == 'POST']))

    def test_invalid_event_shape_is_rejected_before_provider_effect(self):
        invalid = self.event()
        invalid.pop('body')
        with self.assertRaisesRegex(EffectNotStarted, '^append_event_preflight_failed$') as error:
            self.adapter.append_event(invalid)
        self.assertEqual('invalid event shape', str(error.exception.__cause__))
        self.assertEqual(0, len(self.transport.calls))

    def test_append_requires_caller_owned_durable_admission(self):
        adapter = GoogleSheets(
            {'sheet_id': 'sheet-id'}, self.path, '123', 'clinic@example.com',
            transport=self.transport, credentials=FakeCredentials(),
        )
        with self.assertRaisesRegex(EffectNotStarted, '^append_event_preflight_failed$') as error:
            adapter.append_event(self.event())
        self.assertEqual('durable event admission is required', str(error.exception.__cause__))
        adapter.set_event_admission(lambda _sheet, _key: self.admission_lock)
        self.assertTrue(adapter.append_event(self.event())['created'])
        self.assertEqual(1, len([call for call in self.transport.calls if call[0] == 'POST']))

    def test_missing_approved_scope_is_rejected_at_construction(self):
        credentials = FakeCredentials()
        credentials.scopes = [SHEETS_SCOPE, OPENID_SCOPE]
        with self.assertRaisesRegex(ValueError, '^Google credential lacks required scopes$'):
            self.make_adapter(credentials=credentials)

    def test_shared_admission_serializes_concurrent_append_to_one_provider_write(self):
        barrier = threading.Barrier(2)
        results = []
        errors = []
        result_lock = threading.Lock()

        def append_from_worker():
            adapter = self.make_adapter()
            try:
                barrier.wait()
                result = adapter.append_event(self.event())
                with result_lock:
                    results.append(result)
            except Exception as error:
                with result_lock:
                    errors.append(error)

        first = threading.Thread(target=append_from_worker)
        second = threading.Thread(target=append_from_worker)
        first.start()
        second.start()
        first.join()
        second.join()
        self.assertEqual([], errors)
        self.assertEqual([False, True], sorted(result['created'] for result in results))
        self.assertEqual(1, len([call for call in self.transport.calls if call[0] == 'POST']))

    def test_post_write_duplicate_readback_is_uncertain_not_a_validation_error(self):
        original_request = self.transport.request

        def duplicate_after_append(method, url, *, params=None, json=None):
            response = original_request(method, url, params=params, json=json)
            if method == 'POST':
                self.transport.events.append(json['values'][0])
            return response

        self.transport.request = duplicate_after_append
        with self.assertRaisesRegex(RuntimeError, '^event append outcome is uncertain; reconcile before retry$'):
            self.adapter.append_event(self.event())


if __name__ == '__main__':
    unittest.main()
