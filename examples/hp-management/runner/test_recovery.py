"""Failure recovery behaviour using local fakes only.

No test in this module talks to Google, GitHub, AWS, Gmail, or a real Codex
session.  The one process fixture is a Python sleep process launched by this
test and terminated only through its recorded, immediately rechecked PID.
"""
import copy
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent))

from agent import Agent
from agent_store import AgentStore
from codex_worker import atomic_json, process_identity
from provider_errors import AuthenticationRequired
from test_agent import GitHub, Mail, Sheets
import test_ledger


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.now = [1000.0]
        self.store = AgentStore(self.path / 'state.sqlite3', clock=lambda: self.now[0])
        fixture = test_ledger.LedgerTestCase()
        self.row = fixture.request()
        self.key = (self.row['site_id'], self.row['request_id'], 1)
        self.event = {
            'event_id': str(uuid4()), 'request_id': self.row['request_id'], 'revision': '1',
            'occurred_at': '2026-11-02T01:00:00Z', 'actor': 'customer', 'kind': 'ready_for_dev',
            'body': 'ready', 'reply_to_event_id': '', 'event_idempotency_key': 'ready',
        }
        self.sheets = Sheets(self.row, self.event)
        self.github = GitHub()
        self.config = {
            'site': fixture.config(), 'intake_start_at': '2026-11-02T00:00:00Z', 'notice_id': 'notice',
            'work_directory': str(self.path / 'work'), 'auto_merge_dev': True,
            'recovery': {'enabled': True, 'max_retries': 2, 'base_delay_seconds': 5, 'stage_timeout_seconds': 100},
        }
        self.workers = 0
        self.owned = []
        self.agent = self.make_agent()

    def tearDown(self):
        for process, record in self.owned:
            if process.poll() is None:
                # This fixture owns this exact process. Do not signal if the
                # recorded PID has changed identity.
                self.assertEqual(process_identity(process.pid), record['identity'])
                process.terminate()
                process.wait(timeout=5)
        self.store.close()
        self.temp.cleanup()

    def make_agent(self, *, worker=None, verifier=None, reviewer=None, mail=None):
        return Agent(self.config, self.store, self.sheets, self.github,
                     worker=worker or self.worker, verifier=verifier or self.verifier,
                     reviewer=reviewer or self.reviewer, clock=lambda: self.now[0], mail=mail)

    def worker(self, key, request, base, directory):
        self.workers += 1
        after = copy.deepcopy(base['content'])
        after['notices'][0]['body'] = 'changed'
        after['changeRequest'] = {'id': request['request_id'], 'revision': int(request['revision'])}
        child = directory / 'child'
        child.mkdir(parents=True, exist_ok=True)
        atomic_json(child / 'result.json', {'state': 'success', 'content': after})
        return {'pid': 1, 'identity': 'test-receipt'}

    def verifier(self, *_):
        return {'root_pristine_tests': True}

    def reviewer(self, *_):
        return {'approved': True, 'findings': []}

    def tick_until(self, stage, limit=20):
        for _ in range(limit):
            result = self.agent.tick()
            if result.get('stage') == stage:
                return result
        self.fail('stage not reached: ' + stage)

    def launch_owned_sleep_worker(self, key, request, base, directory):
        self.workers += 1
        (directory / 'control' / 'private').mkdir(parents=True, exist_ok=True)
        child = directory / 'child'
        child.mkdir(parents=True, exist_ok=True)
        (child / 'partial-result.txt').write_text('partial only')
        command = [sys.executable, '-c', 'import time; time.sleep(60)']
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        record = {
            'pid': process.pid, 'ppid': os.getpid(), 'command': command,
            'started_at': datetime.now(timezone.utc).isoformat(), 'identity': process_identity(process.pid),
        }
        self.assertTrue(record['identity'])
        self.owned.append((process, record))
        return record

    def test_stopped_worker_creates_new_attempt_without_reusing_old_workspace(self):
        self.agent = self.make_agent(worker=self.launch_owned_sleep_worker)
        self.assertEqual('coding', self.agent.tick()['stage'])
        first_process, first = self.owned[0]
        # Signal only the exact PID launched above, after checking its original
        # process identity; no name, group, or tree based operation is used.
        self.assertEqual(first['identity'], process_identity(first['pid']))
        first_process.terminate()
        first_process.wait(timeout=5)
        self.assertEqual('retry_wait', self.agent.tick()['stage'])
        runtime = self.store.runtime(self.key)
        self.now[0] = runtime['retry_at']
        self.assertEqual('coding', self.agent.tick()['stage'])
        root = self.path / 'work' / (self.key[1] + '-r1')
        self.assertTrue((root / 'child' / 'partial-result.txt').is_file())
        self.assertTrue((root / 'attempt-2' / 'child' / 'partial-result.txt').is_file())
        self.assertEqual(2, self.store.runtime(self.key)['attempt'])
        self.assertEqual(2, self.workers)
        self.assertEqual(0, self.github.candidates)

    def test_repeated_worker_failures_stop_after_the_configured_attempt_budget(self):
        self.agent = self.make_agent(worker=self.launch_owned_sleep_worker)
        max_retries = self.config['recovery']['max_retries']
        for attempt in range(1, max_retries + 2):
            self.assertEqual('coding', self.agent.tick()['stage'])
            process, record = self.owned[-1]
            self.assertEqual(record['identity'], process_identity(record['pid']))
            process.terminate()
            process.wait(timeout=5)
            result = self.agent.tick()
            if attempt <= max_retries:
                self.assertEqual('retry_wait', result['stage'])
                self.now[0] = self.store.runtime(self.key)['retry_at']
            else:
                self.assertEqual('needs_input', result['stage'])
        self.assertEqual(max_retries + 1, self.workers)
        self.store.close()
        self.store = AgentStore(self.path / 'state.sqlite3', clock=lambda: self.now[0])
        self.agent = self.make_agent(worker=self.launch_owned_sleep_worker)
        self.assertEqual('idle', self.agent.tick()['stage'])
        self.assertEqual(max_retries + 1, self.workers)
        self.assertEqual(0, self.store.row('SELECT COUNT(*) AS n FROM agent_effects')['n'])

    def test_due_worker_retry_can_wait_past_deadline_before_launch(self):
        self.agent = self.make_agent(worker=self.launch_owned_sleep_worker)
        self.assertEqual('coding', self.agent.tick()['stage'])
        process, record = self.owned[-1]
        self.assertEqual(record['identity'], process_identity(record['pid']))
        process.terminate()
        process.wait(timeout=5)
        self.assertEqual('retry_wait', self.agent.tick()['stage'])
        self.now[0] = self.store.runtime(self.key)['deadline_at'] + 100
        self.assertEqual('coding', self.agent.tick()['stage'])
        runtime = self.store.runtime(self.key)
        self.assertEqual(self.now[0] + 100, runtime['deadline_at'])
        self.assertEqual((1, 2, 'queued'), (runtime['failures'], runtime['attempt'], runtime['resume_stage']))
        self.assertTrue(any(i['resolved_at'] is None for i in self.store.incidents()))

    def test_verification_retry_reuses_candidate_without_new_worker(self):
        calls = []
        def verifier(*_):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError('owned_process_failed')
            return {'root_pristine_tests': True}
        self.agent = self.make_agent(verifier=verifier)
        self.tick_until('verifying')
        self.assertEqual('retry_wait', self.agent.tick()['stage'])
        candidate = self.store.job(self.key)['data']['candidate']
        self.now[0] = self.store.runtime(self.key)['retry_at']
        self.assertEqual('reviewing', self.agent.tick()['stage'])
        self.assertEqual(1, self.workers)
        self.assertEqual(candidate, self.store.job(self.key)['data']['candidate'])
        self.assertEqual(2, self.store.job(self.key)['data']['verification_attempt'])

    def test_reviewer_rejection_needs_new_revision_not_recovery(self):
        self.agent = self.make_agent(reviewer=lambda *_: (_ for _ in ()).throw(ValueError('independent_review_rejected')))
        self.tick_until('reviewing')
        self.assertEqual('needs_input', self.agent.tick()['stage'])
        with self.assertRaisesRegex(ValueError, 'new_revision_required_after_review_rejection'):
            self.agent.recover(self.key, 'resume', 'operator@example.com')
        self.assertEqual((1, 0), (self.workers, self.github.candidates))

    def test_review_interruption_retries_same_candidate_without_new_worker(self):
        calls = []
        def reviewer(*_):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError('owned_process_failed')
            return {'approved': True, 'findings': []}
        self.agent = self.make_agent(reviewer=reviewer)
        self.tick_until('reviewing')
        candidate = self.store.job(self.key)['data']['candidate']
        self.assertEqual('retry_wait', self.agent.tick()['stage'])
        self.now[0] = self.store.runtime(self.key)['retry_at']
        self.assertEqual('candidate', self.agent.tick()['stage'])
        self.assertEqual((1, 0), (self.workers, self.github.candidates))
        self.assertEqual(candidate, self.store.job(self.key)['data']['candidate'])
        self.assertEqual(2, self.store.job(self.key)['data']['review_attempt'])

    def test_cancel_before_due_retry_stops_without_new_worker_or_effect(self):
        self.agent = self.make_agent(worker=self.launch_owned_sleep_worker)
        self.assertEqual('coding', self.agent.tick()['stage'])
        process, record = self.owned[0]
        self.assertEqual(record['identity'], process_identity(record['pid']))
        process.terminate()
        process.wait(timeout=5)
        self.assertEqual('retry_wait', self.agent.tick()['stage'])
        self.sheets.events.append({**self.event, 'event_id': str(uuid4()), 'kind': 'request_cancelled',
                                   'event_idempotency_key': 'cancel'})
        self.now[0] = self.store.runtime(self.key)['retry_at']
        self.assertEqual('stopped', self.agent.tick()['stage'])
        self.assertEqual(1, self.workers)
        self.assertEqual(0, self.store.row('SELECT COUNT(*) AS n FROM agent_effects')['n'])

    def test_manual_recovery_rechecks_cancel_before_any_effect(self):
        self.agent = self.make_agent(verifier=lambda *_: (_ for _ in ()).throw(RuntimeError('owned_process_failed')))
        self.tick_until('verifying')
        self.assertEqual('retry_wait', self.agent.tick()['stage'])
        self.sheets.events.append({**self.event, 'event_id': str(uuid4()), 'kind': 'request_cancelled',
                                   'event_idempotency_key': 'cancel-before-manual-recover'})
        with self.assertRaisesRegex(ValueError, 'request_cancelled_on_sheet'):
            self.agent.recover(self.key, 'resume', 'operator@example.com')
        self.assertEqual((1, 0), (self.workers, self.github.candidates))
        self.assertEqual(0, self.store.row('SELECT COUNT(*) AS n FROM agent_effects')['n'])

    def test_superseded_parked_revision_is_retired_and_current_revision_progresses(self):
        self.store.execute('ingest', {'request': self.row})
        self.store.add_job(self.row)
        self.store.set_error(self.key, 'review_interrupted')
        self.store.save(self.key, 'needs_input', {'review_recovery': {'code': 'review_interrupted'}}, None)
        newer = {**self.row, 'revision': '2'}
        newer_key = (newer['site_id'], newer['request_id'], 2)
        self.store.execute('ingest', {'request': newer})
        self.store.add_job(newer)
        self.sheets.rows = [newer]
        self.sheets.events = [{**self.event, 'event_id': str(uuid4()), 'revision': '2', 'event_idempotency_key': 'ready-r2'}]
        self.assertEqual('coding', self.agent.tick()['stage'])
        self.assertEqual('stopped', self.store.job(self.key)['stage'])
        self.assertEqual('coding', self.store.job(newer_key)['stage'])
        self.assertFalse(any(i['resolved_at'] is None and i['revision'] == 1 for i in self.store.incidents()))

    def test_pending_admitted_effect_prevents_parked_revision_retirement(self):
        self.store.execute('ingest', {'request': self.row})
        self.store.add_job(self.row)
        claim = self.store.execute('claim', {**self.row, 'owner': 'test', 'ttl': 100})
        self.store.effect({**self.row, 'token': claim['token']}, 'candidate', {'body': 'unchanged'})
        self.store.set_error(self.key, 'response_lost')
        self.store.save(self.key, 'needs_input', {'provider_recovery': {'code': 'response_lost'}}, claim['token'])
        # This creates the legacy/migration condition directly. Normal ledger
        # ingestion correctly refuses to supersede an admitted effect.
        self.store.connection.execute("UPDATE requests SET state='superseded' WHERE site_id=? AND request_id=? AND revision=?", self.key)
        self.assertEqual('idle', self.agent.tick()['stage'])
        self.assertEqual('needs_input', self.store.job(self.key)['stage'])
        self.assertTrue(any(i['resolved_at'] is None and i['revision'] == 1 for i in self.store.incidents()))

    def test_deadline_exhaustion_parks_without_new_effect(self):
        self.tick_until('verifying')
        runtime = self.store.runtime(self.key)
        self.now[0] = runtime['deadline_at'] + 1
        self.assertEqual('needs_input', self.agent.tick()['stage'])
        self.assertEqual('stage_deadline_exceeded', self.store.job(self.key)['error'])
        self.assertEqual((1, 0), (self.workers, self.github.candidates))

    def test_authentication_failure_pauses_intake_until_explicit_reconnect(self):
        class FailingSheets(Sheets):
            def snapshot(inner):
                raise AuthenticationRequired('google', 'google_http_401', 401)
        self.sheets = FailingSheets(self.row, self.event)
        self.agent = self.make_agent()
        result = self.agent.tick()
        self.assertEqual(('intake_blocked', 'google_http_401'), (result['stage'], result['error']))
        self.assertEqual(1, self.store.service_runtime()['paused'])
        self.assertEqual('operator_reconnection_required', self.agent.tick()['error'])
        self.sheets = Sheets(self.row, self.event)
        self.agent.sheets = self.sheets
        self.assertEqual('intake_recovered', self.agent.recover_intake('operator@example.com')['stage'])
        self.assertEqual('coding', self.agent.tick()['stage'])

    def test_codex_auth_failed_worker_receipt_parks_without_automatic_retry(self):
        def auth_failed_worker(key, request, base, directory):
            self.workers += 1
            child = directory / 'child'
            child.mkdir(parents=True, exist_ok=True)
            atomic_json(child / 'result.json', {'state': 'failed', 'error': 'AuthenticationRequired'})
            return {'pid': 1, 'identity': 'test-receipt'}
        self.agent = self.make_agent(worker=auth_failed_worker)
        self.assertEqual('coding', self.agent.tick()['stage'])
        result = self.agent.tick()
        self.assertEqual(('needs_input', 'authentication_required'), (result['stage'], result['error']))
        self.assertEqual('authentication_required', self.store.job(self.key)['error'])
        self.assertIsNone(self.store.runtime(self.key)['retry_at'])
        self.assertEqual(1, self.workers)

    def test_intake_retry_limit_requires_explicit_reconnect(self):
        class FailingSheets(Sheets):
            def snapshot(inner):
                raise RuntimeError('network_timeout')
        self.sheets = FailingSheets(self.row, self.event)
        self.agent = self.make_agent()
        for expected_failures in (1, 2, 3):
            self.assertEqual('intake_blocked', self.agent.tick()['stage'])
            service = self.store.service_runtime()
            self.assertEqual(expected_failures, service['failures'])
            self.now[0] = service['retry_at']
        self.assertEqual('operator_reconnection_required', self.agent.tick()['error'])
        self.assertEqual(1, self.store.service_runtime()['paused'])

    def test_ambiguous_preview_email_readback_does_not_resend(self):
        class UncertainMail(Mail):
            def send_notice(inner, envelope, key):
                inner.sent.append((copy.deepcopy(envelope), key))
                raise RuntimeError('response_lost')
        mail = UncertainMail()
        self.config['mail_enabled'] = True
        self.agent = self.make_agent(mail=mail)
        self.tick_until('notification')
        self.assertEqual('retry_wait', self.agent.tick()['stage'])
        self.now[0] = self.store.runtime(self.key)['retry_at']
        self.assertEqual('awaiting_approval', self.agent.tick()['stage'])
        self.assertEqual(1, len(mail.sent))


if __name__ == '__main__':
    unittest.main()
