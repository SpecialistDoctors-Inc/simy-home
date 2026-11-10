"""Admission and exact-artifact approval regressions, no external effects."""
from copy import deepcopy
import json
import unittest
from uuid import uuid4

from service import Service, Rejected
from store import MemoryStore, Conflict


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.now = 1000
        self.service = Service(self.store, clock=lambda: self.now, publication_enabled=True)
        self.claims = {'sub': 'example-subject', 'email': 'member@example.invalid', 'scope': 'hp:read hp:write'}
        self.site_id = 'example-site'
        self.workspace_id = str(uuid4())
        self.preview_id = str(uuid4())
        self.store.put('principal:' + self.claims['sub'], {'sites': {self.site_id: ['read', 'edit', 'publish']}})
        self.store.put('site:' + self.site_id, {'name': 'Example Site', 'config_version': 1, 'initial_main_commit': 'a' * 40, 'dev_url': 'https://preview.example.invalid', 'prod_url': 'https://site.example.invalid', 'current_preview': self.preview_id, 'current_publication': 'old-publication'})
        self.store.put('workspace:' + self.workspace_id, {'workspace_id': self.workspace_id, 'site_id': self.site_id, 'subject': self.claims['sub'], 'head_commit': 'a' * 40})
        self.store.put('preview:' + self.preview_id, {'preview_id': self.preview_id, 'site_id': self.site_id, 'status': 'verified', 'source_commit': 'b' * 40, 'artifact_sha256': 'c' * 64, 'url': 'https://preview.example.invalid/current', 'summary': 'Update opening hours'})

    def update(self, key, **changes):
        value = self.store.get(key)
        value.update(changes)
        return self.store.put(key, value, value['_version'])

    def body(self):
        return dict(operation_id=str(uuid4()), site_id=self.site_id, workspace_id=self.workspace_id, base_commit='a' * 40, bundle_file_id='example-drive-file', bundle_sha256='d' * 64)

    def prepare(self):
        result = self.service.prepare_publish(self.claims, self.site_id, self.preview_id)
        return result['structuredContent']['approval_id'], result['_meta']['confirmation_nonce'], result

    def test_publication_details_freeze_the_exact_baseline_and_target(self):
        changes = {'base_commit': 'a'*40, 'items': [{'title': '診療時間', 'kind': 'changed', 'before': '18時', 'after': '19時'}], 'additional_count': 0}
        self.update('preview:' + self.preview_id, publication_changes=changes)
        self.update('site:' + self.site_id, current_publication={'artifact_sha256': 'd'*64})
        self.store.put('content-version:'+self.site_id+':'+'d'*64, {'version': 2})
        self.store.put('content-version:'+self.site_id+':'+'c'*64, {'version': 3})
        approval, _, result = self.prepare()
        details = result['structuredContent']['publication_details']
        self.assertEqual((details['from_version'], details['to_version']), (2, 3))
        self.assertEqual(details['changes']['items'][0]['after'], '19時')
        self.update('preview:' + self.preview_id, publication_changes={**changes, 'items': []})
        self.assertEqual(self.service.confirmation(self.claims, approval)['publication_details'], details)

    def test_summary_from_another_baseline_is_not_presented(self):
        self.update('preview:' + self.preview_id, publication_changes={'base_commit': 'e'*40, 'items': [], 'additional_count': 0})
        _, _, result = self.prepare()
        self.assertIsNone(result['structuredContent']['publication_details']['changes'])

    def operations(self):
        return {key: value for key, value in self.store.rows.items() if key.startswith('operation:')}

    def stopped(self, pending=True):
        operation = self.service.admit(self.claims, 'save_draft', self.body())['operation_id']
        changes = {'status': 'needs_attention', 'stage': 'preview_deploy', 'error': 'retry_budget_exhausted',
            'retry_attempts': 8, 'retry_generation': 11, 'retry_at': self.now + 500,
            'wait_deadline': self.now - 10, 'wait_stage': 'preview_deploy',
            'execution_site': {'site_id': self.site_id, 'config_version': 1},
            'phases': {'artifact_upload': {'key': 'exact-prior-artifact'}},
            'lease_owner': 'old-owner', 'lease_epoch': 4}
        if pending:
            changes['pending_effect'] = {'name': 'preview_deploy', 'lease_epoch': 4,
                'reconciliation': {'kind': 'preview_deploy', 'sealed': 'PRIVATE-BODY-NOT-FOR-AUDIT'}}
        self.update('operation:' + operation, **changes)
        self.store.put('lease:site:' + self.site_id, {'owner': 'old-owner', 'operation_id': operation,
            'blocked_operation': operation if pending else None, 'epoch': 4, 'until': 0})
        return operation

    def test_resume_audits_same_operation_and_preserves_all_sealed_work_and_deadlines(self):
        operation = self.stopped()
        key = 'operation:' + operation
        before = self.store.get(key)
        lease = self.store.get('lease:site:' + self.site_id)
        recovery = str(uuid4())
        result = self.service.resume(self.claims, operation, recovery)
        self.assertEqual((result['operation_id'], result['status']), (operation, 'reconciling'))
        after = self.store.get(key)
        changed = {'status', 'queue_state', 'retry_at', 'retry_attempts', 'retry_generation', 'error', '_version'}
        self.assertEqual({name:value for name,value in before.items() if name not in changed},
            {name:value for name,value in after.items() if name not in changed})
        self.assertEqual((after['queue_state'], after['retry_at'], after['retry_attempts'], after['retry_generation'], after['error']), ('pending', self.now, 0, 12, None))
        self.assertEqual(self.store.get('lease:site:' + self.site_id), lease)
        audit = self.store.get('resumption:' + recovery)
        self.assertEqual((audit['operation_id'], audit['subject'], audit['original_fingerprint']), (operation, self.claims['sub'], before['fingerprint']))
        self.assertEqual((audit['prior_error'], audit['prior_retry_attempts'], audit['prior_retry_generation'], audit['resumed_at']), ('retry_budget_exhausted', 8, 11, self.now))
        self.assertNotIn('PRIVATE-BODY-NOT-FOR-AUDIT', json.dumps(audit))
        self.assertFalse({'input', 'pending_effect', 'phases', 'execution_site'} & set(audit))
        self.assertEqual(len(self.operations()), 1)

    def test_resume_without_pending_queues_retry_wait_and_replay_after_running_does_not_reset(self):
        operation = self.stopped(pending=False)
        recovery = str(uuid4())
        self.assertEqual(self.service.resume(self.claims, operation, recovery)['status'], 'retry_wait')
        self.update('operation:' + operation, status='running', retry_attempts=3, retry_generation=18, retry_at=self.now + 30)
        self.update('lease:site:' + self.site_id, until=self.now + 300)
        before = deepcopy(self.store.rows)
        self.assertEqual(self.service.resume(self.claims, operation, recovery)['status'], 'running')
        self.assertEqual(self.store.rows, before)
        self.update('operation:' + operation, status='cancelled', cancel_requested=True)
        before = deepcopy(self.store.rows)
        self.assertEqual(self.service.resume(self.claims, operation, recovery)['status'], 'cancelled')
        self.assertEqual(self.store.rows, before)

    def test_resume_committed_response_loss_replays_existing_audit_without_second_reset(self):
        operation = self.stopped()
        recovery = str(uuid4())
        original = self.store.transact
        def lost(writes):
            original(writes)
            raise OSError('response lost after atomic admission')
        self.store.transact = lost
        with self.assertRaises(OSError):
            self.service.resume(self.claims, operation, recovery)
        before = deepcopy(self.store.rows)
        replay = self.service.resume(self.claims, operation, recovery)
        self.assertEqual(replay['status'], 'reconciling')
        self.assertEqual(self.store.rows, before)
        self.assertEqual(self.store.get('operation:' + operation)['retry_generation'], 12)
        self.assertEqual(self.store.get('resumption:' + recovery)['_version'], 1)

    def test_resume_reconciliation_flag_uses_reconciling_without_changing_old_fence(self):
        operation = self.stopped(pending=False)
        self.update('operation:' + operation, reconciliation_required=True)
        self.assertEqual(self.service.resume(self.claims, operation, str(uuid4()))['status'], 'reconciling')
        self.assertEqual(self.store.get('operation:' + operation)['lease_epoch'], 4)

    def test_resume_rejects_other_owner_insufficient_role_scope_and_binding_drift(self):
        operation = self.stopped()
        self.store.put('principal:other-subject', {'sites': {self.site_id: ['read', 'edit', 'publish']}})
        for claims in [dict(self.claims, sub='other-subject'), dict(self.claims, scope='hp:read')]:
            with self.subTest(claims=claims), self.assertRaises(Rejected):
                self.service.resume(claims, operation, str(uuid4()))
        original = deepcopy(self.store.rows)
        for mutation in [lambda: self.update('principal:' + self.claims['sub'], sites={self.site_id: ['read']}),
                         lambda: self.update('principal:' + self.claims['sub'], disabled=True),
                         lambda: self.update('principal:' + self.claims['sub'], sites={self.site_id: ['read', 'edit', 'publish']}),
                         lambda: self.update('site:' + self.site_id, config_version=2)]:
            with self.subTest(mutation=mutation):
                mutation()
                with self.assertRaises(Rejected):self.service.resume(self.claims, operation, str(uuid4()))
                self.assertEqual(self.store.get('operation:' + operation)['status'], 'needs_attention')
                self.assertFalse(any(key.startswith('resumption:') for key in self.store.rows))
                self.store.rows = deepcopy(original)

    def test_resume_rejects_active_other_blocked_lease_cancellation_and_terminal_reporting_states(self):
        operation = self.stopped()
        original = deepcopy(self.store.rows)
        mutations = [lambda: self.update('lease:site:' + self.site_id, until=self.now + 1),
            lambda: self.update('lease:site:' + self.site_id, blocked_operation=str(uuid4())),
            lambda: self.update('operation:' + operation, cancel_requested=True)]
        mutations += [lambda status=status: self.update('operation:' + operation, status=status)
            for status in ('cancelled', 'failed', 'completed', 'running', 'queued', 'retry_wait', 'reconciling', 'published_after_cancel_or_revocation')]
        mutations.append(lambda: self.update('operation:' + operation, status='completed', reporting_required=True, reporting_state='needs_attention'))
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                mutation(); before = deepcopy(self.store.rows)
                with self.assertRaises(Rejected):self.service.resume(self.claims, operation, str(uuid4()))
                self.assertEqual(self.store.rows, before)
                self.store.rows = deepcopy(original)

    def test_resume_recovery_id_conflicts_and_malformed_ids_do_not_rearm(self):
        operation = self.stopped()
        recovery = str(uuid4())
        self.service.resume(self.claims, operation, recovery)
        second = self.service.admit(self.claims, 'open_workspace', {'operation_id': str(uuid4()), 'site_id': self.site_id})['operation_id']
        self.update('operation:' + second, status='needs_attention')
        with self.assertRaisesRegex(Rejected, 'resumption_id_conflict'):
            self.service.resume(self.claims, second, recovery)
        for op, rec in [('bad', str(uuid4())), (operation, 'bad')]:
            with self.assertRaisesRegex(Rejected, 'invalid_id'):
                self.service.resume(self.claims, op, rec)
        self.assertEqual(self.store.get('operation:' + operation)['retry_generation'], 12)

    def test_publish_resume_requires_original_accepted_approval_and_never_creates_another(self):
        approval_id, nonce, _ = self.prepare()
        operation = self.service.confirm_publish(self.claims, approval_id, nonce)['operation_id']
        self.update('operation:' + operation, status='needs_attention', retry_attempts=8, error='retry_budget_exhausted')
        before = deepcopy(self.store.rows)
        self.service.publication_enabled = False
        with self.assertRaisesRegex(Rejected, 'publication_not_enabled'):
            self.service.resume(self.claims, operation, str(uuid4()))
        self.service.publication_enabled = True
        self.update('approval:' + approval_id, state='prepared')
        with self.assertRaisesRegex(Rejected, 'resumption_approval_invalid'):
            self.service.resume(self.claims, operation, str(uuid4()))
        self.store.rows = deepcopy(before)
        result = self.service.resume(self.claims, operation, str(uuid4()))
        self.assertEqual(result['operation_id'], operation)
        self.assertEqual(self.store.get('operation:' + operation)['input'], {'approval_id': approval_id})
        self.assertEqual(self.store.get('approval:' + approval_id), before['approval:' + approval_id])
        self.assertEqual(len(self.operations()), 1)
        self.assertEqual(sum(key.startswith('approval:') for key in self.store.rows), 1)

    def test_resume_transaction_checks_absent_lease_and_current_principal_site_operation_audit(self):
        operation = self.stopped()
        original = deepcopy(self.store.rows)
        for target in ('principal', 'site', 'operation', 'lease', 'audit'):
            with self.subTest(target=target):
                self.store.rows = deepcopy(original)
                recovery = str(uuid4())
                if target == 'lease':self.store.rows.pop('lease:site:' + self.site_id)
                def mutation():
                    if target == 'principal':self.update('principal:' + self.claims['sub'], disabled=True)
                    elif target == 'site':self.update('site:' + self.site_id, config_version=2)
                    elif target == 'operation':self.update('operation:' + operation, cancel_requested=True)
                    elif target == 'lease':self.store.put('lease:site:' + self.site_id, {'until': self.now + 300, 'blocked_operation': operation})
                    else:self.store.put('resumption:' + recovery, {'operation_id': 'other', 'subject': 'other'})
                self.race_before_transaction(mutation)
                with self.assertRaises(Conflict):self.service.resume(self.claims, operation, recovery)
                self.assertEqual(self.store.get('operation:' + operation)['status'], 'needs_attention')
                self.assertEqual(self.store.get('operation:' + operation)['retry_attempts'], 8)
                if target != 'audit':self.assertIsNone(self.store.get('resumption:' + recovery))

    def test_publish_resume_checks_original_approval_version_atomically(self):
        approval_id, nonce, _ = self.prepare()
        operation = self.service.confirm_publish(self.claims, approval_id, nonce)['operation_id']
        self.update('operation:' + operation, status='needs_attention')
        recovery = str(uuid4())
        self.race_before_transaction(lambda: self.update('approval:' + approval_id, state='revoked'))
        with self.assertRaises(Conflict):
            self.service.resume(self.claims, operation, recovery)
        self.assertEqual(self.store.get('operation:' + operation)['status'], 'needs_attention')
        self.assertIsNone(self.store.get('resumption:' + recovery))

    def test_resume_audit_does_not_copy_an_unclassified_error_body(self):
        operation = self.stopped()
        self.update('operation:' + operation, error='https://example.invalid/?token=PRIVATE-ERROR-BODY')
        recovery = str(uuid4())
        self.service.resume(self.claims, operation, recovery)
        audit = self.store.get('resumption:' + recovery)
        self.assertEqual(audit['prior_error'], 'unclassified_error')
        self.assertEqual(len(audit['prior_error_sha256']), 64)
        self.assertNotIn('PRIVATE-ERROR-BODY', json.dumps(audit))

    def test_operation_admission_idempotent_and_input_conflict(self):
        body = self.body()
        first = self.service.admit(self.claims, 'save_draft', body)
        again = self.service.admit(self.claims, 'save_draft', body)
        self.assertEqual(first, again)
        self.assertEqual(len(self.operations()), 1)
        stored = next(iter(self.operations().values()))
        self.assertEqual(stored['input'], body)
        self.assertEqual(stored['queue_state'], 'pending')
        self.assertEqual(stored['subject'], self.claims['sub'])
        self.assertNotIn('input', first)
        self.assertNotIn('fingerprint', first)
        with self.assertRaisesRegex(Rejected, 'operation_id_conflict'):
            self.service.admit(self.claims, 'save_draft', dict(body, bundle_sha256='e' * 64))

    def test_retry_after_workspace_advances_returns_original_receipt(self):
        body = self.body()
        first = self.service.admit(self.claims, 'save_draft', body)
        self.update('workspace:' + self.workspace_id, head_commit='b' * 40)
        self.assertEqual(self.service.admit(self.claims, 'save_draft', body), first)
        self.assertEqual(len(self.operations()), 1)

    def test_wrong_actor_site_roles_scopes_and_unknown_inputs_rejected(self):
        other = {'sub': 'other-subject', 'scope': 'hp:read hp:write'}
        self.store.put('principal:other-subject', {'sites': {self.site_id: ['read', 'edit', 'publish']}})
        for claims, body in [(other, self.body()), (self.claims, dict(self.body(), site_id='unbound-site')), (dict(self.claims, scope='hp:read'), self.body()), (self.claims, dict(self.body(), repository='customer-selected-repository'))]:
            with self.subTest(claims=claims, body=body), self.assertRaises(Rejected):
                self.service.admit(claims, 'save_draft', body)
        self.update('principal:' + self.claims['sub'], sites={self.site_id: ['read']})
        with self.assertRaises(Rejected):
            self.service.admit(self.claims, 'open_workspace', {'operation_id': str(uuid4()), 'site_id': self.site_id})
        self.assertEqual(self.operations(), {})

    def test_invalid_input_and_stale_workspace_rejected(self):
        for changes in [dict(base_commit='short'), dict(base_commit='b' * 40), dict(bundle_sha256='bad'), dict(bundle_file_id='../bad'), dict(operation_id='not-a-uuid')]:
            with self.subTest(changes=changes), self.assertRaises(Rejected):
                self.service.admit(self.claims, 'save_draft', dict(self.body(), **changes))
        self.update('workspace:' + self.workspace_id, closed=True)
        with self.assertRaises(Rejected):
            self.service.admit(self.claims, 'save_draft', self.body())
        self.assertEqual(self.operations(), {})

    def test_failed_queue_admission_creates_no_partial_workspace_or_effect(self):
        before = deepcopy(self.store.rows)
        original = self.store.transact
        def unavailable(writes):
            raise OSError('queue store unavailable')
        self.store.transact = unavailable
        with self.assertRaises(OSError):
            self.service.admit(self.claims, 'open_workspace', {'operation_id': str(uuid4()), 'site_id': self.site_id})
        self.assertEqual(self.store.rows, before)
        self.store.transact = original
        result = self.service.admit(self.claims, 'open_workspace', {'operation_id': str(uuid4()), 'site_id': self.site_id})
        self.assertEqual(result['status'], 'queued')
        self.assertEqual(self.store.get('workspace:' + result['workspace_id'])['status'], 'preparing')

    def race_before_transaction(self, mutation):
        original = self.store.transact
        fired = False
        def transact(writes):
            nonlocal fired
            if not fired:
                fired = True
                self.store.transact = original
                mutation()
            original(writes)
        self.store.transact = transact

    def test_workspace_change_during_admission_is_conditionally_rejected(self):
        self.race_before_transaction(lambda: self.update('workspace:' + self.workspace_id, head_commit='b' * 40))
        with self.assertRaises(Conflict):
            self.service.admit(self.claims, 'save_draft', self.body())
        self.assertEqual(self.operations(), {})

    def test_membership_revocation_during_admission_is_conditionally_rejected(self):
        self.race_before_transaction(lambda: self.update('principal:' + self.claims['sub'], disabled=True))
        with self.assertRaises(Conflict):
            self.service.admit(self.claims, 'save_draft', self.body())
        self.assertEqual(self.operations(), {})

    def test_cancel_before_effects_is_terminal_and_idempotent(self):
        admitted = self.service.admit(self.claims, 'save_draft', self.body())
        first = self.service.cancel(self.claims, admitted['operation_id'])
        self.assertEqual(first['status'], 'cancelled')
        self.assertEqual(self.service.cancel(self.claims, admitted['operation_id']), first)
        stored = self.store.get('operation:' + admitted['operation_id'])
        self.assertTrue(stored['cancel_requested'])
        self.assertNotIn('queue_state', stored)
        with self.assertRaises(Rejected):
            self.service.cancel(dict(self.claims, sub='other-subject'), admitted['operation_id'])

    def test_running_cancel_requests_cooperation_without_claiming_completion(self):
        admitted = self.service.admit(self.claims, 'save_draft', self.body())
        self.update('operation:' + admitted['operation_id'], status='running', effects=['draft_saved'])
        result = self.service.cancel(self.claims, admitted['operation_id'])
        self.assertEqual(result['status'], 'running')
        self.assertTrue(self.store.get('operation:' + admitted['operation_id'])['cancel_requested'])

    def test_nonce_is_only_private_metadata_and_persisted_as_hash(self):
        approval_id, nonce, response = self.prepare()
        preview = self.store.get('preview:' + self.preview_id)
        self.assertEqual(response['structuredContent']['site_id'], self.site_id)
        self.assertEqual(response['structuredContent']['source_commit'], preview['source_commit'])
        self.assertEqual(response['structuredContent']['artifact_sha256'], preview['artifact_sha256'])
        self.assertNotIn(nonce, json.dumps(response['structuredContent']))
        self.assertNotIn(nonce, json.dumps(response['content']))
        approval = self.store.get('approval:' + approval_id)
        self.assertNotIn(nonce, json.dumps(approval))
        self.assertNotEqual(approval['nonce_hash'], nonce)
        self.assertEqual(self.operations(), {})
        with self.assertRaises(Rejected):
            self.service.confirm_publish(self.claims, approval_id, 'wrong-nonce')
        with self.assertRaises(Rejected):
            self.service.confirm_publish(dict(self.claims, sub='other-subject'), approval_id, nonce)
        self.assertEqual(self.operations(), {})

    def test_confirmation_readback_recovers_lost_reply_and_other_surface_without_writes(self):
        first, nonce, _ = self.prepare()
        second, _, _ = self.prepare()
        before = deepcopy(self.store.rows)
        self.assertEqual(self.service.confirmation(self.claims, first)['state'], 'prepared')
        self.assertEqual(self.store.rows, before)
        operation = self.service.confirm_publish(self.claims, first, nonce)
        # The client lost this response and only retained the approval ID.
        before = deepcopy(self.store.rows)
        result = self.service.confirmation(dict(self.claims, scope='hp:read'), first)
        self.assertEqual(result['state'], 'accepted')
        self.assertEqual(result['operation'], operation)
        other_surface = self.service.confirmation(self.claims, second)
        self.assertEqual(other_surface['state'], 'already_requested')
        self.assertEqual(other_surface['operation']['operation_id'], operation['operation_id'])
        self.assertEqual(self.store.rows, before)
        self.assertEqual(len(self.operations()), 1)
        for private in (nonce, 'nonce_hash', 'subject', 'member_version', 'site_config_version'):
            self.assertNotIn(private, json.dumps(result))

    def test_confirmation_readback_checks_owner_scope_and_live_read_access(self):
        approval, _, _ = self.prepare()
        for claims in (dict(self.claims, sub='other'), dict(self.claims, scope='hp:write')):
            with self.subTest(claims=claims), self.assertRaises(Rejected):
                self.service.confirmation(claims, approval)
        with self.assertRaises(Rejected):
            self.service.confirmation(self.claims, str(uuid4()))
        self.update('principal:' + self.claims['sub'], disabled=True)
        with self.assertRaisesRegex(Rejected, 'access_revoked'):
            self.service.confirmation(self.claims, approval)
        self.update('principal:' + self.claims['sub'], disabled=False, sites={self.site_id: ['publish']})
        with self.assertRaisesRegex(Rejected, 'site_access_denied'):
            self.service.confirmation(self.claims, approval)
        self.assertEqual(self.operations(), {})

    def test_confirmation_readback_preserves_test_mode_and_reports_expiry_without_accepting(self):
        self.service.publication_enabled = False
        pending, _, _ = self.prepare()
        approval, nonce, _ = self.prepare()
        completion = self.service.confirm_publish(self.claims, approval, nonce)
        self.now += 601
        self.service.publication_enabled = True
        before = deepcopy(self.store.rows)
        tested = self.service.confirmation(self.claims, approval)
        self.assertEqual(tested['mode'], 'connection_test')
        self.assertEqual(tested['result'], completion)
        self.assertEqual(tested['state'], 'connection_tested')
        self.assertNotIn('operation', tested)
        self.assertEqual(self.service.confirmation(self.claims, pending)['state'], 'expired')
        self.assertEqual(self.store.rows, before)
        self.assertEqual(self.operations(), {})

    def test_withdrawal_blocks_late_confirmation_and_replays_without_publication(self):
        approval, nonce, _ = self.prepare()
        result = self.service.cancel_confirmation(self.claims, approval)
        self.assertEqual(result['state'], 'cancelled')
        self.assertNotIn(nonce, json.dumps(result))
        before = deepcopy(self.store.rows)
        self.assertEqual(self.service.cancel_confirmation(self.claims, approval), result)
        self.assertEqual(self.store.rows, before)
        with self.assertRaisesRegex(Rejected, 'confirmation_expired'):
            self.service.confirm_publish(self.claims, approval, nonce)
        self.assertEqual(self.operations(), {})
        # An expired but unresolved record can also be withdrawn definitively.
        expired, _, _ = self.prepare()
        self.now += 601
        self.assertEqual(self.service.cancel_confirmation(self.claims, expired)['state'], 'cancelled')

    def test_withdrawal_preserves_accepted_operation_and_connection_result(self):
        approval, nonce, _ = self.prepare()
        operation = self.service.confirm_publish(self.claims, approval, nonce)
        before = deepcopy(self.store.rows)
        self.assertEqual(self.service.cancel_confirmation(self.claims, approval)['operation'], operation)
        self.assertEqual(self.store.rows, before)
        self.assertFalse(self.store.get('operation:' + operation['operation_id']).get('cancel_requested'))
        self.service.publication_enabled = False
        tested, nonce, _ = self.prepare()
        result = self.service.confirm_publish(self.claims, tested, nonce)
        self.assertEqual(self.service.cancel_confirmation(self.claims, tested)['result'], result)

    def test_withdrawing_duplicate_card_keeps_other_surfaces_existing_publication_visible(self):
        first, nonce, _ = self.prepare()
        duplicate, duplicate_nonce, _ = self.prepare()
        operation = self.service.confirm_publish(self.claims, first, nonce)
        self.assertEqual(self.service.confirm_publish(self.claims, duplicate, duplicate_nonce), operation)
        self.assertEqual(self.store.get('approval:' + duplicate)['state'], 'prepared')
        readback = self.service.cancel_confirmation(self.claims, duplicate)
        self.assertEqual(self.store.get('approval:' + duplicate)['state'], 'cancelled')
        self.assertEqual(readback['state'], 'already_requested')
        self.assertEqual(readback['operation'], operation)
        self.assertEqual(self.service.confirmation(self.claims, duplicate), readback)
        self.assertEqual(len(self.operations()), 1)
        self.assertFalse(self.store.get('operation:' + operation['operation_id']).get('cancel_requested'))

    def test_withdrawal_owner_live_permission_and_concurrent_acceptance_are_checked(self):
        approval, nonce, _ = self.prepare()
        for claims in (dict(self.claims, sub='other'), dict(self.claims, scope='hp:read'), dict(self.claims, scope='hp:write')):
            with self.subTest(claims=claims), self.assertRaises(Rejected):
                self.service.cancel_confirmation(claims, approval)
        self.assertEqual(self.store.get('approval:' + approval)['state'], 'prepared')
        original = self.store.transact
        def accept_first(writes):
            self.store.transact = original
            self.service.confirm_publish(self.claims, approval, nonce)
            original(writes)
        self.store.transact = accept_first
        with self.assertRaises(Conflict):
            self.service.cancel_confirmation(self.claims, approval)
        readback = self.service.confirmation(self.claims, approval)
        self.assertEqual(readback['state'], 'accepted')
        self.assertEqual(len(self.operations()), 1)
        self.assertFalse(self.store.get('operation:' + readback['operation']['operation_id']).get('cancel_requested'))

    def test_withdrawal_wins_against_inflight_confirmation_atomic_acceptance(self):
        approval, nonce, _ = self.prepare()
        original = self.store.transact
        def cancel_first(writes):
            self.store.transact = original
            self.service.cancel_confirmation(self.claims, approval)
            original(writes)
        self.store.transact = cancel_first
        with self.assertRaises(Conflict):
            self.service.confirm_publish(self.claims, approval, nonce)
        self.assertEqual(self.service.confirmation(self.claims, approval)['state'], 'cancelled')
        self.assertEqual(self.operations(), {})

    def test_connection_test_audits_only_and_never_becomes_publication(self):
        self.service.publication_enabled = False
        approval_id, nonce, response = self.prepare()
        self.assertEqual(response['structuredContent']['mode'], 'connection_test')
        self.assertIn('公開は行いません', response['content'][0]['text'])
        self.assertNotIn(nonce, json.dumps(response['structuredContent']))
        before = deepcopy(self.store.rows)
        self.service.publication_enabled = True
        result = self.service.confirm_publish(self.claims, approval_id, nonce)
        self.assertEqual(result, {'kind': 'connection_test', 'status': 'completed', 'approval_id': approval_id,
            'preview_id': self.preview_id, 'completed_at': self.now})
        audit = self.store.get('approval:' + approval_id)
        self.assertEqual((audit['mode'], audit['state'], audit['result']), ('connection_test', 'connection_tested', result))
        self.assertNotIn(nonce, json.dumps(audit))
        self.assertEqual(set(self.store.rows), set(before))
        for key in before:
            if key != 'approval:' + approval_id:
                self.assertEqual(self.store.rows[key], before[key])
        self.assertEqual(self.operations(), {})
        self.assertEqual(self.store.pending(now=self.now), [])
        tested = deepcopy(self.store.rows)
        self.service.publication_enabled = False
        self.assertEqual(self.service.confirm_publish(self.claims, approval_id, nonce), result)
        self.assertEqual(self.store.rows, tested)
        self.service.publication_enabled = True
        normal_id, normal_nonce, response = self.prepare()
        self.assertEqual(response['structuredContent']['mode'], 'publish')
        self.assertEqual(self.service.confirm_publish(self.claims, normal_id, normal_nonce)['kind'], 'publish')
        self.assertEqual(len(self.operations()), 1)

    def test_connection_test_rejects_nonce_actor_scope_and_unverified_preview(self):
        self.service.publication_enabled = False
        approval_id, nonce, _ = self.prepare()
        original = deepcopy(self.store.rows)
        for claims, supplied in [(self.claims, 'wrong'), (dict(self.claims, sub='other'), nonce),
                                 (dict(self.claims, scope='hp:read'), nonce)]:
            with self.subTest(claims=claims), self.assertRaises(Rejected):
                self.service.confirm_publish(claims, approval_id, supplied)
            self.assertEqual(self.store.rows, original)
        self.update('preview:' + self.preview_id, status='superseded')
        with self.assertRaisesRegex(Rejected, 'preview_not_current'):
            self.prepare()

    def test_connection_test_first_confirmation_and_replay_recheck_live_bindings(self):
        self.service.publication_enabled = False
        mutations = [('site:' + self.site_id, dict(current_preview=str(uuid4()))),
            ('site:' + self.site_id, dict(config_version=2)),
            ('site:' + self.site_id, dict(current_main_commit='e' * 40)),
            ('site:' + self.site_id, dict(current_publication='another')),
            ('preview:' + self.preview_id, dict(artifact_sha256='f' * 64)),
            ('preview:' + self.preview_id, dict(source_commit='f' * 40)),
            ('preview:' + self.preview_id, dict(status='superseded')),
            ('principal:' + self.claims['sub'], dict(disabled=True)),
            ('principal:' + self.claims['sub'], dict(sites={self.site_id: ['read', 'edit']}))]
        fixture = deepcopy(self.store.rows)
        for tested in (False, True):
            for key, changes in mutations:
                with self.subTest(tested=tested, changes=changes):
                    self.store.rows = deepcopy(fixture)
                    approval_id, nonce, _ = self.prepare()
                    if tested:
                        self.service.confirm_publish(self.claims, approval_id, nonce)
                    self.update(key, **changes)
                    before = deepcopy(self.store.rows)
                    with self.assertRaises(Rejected):
                        self.service.confirm_publish(self.claims, approval_id, nonce)
                    self.assertEqual(self.store.rows, before)
            self.store.rows = deepcopy(fixture)
            approval_id, nonce, _ = self.prepare()
            if tested:
                self.service.confirm_publish(self.claims, approval_id, nonce)
            self.now += 600
            with self.assertRaisesRegex(Rejected, 'expired'):
                self.service.confirm_publish(self.claims, approval_id, nonce)

    def test_connection_test_completion_is_atomic_against_revocation(self):
        self.service.publication_enabled = False
        approval_id, nonce, _ = self.prepare()
        self.race_before_transaction(lambda: self.update('principal:' + self.claims['sub'], disabled=True))
        with self.assertRaises(Conflict):
            self.service.confirm_publish(self.claims, approval_id, nonce)
        self.assertEqual(self.store.get('approval:' + approval_id)['state'], 'prepared')
        self.assertEqual(self.operations(), {})

    def test_connection_test_response_loss_replays_durable_completion(self):
        self.service.publication_enabled = False
        approval_id, nonce, _ = self.prepare()
        original = self.store.transact
        def lost(writes):
            original(writes)
            raise OSError('response lost after audit commit')
        self.store.transact = lost
        with self.assertRaises(OSError):
            self.service.confirm_publish(self.claims, approval_id, nonce)
        self.store.transact = original
        before = deepcopy(self.store.rows)
        result = self.service.confirm_publish(self.claims, approval_id, nonce)
        self.assertEqual(result, before['approval:' + approval_id]['result'])
        self.assertEqual(self.store.rows, before)
        self.assertEqual(self.operations(), {})

    def test_double_confirmation_returns_same_queued_operation(self):
        approval_id, nonce, response = self.prepare()
        first = self.service.confirm_publish(self.claims, approval_id, nonce)
        second = self.service.confirm_publish(self.claims, approval_id, nonce)
        self.assertEqual(first, second)
        self.assertEqual(first['kind'], 'publish')
        self.assertEqual(len(self.operations()), 1)
        self.assertEqual(self.store.get('approval:' + approval_id)['state'], 'accepted')

    def test_expired_confirmation_has_no_effect(self):
        approval_id, nonce, response = self.prepare()
        self.now += 600
        with self.assertRaisesRegex(Rejected, 'expired'):
            self.service.confirm_publish(self.claims, approval_id, nonce)
        self.assertEqual(self.operations(), {})

    def test_stale_preview_config_publication_and_artifact_rejected(self):
        mutations = [('site:' + self.site_id, dict(current_preview=str(uuid4()))), ('site:' + self.site_id, dict(current_main_commit='e' * 40)), ('site:' + self.site_id, dict(config_version=2)), ('site:' + self.site_id, dict(current_publication='another-publication')), ('preview:' + self.preview_id, dict(artifact_sha256='f' * 64)), ('preview:' + self.preview_id, dict(source_commit='f' * 40)), ('preview:' + self.preview_id, dict(status='superseded'))]
        for key, changes in mutations:
            with self.subTest(changes=changes):
                original = deepcopy(self.store.rows)
                approval_id, nonce, response = self.prepare()
                self.update(key, **changes)
                with self.assertRaisesRegex(Rejected, 'stale'):
                    self.service.confirm_publish(self.claims, approval_id, nonce)
                self.assertEqual(self.operations(), {})
                self.store.rows = original

    def test_revoked_membership_and_publication_gate_block_confirmation(self):
        approval_id, nonce, response = self.prepare()
        key = 'principal:' + self.claims['sub']
        self.update(key, sites={self.site_id: ['read', 'edit']})
        with self.assertRaises(Rejected):
            self.service.confirm_publish(self.claims, approval_id, nonce)
        self.update(key, sites={self.site_id: ['read', 'edit', 'publish']})
        with self.assertRaisesRegex(Rejected, 'stale'):
            self.service.confirm_publish(self.claims, approval_id, nonce)
        self.service.publication_enabled = False
        with self.assertRaisesRegex(Rejected, 'not_enabled'):
            self.service.confirm_publish(self.claims, approval_id, nonce)
        _, _, test_card = self.prepare()
        self.assertEqual(test_card['structuredContent']['mode'], 'connection_test')
        self.assertEqual(self.operations(), {})

    def test_concurrent_revocation_before_confirm_transaction_wins_atomically(self):
        approval_id, nonce, response = self.prepare()
        self.race_before_transaction(lambda: self.update('principal:' + self.claims['sub'], disabled=True))
        with self.assertRaises(Conflict):
            self.service.confirm_publish(self.claims, approval_id, nonce)
        self.assertEqual(self.store.get('approval:' + approval_id)['state'], 'prepared')
        self.assertEqual(self.operations(), {})

    def test_concurrent_confirm_first_then_revocation_keeps_exact_one_operation(self):
        approval_id, nonce, response = self.prepare()
        operation = self.service.confirm_publish(self.claims, approval_id, nonce)
        self.update('principal:' + self.claims['sub'], disabled=True)
        with self.assertRaises(Rejected):
            self.service.confirm_publish(self.claims, approval_id, nonce)
        self.assertEqual(list(self.operations()), ['operation:' + operation['operation_id']])


if __name__ == '__main__':
    unittest.main()
