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

    def operations(self):
        return {key: value for key, value in self.store.rows.items() if key.startswith('operation:')}

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
            self.service.prepare_publish(self.claims, self.site_id, self.preview_id)
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
