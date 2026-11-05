"""Reporting effect safety with provider fakes only; no credentials/network."""
from copy import deepcopy
import unittest
from uuid import uuid4

from executor import Busy
from reporting import Reporter
from store import MemoryStore, Conflict


class Crash(BaseException):
    pass


class Sheets:
    def __init__(self):
        self.spreadsheet_id = 'example-private-sheet-binding'
        self.identity = {'sub': 'operator-subject', 'email': 'operator@example.invalid'}
        self.requests = {}
        self.request_appends = 0
        self.request_crash = False
        self.request_ambiguous = False
        self.after_request = None
        self.events = {}
        self.appends = 0
        self.reads = 0
        self.crash = False
        self.ambiguous = False
        self.after_append = None
        self.guard = lambda new=False: None

    def authorized_user(self):
        self.guard()
        return self.identity

    def find_request(self, request_id, revision):
        self.guard()
        self.reads += 1
        return deepcopy(self.requests.get((request_id, revision)))

    def append_request(self, row):
        self.guard(True)
        self.request_appends += 1
        if not self.request_ambiguous:
            self.requests[(row['request_id'], row['revision'])] = deepcopy(row)
        if self.after_request:
            self.after_request()
        if self.request_crash:
            raise Crash()
        if self.request_ambiguous:
            raise RuntimeError('unknown request append outcome')
        return {'readback_verified': True, 'request': deepcopy(row)}

    def find_event(self, key):
        self.guard()
        self.reads += 1
        return deepcopy(self.events.get(key))

    def append_event(self, event):
        self.guard(True)
        self.appends += 1
        if not self.ambiguous:
            self.events[event['event_idempotency_key']] = deepcopy(event)
        if self.after_append:
            self.after_append()
        if self.crash:
            raise Crash()
        if self.ambiguous:
            raise RuntimeError('unknown provider append outcome with private details')
        return {'readback_verified': True, 'event': deepcopy(event)}


class Mail:
    def __init__(self):
        self.recipient = 'recipient@example.invalid'
        self.identity = {'sub': 'operator-subject', 'email': 'operator@example.invalid'}
        self.notices = {}
        self.sends = 0
        self.reads = 0
        self.guard = lambda new=False: None
        self.crash = False
        self.ambiguous = False
        self.after_send = None
        self.before_send = None

    def authorized_user(self):
        self.guard()
        return self.identity

    def find_notice(self, envelope, key):
        self.guard()
        self.reads += 1
        found = self.notices.get(key)
        if found:
            if found['envelope'] != envelope:
                raise ValueError('notice envelope mismatch')
            return {'provider_message_id': found['id'], 'readback_verified': True}
        return None

    def send_notice(self, envelope, key):
        if self.before_send:
            self.before_send()
        self.guard(True)
        self.sends += 1
        if not self.ambiguous:
            self.notices[key] = {'envelope': deepcopy(envelope), 'id': 'example-message'}
        if self.after_send:
            self.after_send()
        if self.crash:
            raise Crash()
        if self.ambiguous:
            raise RuntimeError('unknown mail outcome with private details')
        return {'provider_message_id': 'example-message', 'readback_verified': True}


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.now = 10000
        self.operation_id = str(uuid4())
        self.workspace_id = str(uuid4())
        self.preview_id = str(uuid4())
        self.site_id = 'example-site'
        self.site = {'site_id': self.site_id, 'config_version': 1, 'sheet_id': 'example-private-sheet-binding', 'recipient': 'recipient@example.invalid', 'operator_subject': 'operator-subject', 'operator_email': 'operator@example.invalid', 'mail_enabled': True, 'dev_url': 'https://preview.example.invalid', 'prod_url': 'https://site.example.invalid', 'current_preview': self.preview_id}
        self.store.put('site:' + self.site_id, self.site)
        self.store.put('principal:member-subject', {'sites': {self.site_id: ['read', 'edit', 'publish']}})
        self.store.put('workspace:' + self.workspace_id, {'site_id': self.site_id, 'subject': 'member-subject', 'snapshot_file_id': 'example-snapshot', 'snapshot_sha256': 'c' * 64})
        self.op = {'operation_id': self.operation_id, 'site_id': self.site_id, 'subject': 'member-subject', 'kind': 'save_draft', 'status': 'completed', 'created_at': self.now - 60, 'completed_at': self.now, 'member_version': 1, 'site_config_version': 1, 'execution_site': deepcopy(self.site), 'reporting_required': True, 'reporting_state': 'pending',
            'input': {'workspace_id': self.workspace_id, 'base_commit': 'a' * 40, 'bundle_sha256': 'b' * 64},
            'result': {'kind': 'saved', 'operation_id': self.operation_id, 'site_id': self.site_id, 'workspace_id': self.workspace_id, 'base_commit': 'a' * 40, 'saved_commit': 'd' * 40, 'bundle_sha256': 'b' * 64}}
        self.store.put('operation:' + self.operation_id, self.op)
        self.sheets, self.mail = Sheets(), Mail()
        def factory(provider):
            def create(site, guard):
                provider.guard = guard
                return provider
            return create
        self.reporter = Reporter(self.store, factory(self.sheets), factory(self.mail), clock=lambda: self.now)

    def update(self, key, **changes):
        old = self.store.get(key)
        return self.store.put(key, {**old, **changes}, old['_version'])

    def result(self):
        return self.reporter.report(self.operation_id)

    def record(self):
        return self.store.get('reporting:' + self.operation_id)

    def preview(self, published=False):
        proof = {'source_commit': 'd' * 40, 'artifact_sha256': 'e' * 64, 'conclusion': 'success'}
        preview = {'preview_id': self.preview_id, 'site_id': self.site_id, 'operation_id': self.operation_id, 'status': 'verified', 'source_commit': 'd' * 40, 'artifact_sha256': 'e' * 64, 'url': self.site['dev_url'], 'validation': proof}
        self.store.put('preview:' + self.preview_id, preview)
        value = {'kind': 'preview', 'preview_id': self.preview_id, 'source_commit': 'd' * 40, 'artifact_sha256': 'e' * 64, 'preview_url': self.site['dev_url']}
        kind = 'submit_preview'
        if published:
            publication = {'operation_id': self.operation_id, 'preview_id': self.preview_id, 'source_commit': 'd' * 40, 'artifact_sha256': 'e' * 64, 'main_commit': 'f' * 40, 'receipt': {'verified': True, 'artifact_sha256': 'e' * 64}}
            self.update('site:' + self.site_id, current_publication=publication)
            value = {'kind': 'published', **publication}
            kind = 'publish'
        self.update('operation:' + self.operation_id, kind=kind, result=value)

    def test_duplicate_reports_append_and_send_once_with_exact_durable_envelope(self):
        first = self.result()
        self.assertEqual(first['state'], 'complete')
        self.assertEqual(self.result(), first)
        self.assertEqual((self.sheets.appends, self.mail.sends), (1, 0))
        record = self.record()
        self.assertEqual(record['event_key'], 'hp-control:' + self.operation_id + ':draft_saved')
        self.assertEqual(record['event']['request_id'], self.operation_id)
        self.assertEqual(record['event']['revision'], '1')
        self.assertNotEqual(record['event']['kind'], 'ready_for_dev')
        self.assertIn('HP-NOTICE-' + record['notice_key'], record['envelope']['body'])
        self.assertEqual(first['phases']['mail'], 'not_required')
        self.assertNotIn('mail', first['receipts'])
        self.assertFalse(self.store.get('operation:' + self.operation_id)['reporting_required'])

    def test_request_row_frozen_before_event_and_uses_v2_identity_without_legacy_authority(self):
        self.update('operation:' + self.operation_id, summary='診療時間のお知らせを更新')
        def inspect():
            self.assertEqual(self.record()['phases']['request'], 'admitted')
            self.assertEqual(self.sheets.appends, 0)
        self.sheets.after_request = inspect
        receipt = self.result()
        self.assertEqual(receipt['state'], 'complete')
        self.assertEqual(self.result(), receipt)
        self.assertEqual((self.sheets.request_appends, self.sheets.appends), (1, 1))
        row = self.record()['request']
        self.assertEqual(row['request_id'], self.operation_id)
        self.assertEqual(row['revision'], '1')
        self.assertEqual(row['site_id'], self.site_id)
        self.assertEqual(row['outcome'], '診療時間のお知らせを更新')
        self.assertEqual(row['target'], self.site['dev_url'])
        self.assertEqual(row['proposal_state'], 'local_draft')
        self.assertEqual(row['requester_ref'], 'google-sub:member-subject')
        self.assertEqual(row['assets_rights'], 'この操作の提出ファイルを参照')
        self.assertEqual(row['dependencies'], 'この操作の提出ファイルを参照')
        self.assertNotIn('ready_for_dev', row.values())
        self.assertIn(self.op['result']['saved_commit'], row['acceptance'])

    def test_request_append_crash_is_read_back_before_event_without_duplicate(self):
        self.sheets.request_crash = True
        with self.assertRaises(Crash):
            self.result()
        self.assertEqual(self.record()['phases']['request'], 'admitted')
        self.assertEqual((self.sheets.request_appends, self.sheets.appends), (1, 0))
        self.now += 301
        self.sheets.request_crash = False
        self.assertEqual(self.result()['state'], 'complete')
        self.assertEqual((self.sheets.request_appends, self.sheets.appends), (1, 1))

    def test_ambiguous_request_is_never_appended_again_and_blocks_events(self):
        self.sheets.request_ambiguous = True
        self.assertEqual(self.result()['state'], 'reconciling')
        self.assertEqual(self.result()['state'], 'reconciling')
        self.assertEqual((self.sheets.request_appends, self.sheets.appends), (1, 0))
        self.assertEqual(self.mail.sends, 0)

    def test_matching_request_key_with_mutated_content_never_overwrites_or_emits_event(self):
        self.sheets.request_crash = True
        with self.assertRaises(Crash):
            self.result()
        self.sheets.requests[(self.operation_id, '1')]['outcome'] = 'changed outside reporter'
        self.now += 301
        self.sheets.request_crash = False
        receipt = self.result()
        self.assertEqual(receipt['state'], 'needs_attention')
        self.assertEqual((self.sheets.request_appends, self.sheets.appends), (1, 0))
        self.assertEqual(self.sheets.requests[(self.operation_id, '1')]['outcome'], 'changed outside reporter')

    def test_outbox_admitted_before_send_and_cancellation_during_send_is_readback_only(self):
        self.preview()
        def inspect():
            self.assertEqual(self.record()['phases']['mail'], 'admitted')
            self.assertEqual(self.store.get('lease:site:' + self.site_id)['blocked_operation'], self.operation_id)
        self.mail.before_send = inspect
        self.mail.after_send = lambda: self.update('operation:' + self.operation_id, cancel_requested=True)
        receipt = self.result()
        self.assertEqual(receipt['state'], 'complete')
        self.assertEqual(self.mail.sends, 1)
        self.assertTrue(receipt['receipts']['mail']['readback_verified'])
        self.assertEqual(receipt['receipts']['mail']['inbox_delivery'], 'unknown')
        self.assertIsNone(self.store.get('lease:site:' + self.site_id)['blocked_operation'])

    def test_crash_after_sheet_append_reconciles_without_duplicate_or_draft_email(self):
        self.sheets.crash = True
        with self.assertRaises(Crash):
            self.result()
        self.assertEqual(self.record()['phases']['sheet'], 'admitted')
        self.assertEqual(self.sheets.appends, 1)
        with self.assertRaises(Busy):
            self.result()
        self.now += 301
        self.sheets.crash = False
        receipt = self.result()
        self.assertEqual(receipt['state'], 'complete')
        self.assertEqual((self.sheets.appends, self.mail.sends), (1, 0))

    def test_crash_after_mail_send_reconciles_after_revocation_without_resend(self):
        self.preview()
        self.mail.crash = True
        with self.assertRaises(Crash):
            self.result()
        self.assertEqual(self.record()['phases']['mail'], 'admitted')
        self.update('principal:member-subject', disabled=True)
        self.update('operation:' + self.operation_id, cancel_requested=True)
        self.now += 301
        self.mail.crash = False
        receipt = self.result()
        self.assertEqual(receipt['state'], 'complete')
        self.assertEqual((self.sheets.appends, self.mail.sends), (1, 1))
        self.assertTrue(receipt['receipts']['mail']['provider_accepted'])

    def test_ambiguous_mail_outcome_blocks_other_work_and_readback_never_resends(self):
        self.preview()
        self.mail.ambiguous = True
        first = self.result()
        self.assertEqual(first['state'], 'reconciling')
        self.assertEqual(self.mail.sends, 1)
        self.assertEqual(self.result()['state'], 'reconciling')
        self.assertEqual(self.mail.sends, 1)
        self.assertEqual(self.store.get('lease:site:' + self.site_id)['blocked_operation'], self.operation_id)
        another = str(uuid4())
        self.store.put('operation:' + another, {**self.op, 'operation_id': another})
        with self.assertRaises(Busy):
            self.reporter.report(another)
        self.assertNotIn('private details', str(self.result()))

    def test_cancel_after_sheet_append_reconciles_and_suppresses_new_mail(self):
        self.preview()
        self.sheets.crash = True
        with self.assertRaises(Crash):
            self.result()
        self.update('operation:' + self.operation_id, cancel_requested=True)
        self.now += 301
        self.sheets.crash = False
        receipt = self.result()
        self.assertEqual(receipt['state'], 'suppressed')
        self.assertEqual(receipt['phases'], {'request': 'done', 'sheet': 'done', 'mail': 'suppressed'})
        self.assertEqual((self.sheets.appends, self.mail.sends), (1, 0))

    def test_revoked_wrong_site_and_binding_changes_allow_no_new_effects(self):
        for mutation in [lambda: self.update('principal:member-subject', disabled=True), lambda: self.update('site:' + self.site_id, site_id='other-site'), lambda: self.update('site:' + self.site_id, recipient='other@example.invalid'), lambda: self.update('site:' + self.site_id, sheet_id='other-sheet-binding'), lambda: self.update('site:' + self.site_id, config_version=2), lambda: self.update('operation:' + self.operation_id, result={**self.op['result'], 'site_id': 'other-site'})]:
            with self.subTest(mutation=mutation):
                original = deepcopy(self.store.rows)
                mutation()
                self.assertEqual(self.result()['state'], 'suppressed' if self.store.get('principal:member-subject').get('disabled') else 'needs_attention')
                self.assertEqual((self.sheets.appends, self.mail.sends), (0, 0))
                self.store.rows = original

    def test_provider_wrong_recipient_does_not_send(self):
        self.preview()
        self.mail.recipient = 'other@example.invalid'
        receipt = self.result()
        self.assertEqual(receipt['state'], 'needs_attention')
        self.assertEqual(self.mail.sends, 0)
        self.assertEqual(self.sheets.appends, 1)

    def test_wrong_operator_has_no_external_write(self):
        self.sheets.identity = {'sub': 'wrong-operator', 'email': 'operator@example.invalid'}
        self.assertEqual(self.result()['state'], 'needs_attention')
        self.assertEqual((self.sheets.appends, self.mail.sends), (0, 0))

    def test_workspace_ready_uses_new_event_kind(self):
        self.update('operation:' + self.operation_id, kind='open_workspace', workspace_id=self.workspace_id,
            result={'kind': 'workspace', 'site_id': self.site_id, 'workspace_id': self.workspace_id,
                'snapshot_file_id': 'example-snapshot', 'snapshot_sha256': 'c' * 64, 'base_commit': 'a' * 40})
        self.assertEqual(self.result()['event_kind'], 'workspace_ready')
        self.assertEqual(self.record()['event']['kind'], 'workspace_ready')
        self.assertEqual(self.record()['phases']['request'], 'not_required')
        self.assertEqual(self.sheets.request_appends, 0)

    def test_verified_published_event_reports_production_url_without_claiming_inbox_delivery(self):
        self.preview(published=True)
        receipt = self.result()
        self.assertEqual(receipt['event_kind'], 'published')
        self.assertEqual(self.record()['request']['proposal_state'], 'local_publication')
        self.assertEqual(self.record()['request']['target'], self.site['prod_url'])
        self.assertEqual(receipt['state'], 'complete')
        self.assertIn(self.site['prod_url'], self.record()['event']['body'])
        self.assertIn(self.site['dev_url'], self.record()['event']['body'])
        self.assertEqual(receipt['receipts']['mail']['inbox_delivery'], 'unknown')

    def test_binding_failure_reconciling_admitted_mail_requires_attention_and_keeps_site_blocked(self):
        self.preview()
        self.mail.crash = True
        with self.assertRaises(Crash):
            self.result()
        self.now += 301
        self.mail.crash = False
        self.mail.recipient = 'other@example.invalid'
        receipt = self.result()
        self.assertEqual(receipt['state'], 'needs_attention')
        self.assertEqual(self.mail.sends, 1)
        operation = self.store.get('operation:' + self.operation_id)
        self.assertTrue(operation['reporting_required'])
        self.assertNotIn('queue_state', operation)
        self.assertEqual(self.store.get('lease:site:' + self.site_id)['blocked_operation'], self.operation_id)

    def test_revoked_during_new_send_admission_cannot_send(self):
        self.preview()
        self.mail.before_send = lambda: self.update('principal:member-subject', disabled=True)
        receipt = self.result()
        self.assertEqual(self.mail.sends, 0)
        # An adapter must explicitly prove no write began before this could be
        # reset. An absent remote receipt is never authority to resend.
        self.assertEqual(receipt['state'], 'reconciling')
        self.assertEqual(self.result()['state'], 'reconciling')
        self.assertEqual(self.mail.sends, 0)

    def test_preview_event_contains_exact_verified_artifact_and_publication_has_exact_live_binding(self):
        self.preview()
        receipt = self.result()
        self.assertEqual(receipt['event_kind'], 'dev_preview_ready')
        self.assertEqual(self.record()['request']['proposal_state'], 'local_preview')
        self.assertEqual(self.record()['request']['target'], self.site['dev_url'])
        event = self.record()['event']
        self.assertIn('d' * 40, event['body'])
        self.assertIn('e' * 64, event['body'])
        self.assertIn(self.site['dev_url'], event['body'])
        self.assertNotIn('ready_for_dev', event['kind'])

    def test_published_requires_verified_current_publication(self):
        self.preview(published=True)
        publication = self.store.get('site:' + self.site_id)['current_publication']
        self.update('site:' + self.site_id, current_publication={**publication, 'artifact_sha256': '0' * 64})
        self.assertEqual(self.result()['state'], 'needs_attention')
        self.assertEqual((self.sheets.appends, self.mail.sends), (0, 0))

    def test_disabled_mail_is_explicitly_skipped_and_unconfigured_adapter_not_successful(self):
        self.preview()
        self.update('site:' + self.site_id, mail_enabled=False)
        self.update('operation:' + self.operation_id, execution_site={**self.site, 'mail_enabled': False})
        receipt = self.result()
        self.assertEqual(receipt['phases']['mail'], 'disabled')
        self.assertNotIn('mail', receipt['receipts'])
        self.assertEqual(self.mail.sends, 0)
        other = str(uuid4())
        self.store.put('operation:' + other, {**self.op, 'operation_id': other, 'result': {**self.op['result'], 'operation_id': other}, 'execution_site': {**self.site, 'mail_enabled': False}})
        self.reporter.sheets_factory = None
        receipt = self.reporter.report(other)
        self.assertEqual(receipt['state'], 'pending')
        self.assertTrue(self.store.get('operation:' + other)['reporting_required'])

    def test_stale_fence_prevents_provider_write(self):
        self.preview()
        def expire():
            self.now += 301
        self.mail.before_send = expire
        with self.assertRaises(Busy):
            self.result()
        self.assertEqual(self.mail.sends, 0)
        self.assertEqual(self.store.get('lease:site:' + self.site_id)['blocked_operation'], self.operation_id)


class CloudReportingTests(unittest.TestCase):
    def setUp(self):
        import sys
        from pathlib import Path
        runner = str(Path(__file__).resolve().parent.parent / 'runner')
        sys.path.insert(0, runner)
        self.addCleanup(lambda: sys.path.remove(runner))
        self.site = {'site_id': 'example-site', 'dev_url': 'https://preview.example.invalid', 'prod_url': 'https://site.example.invalid', 'sheet_id': 'example-private-sheet-binding', 'recipient': 'recipient@example.invalid', 'operator_subject': 'operator-subject', 'operator_email': 'operator@example.invalid'}
        self.scopes = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']
        self.material = dict(client_id='fake-client', client_secret='fake-secret', refresh_token='fake-refresh-value', scopes=self.scopes)
        self.guards, self.sessions, self.raw_credentials = [], [], []
        self.guard = lambda new=False: self.guards.append(new)

    def session(self):
        class Response:
            headers = {}
            status_code = 200
            def __init__(self, data):
                import json
                self.data = json.dumps(data).encode()
            def iter_content(self, chunk_size):
                yield self.data
            def close(self):
                pass
        owner = self
        class Session:
            def __init__(self):
                self.calls = []
            def request(self, method, url, **kwargs):
                self.calls.append((method, url, kwargs))
                if url == 'https://openidconnect.googleapis.com/v1/userinfo':
                    return Response({'sub': owner.site['operator_subject'], 'email': owner.site['operator_email'], 'email_verified': True})
                if url == 'https://oauth2.googleapis.com/token':
                    return Response({'access_token': 'fake-access-value', 'expires_in': 3600})
                return Response({})
        value = Session()
        self.sessions.append(value)
        return value

    def credentials(self, **kwargs):
        class Credentials:
            valid = True
            expired = False
            def __init__(self, values):
                self.values, self.scopes = values, values['scopes']
                self.refreshes = []
            def apply(self, headers):
                headers['Authorization'] = 'Bearer fake-provider-access'
            def refresh(self, request):
                self.refreshes.append(request)
                request('https://oauth2.googleapis.com/token', method='POST', body=b'grant_type=refresh_token')
        value = Credentials(kwargs)
        self.raw_credentials.append(value)
        return value

    def factories(self):
        from cloud_reporting import factories
        return factories('example-operator-secret-reference', lambda ref: deepcopy(self.material), session_factory=self.session, credential_factory=self.credentials)

    def test_legacy_providers_use_in_memory_credentials_and_verified_operator(self):
        sheets, mail = self.factories()
        for factory in (sheets, mail):
            provider = factory(self.site, self.guard)
            self.assertEqual(provider.authorized_user()['sub'], self.site['operator_subject'])
            self.assertEqual(self.raw_credentials[-1].values['token_uri'], 'https://oauth2.googleapis.com/token')
            self.assertIsNone(self.raw_credentials[-1].values['token'])
            self.assertEqual(self.sessions[-1].calls[-1][2]['allow_redirects'], False)
        self.assertTrue(all(not value for value in self.guards))
        self.assertEqual(len(self.raw_credentials), 2)

    def test_fixed_origins_no_redirects_and_method_aware_write_guard(self):
        from cloud_reporting import _Transport, _Credentials, _OAuthRequest
        from service import Rejected
        session = self.session()
        credentials = _Credentials(self.credentials(scopes=self.scopes), _OAuthRequest(session, self.guard))
        transport = _Transport(credentials, session, self.guard, 'sheet', self.site)
        for url in ['https://attacker.example.invalid/values:batchGet', 'http://sheets.googleapis.com/v4/spreadsheets/example-private-sheet-binding/values:batchGet', 'https://sheets.googleapis.com/v4/spreadsheets/other-sheet/values:batchGet']:
            with self.subTest(url=url), self.assertRaises(Rejected):
                transport.request('GET', url)
        self.assertEqual(session.calls, [])
        transport.request('POST', 'https://sheets.googleapis.com/v4/spreadsheets/example-private-sheet-binding/values/Events%21A5%3AI:append', json={})
        self.assertTrue(self.guards[-1])
        self.assertFalse(session.calls[-1][2]['allow_redirects'])
        self.assertEqual(session.calls[-1][2]['timeout'], 20)
        credentials.refresh(object())
        self.assertFalse(self.guards[-1])
        self.assertEqual(session.calls[-1][1], 'https://oauth2.googleapis.com/token')
        self.assertFalse(session.calls[-1][2]['allow_redirects'])
        with self.assertRaises(Rejected):
            _OAuthRequest(session, self.guard)('https://attacker.example.invalid/token', method='POST')

    def test_reject_unapproved_scopes_and_token_origin_before_network(self):
        from service import Rejected
        sheets, mail = self.factories()
        self.material['token_uri'] = 'https://attacker.example.invalid/token'
        with self.assertRaises(Rejected):
            sheets(self.site, self.guard)
        self.assertEqual(self.sessions[-1].calls, [])
        del self.material['token_uri']
        self.material['scopes'] = ['openid']
        for factory in (sheets, mail):
            with self.assertRaises(Rejected):
                factory(self.site, self.guard)
            self.assertEqual(self.sessions[-1].calls, [])

    def workbook_provider(self):
        from cloud_reporting import factories
        from google_provider import FIELDS, EVENT_FIELDS
        from contextlib import nullcontext
        owner = self
        class Response:
            status_code = 200
            headers = {}
            def __init__(self, payload):
                import json
                self.data = json.dumps(payload).encode()
            def iter_content(self, chunk_size):
                yield self.data
            def close(self):
                pass
        class Session:
            def __init__(self):
                self.requests = [list(FIELDS)]
                self.events = [list(EVENT_FIELDS)]
                self.calls = []
                self.appends = 0
                self.loss = False
            def request(self, method, url, **kwargs):
                self.calls.append((method, url, kwargs))
                if url == 'https://openidconnect.googleapis.com/v1/userinfo':
                    return Response({'sub': owner.site['operator_subject'], 'email': owner.site['operator_email'], 'email_verified': True})
                if method == 'GET' and url.endswith('/values:batchGet'):
                    return Response({'valueRanges': [{'values': deepcopy(self.requests)}, {'values': deepcopy(self.events)}]})
                if method == 'POST' and url.endswith('/values/Requests%21A5%3AN:append'):
                    self.appends += 1
                    self.requests.extend(deepcopy(kwargs['json']['values']))
                    if self.loss:
                        raise RuntimeError('simulated response loss after append')
                    return Response({'updates': {'updatedRows': 1}})
                raise AssertionError('unexpected fake endpoint')
        session = Session()
        sheets, _ = factories('example-operator-secret', lambda ref: deepcopy(self.material), session_factory=lambda: session, credential_factory=self.credentials)
        provider = sheets(self.site, self.guard)
        provider.set_request_admission(lambda sheet, request, revision: nullcontext())
        harness = ReportingTests(methodName='test_duplicate_reports_append_and_send_once_with_exact_durable_envelope')
        harness.setUp()
        harness.result()
        return provider, session, harness.record()['request']

    def test_real_requests_wrapper_raw_row5_append_and_response_loss_readback(self):
        from google_provider import FIELDS
        provider, session, row = self.workbook_provider()
        session.loss = True
        with self.assertRaises(RuntimeError):
            provider.append_request(row)
        self.assertEqual(session.appends, 1)
        self.assertEqual(provider.find_request(row['request_id'], '1'), row)
        # Reporter recovery calls find_request only; even direct adapter retry
        # cannot append again when its stable key has already been observed.
        session.loss = False
        self.assertFalse(provider.append_request(row)['created'])
        self.assertEqual(session.appends, 1)
        post = next(call for call in session.calls if call[0] == 'POST')
        self.assertTrue(post[1].endswith('Requests%21A5%3AN:append'))
        self.assertEqual(post[2]['params']['valueInputOption'], 'RAW')
        self.assertEqual(post[2]['json']['values'], [[row[field] for field in FIELDS]])
        self.assertTrue(self.guards.count(True) >= 1)
        ranges = next(call[2]['params']['ranges'] for call in session.calls if call[0] == 'GET' and call[1].endswith('/values:batchGet'))
        self.assertTrue(ranges[0].startswith('Requests!A4:'))
        self.assertTrue(ranges[1].startswith('Events!A4:'))

    def test_real_requests_wrapper_rejects_bad_headers_malformed_rows_and_duplicate_keys(self):
        from google_provider import FIELDS
        from service import Rejected
        provider, session, row = self.workbook_provider()
        for malformed in [dict(row, extra='not a column'), dict(row, proposal_state='ready_for_dev'), dict(row, site_id='other-site'), dict(row, assets_rights='権利確認済み'), dict(row, target='https://other.example.invalid')]:
            with self.subTest(malformed=malformed), self.assertRaises(Rejected):
                provider.append_request(malformed)
        self.assertEqual(session.appends, 0)
        session.requests[0][0] = 'wrong_header'
        with self.assertRaises(Rejected):
            provider.append_request(row)
        self.assertEqual(session.appends, 0)
        session.requests = [list(FIELDS), [row[field] for field in FIELDS], [row[field] for field in FIELDS]]
        with self.assertRaises(Rejected):
            provider.find_request(row['request_id'], '1')
        self.assertEqual(session.appends, 0)
        incomplete = dict(row, acceptance='')
        session.requests = [list(FIELDS), [incomplete[field] for field in FIELDS]]
        with self.assertRaises(Rejected):
            provider.find_request(row['request_id'], '1')
        self.assertEqual(session.appends, 0)

    def test_reporting_retry_generation_backoff_and_attention_stop_queue(self):
        harness = ReportingTests(methodName='test_duplicate_reports_append_and_send_once_with_exact_durable_envelope')
        harness.setUp()
        harness.reporter.sheets_factory = None
        harness.update('operation:' + harness.operation_id, queue_state='sent', retry_generation=4, retry_at=harness.now + 50)
        result = harness.result()
        self.assertEqual(result['state'], 'pending')
        op = harness.store.get('operation:' + harness.operation_id)
        self.assertEqual(op['queue_state'], 'pending')
        self.assertEqual(op['retry_generation'], 5)
        self.assertEqual(op['retry_at'], harness.now + 50)
        harness.reporter.sheets_factory = lambda site, guard: harness.sheets
        harness.update('site:' + harness.site_id, recipient='other@example.invalid')
        result = harness.result()
        self.assertEqual(result['state'], 'needs_attention')
        op = harness.store.get('operation:' + harness.operation_id)
        self.assertNotIn('queue_state', op)
        self.assertTrue(op['reporting_required'])


if __name__ == '__main__':
    unittest.main()
