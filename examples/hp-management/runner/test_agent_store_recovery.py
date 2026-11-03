"""Regression coverage for durable HP recovery state.

These tests exercise SQLite only. They never start Codex or call Sheets, Gmail,
GitHub, AWS, or a network provider.
"""
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from agent_store import AgentStore
import test_ledger


class AgentStoreRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'state.sqlite3'
        self.now = [1000.0]
        self.store = AgentStore(self.path, clock=lambda: self.now[0], stage_timeout_seconds=100)
        fixture = test_ledger.LedgerTestCase()
        self.config = fixture.config()
        self.request = fixture.request()
        self.store.execute('config', {'config': self.config})
        self.store.execute('ingest', {'request': self.request})
        self.store.add_job(self.request)
        self.key = ('clinic', test_ledger.REQUEST_ID, 1)
        self.claim = self.store.execute('claim', {**self.request, 'owner': 'test', 'ttl': 100})
        self.token = self.claim['token']

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_add_job_creates_runtime_and_backfills_missing_runtime(self):
        self.assertEqual('queued', self.store.runtime(self.key)['stage'])
        self.store.connection.execute('DELETE FROM agent_job_runtime WHERE site_id=? AND request_id=? AND revision=?', self.key)
        self.store.close()
        self.store = AgentStore(self.path, clock=lambda: self.now[0], stage_timeout_seconds=100)
        runtime = self.store.runtime(self.key)
        self.assertEqual(('queued', 1, 0), (runtime['stage'], runtime['attempt'], runtime['failures']))

    def test_same_stage_keeps_error_and_deadline_but_forward_progress_resolves_incident(self):
        self.store.set_error(self.key, 'worker_timeout')
        before = self.store.runtime(self.key)
        self.now[0] += 4
        self.store.save(self.key, 'queued', {'checkpoint': True}, self.token)
        same = self.store.runtime(self.key)
        self.assertEqual(before['deadline_at'], same['deadline_at'])
        self.assertEqual(before['progress_at'], same['progress_at'])
        self.assertEqual('worker_timeout', self.store.job(self.key)['error'])
        self.assertTrue(any(i['resolved_at'] is None for i in self.store.incidents()))
        self.store.save(self.key, 'coding', {'checkpoint': True}, self.token)
        self.assertIsNone(self.store.job(self.key)['error'])
        self.assertEqual(0, self.store.runtime(self.key)['failures'])
        self.assertTrue(all(i['resolved_at'] is not None for i in self.store.incidents()))

    def test_retry_is_bounded_keeps_deadline_and_requires_due_typed_resume(self):
        before = self.store.runtime(self.key)
        result = self.store.fail_job(self.key, 'worker_timeout', 'queued', retryable=True,
                                     max_retries=2, base_delay=10)
        self.assertEqual('retry_wait', result['stage'])
        runtime = self.store.runtime(self.key)
        self.assertEqual(before['deadline_at'], runtime['deadline_at'])
        with self.assertRaisesRegex(ValueError, 'retry_not_due'):
            self.store.resume_job(self.key, 'queued', new_attempt=True)
        self.now[0] = result['retry_at']
        resumed = self.store.resume_job(self.key, 'queued', new_attempt=True)
        self.assertEqual(('queued', 2), (resumed['stage'], resumed['attempt']))
        self.assertEqual(before['deadline_at'], self.store.runtime(self.key)['deadline_at'])
        self.assertEqual(1, self.store.runtime(self.key)['failures'])
        self.assertTrue(any(i['resolved_at'] is None for i in self.store.incidents()))
        # `coding` is an intermediate retry state; a validated candidate is
        # the first success beyond the queued recovery target.
        self.store.save(self.key, 'verifying', {'verified': True}, self.token)
        self.assertTrue(all(i['resolved_at'] is not None for i in self.store.incidents()))

    def test_auto_retry_budget_is_cumulative_until_real_forward_progress(self):
        first = self.store.fail_job(self.key, 'worker_timeout', 'queued', retryable=True,
                                    max_retries=2, base_delay=10)
        self.now[0] = first['retry_at']
        self.store.resume_job(self.key, 'queued')
        second = self.store.fail_job(self.key, 'worker_timeout', 'queued', retryable=True,
                                     max_retries=2, base_delay=10)
        self.assertEqual(('retry_wait', 2), (second['stage'], second['failures']))
        self.now[0] = second['retry_at']
        self.store.resume_job(self.key, 'queued')
        exhausted = self.store.fail_job(self.key, 'worker_timeout', 'queued', retryable=True,
                                        max_retries=2, base_delay=10)
        self.assertEqual(('needs_input', 3), (exhausted['stage'], exhausted['failures']))

    def test_ambiguous_reconciliation_cycle_cannot_reset_its_budget(self):
        self.store.save(self.key, 'candidate', {'candidate': True}, self.token)
        initial = self.store.runtime(self.key)
        for expected_failures in (1, 2):
            failed = self.store.fail_job(self.key, 'response_lost', 'candidate', retryable=True,
                                         max_retries=2, base_delay=10)
            self.assertEqual(('retry_wait', expected_failures), (failed['stage'], failed['failures']))
            self.now[0] = failed['retry_at']
            self.store.resume_job(self.key, 'candidate')
            # An absent provider readback parks again; it is not progress.
            self.store.save(self.key, 'provider_reconciliation_required', {'provider_recovery': {}}, self.token)
            runtime = self.store.runtime(self.key)
            self.assertEqual(('candidate', expected_failures, initial['deadline_at']),
                             (runtime['resume_stage'], runtime['failures'], runtime['deadline_at']))
        exhausted = self.store.fail_job(self.key, 'provider_reconciliation_required', 'candidate', retryable=True,
                                        max_retries=2, base_delay=10)
        self.assertEqual(('needs_input', 3), (exhausted['stage'], exhausted['failures']))
        self.assertEqual(initial['deadline_at'], self.store.runtime(self.key)['deadline_at'])
        self.store.resume_job(self.key, 'candidate', reset_budget=True)
        self.store.save(self.key, 'ci', {'reconciled': True}, self.token)
        advanced = self.store.runtime(self.key)
        self.assertIsNone(advanced['resume_stage'])
        self.assertEqual(0, advanced['failures'])

    def test_stopped_terminal_closes_a_pending_recovery_cycle(self):
        self.store.fail_job(self.key, 'worker_timeout', 'queued', retryable=False)
        self.assertEqual('queued', self.store.runtime(self.key)['resume_stage'])
        self.store.save(self.key, 'stopped', {}, None)
        self.assertIsNone(self.store.runtime(self.key)['resume_stage'])
        self.assertTrue(all(i['resolved_at'] is not None for i in self.store.incidents()))

    def test_explicit_resume_can_start_a_new_bounded_budget_without_resolving_incident(self):
        self.store.fail_job(self.key, 'worker_timeout', 'queued', retryable=False)
        old = self.store.runtime(self.key)
        self.now[0] += 5
        resumed = self.store.resume_job(self.key, 'queued', new_attempt=True, reset_budget=True)
        current = self.store.runtime(self.key)
        self.assertEqual(2, resumed['attempt'])
        self.assertEqual(0, current['failures'])
        self.assertEqual(self.now[0] + 100, current['deadline_at'])
        self.assertGreater(current['deadline_at'], old['deadline_at'])
        self.assertTrue(any(i['resolved_at'] is None for i in self.store.incidents()))

    def test_storewide_incident_resolves_without_touching_a_request_incident(self):
        self.store.set_error(self.key, 'worker_timeout')
        self.store.open_incident(None, 'intake_unavailable')
        self.assertEqual(2, len([i for i in self.store.incidents() if i['resolved_at'] is None]))
        self.store.resolve_incidents(None)
        open_rows = [i for i in self.store.incidents() if i['resolved_at'] is None]
        self.assertEqual(['worker_timeout'], [i['code'] for i in open_rows])

    def test_exhausted_retry_parks_for_operator(self):
        result = self.store.fail_job(self.key, 'worker_timeout', 'queued', retryable=True,
                                     max_retries=0, base_delay=10)
        self.assertEqual('needs_input', result['stage'])
        self.assertIsNone(result['retry_at'])

    def test_recovered_worker_waits_without_consuming_attempt_execution_time(self):
        failure = self.store.fail_job(self.key, 'worker_failed', 'queued',
                                      retryable=True, max_retries=2, base_delay=10)
        self.now[0] = failure['retry_at']
        self.store.resume_job(self.key, 'queued', new_attempt=True)
        self.now[0] += 200
        self.store.save(self.key, 'worker_starting', {}, self.token)
        runtime = self.store.runtime(self.key)
        self.assertEqual(self.now[0] + 100, runtime['deadline_at'])
        self.assertEqual((1, 2, 'queued'), (runtime['failures'], runtime['attempt'], runtime['resume_stage']))
        self.assertTrue(any(i['resolved_at'] is None for i in self.store.incidents()))
        self.store.save(self.key, 'coding', {}, self.token)
        self.assertEqual(runtime['deadline_at'], self.store.runtime(self.key)['deadline_at'])

    def test_incident_acknowledgement_preserves_audit_record(self):
        self.store.set_error(self.key, 'google_auth_expired')
        incident = next(i for i in self.store.incidents() if i['resolved_at'] is None)
        acknowledged = self.store.acknowledge(incident['key'], 'operator@example.com')
        self.assertEqual('operator@example.com', acknowledged['acknowledged_by'])
        self.store.resolve_incidents(self.key)
        saved = next(i for i in self.store.incidents() if i['key'] == incident['key'])
        self.assertIsNotNone(saved['resolved_at'])
        self.assertIsNotNone(saved['acknowledged_at'])

    def test_not_started_effect_requires_fresh_lease_before_readmission(self):
        request = {**self.request, 'token': self.token}
        first = self.store.effect(request, 'candidate', {'body': 'one'})
        self.assertEqual('new', first['state'])
        self.store.abandon_not_started(first['key'])
        retry = self.store.effect(request, 'candidate', {'body': 'one'})
        self.assertEqual('new', retry['state'])
        self.assertEqual('admitted', self.store.row('SELECT state FROM agent_effects WHERE key=?', (first['key'],))['state'])
        with self.assertRaisesRegex(ValueError, 'effect_input_conflict'):
            self.store.effect(request, 'candidate', {'body': 'different'})

    def test_notification_not_started_can_only_return_to_reservation_under_lease(self):
        proof = {**test_ledger.LedgerTestCase().identity(), 'run_id': 1, 'run_attempt': 1,
                 'url': self.config['dev_url'], 'tests_passed': True}
        self.store.execute('preview', {**self.request, 'token': self.token, **proof})
        reserved = self.store.execute('outbox-reserve', {**self.request, 'token': self.token, 'kind': 'preview_ready'})
        admitted = self.store.execute('outbox-admit', {**self.request, 'token': self.token,
                                                        'kind': 'preview_ready', 'key': reserved['key']})
        self.assertTrue(admitted['may_send'])
        self.store.notification_not_started(reserved['key'], self.token)
        self.assertEqual('reserved', self.store.retry_notification(reserved['key'], self.token)['state'])
        second = self.store.execute('outbox-admit', {**self.request, 'token': self.token,
                                                      'kind': 'preview_ready', 'key': reserved['key']})
        self.assertTrue(second['may_send'])


if __name__ == '__main__':
    unittest.main()
