from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from cryptography.fernet import Fernet

from bundles import sha256
from cloud_providers import S3Artifacts
from executor import Executor
from mcp_adapter import App
from service import Service
from store import MemoryStore
import test_executor
import test_wordpress_provider
from wordpress_editor import WordPressEditor, WordPressTransfers
from wordpress_onboarding import WordPressOnboarding


ORG = 'f4dbf297-4526-41f5-bd7b-2ba20b4736d9'
SUBJECT = 'google-subject'
ORIGIN = 'https://clinic.wordpress.com'


class FixtureTransfer:
    def __init__(self):
        self.files = {}

    def generate_presigned_url(self, method, *, Params, ExpiresIn):
        return 'https://fixture.s3.ap-northeast-1.amazonaws.com/' + Params['Key'] + '?signed=' + method

    def get_object(self, *, Bucket, Key):
        return {'Body': BytesIO(self.files[Key]), 'ContentLength': len(self.files[Key])}

    def put_object(self, *, Bucket, Key, Body, **options):
        if Key in self.files and self.files[Key] != Body:
            raise AssertionError('immutable fixture changed')
        self.files[Key] = Body


class WordPressEditorTest(unittest.TestCase):
    def test_signup_native_protocol_and_exact_approved_publish(self):
        fixture = test_wordpress_provider.WordPressProviderTest()
        fixture.setUp()
        store, objects = MemoryStore(), FixtureTransfer()
        artifacts = S3Artifacts('fixture', objects, lambda: None)
        paid = False
        resolver = lambda org, sub: paid and org == ORG and sub == SUBJECT
        service = Service(store, publication_enabled=True, license_resolver=resolver, wordpress_test_origin=ORIGIN)
        onboarding = WordPressOnboarding(store, {'credential_key': Fernet.generate_key().decode()}, provider=fixture.provider)
        transfers = WordPressTransfers(store, service, objects, 'fixture')
        editor = WordPressEditor(onboarding, transfers, 'https://hp-control.example/mcp')
        executor = Executor(store, None, None, artifacts, publication_enabled=True, license_resolver=resolver,
                            wordpress=editor, wordpress_test_origin=ORIGIN)
        claims = {'sub': SUBJECT, 'scope': 'hp:read hp:write'}
        app = App(None, service, lambda _: claims, None, None, preflight_token=lambda: 's' * 32,
                  wordpress=lambda: onboarding, wordpress_transfers=transfers)

        def rpc(name, args):
            result = app({'rawPath': '/mcp', 'httpMethod': 'POST', 'headers': {
                'authorization': 'Bearer fixture', 'content-type': 'application/json'}, 'body': json.dumps({
                    'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': name, 'arguments': args}})})
            value = json.loads(result['body'])['result']
            self.assertFalse(value.get('isError'), value.get('structuredContent'))
            return value

        state = onboarding.start(ORG, SUBJECT, ORIGIN)['state']
        onboarding.finish(ORG, SUBJECT, state, 'fixture')
        self.assertTrue(service.license_preflight(ORG, SUBJECT)['ready'])
        self.assertEqual(rpc('hp_list_sites', {})['structuredContent']['sites'], [])
        paid = True
        site = rpc('hp_list_sites', {})['structuredContent']['sites'][0]
        self.assertEqual(site['roles'], ['read', 'edit', 'publish'])
        site_id = site['site_id']

        def execute(name, args, operation=None):
            operation = operation or str(uuid4())
            rpc(name, {'operation_id': operation, 'site_id': site_id, **args})
            output = executor.execute(operation)
            self.assertEqual(output['status'], 'completed', output.get('error'))
            return output['result']

        receipt = execute('hp_open_workspace', {})
        workspace = {'site_id': site_id, 'workspace_id': receipt['workspace_id']}
        download = rpc('hp_download_workspace', workspace)
        self.assertNotIn('url', download['structuredContent'])
        self.assertEqual(download['_meta']['hp_transfer']['method'], 'GET')
        initial = store.get('workspace:' + receipt['workspace_id'])
        snapshot = artifacts.get_exact(initial['initial_snapshot_key'], receipt['snapshot_sha256'])
        base, operation, data = self.package(receipt, snapshot)
        upload = rpc('hp_prepare_upload', {**workspace, 'operation_id': operation, 'base_commit': base,
                     'bundle_sha256': sha256(data), 'size': str(len(data))})
        self.assertEqual(upload['_meta']['hp_transfer']['headers']['If-None-Match'], '*')
        objects.files[store.get('upload:hp-upload-' + operation)['key']] = data
        saved = execute('hp_save_draft', {'workspace_id': receipt['workspace_id'], 'base_commit': base,
                        'bundle_file_id': 'hp-upload-' + operation, 'bundle_sha256': sha256(data)}, operation)
        preview = execute('hp_submit_preview', {'workspace_id': receipt['workspace_id'], 'saved_commit': saved['saved_commit']})
        current_page = '/wp/v2/sites/123/pages/456?context=edit'
        self.assertEqual(fixture.replies[current_page]['content']['raw'], '<h1>Clinic</h1>')
        approval = rpc('hp_prepare_publish', {'site_id': site_id, 'preview_id': preview['preview_id']})
        self.assertEqual(fixture.replies[current_page]['content']['raw'], '<h1>Clinic</h1>')
        confirmation = rpc('hp_confirm_publish', {'approval_id': approval['structuredContent']['approval_id'],
                            'confirmation_nonce': approval['_meta']['confirmation_nonce']})['structuredContent']
        published = executor.execute(confirmation['operation_id'])
        self.assertEqual(published['result']['kind'], 'published')
        self.assertEqual(published['result']['receipt']['url'], ORIGIN)
        self.assertEqual(fixture.replies[current_page]['content']['raw'], '<h1>Edited clinic</h1>')
        self.assertEqual(store.get('workspace:' + receipt['workspace_id'])['base_on_dev'], saved['saved_commit'])

    @staticmethod
    def package(receipt, snapshot):
        native = os.environ.get('HP_NATIVE_EDITOR_TEST_BIN')
        base = receipt['base_commit']
        if not native:
            operation = str(uuid4())
            return base, operation, test_executor.changes(receipt['site_id'], receipt['workspace_id'], base,
                        operation, b'<h1>Clinic</h1>', b'<h1>Edited clinic</h1>')
        with TemporaryDirectory(prefix='hp-wordpress-mac-') as tmp:
            root = Path(tmp)
            source, record, workspace, delta = [root / name for name in ('snapshot.zip', 'receipt.json', 'workspace', 'changes.zip')]
            source.write_bytes(snapshot)
            record.write_text(json.dumps(receipt))
            subprocess.run([native, 'init', str(source), str(workspace), '--receipt', str(record)],
                           check=True, capture_output=True, timeout=20)
            index, = [file for file in workspace.rglob('index.html') if '.hp' not in file.parts]
            index.write_text('<h1>Edited clinic</h1>')
            subprocess.run([native, 'pack', str(workspace), str(delta)], check=True, capture_output=True, timeout=20)
            from zipfile import ZipFile
            with ZipFile(delta) as archive:
                operation = json.loads(archive.read('manifest.json'))['operation_id']
            return base, operation, delta.read_bytes()
