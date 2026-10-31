"""Behavioral tests for the local HP delivery control ledger."""
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from ledger import Ledger


REQUEST_ID = '11111111-1111-4111-8111-111111111111'
SOURCE_SHA = 'a' * 40
ARTIFACT_HASH = 'b' * 64


class LedgerTestCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.directory.name, 'ledger.sqlite3')
        self.now = [1_000.0]
        self.ledger = Ledger(self.path, clock=lambda: self.now[0])
        self.configure()
        self.ingest()

    def tearDown(self):
        self.ledger.close()
        self.directory.cleanup()

    def config(self, **overrides):
        return {
            'site_id': 'clinic',
            'sheet_id': 'sheet_123456789',
            'repo': 'owner/repo',
            'content_path': 'site/content.json',
            'dev_url': 'https://dev.example',
            'prod_url': 'https://www.example',
            'recipient': 'clinic@example.com',
            'requester_ref': 'customer-1',
            'notification_recipient_ref': 'recipient-1',
            **overrides,
        }

    def request(self, revision='1', **overrides):
        return {
            'request_id': REQUEST_ID,
            'revision': revision,
            'site_id': 'clinic',
            'outcome': 'お知らせを追加',
            'target': 'https://dev.example/#news',
            'effective_at': '',
            'expires_at': '',
            'timezone': 'Asia/Tokyo',
            'assets_rights': 'confirmed',
            'dependencies': 'none',
            'acceptance': 'visible',
            'requester_ref': 'customer-1',
            'notification_recipient_ref': 'recipient-1',
            'proposal_state': 'ready_for_dev',
            **overrides,
        }

    def key(self, revision=1, **overrides):
        return {
            'site_id': 'clinic',
            'request_id': REQUEST_ID,
            'revision': revision,
            **overrides,
        }

    def identity(self, **overrides):
        return {
            'source_sha': SOURCE_SHA,
            'artifact_id': '123',
            'artifact_hash': ARTIFACT_HASH,
            **overrides,
        }

    def configure(self, **overrides):
        return self.ledger.execute('config', {'config': self.config(**overrides)})

    def ingest(self, revision='1', **overrides):
        return self.ledger.execute('ingest', {'request': self.request(revision, **overrides)})

    def claim(self, revision=1, owner='developer', ttl=120):
        return self.ledger.execute('claim', self.key(revision, owner=owner, ttl=ttl))

    def preview(self, token, revision=1, **overrides):
        return self.ledger.execute('preview', self.key(
            revision,
            token=token,
            run_id=41_234_567_890,
            run_attempt=1,
            url='https://dev.example',
            tests_passed=True,
            **self.identity(**overrides),
        ))

    def approved(self):
        claim = self.claim()
        self.preview(claim['token'])
        self.ledger.execute('approve', self.key(
            **self.identity(), human_confirmation_ref='operator-confirmation:42'
        ))
        return claim

    def assert_error(self, code, operation, data):
        with self.assertRaisesRegex(ValueError, '^' + code + '$'):
            self.ledger.execute(operation, data)

    def test_lifecycle_requires_exact_approval_and_publishes_approved_artifact(self):
        claim = self.claim()
        self.assertEqual('preview_ready', self.preview(claim['token'])['state'])
        self.assert_error(
            'approval_artifact_mismatch',
            'approve',
            self.key(**self.identity(artifact_id='124'), human_confirmation_ref='operator:1'),
        )
        approval = self.ledger.execute('approve', self.key(
            **self.identity(), human_confirmation_ref='operator-confirmation:42'
        ))
        self.assertEqual({'state': 'approved', 'reused': False}, approval)
        publication = self.ledger.execute('publish', self.key(
            token=claim['token'],
            release_sha='c' * 40,
            url='https://www.example',
            run_id=11,
            readback_verified=True,
            **self.identity(),
        ))
        self.assertEqual({'state': 'published', 'reused': False}, publication)
        status = self.ledger.execute('status', self.key())
        self.assertEqual('published', status['state'])
        self.assertEqual('operator-confirmation:42', status['approval']['human_confirmation_ref'])

    def test_replay_revision_conflict_and_supersession_fail_closed(self):
        replay = self.ingest()
        self.assertTrue(replay['reused'])
        self.assert_error('request_conflict', 'ingest', {
            'request': self.request(outcome='別のお知らせ')
        })

        old_claim = self.claim()
        self.preview(old_claim['token'])
        self.ledger.execute('approve', self.key(
            **self.identity(), human_confirmation_ref='operator:old'
        ))
        self.ingest('2', outcome='更新済みお知らせ')
        self.assert_error('request_superseded', 'publish', self.key(
            token=old_claim['token'],
            release_sha='c' * 40,
            url='https://www.example',
            run_id=11,
            readback_verified=True,
            **self.identity(),
        ))
        self.assertEqual('superseded', self.ledger.execute('status', self.key())['state'])
        self.assertEqual('queued', self.ledger.execute('status', self.key(2))['state'])

    def test_lease_expiry_renew_cancel_revoke_and_config_drift(self):
        claim = self.claim(ttl=60)
        self.now[0] += 61
        self.assert_error('lease_unavailable', 'renew', self.key(token=claim['token'], ttl=60))
        self.assert_error('invalid_positive_integer', 'claim', self.key(owner='bad', ttl=0))
        self.assert_error('lease_ttl_exceeded', 'claim', self.key(owner='bad', ttl=3601))

        new_claim = self.claim(owner='next')
        self.ledger.execute('cancel', self.key(reason='customer withdrew request'))
        self.assert_error('request_inactive', 'preview', self.key(
            token=new_claim['token'], run_id=10, run_attempt=1,
            url='https://dev.example', tests_passed=True, **self.identity(),
        ))

        self.ingest('2')
        self.ledger.execute('revoke', self.key(2, reason='access revoked'))
        self.assert_error('request_inactive', 'claim', self.key(2, owner='developer', ttl=60))

        self.ingest('3')
        self.configure(recipient='changed@example.com')
        self.assert_error('config_drift', 'claim', self.key(3, owner='developer', ttl=60))

    def test_outbox_admission_deduplicates_and_requires_provider_readback(self):
        claim = self.claim()
        self.preview(claim['token'])
        reserve = self.ledger.execute('outbox-reserve', self.key(
            token=claim['token'], kind='preview_ready'
        ))
        self.assertTrue(reserve['created'])
        self.assertFalse(reserve['may_send'])
        self.assertEqual('reserved', reserve['state'])
        duplicate = self.ledger.execute('outbox-reserve', self.key(
            token=claim['token'], kind='preview_ready'
        ))
        self.assertFalse(duplicate['created'])
        self.assertFalse(duplicate['may_send'])

        admission = self.ledger.execute('outbox-admit', self.key(
            token=claim['token'], kind='preview_ready', key=reserve['key']
        ))
        self.assertTrue(admission['may_send'])
        self.assertEqual('sending', admission['state'])
        self.assertEqual('clinic@example.com', admission['envelope']['to'])
        repeated_admission = self.ledger.execute('outbox-admit', self.key(
            token=claim['token'], kind='preview_ready', key=reserve['key']
        ))
        self.assertFalse(repeated_admission['may_send'])
        self.assertEqual('sending', repeated_admission['state'])

        ambiguous = self.ledger.execute('outbox-record', self.key(
            token=claim['token'], key=reserve['key'], state='ambiguous'
        ))
        self.assertEqual('ambiguous', ambiguous['state'])

        self.assert_error('invalid_text', 'outbox-record', self.key(
            token=claim['token'], key=reserve['key'], state='provider_accepted',
            readback_verified=True,
        ))
        accepted = self.ledger.execute('outbox-record', self.key(
            token=claim['token'], key=reserve['key'], state='provider_accepted',
            provider_message_id='mail-123', readback_verified=True,
        ))
        self.assertEqual('provider_accepted', accepted['state'])
        self.assert_error('invalid_text', 'outbox-record', self.key(
            token=claim['token'], key=reserve['key'], state='inbox_verified',
            provider_message_id='mail-123', readback_verified=True,
        ))
        inbox = self.ledger.execute('outbox-record', self.key(
            token=claim['token'], key=reserve['key'], state='inbox_verified',
            provider_message_id='mail-123', readback_verified=True,
            inbox_evidence_ref='inbox-thread:123',
        ))
        self.assertEqual('inbox_verified', inbox['state'])
        result = self.ledger.execute('outbox-query', self.key())
        self.assertEqual(['inbox_verified'], [item['state'] for item in result['notifications']])

    def test_invalid_content_path_is_rejected(self):
        for path in ('../escape', '.', ''):
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError, '^invalid_content_path$'):
                    self.ledger.execute('config', {'config': self.config(content_path=path)})

    def test_github_sized_run_id_is_accepted(self):
        claim = self.claim()
        preview = self.ledger.execute('preview', self.key(
            token=claim['token'],
            run_id=41_234_567_890,
            run_attempt=1,
            url='https://dev.example',
            tests_passed=True,
            **self.identity(),
        ))
        self.assertEqual('preview_ready', preview['state'])

    def test_separate_connections_race_to_claim_exactly_once(self):
        # Each worker opens its own SQLite connection inside its own thread.
        barrier = threading.Barrier(2)
        results = []
        errors = []
        result_lock = threading.Lock()

        def contender(owner):
            ledger = None
            try:
                ledger = Ledger(self.path, clock=lambda: self.now[0])
                barrier.wait()
                result = ledger.execute('claim', self.key(owner=owner, ttl=120))
                with result_lock:
                    results.append(result)
            except ValueError as error:
                with result_lock:
                    errors.append(str(error))
            finally:
                if ledger is not None:
                    ledger.close()

        first = threading.Thread(target=contender, args=('developer-a',))
        second = threading.Thread(target=contender, args=('developer-b',))
        first.start()
        second.start()
        first.join()
        second.join()
        self.assertEqual(1, len(results))
        self.assertEqual(['lease_busy'], errors)

    def test_stale_token_cannot_release_a_replacement_lease(self):
        first = self.claim(ttl=1)
        self.now[0] += 2
        replacement = self.claim(owner='replacement')
        stale_release = self.ledger.execute('release', self.key(token=first['token']))
        self.assertEqual({'released': False}, stale_release)
        self.assertEqual('preview_ready', self.preview(replacement['token'])['state'])

    def test_request_binding_mismatch_is_rejected_for_requester_and_recipient(self):
        for field in ('requester_ref', 'notification_recipient_ref'):
            with self.subTest(field=field):
                request = self.request(request_id='22222222-2222-4222-8222-222222222222')
                request[field] = 'different-binding'
                self.assert_error('request_binding_mismatch', 'ingest', {'request': request})

        cross_site = self.request(
            request_id='33333333-3333-4333-8333-333333333333',
            site_id='other-clinic',
            target='https://dev.example/#news',
        )
        self.assert_error('config_missing', 'ingest', {'request': cross_site})

    def test_preview_and_publication_reject_wrong_or_unapproved_evidence(self):
        claim = self.claim()
        self.assert_error('preview_evidence_invalid', 'preview', self.key(
            token=claim['token'], run_id=10, run_attempt=1,
            url='https://wrong.example', tests_passed=True, **self.identity(),
        ))
        self.assert_error('preview_evidence_invalid', 'preview', self.key(
            token=claim['token'], run_id=10, run_attempt=1,
            url='https://dev.example', tests_passed=False, **self.identity(),
        ))
        self.preview(claim['token'])
        self.assert_error('publication_artifact_mismatch', 'publish', self.key(
            token=claim['token'], release_sha='c' * 40, url='https://www.example',
            run_id=11, readback_verified=True, **self.identity(),
        ))
        self.ledger.execute('approve', self.key(
            **self.identity(), human_confirmation_ref='operator-confirmation:publication'
        ))
        self.assert_error('publication_not_verified', 'publish', self.key(
            token=claim['token'], release_sha='c' * 40, url='https://wrong.example',
            run_id=11, readback_verified=True, **self.identity(),
        ))

    def test_immutable_replays_are_idempotent_but_divergence_conflicts(self):
        claim = self.claim()
        first_preview = self.preview(claim['token'])
        self.assertFalse(first_preview['reused'])
        self.assertTrue(self.preview(claim['token'])['reused'])
        self.assert_error('preview_conflict', 'preview', self.key(
            token=claim['token'], run_id=41_234_567_890, run_attempt=1,
            url='https://dev.example', tests_passed=True,
            **self.identity(source_sha='d' * 40),
        ))
        first_approval = self.ledger.execute('approve', self.key(
            **self.identity(), human_confirmation_ref='operator-confirmation:immutable'
        ))
        self.assertFalse(first_approval['reused'])
        self.assertTrue(self.ledger.execute('approve', self.key(
            **self.identity(), human_confirmation_ref='operator-confirmation:immutable'
        ))['reused'])
        self.assert_error('approval_conflict', 'approve', self.key(
            **self.identity(), human_confirmation_ref='operator-confirmation:different'
        ))
        publication_data = self.key(
            token=claim['token'], release_sha='c' * 40, url='https://www.example',
            run_id=12, readback_verified=True, **self.identity(),
        )
        self.assertFalse(self.ledger.execute('publish', publication_data)['reused'])
        self.assertTrue(self.ledger.execute('publish', publication_data)['reused'])
        self.assert_error('publication_conflict', 'publish', self.key(
            token=claim['token'], release_sha='c' * 40, url='https://www.example',
            run_id=13, readback_verified=True, **self.identity(),
        ))

    def test_write_lock_expiry_prevents_preview_after_waiting_for_lock(self):
        claim = self.claim(ttl=1)
        lock_acquired = threading.Event()
        attempted_preview = threading.Event()
        errors = []
        errors_lock = threading.Lock()

        def delayed_preview():
            ledger = None
            try:
                ledger = Ledger(self.path, clock=lambda: self.now[0])
                lock_acquired.wait()
                attempted_preview.set()
                ledger.execute('preview', self.key(
                    token=claim['token'], run_id=10, run_attempt=1,
                    url='https://dev.example', tests_passed=True, **self.identity(),
                ))
            except ValueError as error:
                with errors_lock:
                    errors.append(str(error))
            finally:
                if ledger is not None:
                    ledger.close()

        worker = threading.Thread(target=delayed_preview)
        worker.start()
        self.ledger.connection.execute('BEGIN IMMEDIATE')
        lock_acquired.set()
        self.assertTrue(attempted_preview.wait(timeout=2))
        self.now[0] += 2
        self.ledger.connection.commit()
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(['lease_unavailable'], errors)

    def test_separate_connections_race_to_admit_outbox_once(self):
        claim = self.claim()
        self.preview(claim['token'])
        reservation = self.ledger.execute('outbox-reserve', self.key(
            token=claim['token'], kind='preview_ready'
        ))
        barrier = threading.Barrier(2)
        results = []
        errors = []
        result_lock = threading.Lock()

        def admit():
            ledger = None
            try:
                ledger = Ledger(self.path, clock=lambda: self.now[0])
                barrier.wait()
                result = ledger.execute('outbox-admit', self.key(
                    token=claim['token'], kind='preview_ready', key=reservation['key']
                ))
                with result_lock:
                    results.append(result)
            except ValueError as error:
                with result_lock:
                    errors.append(str(error))
            finally:
                if ledger is not None:
                    ledger.close()

        first = threading.Thread(target=admit)
        second = threading.Thread(target=admit)
        first.start()
        second.start()
        first.join()
        second.join()
        self.assertEqual([], errors)
        self.assertEqual(2, len(results))
        self.assertEqual([False, True], sorted(result['may_send'] for result in results))
        self.assertEqual(1, len({result['key'] for result in results}))

    def test_reserved_notification_does_not_block_cancellation_revision_or_config_change(self):
        claim = self.claim()
        self.preview(claim['token'])
        self.ledger.execute('outbox-reserve', self.key(
            token=claim['token'], kind='preview_ready'
        ))
        self.ledger.execute('cancel', self.key(reason='cancel before provider admission'))
        self.assertEqual('cancelled', self.ledger.execute('status', self.key())['state'])

        self.ingest('2')
        claim = self.claim(revision=2)
        self.preview(claim['token'], revision=2)
        self.ledger.execute('outbox-reserve', self.key(
            2, token=claim['token'], kind='preview_ready'
        ))
        self.configure(recipient='new-recipient@example.com')
        self.assertEqual(2, self.configure(recipient='new-recipient@example.com')['config_revision'])

    def test_stale_reserved_notification_cannot_be_admitted_after_lease_expiry(self):
        claim = self.claim(ttl=1)
        self.preview(claim['token'])
        reservation = self.ledger.execute('outbox-reserve', self.key(
            token=claim['token'], kind='preview_ready'
        ))
        self.now[0] += 2
        self.assert_error('lease_unavailable', 'outbox-admit', self.key(
            token=claim['token'], kind='preview_ready', key=reservation['key']
        ))

    def test_admitted_delivery_blocks_mutation_until_reconciled_after_lease_expiry(self):
        claim = self.claim(ttl=1)
        self.preview(claim['token'])
        reservation = self.ledger.execute('outbox-reserve', self.key(
            token=claim['token'], kind='preview_ready'
        ))
        admission = self.ledger.execute('outbox-admit', self.key(
            token=claim['token'], kind='preview_ready', key=reservation['key']
        ))
        self.assertTrue(admission['may_send'])
        self.assert_error('delivery_reconciliation_required', 'cancel', self.key(
            reason='must not cancel an admitted provider effect'
        ))
        self.now[0] += 2
        receipt = self.ledger.execute('outbox-record', {
            'key': reservation['key'],
            'token': claim['token'],
            'state': 'provider_accepted',
            'provider_message_id': 'mail-after-expiry',
            'readback_verified': True,
        })
        self.assertEqual('provider_accepted', receipt['state'])
        self.ingest('2')
        self.assertEqual('queued', self.ledger.execute('status', self.key(2))['state'])

    def test_sending_or_ambiguous_delivery_blocks_all_effects_until_provider_acceptance(self):
        claim = self.approved()
        reservation = self.ledger.execute('outbox-reserve', self.key(
            token=claim['token'], kind='preview_ready'
        ))
        self.ledger.execute('outbox-admit', self.key(
            token=claim['token'], kind='preview_ready', key=reservation['key']
        ))
        blocked_operations = (
            ('config', {'config': self.config(recipient='blocked@example.com')}),
            ('ingest', {'request': self.request('2')}),
            ('claim', self.key(owner='other-developer', ttl=60)),
            ('cancel', self.key(reason='blocked cancellation')),
            ('revoke', self.key(reason='blocked revocation')),
            ('publish', self.key(
                token=claim['token'], release_sha='c' * 40, url='https://www.example',
                run_id=11, readback_verified=True, **self.identity(),
            )),
        )
        for operation, data in blocked_operations:
            with self.subTest(operation=operation, state='sending'):
                self.assert_error('delivery_reconciliation_required', operation, data)

        self.ledger.execute('outbox-record', {
            'key': reservation['key'], 'token': claim['token'], 'state': 'ambiguous',
        })
        for operation, data in blocked_operations:
            with self.subTest(operation=operation, state='ambiguous'):
                self.assert_error('delivery_reconciliation_required', operation, data)

        self.ledger.execute('outbox-record', {
            'key': reservation['key'],
            'token': claim['token'],
            'state': 'provider_accepted',
            'provider_message_id': 'mail-reconciled',
            'readback_verified': True,
        })
        self.ingest('2')
        self.assertEqual('queued', self.ledger.execute('status', self.key(2))['state'])


if __name__ == '__main__':
    unittest.main()
