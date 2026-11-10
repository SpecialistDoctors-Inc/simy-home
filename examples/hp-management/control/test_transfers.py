"""HP-only transport integration with fake storage/providers; no cloud writes."""
from copy import deepcopy
import json
import unittest
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from bundles import sha256
from service import Rejected
from transfers import Transfers, PREFIX
import test_executor as fixtures


class S3:
    def __init__(self): self.calls = []
    def generate_presigned_url(self, method, **kwargs):
        self.calls.append((method, kwargs))
        return 'https://unit.s3.us-east-1.amazonaws.com/private?signature=private'


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ExecutorTests()
        self.fixture.setUp()
        self.f = self.fixture
        row = self.f.store.get('site:' + self.f.site)
        self.f.store.put('site:' + self.f.site, {**row, 'direct_transfer_enabled': True}, row['_version'])
        self.s3 = S3()
        self.transfer = Transfers(self.f.service, 'unit-artifacts', self.s3)
        self.workspace, self.opened = self.f.open()

    def body(self):
        operation = str(uuid4())
        data = fixtures.changes(self.f.site, self.workspace, self.opened['base_commit'], operation, b'base', b'edited')
        return dict(operation_id=operation, site_id=self.f.site, workspace_id=self.workspace,
            base_commit=self.opened['base_commit'], bundle_sha256=sha256(data), size=str(len(data))), data

    def saved_body(self, body):
        return {k: v for k, v in {**body, 'bundle_file_id': PREFIX + body['operation_id']}.items() if k != 'size'}

    def test_download_and_save_without_customer_drive_keep_dev_and_main_unchanged(self):
        public, private = self.transfer.download(self.f.claims, self.f.site, self.workspace)
        self.assertEqual(public['snapshot_sha256'], self.opened['snapshot_sha256'])
        self.assertNotIn('url', public)
        key = self.s3.calls[-1][1]['Params']['Key']
        self.assertEqual(sha256(self.f.artifacts.files[key]), public['snapshot_sha256'])
        body, data = self.body()
        result, private = self.transfer.prepare_upload(self.f.claims, body)
        params = self.s3.calls[-1][1]['Params']
        self.assertEqual(params['IfNoneMatch'], '*')
        self.assertEqual(params['ContentLength'], len(data))
        self.assertEqual(result, self.transfer.prepare_upload(self.f.claims, body)[0])
        self.f.artifacts.files[params['Key']] = data
        self.f.service.admit(self.f.claims, 'save_draft', self.saved_body(body))
        self.f.drive.read_exact = lambda *args: self.fail('Customer draft should not use Drive transport')
        saved = self.f.execute(body['operation_id'])
        self.assertEqual(saved['status'], 'completed')
        self.assertEqual(saved['result']['bundle_sha256'], sha256(data))
        self.assertEqual(self.f.github.branches['dev'], self.f.github.base)
        self.assertEqual(self.f.github.branches['main'], self.f.github.base)
        self.assertEqual(len(self.f.github.created_commits), 1)
        self.f.execute(body['operation_id'])
        self.assertEqual(len(self.f.github.created_commits), 1)

    def test_actor_workspace_and_changed_bytes_do_not_reuse_transfer(self):
        body, data = self.body()
        self.transfer.prepare_upload(self.f.claims, body)
        for changed in ({'bundle_sha256': 'e'*64}, {'size': '123'}, {'operation_id': 'bad'}):
            with self.assertRaises(Rejected):
                self.transfer.prepare_upload(self.f.claims, {**body, **changed})
        self.f.store.put('principal:other', {'sites': {self.f.site: ['read', 'edit']}})
        other = {**self.f.claims, 'sub': 'other'}
        before = len(self.s3.calls)
        with self.assertRaises(Rejected): self.transfer.download(other, self.f.site, self.workspace)
        with self.assertRaises(Rejected): self.transfer.prepare_upload(other, body)
        with self.assertRaises(Rejected): self.f.service.admit(other, 'save_draft', self.saved_body(body))
        self.assertEqual(before, len(self.s3.calls))

    def test_revocation_blocks_upload_signing_and_save_admission(self):
        body, data = self.body()
        self.transfer.prepare_upload(self.f.claims, body)
        member = self.f.store.get('principal:operator')
        self.f.store.put('principal:operator', {**member, 'disabled': True}, member['_version'])
        with self.assertRaises(Rejected): self.transfer.prepare_upload(self.f.claims, body)
        with self.assertRaises(Rejected): self.f.service.admit(self.f.claims, 'save_draft', self.saved_body(body))

    def test_unregistered_marker_does_not_admit_save(self):
        body, _ = self.body()
        with self.assertRaisesRegex(Rejected, 'transfer_access_denied'):
            self.f.service.admit(self.f.claims, 'save_draft', self.saved_body(body))

    def test_upload_mismatch_or_corrupt_storage_never_commits(self):
        body, data = self.body()
        self.transfer.prepare_upload(self.f.claims, body)
        key = self.s3.calls[-1][1]['Params']['Key']
        self.f.artifacts.files[key] = b'wrong bytes'
        self.f.service.admit(self.f.claims, 'save_draft', self.saved_body(body))
        try: self.f.execute(body['operation_id'])
        except Exception: pass
        self.assertEqual(self.f.github.created_commits, set())
        self.assertNotEqual(self.f.service.operation(self.f.claims, body['operation_id'])['status'], 'completed')

    def test_private_urls_do_not_enter_mcp_public_result_or_ledger(self):
        from mcp_adapter import App
        app = App(None, self.f.service, None, None, '', transfers=self.transfer)
        body, _ = self.body()
        result = app.call_tool('hp_prepare_upload', body, self.f.claims, {}, {})
        self.assertIn('hp_transfer', result['_meta'])
        self.assertNotIn('signature=private', json.dumps(result['structuredContent']))
        self.assertNotIn('signature=private', json.dumps(result['content']))
        self.assertNotIn('signature=private', json.dumps(self.f.store.rows))

    def test_real_presigning_binds_bytes_length_create_only_and_regional_origin(self):
        import boto3
        from botocore.config import Config
        s3 = boto3.client('s3', region_name='us-east-1',
            endpoint_url='https://s3.us-east-1.amazonaws.com',
            aws_access_key_id='fixture-key', aws_secret_access_key='fake-signing-key-for-unit-tests',
            config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'}))
        transfer = Transfers(self.f.service, 'unit-artifacts', s3)
        body, data = self.body()
        public, private = transfer.prepare_upload(self.f.claims, body)
        parsed = urlsplit(private['url'])
        self.assertEqual(parsed.hostname, 'unit-artifacts.s3.us-east-1.amazonaws.com')
        signed = parse_qs(parsed.query)['X-Amz-SignedHeaders'][0].split(';')
        self.assertEqual(set(signed) - {'host'}, {name.lower() for name in private['headers']})
        self.assertEqual(private['headers']['Content-Length'], str(len(data)))

    def test_refreshes_same_upload_after_membership_change_only_before_save_admission(self):
        body, _ = self.body()
        first = self.transfer.prepare_upload(self.f.claims, body)[0]
        member = self.f.store.get('principal:operator')
        self.f.store.put('principal:operator', {**member, 'note': 'changed'}, member['_version'])
        self.assertEqual(first, self.transfer.prepare_upload(self.f.claims, body)[0])
        self.f.service.admit(self.f.claims, 'save_draft', self.saved_body(body))
        member = self.f.store.get('principal:operator')
        self.f.store.put('principal:operator', {**member, 'note': 'changed again'}, member['_version'])
        before = self.f.store.get('transfer:' + body['operation_id'])
        with self.assertRaisesRegex(Rejected, 'transfer_binding_changed'):
            self.transfer.prepare_upload(self.f.claims, body)
        self.assertEqual(before, self.f.store.get('transfer:' + body['operation_id']))


if __name__ == '__main__': unittest.main()
