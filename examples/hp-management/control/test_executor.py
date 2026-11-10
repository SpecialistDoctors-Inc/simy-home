"""Behavioral executor/provider regressions; every external provider is a fake."""
from copy import deepcopy
from io import BytesIO
import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from uuid import uuid4
import zipfile

from bundles import sha256, MAX_TRANSPORT, BundleError
from cloud_providers import GoogleDrive, ProviderError, S3Artifacts, google_transport
from executor import Executor, Busy, IntegrationUnavailable, ReconciliationRequired
from service import Service, fingerprint, Rejected
from store import MemoryStore, Conflict


def changes(site, workspace, base, operation, before, after):
    manifest = {'schema_version': 1, 'kind': 'changes', 'site_id': site,
        'workspace_id': workspace, 'base_commit': base, 'operation_id': operation,
        'changes': [{'path': 'index.html', 'action': 'modify', 'base_sha256': sha256(before),
            'sha256': sha256(after), 'size': len(after)}]}
    stream = BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr('manifest.json', json.dumps(manifest))
        archive.writestr('files/index.html', after)
    return stream.getvalue()


def package(files, commit, operation):
    digest = fingerprint([{'path': p, 'sha256': sha256(v), 'size': len(v)} for p,v in sorted(files.items())])
    metadata = {'schema_version': 1, 'source_commit': commit, 'operation_id': operation,
                'source_sha256': digest, 'version': digest}
    stream = BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        for name, value in files.items():
            archive.writestr(name, value)
        archive.writestr('version.json', json.dumps(metadata))
    return stream.getvalue()


class GitHub:
    def __init__(self):
        self.base = 'a' * 40
        self.branches = {'dev': self.base, 'main': self.base}
        self.sources = {self.base: {'index.html': b'base', 'style.css': b'base css'}}
        self.created_commits = set()
        self.commit_intents = {}
        self.fail_commit_once = False

    def head(self, branch):
        return self.branches[branch]

    def read_site_at(self, commit):
        return SimpleNamespace(commit=commit, files=deepcopy(self.sources[commit]))

    def ensure_workspace_branch(self, workspace, base):
        name = 'codex/hp/' + workspace
        if self.branches.get(name, base) != base:
            raise RuntimeError('wrong head')
        self.branches[name] = base
        return name

    def commit_site(self, branch, expected, files, title, operation, timestamp):
        digest = fingerprint({'parent': expected, 'files': {p:sha256(v) for p,v in files.items()},
                              'title': title, 'operation': operation, 'timestamp': timestamp})[:40]
        if files == self.sources[expected]:
            digest = expected
        if self.branches[branch] not in (expected, digest):
            raise RuntimeError('stale head')
        self.created_commits.add(digest)
        self.commit_intents[digest] = (expected, {p:sha256(v) for p,v in files.items()}, title, operation, timestamp)
        self.sources[digest] = deepcopy(files)
        self.branches[branch] = digest
        if self.fail_commit_once:
            self.fail_commit_once = False
            raise RuntimeError('response lost after accepted commit')
        return SimpleNamespace(commit=digest)

    def reconcile_site_commit(self, branch, parent, file_hashes, title, operation, timestamp):
        current=self.branches[branch]
        if self.commit_intents.get(current) == (parent,file_hashes,title,operation,timestamp):
            return {'commit':current}
        if current==parent and {p:sha256(v) for p,v in self.sources[current].items()}==file_hashes:
            return {'commit':current}
        return None


class Drive:
    def __init__(self):
        self.files, self.created = {}, set()
        self.fail_upload_once = False

    def reserve_id(self):
        return 'drive-id-' + str(uuid4())

    def create_exact(self, parent, file_id, data, operation):
        if file_id in self.files:
            if self.files[file_id] != (parent, data):
                raise ProviderError('mismatch')
        else:
            self.created.add(file_id)
            self.files[file_id] = parent, data
        if self.fail_upload_once:
            self.fail_upload_once = False
            raise RuntimeError('response lost after accepted upload')
        return {'download_url': 'https://drive.google.com/file/d/' + file_id + '/view'}

    def read_exact(self, parent, file_id):
        actual, data = self.files[file_id]
        if actual != parent:
            raise ProviderError('wrong parent')
        return data


class Artifacts:
    def __init__(self):
        self.files = {}
    def put_exact(self, key, data):
        if key in self.files and self.files[key] != data:
            raise ProviderError('immutable mismatch')
        self.files[key] = data
        return {'key': key}
    def get_exact(self, key, digest):
        data = self.files[key]
        if sha256(data) != digest:
            raise ProviderError('digest mismatch')
        return data


class Validator:
    def __init__(self, github):
        self.github, self.calls, self.data = github, 0, {}
        self.corrupt = False
        self.stale_live = False
    def validate(self, site, commit, operation, tree_hash, guard):
        guard(); self.calls += 1
        files = deepcopy(self.github.sources[commit])
        if self.corrupt:
            files['index.html'] = b'unrelated'
        data = package(files, commit, operation)
        self.data[sha256(data)] = data
        return {'source_commit': commit, 'tree_sha256': tree_hash, 'conclusion': 'success',
            'artifact_sha256': sha256(data), 'package_operation_id':operation, 'run_id': 42}
    def artifact(self, proof, guard):
        guard()
        return self.data[proof['artifact_sha256']]
    def readback(self, site, proof, guard):
        guard()
        return {'verified': True, 'source_commit': 'f' * 40 if self.stale_live else proof['source_commit'],
                'artifact_sha256': proof['artifact_sha256']}


class BrowserValidator:
    """Injected fake renderer, only for executor ordering/proof regressions."""
    def __init__(self): self.calls=0; self.mismatch=False
    def preflight(self,site,guard): guard()
    def validate(self,site,preview,artifact_key,operation,guard):
        guard(); self.calls+=1
        prefix='browser-validation/'+preview['site_id']+'/'+operation+'/'+preview['artifact_sha256']+'/'
        return {'verified':True,'source_commit':preview['source_commit'],
            'artifact_sha256':'f'*64 if self.mismatch else preview['artifact_sha256'],
            'report_key':prefix+'report.json','screenshot_keys':[prefix+'desktop.png',prefix+'mobile.png']}
    def reconcile(self,*args): return None


class Publisher:
    def __init__(self):
        self.effects, self.fail_once = {}, False
    def preflight(self, site, guard):
        guard()
    def reconcile(self, site, preview, operation, fence, guard):
        guard()
        return self.effects.get(operation)
    def publish(self, site, preview, data, operation, fence, guard):
        guard()
        result = {'verified': True, 'artifact_sha256': sha256(data)}
        self.effects.setdefault(operation, result)
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError('provider write accepted but response lost')
        return self.effects[operation]


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.store, self.github, self.drive, self.artifacts = MemoryStore(), GitHub(), Drive(), Artifacts()
        self.now = 1000
        self.clock = lambda: self.now
        self.service = Service(self.store, clock=self.clock, publication_enabled=True)
        self.claims = {'sub': 'operator', 'scope': 'hp:read hp:write'}
        self.site = 'test-site'
        self.store.put('principal:operator', {'sites': {self.site: ['read', 'edit', 'publish']}})
        self.store.put('site:' + self.site, {'site_id':self.site,'name': 'Test', 'config_version': 1,
            'dev_url': 'https://preview.example.invalid', 'prod_url': 'https://site.example.invalid', 'initial_main_commit': self.github.base,
            'drive_workspace_folder_id': 'workspace-folder', 'drive_changes_folder_id': 'changes-folder'})
        self.validator, self.publisher = Validator(self.github), Publisher()
        self.preview_publisher = Publisher()
        self.browser_validator = BrowserValidator()
        self.executor = Executor(self.store, lambda site,guard: self.github, self.drive, self.artifacts,
            self.validator, self.publisher, clock=self.clock, publication_enabled=True, preview_publisher=self.preview_publisher, browser_validator=self.browser_validator)

    def execute(self, operation):
        row=self.store.get('operation:'+operation)
        self.now=max(self.now,row.get('retry_at',0))
        return self.executor.execute(operation)

    def admit(self, kind, **body):
        operation = body.pop('operation_id', str(uuid4()))
        self.service.admit(self.claims, kind, {'operation_id': operation, 'site_id': self.site, **body})
        return operation

    def open(self):
        operation = self.admit('open_workspace')
        result = self.execute(operation)['result']
        return result['workspace_id'], result

    def test_consumer_keeps_single_retry_when_conflict_happens_inside_run(self):
        from hp_control import consume_commands
        operation = self.admit('open_workspace')
        event = {'Records': [{'messageId': 'in-run-conflict',
                             'body': json.dumps({'operation_id': operation})}]}
        with patch.object(self.github, 'head', side_effect=Conflict('provider_read_conflict')):
            self.assertEqual(consume_commands(event, None, executor=self.executor), {'batchItemFailures': []})
        row = self.store.get('operation:' + operation)
        self.assertEqual((row['retry_attempts'], row['retry_generation']), (1, 1))
        self.assertEqual((row['queue_state'], row['retry_at']), ('pending', 1005))
        self.assertEqual(row['error'], 'provider_retry_required')

    def save(self, workspace, before=b'base', after=b'edited'):
        base = self.store.get('workspace:' + workspace)['head_commit']
        operation, file_id = str(uuid4()), 'change-file-' + str(uuid4())
        data = changes(self.site, workspace, base, operation, before, after)
        self.drive.files[file_id] = 'changes-folder', data
        self.admit('save_draft', operation_id=operation, workspace_id=workspace,
            base_commit=base, bundle_file_id=file_id, bundle_sha256=sha256(data))
        return operation

    def preview(self):
        workspace,_ = self.open()
        saved = self.execute(self.save(workspace))['result']
        operation = self.admit('submit_preview', workspace_id=workspace, saved_commit=saved['saved_commit'])
        return operation, self.execute(operation)

    def publish_operation(self):
        _, op = self.preview()
        prepared = self.service.prepare_publish(self.claims, self.site, op['result']['preview_id'])
        return self.service.confirm_publish(self.claims, prepared['structuredContent']['approval_id'],
            prepared['_meta']['confirmation_nonce'])['operation_id']

    def test_provider_binding_failure_after_claim_has_durable_recovery(self):
        operation = self.admit('open_workspace')
        class InvalidBinding:
            def for_site(inner, site, guard):
                raise RuntimeError('provider binding unavailable')
        self.executor.drive = InvalidBinding()
        with self.assertRaises(RuntimeError):
            self.execute(operation)
        row = self.store.get('operation:' + operation)
        self.assertEqual((row['status'], row['queue_state']), ('retry_wait', 'pending'))
        self.assertEqual(self.store.get('lease:site:' + self.site)['until'], 0)
        self.assertNotIn('pending_effect', row)

    def test_open_replay_and_ambiguous_upload_reuses_exact_file_id(self):
        operation = self.admit('open_workspace')
        self.drive.fail_upload_once = True
        with self.assertRaises(RuntimeError):
            self.execute(operation)
        first = self.execute(operation)
        self.assertEqual(first['status'], 'completed')
        self.assertEqual(self.execute(operation), first)
        self.assertEqual(len(self.drive.created), 1)
        self.assertEqual(self.github.branches['codex/hp/' + first['workspace_id']], self.github.base)

    def test_save_receipt_acknowledges_exact_bytes_and_ambiguous_commit_is_replayed(self):
        workspace,_ = self.open()
        operation = self.save(workspace)
        self.github.fail_commit_once = True
        with self.assertRaises(RuntimeError):
            self.execute(operation)
        saved = self.execute(operation)
        self.assertEqual(saved['status'], 'completed')
        receipt = saved['result']
        self.assertEqual(set(receipt), {'schema_version','kind','site_id','workspace_id','operation_id','base_commit','saved_commit','bundle_sha256'})
        self.assertEqual(receipt['base_commit'], self.github.base)
        self.assertEqual(len(self.github.created_commits), 1)
        self.assertEqual(self.store.get('workspace:' + workspace)['head_commit'], receipt['saved_commit'])
        self.assertEqual(self.execute(operation), saved)

    def test_noop_save_acknowledges_without_creating_git_objects(self):
        workspace,_ = self.open()
        operation,file_id = str(uuid4()),'noop-file-' + str(uuid4())
        manifest = {'schema_version':1,'kind':'changes','site_id':self.site,'workspace_id':workspace,
            'base_commit':self.github.base,'operation_id':operation,'changes':[]}
        stream=BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:
            archive.writestr('manifest.json',json.dumps(manifest))
        data=stream.getvalue(); self.drive.files[file_id]=('changes-folder',data)
        self.admit('save_draft',operation_id=operation,workspace_id=workspace,base_commit=self.github.base,
            bundle_file_id=file_id,bundle_sha256=sha256(data))
        result=self.execute(operation)
        self.assertEqual(result['result']['saved_commit'],self.github.base)
        self.assertFalse(self.github.created_commits)

    def test_receipt_is_recorded_after_inflight_write_even_if_membership_revoked(self):
        operation=self.admit('open_workspace')
        original=self.drive.create_exact
        def revoke(*args):
            result=original(*args)
            member=self.store.get('principal:operator')
            self.store.put('principal:operator',{**member,'disabled':True},member['_version'])
            return result
        self.drive.create_exact=revoke
        result=self.execute(operation)
        self.assertEqual(result['status'],'failed')
        self.assertIn('snapshot_upload',result['phases'])
        self.assertNotIn('pending_effect',result)
        self.assertEqual(len(self.drive.created),1)

    def test_unknown_effect_after_revoke_reconciles_readonly_before_terminal(self):
        operation=self.admit('open_workspace')
        self.drive.fail_upload_once=True
        with self.assertRaises(RuntimeError): self.execute(operation)
        row=self.store.get('principal:operator')
        self.store.put('principal:operator',{**row,'disabled':True},row['_version'])
        result=self.execute(operation)
        self.assertEqual(result['error'],'access_revoked')
        self.assertIn('snapshot_upload',result['phases'])
        self.assertEqual(len(self.drive.created),1)
        self.assertFalse(self.store.get('lease:site:'+self.site).get('blocked_operation'))

    def test_unreconciled_publisher_blocks_site_after_cancel_without_another_write(self):
        operation=self.publish_operation()
        calls=[]
        class Unknown:
            def publish(self,*args):
                calls.append(args); raise RuntimeError('unknown outcome')
            def reconcile(self,*args): return None
        self.executor.publisher=Unknown()
        with self.assertRaises(RuntimeError): self.execute(operation)
        self.service.cancel(self.claims,operation)
        with self.assertRaises(ReconciliationRequired): self.execute(operation)
        self.assertEqual(len(calls),1)
        self.assertEqual(self.store.get('operation:'+operation)['status'],'reconciling')
        other=self.admit('open_workspace')
        self.assertEqual(self.execute(other)['status'], 'retry_wait')

    def test_wrong_bundle_hash_never_commits(self):
        workspace,_ = self.open()
        operation = self.save(workspace)
        row = self.store.get('operation:' + operation)
        row['input']['bundle_sha256'] = 'f' * 64
        self.store.put('operation:' + operation, row, row['_version'])
        result = self.execute(operation)
        self.assertEqual(result['error'], 'bundle_hash_mismatch')
        self.assertFalse(self.github.created_commits)

    def test_revoked_membership_before_execution_has_no_provider_effect(self):
        operation = self.admit('open_workspace')
        row = self.store.get('principal:operator')
        self.store.put('principal:operator', {**row, 'disabled': True}, row['_version'])
        result = self.execute(operation)
        self.assertEqual(result['error'], 'access_revoked')
        self.assertEqual(self.github.branches, {'dev': self.github.base, 'main': self.github.base})
        self.assertFalse(self.drive.created)

    def test_fenced_site_lease_prevents_parallel_commands(self):
        operation = self.admit('open_workspace')
        self.store.put('lease:site:' + self.site, {'owner': 'other', 'epoch': 5, 'until': 1100})
        result=self.execute(operation)
        self.assertEqual(result['status'],'retry_wait')
        self.assertEqual(result['queue_state'],'pending')
        self.assertFalse(self.drive.created)

    def test_pending_effect_blocks_other_operations_even_after_lease_timeout(self):
        first=self.admit('open_workspace')
        other=self.admit('open_workspace')
        create=self.drive.create_exact
        def while_inflight(*args):
            self.executor.clock=lambda:2000
            self.assertEqual(self.execute(other)['status'], 'retry_wait')
            self.executor.clock=self.clock
            return create(*args)
        self.drive.create_exact=while_inflight
        self.assertEqual(self.execute(first)['status'],'completed')
        self.assertFalse(self.store.get('lease:site:'+self.site).get('blocked_operation'))

    def test_expired_executor_cannot_write_after_replacement(self):
        operation = self.admit('open_workspace')
        def replace(branch):
            row = self.store.get('lease:site:' + self.site)
            self.store.put('lease:site:' + self.site, {**row, 'owner': 'replacement', 'epoch': row['epoch']+1}, row['_version'])
            return self.github.base
        self.github.head = replace
        with self.assertRaises(Busy):
            self.execute(operation)
        self.assertEqual(self.store.get('lease:site:' + self.site)['owner'], 'replacement')
        self.assertFalse(self.drive.created)

    def test_failed_ci_after_initial_wait_is_observed_terminal_and_unblocks_site(self):
        from github_workflow import ValidationPending,ValidationFailed
        workspace,_=self.open()
        saved=self.execute(self.save(workspace))['result']
        operation=self.admit('submit_preview',workspace_id=workspace,saved_commit=saved['saved_commit'])
        def waiting(*args): raise ValidationPending('candidate_pr_created')
        def failed(*args): raise ValidationFailed('github_validation_failed')
        self.validator.validate=waiting
        self.validator.reconcile=failed
        with self.assertRaises(ValidationPending): self.execute(operation)
        self.assertEqual(self.store.get('lease:site:'+self.site)['blocked_operation'],operation)
        result=self.execute(operation)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['error'],'github_validation_failed')
        self.assertEqual(result['phases']['github_validation'],{'observed_failure':'github_validation_failed'})
        self.assertNotIn('pending_effect',result)
        self.assertNotIn('queue_state',result)
        self.assertIsNone(self.store.get('lease:site:'+self.site)['blocked_operation'])
        self.assertEqual(self.execute(self.admit('open_workspace'))['status'],'completed')

    def test_queued_busy_delivery_is_durably_deferred_without_taking_site_lease(self):
        operation=self.admit('open_workspace')
        row=self.store.get('operation:'+operation)
        self.store.put('operation:'+operation,{**row,'queue_state':'sent'},row['_version'])
        self.store.put('lease:site:'+self.site,{'owner':'other','epoch':8,'until':0,'blocked_operation':'other-operation'})
        before=self.store.get('lease:site:'+self.site)
        result=self.executor.execute(operation)
        self.assertEqual(result['status'],'retry_wait')
        self.assertEqual(result['queue_state'],'pending')
        self.assertEqual(result['retry_at'],self.now+30)
        self.assertEqual(result['retry_generation'],1)
        self.assertEqual(self.store.get('lease:site:'+self.site),before)
        self.assertFalse(self.drive.created)
        self.assertEqual(self.github.branches,{'dev':self.github.base,'main':self.github.base})
        self.assertEqual(self.executor.execute(operation),result)

    def test_preview_no_changes_never_creates_pr_commit_or_deployment_or_report(self):
        workspace,_=self.open()
        site=self.store.get('site:'+self.site)
        self.store.put('site:'+self.site,{**site,'reporting_enabled':True},site['_version'])
        operation=self.admit('submit_preview',workspace_id=workspace,saved_commit=self.github.base)
        before=deepcopy(self.github.branches)
        result=self.execute(operation)
        self.assertEqual(result['result']['kind'],'no_changes')
        self.assertFalse(result.get('reporting_required'))
        self.assertNotIn('queue_state',result)
        self.assertEqual(self.github.branches,before)
        self.assertFalse(self.github.created_commits)
        self.assertEqual(self.validator.calls,0)
        self.assertFalse(self.preview_publisher.effects)

    def test_repeat_preview_reuses_current_verified_coordinates_without_effects(self):
        first_operation,first=self.preview()
        workspace=first['input']['workspace_id']
        operation=self.admit('submit_preview',workspace_id=workspace,saved_commit=first['input']['saved_commit'])
        branches=deepcopy(self.github.branches)
        count=len(self.github.created_commits)
        result=self.execute(operation)
        self.assertEqual(result['result']['kind'],'no_changes')
        self.assertEqual(result['result']['preview_id'],first['result']['preview_id'])
        self.assertEqual(result['result']['artifact_sha256'],first['result']['artifact_sha256'])
        self.assertEqual(self.github.branches,branches)
        self.assertEqual(len(self.github.created_commits),count)
        self.assertEqual(self.validator.calls,1)
        self.assertEqual(len(self.preview_publisher.effects),1)

    def test_preview_clears_old_approval_before_deploy_even_when_cancelled_after_write(self):
        old_operation,old=self.preview()
        old_id=old['result']['preview_id']
        workspace,_=self.open()
        saved=self.execute(self.save(workspace,before=b'edited',after=b'next'))['result']
        operation=self.admit('submit_preview',workspace_id=workspace,saved_commit=saved['saved_commit'])
        publish=self.preview_publisher.publish
        def cancel_after(*args):
            self.assertIsNone(self.store.get('site:'+self.site).get('current_preview'))
            with self.assertRaises(Rejected): self.service.prepare_publish(self.claims,self.site,old_id)
            receipt=publish(*args)
            self.service.cancel(self.claims,operation)
            return receipt
        self.preview_publisher.publish=cancel_after
        result=self.execute(operation)
        self.assertEqual(result['status'],'cancelled')
        self.assertIsNone(self.store.get('site:'+self.site).get('current_preview'))
        with self.assertRaises(Rejected): self.service.prepare_publish(self.claims,self.site,old_id)

    def test_ambiguous_preview_deployment_never_retains_old_approval_pointer(self):
        _,old=self.preview()
        old_id=old['result']['preview_id']
        old_time=self.store.get('preview:'+old_id)['updated_at']
        self.now += 60
        workspace,_=self.open()
        saved=self.execute(self.save(workspace,before=b'edited',after=b'next'))['result']
        operation=self.admit('submit_preview',workspace_id=workspace,saved_commit=saved['saved_commit'])
        self.preview_publisher.fail_once=True
        with self.assertRaises(RuntimeError): self.execute(operation)
        self.assertIsNone(self.store.get('site:'+self.site).get('current_preview'))
        self.assertEqual(self.store.get('site:'+self.site)['last_verified_preview'],old_id)
        self.assertEqual(self.service.list_sites(self.claims)[0]['deployments']['dev']['updated_at'],old_time)
        self.assertEqual(self.store.get('lease:site:'+self.site)['blocked_operation'],operation)
        result=self.execute(operation)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(self.store.get('site:'+self.site)['current_preview'],result['result']['preview_id'])
        self.assertEqual(self.store.get('site:'+self.site)['last_verified_preview'],result['result']['preview_id'])
        self.assertEqual(self.service.list_sites(self.claims)[0]['deployments']['dev']['updated_at'],int(self.now))
        self.assertGreater(self.now,old_time)

    def test_verified_preview_records_time_and_last_success_pointer(self):
        _, result = self.preview()
        preview_id = result['result']['preview_id']
        preview = self.store.get('preview:' + preview_id)
        site = self.store.get('site:' + self.site)
        self.assertEqual(preview['updated_at'], int(self.now))
        self.assertEqual(site['last_verified_preview'], preview_id)
        status = self.service.list_sites(self.claims)[0]['deployments']
        self.assertEqual(status['dev']['updated_at'], int(self.now))

    def test_legacy_missing_production_pointer_does_not_block_preview(self):
        site = self.store.get('site:'+self.site)
        self.store.put('site:'+self.site, {**site, 'initial_main_commit': None}, site['_version'])
        _, result = self.preview()
        self.assertEqual(result['status'], 'completed')
        self.assertIsNone(self.store.get('preview:'+result['result']['preview_id'])['publication_changes'])

    def test_invalid_legacy_production_source_does_not_block_preview(self):
        original = self.executor._snapshot
        def snapshot(run, github, commit):
            if 'summary_base' in run.op.get('intents', {}):
                raise BundleError('legacy source invalid')
            return original(run, github, commit)
        self.executor._snapshot = snapshot
        _, result = self.preview()
        self.assertEqual(result['status'], 'completed')
        self.assertIsNone(self.store.get('preview:'+result['result']['preview_id'])['publication_changes'])

    def test_revocation_during_summary_read_still_blocks_dev(self):
        original = self.executor._snapshot
        def snapshot(run, github, commit):
            if 'summary_base' in run.op.get('intents', {}):
                member = self.store.get('principal:operator')
                self.store.put('principal:operator', {**member, 'disabled': True}, member['_version'])
            return original(run, github, commit)
        self.executor._snapshot = snapshot
        original_dev = self.github.branches['dev']
        _, result = self.preview()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error'], 'access_revoked')
        self.assertFalse(self.preview_publisher.effects)
        self.assertEqual(self.github.branches['dev'], original_dev)

    def test_content_versions_advance_only_for_verified_new_artifacts(self):
        _, first = self.preview()
        first_hash = first['result']['artifact_sha256']
        self.assertEqual(self.store.get('content-version:'+self.site+':'+first_hash)['version'], 1)
        workspace,_ = self.open()
        saved = self.execute(self.save(workspace,before=b'edited',after=b'next'))['result']
        operation = self.admit('submit_preview',workspace_id=workspace,saved_commit=saved['saved_commit'])
        self.preview_publisher.fail_once = True
        with self.assertRaises(RuntimeError): self.execute(operation)
        self.assertEqual(self.store.get('site:'+self.site)['last_content_version'], 1)
        second = self.execute(operation)
        second_hash = second['result']['artifact_sha256']
        self.assertNotEqual(second_hash, first_hash)
        self.assertEqual(self.store.get('content-version:'+self.site+':'+second_hash)['version'], 2)
        self.execute(operation)
        self.assertEqual(self.store.get('site:'+self.site)['last_content_version'], 2)
        self.assertEqual(self.service.list_sites(self.claims)[0]['deployments']['dev']['version'], 2)

    def test_invalid_version_registry_fails_before_environment_deployment(self):
        workspace,_ = self.open()
        saved = self.execute(self.save(workspace))['result']
        operation = self.admit('submit_preview',workspace_id=workspace,saved_commit=saved['saved_commit'])
        original = self.store.get
        def get(key):
            if key.startswith('content-version:'): return {'version': True}
            return original(key)
        self.store.get = get
        result = self.execute(operation)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error'], 'content_version_corrupt')
        self.assertFalse(self.preview_publisher.effects)
        self.assertIsNone(self.store.get('site:'+self.site).get('current_preview'))

    def test_preview_preflight_rejects_unbound_publisher_before_candidate_effects(self):
        workspace,_=self.open()
        saved=self.execute(self.save(workspace))['result']
        operation=self.admit('submit_preview',workspace_id=workspace,saved_commit=saved['saved_commit'])
        def unbound(*args): raise IntegrationUnavailable('preview_binding_missing')
        self.preview_publisher.preflight=unbound
        before=deepcopy(self.github.branches)
        commits=len(self.github.created_commits)
        with self.assertRaises(IntegrationUnavailable): self.execute(operation)
        self.assertEqual(self.github.branches,before)
        self.assertEqual(len(self.github.created_commits),commits)
        self.assertEqual(self.validator.calls,0)
        self.assertFalse(self.store.get('operation:'+operation).get('pending_effect'))

    def test_lost_finish_response_never_overwrites_committed_saved_operation(self):
        workspace,_=self.open()
        operation=self.save(workspace)
        transact=self.store.transact
        lost=[False]
        def response_lost(writes):
            transact(writes)
            if not lost[0] and any(getattr(w,'key',None)=='operation:'+operation and getattr(w,'value',None) and w.value.get('status')=='completed' for w in writes):
                lost[0]=True
                raise RuntimeError('transaction committed response lost')
        self.store.transact=response_lost
        with self.assertRaises(RuntimeError): self.execute(operation)
        result=self.store.get('operation:'+operation)
        self.assertEqual(result['status'],'completed')
        self.assertNotIn('retry_at',result)
        self.assertEqual(self.store.get('workspace:'+workspace)['head_commit'],result['result']['saved_commit'])
        self.assertEqual(self.execute(operation),result)

    def test_lost_publish_finish_response_preserves_completed_reporting_outbox(self):
        site=self.store.get('site:'+self.site)
        self.store.put('site:'+self.site,{**site,'reporting_enabled':True},site['_version'])
        operation=self.publish_operation()
        transact=self.store.transact
        lost=[False]
        def response_lost(writes):
            transact(writes)
            if not lost[0] and any(getattr(w,'key',None)=='operation:'+operation and getattr(w,'value',None) and w.value.get('status')=='completed' for w in writes):
                lost[0]=True
                raise RuntimeError('publish finish response lost after commit')
        self.store.transact=response_lost
        with self.assertRaises(RuntimeError): self.execute(operation)
        result=self.store.get('operation:'+operation)
        self.assertEqual(result['status'],'completed')
        self.assertTrue(result['reporting_required'])
        self.assertEqual(result['queue_state'],'pending')
        self.assertNotIn('retry_at',result)
        self.assertEqual(self.store.get('site:'+self.site)['current_publication']['operation_id'],operation)
        self.assertEqual(len(self.publisher.effects),1)
        self.assertEqual(self.execute(operation),result)

    def test_two_consecutive_edits_same_workspace_preserve_unrelated_remote_files(self):
        workspace,_=self.open()
        saved1=self.execute(self.save(workspace))['result']['saved_commit']
        remote1='d'*40
        self.github.sources[remote1]={'index.html':b'base','style.css':b'remote css'}
        self.github.branches['dev']=remote1
        first=self.admit('submit_preview',workspace_id=workspace,saved_commit=saved1)
        self.assertEqual(self.execute(first)['result']['kind'],'preview')
        row=self.store.get('workspace:'+workspace)
        self.assertEqual(row['base_on_dev'],saved1)
        self.assertEqual(row['head_commit'],saved1)
        self.assertEqual(self.github.branches[row['branch']],saved1)
        saved2=self.execute(self.save(workspace,before=b'edited',after=b'next'))['result']['saved_commit']
        remote2='e'*40
        self.github.sources[remote2]={'index.html':b'edited','style.css':b'remote css','extra.txt':b'new remote file'}
        self.github.branches['dev']=remote2
        second=self.admit('submit_preview',workspace_id=workspace,saved_commit=saved2)
        result=self.execute(second)
        self.assertEqual(result['result']['kind'],'preview')
        self.assertEqual(self.github.sources[result['result']['source_commit']],
            {'index.html':b'next','style.css':b'remote css','extra.txt':b'new remote file'})
        row=self.store.get('workspace:'+workspace)
        self.assertEqual(row['base_on_dev'],saved2)
        self.assertEqual(row['head_commit'],saved2)
        self.assertEqual(self.github.branches[row['branch']],saved2)
        self.assertEqual(self.validator.calls,2)

    def test_missing_browser_renderer_fails_closed_before_candidate_effects(self):
        workspace,_=self.open()
        saved=self.execute(self.save(workspace))['result']
        operation=self.admit('submit_preview',workspace_id=workspace,saved_commit=saved['saved_commit'])
        self.executor.browser_validator=None
        before=deepcopy(self.github.branches)
        with self.assertRaisesRegex(IntegrationUnavailable,'browser_validator'): self.execute(operation)
        self.assertEqual(self.github.branches,before)
        self.assertEqual(self.validator.calls,0)
        self.assertFalse(self.preview_publisher.effects)

    def test_browser_artifact_mismatch_never_moves_dev_or_approval(self):
        self.browser_validator.mismatch=True
        _,result=self.preview()
        self.assertEqual(result['error'],'browser_validation_proof_mismatch')
        self.assertEqual(self.github.branches['dev'],self.github.base)
        self.assertFalse(self.preview_publisher.effects)
        self.assertFalse(self.store.get('site:'+self.site).get('current_preview'))

    def test_browser_render_proof_precedes_dev_commit_and_preserves_screenshot_refs(self):
        original=self.browser_validator.validate
        def render(site,preview,artifact_key,operation,guard):
            self.assertEqual(self.github.branches['dev'],self.github.base)
            self.assertIn(artifact_key,self.artifacts.files)
            return original(site,preview,artifact_key,operation,guard)
        self.browser_validator.validate=render
        _,result=self.preview()
        preview=self.store.get('preview:'+result['result']['preview_id'])
        browser=preview['browser_validation']
        self.assertTrue(browser['verified'])
        self.assertEqual(browser['source_commit'],preview['source_commit'])
        self.assertEqual(browser['artifact_sha256'],preview['artifact_sha256'])
        self.assertTrue(browser['report_key'].endswith('/report.json'))
        self.assertEqual(len(browser['screenshot_keys']),2)

    def test_executor_real_browser_validator_carries_package_id_and_reconciles_once(self):
        from browser_validation import BrowserValidation, BrowserValidationPending
        from test_browser_validation import ACCOUNT, CLUSTER, DEFINITION, IMAGE, FakeECS, FakeS3
        s3=FakeS3(); ecs=FakeECS(s3)
        config={'enabled':True,'account_id':ACCOUNT,'region':'ap-northeast-1','cluster':CLUSTER,
            'task_definition':DEFINITION,'image_digest':IMAGE,'container_name':'validator',
            'subnet_ids':['subnet-12345678'],'security_group_ids':['sg-12345678'],
            'artifact_bucket':'artifact-bucket','output_bucket':'output-bucket','deadline_seconds':600}
        self.executor.browser_validator=BrowserValidation(self.store,ecs,s3,config)
        validate_calls=[]
        real_validate=self.executor.browser_validator.validate
        def validate_once(*args):
            validate_calls.append(args)
            return real_validate(*args)
        self.executor.browser_validator.validate=validate_once
        original=self.artifacts.put_exact
        def upload(key,data):
            result=original(key,data)
            s3.objects['artifact-bucket',key]=data
            return result
        self.artifacts.put_exact=upload
        workspace,_=self.open()
        saved=self.execute(self.save(workspace))['result']
        operation=self.admit('submit_preview',workspace_id=workspace,saved_commit=saved['saved_commit'])
        ecs.unknown_ack=True
        with self.assertRaises(BrowserValidationPending): self.execute(operation)
        self.assertEqual(self.github.branches['dev'],self.github.base)
        self.assertEqual(len(ecs.requests),1)
        envelope=json.loads(ecs.requests[0]['overrides']['containerOverrides'][0]['environment'][0]['value'])
        browser_row=next(value for key,value in self.store.rows.items() if key.startswith('browser-validation:'))
        job=json.loads(browser_row['job_json'])
        self.assertEqual(envelope['job_sha256'],sha256(browser_row['job_json'].encode()))
        self.assertEqual(job['package_operation_id'],operation)
        ecs.unknown_ack=False
        result=self.execute(operation)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(len(ecs.requests),1)
        preview=self.store.get('preview:'+result['result']['preview_id'])
        self.assertTrue(preview['browser_validation']['verified'])
        self.assertEqual(len(preview['browser_validation']['screenshot_keys']),2)
        self.assertTrue(any(method=='head_bucket' for method,_ in s3.calls))
        self.assertEqual(len(validate_calls),1)

    def install_real_browser_fixture(self):
        from browser_validation import BrowserValidation
        from test_browser_validation import ACCOUNT, CLUSTER, DEFINITION, IMAGE, FakeECS, FakeS3
        s3=FakeS3();ecs=FakeECS(s3)
        config={'enabled':True,'account_id':ACCOUNT,'region':'ap-northeast-1','cluster':CLUSTER,
            'task_definition':DEFINITION,'image_digest':IMAGE,'container_name':'validator',
            'subnet_ids':['subnet-12345678'],'security_group_ids':['sg-12345678'],
            'artifact_bucket':'artifact-bucket','output_bucket':'output-bucket','deadline_seconds':600}
        self.executor.browser_validator=BrowserValidation(self.store,ecs,s3,config)
        original=self.artifacts.put_exact
        def upload(key,data):
            result=original(key,data);s3.objects['artifact-bucket',key]=data;return result
        self.artifacts.put_exact=upload
        workspace,_=self.open()
        saved=self.execute(self.save(workspace))['result']
        operation=self.admit('submit_preview',workspace_id=workspace,saved_commit=saved['saved_commit'])
        return operation,s3,ecs

    def test_cancel_after_private_manifest_put_finishes_without_task_or_dev_write(self):
        operation,s3,ecs=self.install_real_browser_fixture()
        s3.before_put=lambda args:self.service.cancel(self.claims,operation)
        result=self.execute(operation)
        self.assertEqual(result['status'],'cancelled')
        self.assertTrue(result['phases']['browser_validation']['not_started'])
        self.assertTrue(result['phases']['browser_validation']['launch_prewrite_proven'])
        self.assertNotIn('pending_effect',result)
        self.assertFalse(ecs.requests)
        self.assertEqual(self.github.branches['dev'],self.github.base)
        self.assertFalse(self.preview_publisher.effects)
        self.assertEqual(sum(method=='put_object' for method,_ in s3.calls),1)

    def test_revocation_after_private_manifest_put_records_no_launch_without_new_effect(self):
        operation,s3,ecs=self.install_real_browser_fixture()
        def revoke(args):
            member=self.store.get('principal:operator')
            self.store.put('principal:operator',{**member,'disabled':True},member['_version'])
        s3.before_put=revoke
        result=self.execute(operation)
        self.assertEqual(result['status'],'failed')
        self.assertTrue(result['phases']['browser_validation']['launch_prewrite_proven'])
        self.assertNotIn('pending_effect',result)
        self.assertFalse(ecs.requests)
        self.assertEqual(self.github.branches['dev'],self.github.base)

    def test_cancel_after_unknown_manifest_put_ack_settles_without_new_put_or_task(self):
        from browser_validation import BrowserValidationPending
        operation,s3,ecs=self.install_real_browser_fixture()
        s3.unknown_put_ack=True
        with self.assertRaises(BrowserValidationPending):self.execute(operation)
        row=self.store.get('operation:'+operation)
        self.assertIn('pending_effect',row)
        self.service.cancel(self.claims,operation)
        writes=sum(method=='put_object' for method,_ in s3.calls)
        result=self.execute(operation)
        self.assertEqual(result['status'],'cancelled')
        self.assertTrue(result['phases']['browser_validation']['launch_prewrite_proven'])
        self.assertEqual(sum(method=='put_object' for method,_ in s3.calls),writes)
        self.assertFalse(ecs.requests)

    def test_cancel_with_missing_manifest_and_no_launch_admission_finishes_readonly(self):
        from browser_validation import BrowserValidationPending
        operation,s3,ecs=self.install_real_browser_fixture()
        s3.before_put=lambda args: (_ for _ in ()).throw(OSError('unknown prelaunch object response'))
        with self.assertRaises(BrowserValidationPending):self.execute(operation)
        self.assertFalse(any(key.endswith('/job.json') for bucket,key in s3.objects))
        self.service.cancel(self.claims,operation)
        writes=sum(method=='put_object' for method,_ in s3.calls)
        result=self.execute(operation)
        self.assertEqual(result['status'],'cancelled')
        self.assertTrue(result['phases']['browser_validation']['launch_prewrite_proven'])
        self.assertEqual(sum(method=='put_object' for method,_ in s3.calls),writes)
        self.assertFalse(ecs.requests)
        self.assertNotIn('pending_effect',result)

    def test_cancel_after_unknown_invisible_run_task_stays_ambiguous_and_never_relaunches(self):
        from browser_validation import BrowserValidationPending
        operation,s3,ecs=self.install_real_browser_fixture()
        ecs.unknown_ack=True;ecs.hide_tasks=True
        with self.assertRaises(BrowserValidationPending):self.execute(operation)
        self.service.cancel(self.claims,operation)
        with self.assertRaises(ReconciliationRequired):self.execute(operation)
        result=self.store.get('operation:'+operation)
        self.assertNotEqual(result['status'],'cancelled')
        self.assertIn('pending_effect',result)
        self.assertNotIn('browser_validation',result.get('phases',{}))
        self.assertEqual(len(ecs.requests),1)
        self.assertEqual(sum(method=='put_object' for method,_ in s3.calls),1)
        self.assertEqual(self.github.branches['dev'],self.github.base)

    def test_preview_combines_unrelated_dev_changes_and_binds_ci_artifact(self):
        workspace,_ = self.open()
        saved = self.execute(self.save(workspace))['result']
        remote = 'd' * 40
        self.github.sources[remote] = {'index.html': b'base', 'style.css': b'remote css'}
        self.github.branches['dev'] = remote
        operation = self.admit('submit_preview', workspace_id=workspace, saved_commit=saved['saved_commit'])
        result = self.execute(operation)
        self.assertEqual(result['status'], 'completed')
        preview = self.store.get('preview:' + result['result']['preview_id'])
        self.assertEqual(preview['source_commit'], self.github.branches['dev'])
        self.assertEqual(self.github.sources[preview['source_commit']], {'index.html': b'edited','style.css': b'remote css'})
        self.assertEqual(len(self.artifacts.files), 1)
        self.assertEqual(self.execute(operation), result)
        self.assertEqual(self.validator.calls, 1)

    def test_preview_conflict_is_local_repair_result_without_dev_write(self):
        workspace,_ = self.open()
        site=self.store.get('site:'+self.site)
        self.store.put('site:'+self.site,{**site,'reporting_enabled':True},site['_version'])
        saved = self.execute(self.save(workspace))['result']
        remote = 'd' * 40
        self.github.sources[remote] = {'index.html': b'remote', 'style.css': b'base css'}
        self.github.branches['dev'] = remote
        operation = self.admit('submit_preview', workspace_id=workspace, saved_commit=saved['saved_commit'])
        result = self.execute(operation)
        self.assertEqual(result['result']['kind'], 'conflicts')
        self.assertEqual(result['result']['paths'], ['index.html'])
        self.assertFalse(result.get('reporting_required'))
        self.assertNotIn('queue_state',result)
        self.assertEqual(self.github.branches['dev'], remote)
        self.assertEqual(self.validator.calls, 0)

    def test_unrelated_ci_artifact_never_advances_dev(self):
        self.validator.corrupt = True
        _, result = self.preview()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(self.github.branches['dev'], self.github.base)
        self.assertFalse(self.artifacts.files)

    def test_stale_live_preview_is_not_verified_or_publishable(self):
        self.validator.stale_live = True
        _, result = self.preview()
        self.assertEqual(result['error'], 'preview_readback_mismatch')
        self.assertFalse(any(k.startswith('preview:') for k in self.store.rows))

    def test_missing_validation_adapter_fails_closed_and_stays_resumable(self):
        workspace,_ = self.open()
        saved = self.execute(self.save(workspace))['result']
        operation = self.admit('submit_preview', workspace_id=workspace, saved_commit=saved['saved_commit'])
        self.executor.validator = None
        with self.assertRaises(IntegrationUnavailable):
            self.execute(operation)
        self.assertEqual(self.store.get('operation:' + operation)['status'], 'retry_wait')
        self.assertEqual(self.github.branches['dev'], self.github.base)

    def test_publish_reuses_verified_bytes_and_reconciles_ambiguous_effect(self):
        operation = self.publish_operation()
        self.publisher.fail_once = True
        with self.assertRaises(RuntimeError):
            self.execute(operation)
        result = self.execute(operation)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(self.publisher.effects), 1)
        self.assertEqual(self.validator.calls, 1)
        self.assertEqual(self.execute(operation), result)

    def test_cancel_after_verified_publish_records_factual_pointer_without_new_write(self):
        operation=self.publish_operation()
        publish=self.publisher.publish
        def cancel_after(*args):
            receipt=publish(*args)
            self.service.cancel(self.claims,operation)
            return receipt
        self.publisher.publish=cancel_after
        result=self.execute(operation)
        self.assertEqual(result['status'],'published_after_cancel_or_revocation')
        self.assertEqual(result['result']['kind'],'published_after_cancel_or_revocation')
        current=self.store.get('site:'+self.site)['current_publication']
        self.assertEqual(current['operation_id'],operation)
        self.assertEqual(len(self.publisher.effects),1)
        self.assertEqual(self.execute(operation),result)

    def test_revoked_after_lost_publish_response_reconciles_factual_pointer_readonly(self):
        operation=self.publish_operation()
        self.publisher.fail_once=True
        with self.assertRaises(RuntimeError): self.execute(operation)
        member=self.store.get('principal:operator')
        self.store.put('principal:operator',{**member,'disabled':True},member['_version'])
        def forbidden(*args): self.fail('must not call publisher again after revoke')
        self.publisher.publish=forbidden
        result=self.execute(operation)
        self.assertEqual(result['status'],'published_after_cancel_or_revocation')
        self.assertEqual(self.store.get('site:'+self.site)['current_publication']['operation_id'],operation)
        self.assertEqual(len(self.publisher.effects),1)

    def test_cancel_after_lost_publish_response_reconciles_without_republishing(self):
        operation=self.publish_operation()
        self.publisher.fail_once=True
        with self.assertRaises(RuntimeError): self.execute(operation)
        self.service.cancel(self.claims,operation)
        def forbidden(*args): self.fail('must not publish again after cancel')
        self.publisher.publish=forbidden
        result=self.execute(operation)
        self.assertEqual(result['status'],'published_after_cancel_or_revocation')
        self.assertEqual(len(self.publisher.effects),1)
        self.assertEqual(self.store.get('site:'+self.site)['current_publication']['operation_id'],operation)

    def test_revoke_after_verified_publish_records_factual_state(self):
        operation=self.publish_operation()
        publish=self.publisher.publish
        def revoke(*args):
            receipt=publish(*args)
            member=self.store.get('principal:operator')
            self.store.put('principal:operator',{**member,'disabled':True},member['_version'])
            return receipt
        self.publisher.publish=revoke
        result=self.execute(operation)
        self.assertEqual(result['status'],'published_after_cancel_or_revocation')
        self.assertEqual(self.store.get('site:'+self.site)['current_publication']['operation_id'],operation)
        self.assertEqual(len(self.publisher.effects),1)

    def test_config_changed_after_observed_publication_remains_blocked(self):
        operation=self.publish_operation()
        publish=self.publisher.publish
        def changed(*args):
            receipt=publish(*args)
            site=self.store.get('site:'+self.site)
            self.store.put('site:'+self.site,{**site,'config_version':2},site['_version'])
            return receipt
        self.publisher.publish=changed
        with self.assertRaises(ReconciliationRequired): self.execute(operation)
        row=self.store.get('operation:'+operation)
        self.assertEqual(row['status'],'reconciling')
        self.assertTrue(row['reconciliation_required'])
        self.assertEqual(self.store.get('lease:site:'+self.site)['blocked_operation'],operation)
        self.assertNotIn('current_publication',self.store.get('site:'+self.site))

    def test_missing_preview_publisher_fails_before_candidate_write(self):
        self.executor.preview_publisher=None
        workspace,_=self.open()
        saved=self.execute(self.save(workspace))['result']
        operation=self.admit('submit_preview',workspace_id=workspace,saved_commit=saved['saved_commit'])
        with self.assertRaisesRegex(IntegrationUnavailable,'preview_publisher'): self.execute(operation)
        self.assertEqual(self.github.branches['dev'],self.github.base)
        self.assertEqual(self.validator.calls,0)

    def test_main_uses_only_approved_artifact_not_latest_dev_or_version_metadata(self):
        operation=self.publish_operation()
        latest='f'*40
        self.github.sources[latest]={'index.html':b'unapproved latest dev'}
        self.github.branches['dev']=latest
        result=self.execute(operation)
        main=self.github.branches['main']
        self.assertEqual(self.github.sources[main],{'index.html':b'edited','style.css':b'base css'})
        self.assertNotIn('version.json',self.github.sources[main])
        self.assertEqual(self.github.branches['dev'],latest)
        self.assertEqual(result['result']['main_commit'],main)
        self.assertEqual(self.store.get('site:'+self.site)['current_main_commit'],main)
        self.assertEqual(self.store.get('site:'+self.site)['current_publication']['main_commit'],main)

    def test_main_response_loss_then_revoke_recovers_pointer_without_publish(self):
        operation=self.publish_operation()
        self.github.fail_commit_once=True
        with self.assertRaises(RuntimeError): self.execute(operation)
        member=self.store.get('principal:operator')
        self.store.put('principal:operator',{**member,'disabled':True},member['_version'])
        result=self.execute(operation)
        self.assertEqual(result['error'],'access_revoked')
        self.assertEqual(self.store.get('site:'+self.site)['current_main_commit'],self.github.branches['main'])
        self.assertFalse(self.publisher.effects)
        self.assertIn('main_commit',result['phases'])

    def test_main_stale_head_prevents_production_write(self):
        operation=self.publish_operation()
        unexpected='f'*40
        self.github.sources[unexpected]={'index.html':b'other production source'}
        self.github.branches['main']=unexpected
        with self.assertRaises(RuntimeError): self.execute(operation)
        self.assertFalse(self.publisher.effects)
        self.assertEqual(self.github.branches['main'],unexpected)
        self.assertEqual(self.store.get('lease:site:'+self.site)['blocked_operation'],operation)

    def test_retry_backoff_budget_exhaustion_requires_attention_and_retains_unknown_lock(self):
        operation=self.publish_operation()
        self.executor.max_retry_attempts=3
        calls=[]
        class Unknown:
            def publish(self,*args): calls.append(args); raise RuntimeError('unknown')
            def reconcile(self,*args): return None
        self.executor.publisher=Unknown()
        due=[]
        for attempt in range(1,4):
            with self.assertRaises(RuntimeError): self.execute(operation)
            row=self.store.get('operation:'+operation)
            self.assertEqual(row['retry_attempts'],attempt)
            self.assertEqual(row['retry_generation'],attempt)
            due.append(row['retry_at']-self.now)
        self.assertEqual(due,[5,10,20])
        self.assertEqual(row['status'],'needs_attention')
        self.assertNotIn('queue_state',row)
        self.assertEqual(self.store.get('lease:site:'+self.site)['blocked_operation'],operation)
        self.assertEqual(len(calls),1)
        self.assertEqual(self.executor.execute(operation),row)

    def test_expected_ci_wait_has_deadline_and_does_not_spend_error_budget(self):
        workspace,_=self.open()
        saved=self.execute(self.save(workspace))['result']
        operation=self.admit('submit_preview',workspace_id=workspace,saved_commit=saved['saved_commit'])
        self.executor.max_retry_attempts=2
        from github_workflow import ValidationPending
        calls=[]
        def waiting(*args): calls.append(args); raise ValidationPending('waiting')
        self.validator.validate=waiting
        for attempt in range(3):
            with self.assertRaises(ValidationPending): self.execute(operation)
            row=self.store.get('operation:'+operation)
            self.assertEqual(row['retry_attempts'],0)
            self.assertEqual(row['retry_generation'],attempt+1)
            self.assertEqual(row['status'],'reconciling')
            self.assertEqual(self.executor.execute(operation),row)
        self.assertEqual(len(calls),3)
        self.now=row['wait_deadline']
        with self.assertRaises(ValidationPending): self.execute(operation)
        row=self.store.get('operation:'+operation)
        self.assertEqual(row['status'],'needs_attention')
        self.assertEqual(row['error'],'wait_deadline_exceeded')
        self.assertEqual(row['retry_attempts'],0)
        self.assertNotIn('queue_state',row)

    def test_conditional_publisher_safe_to_resume_requires_fresh_authority(self):
        operation=self.publish_operation()
        original=self.publisher
        class Conditional:
            calls=0
            def publish(inner,*args):
                inner.calls+=1
                if inner.calls==1: raise RuntimeError('original ETag still current')
                return original.publish(*args)
            def reconcile(inner,*args): return {'safe_to_resume':True}
        conditional=Conditional(); self.executor.publisher=conditional
        with self.assertRaises(RuntimeError): self.execute(operation)
        result=self.execute(operation)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(conditional.calls,2)
        self.assertEqual(len(original.effects),1)
        self.assertNotIn('safe_to_resume',result['phases']['publish'])

    def test_conditional_publisher_safe_to_resume_never_replays_after_cancel(self):
        operation=self.publish_operation()
        class Conditional:
            calls=0
            def publish(inner,*args): inner.calls+=1; raise RuntimeError('unknown')
            def reconcile(inner,*args): return {'safe_to_resume':True,'cache_cleanup_requires_attention':True}
        conditional=Conditional(); self.executor.publisher=conditional
        with self.assertRaises(RuntimeError): self.execute(operation)
        self.service.cancel(self.claims,operation)
        with self.assertRaises(ReconciliationRequired): self.execute(operation)
        row=self.store.get('operation:'+operation)
        self.assertEqual(conditional.calls,1)
        self.assertNotIn('publish',row.get('phases',{}))
        self.assertEqual(row['reconciliation_reason'],'cache_cleanup_requires_attention')
        self.assertEqual(row['error'],'cache_cleanup_requires_attention')
        self.assertEqual(self.store.get('lease:site:'+self.site)['blocked_operation'],operation)

    def test_publish_gate_and_revoked_approval_block_effect(self):
        operation = self.publish_operation()
        self.executor.publication_enabled = False
        result = self.execute(operation)
        self.assertEqual(result['error'], 'publication_not_enabled')
        self.assertFalse(self.publisher.effects)

    def test_new_preview_invalidates_previously_accepted_publication(self):
        operation = self.publish_operation()
        site = self.store.get('site:' + self.site)
        self.store.put('site:' + self.site, {**site, 'current_preview': str(uuid4())}, site['_version'])
        result = self.execute(operation)
        self.assertEqual(result['error'], 'approval_stale')
        self.assertFalse(self.publisher.effects)


class CloudProviderTests(unittest.TestCase):
    def test_google_transport_rejects_arbitrary_origins_before_network(self):
        for origin in ('http://www.googleapis.com/drive/v3/files', 'https://attacker.invalid/drive/v3/files',
                       'https://www.googleapis.com@attacker.invalid/drive/v3/files'):
            with self.assertRaises(ProviderError):
                google_transport('GET', origin, {})

    def test_drive_checks_parent_before_downloading(self):
        requests = []
        def transport(method, url, headers, data, limit):
            requests.append(url)
            if url.endswith('/token'):
                return 200, b'{"access_token":"test-only-token"}'
            if url.endswith('/oauth2/v3/userinfo'):
                return 200, json.dumps({'sub': 'operator-subject', 'email': 'operator@example.invalid', 'email_verified': True}).encode()
            return 200, json.dumps({'id': 'allowed-file-id', 'parents': ['wrong-parent-id'],
                'trashed': False, 'mimeType':'application/zip','size':'1'}).encode()
        drive = GoogleDrive('operator-only', lambda ref: {'client_id':'x','client_secret':'x','refresh_token':'x'},
            transport=transport).for_site({'operator_subject': 'operator-subject', 'operator_email': 'operator@example.invalid'}, lambda: None)
        with self.assertRaisesRegex(ProviderError, 'parent'):
            drive.read_exact('expected-parent-id', 'allowed-file-id')
        self.assertFalse(any('alt=media' in url for url in requests))

    def drive_fixture(self, profile=None, guard=None):
        profile = profile or {'sub': 'operator-subject', 'email': 'operator@example.invalid', 'email_verified': True}
        requests, resolutions = [], []
        def resolve(reference):
            resolutions.append(reference)
            return {'client_id': 'test-client', 'client_secret': 'test-client-secret', 'refresh_token': 'test-refresh-value'}
        data = b'exact package'
        metadata = {'id': 'allowed-file-id', 'parents': ['expected-parent-id'], 'trashed': False,
            'mimeType': 'application/zip', 'size': str(len(data))}
        def transport(method, url, headers, body, limit):
            requests.append((method, url, limit))
            if url == 'https://oauth2.googleapis.com/token':
                return 200, b'{"access_token":"test-only-access-value"}'
            if url == 'https://www.googleapis.com/oauth2/v3/userinfo':
                return 200, json.dumps(profile).encode()
            if 'alt=media' in url:
                return 200, data
            return 200, json.dumps(metadata).encode()
        base = GoogleDrive('operator-only', resolve, transport=transport)
        return base, requests, resolutions, data

    def test_drive_wrong_subject_email_or_unverified_identity_prevents_file_io(self):
        for profile in [{'sub': 'different-subject', 'email': 'operator@example.invalid', 'email_verified': True},
                        {'sub': 'operator-subject', 'email': 'different@example.invalid', 'email_verified': True},
                        {'sub': 'operator-subject', 'email': 'operator@example.invalid', 'email_verified': False}]:
            with self.subTest(profile=profile):
                base, requests, _, _ = self.drive_fixture(profile)
                drive = base.for_site({'operator_subject': 'operator-subject', 'operator_email': 'operator@example.invalid'}, lambda: None)
                with self.assertRaisesRegex(ProviderError, 'identity_mismatch'):
                    drive.read_exact('expected-parent-id', 'allowed-file-id')
                self.assertEqual([url for _, url, _ in requests], ['https://oauth2.googleapis.com/token', 'https://www.googleapis.com/oauth2/v3/userinfo'])

    def test_drive_userinfo_redirect_error_or_oversized_body_never_reaches_file_io(self):
        for status, body in [(302, b'{}'), (403, b'{}'), (200, b' ' * (64 * 1024 + 1))]:
            with self.subTest(status=status, size=len(body)):
                base, requests, _, _ = self.drive_fixture()
                original = base.transport
                def transport(method, url, headers, data, limit):
                    if url == 'https://www.googleapis.com/oauth2/v3/userinfo':
                        requests.append((method, url, limit))
                        return status, body
                    return original(method, url, headers, data, limit)
                base.transport = transport
                drive = base.for_site({'operator_subject': 'operator-subject', 'operator_email': 'operator@example.invalid'}, lambda: None)
                with self.assertRaisesRegex(ProviderError, 'identity_verification_failed'):
                    drive.read_exact('expected-parent-id', 'allowed-file-id')
                self.assertEqual(len(requests), 2)

    def test_drive_validates_each_fresh_token_and_construction_has_no_effect(self):
        base, requests, resolutions, data = self.drive_fixture()
        drive = base.for_site({'operator_subject': 'operator-subject', 'operator_email': 'Operator@Example.Invalid'}, lambda: None)
        self.assertEqual((requests, resolutions), ([], []))
        self.assertEqual(drive.read_exact('expected-parent-id', 'allowed-file-id'), data)
        self.assertEqual(len(resolutions), 3)
        for offset in range(0, len(requests), 3):
            group = requests[offset:offset + 3]
            self.assertEqual(group[0][1], 'https://oauth2.googleapis.com/token')
            self.assertEqual(group[1][1], 'https://www.googleapis.com/oauth2/v3/userinfo')
            self.assertEqual(group[1][2], 64 * 1024)
            self.assertIn('/drive/v3/', group[2][1])

    def test_drive_missing_binding_or_revoked_role_guard_fails_before_secret_io(self):
        base, requests, resolutions, _ = self.drive_fixture()
        with self.assertRaisesRegex(ProviderError, 'identity_not_configured'):
            base.read_exact('expected-parent-id', 'allowed-file-id')
        with self.assertRaisesRegex(ProviderError, 'identity_not_configured'):
            base.for_run(lambda: None).read_exact('expected-parent-id', 'allowed-file-id')
        with self.assertRaisesRegex(ProviderError, 'identity_not_configured'):
            base.for_site({'operator_subject': 'operator-subject'}, lambda: None)
        def revoked():
            raise Rejected('access_revoked')
        bound = base.for_site({'operator_subject': 'operator-subject', 'operator_email': 'operator@example.invalid'}, revoked)
        with self.assertRaises(Rejected):
            bound.read_exact('expected-parent-id', 'allowed-file-id')
        self.assertEqual((requests, resolutions), ([], []))

    def test_drive_readonly_reconciliation_retains_frozen_operator_after_role_revocation(self):
        base, requests, _, data = self.drive_fixture()
        site = {'operator_subject': 'operator-subject', 'operator_email': 'operator@example.invalid'}
        def revoked():
            raise Rejected('access_revoked')
        original = base.for_site(site, revoked)
        site['operator_subject'] = 'different-subject'
        site['operator_email'] = 'different@example.invalid'
        fenced_reads = []
        reconciliation = original.for_run(lambda: fenced_reads.append(True))
        self.assertEqual(reconciliation.read_exact('expected-parent-id', 'allowed-file-id'), data)
        self.assertTrue(fenced_reads)
        self.assertTrue(all(method == 'GET' for method, url, _ in requests if '/drive/v3/' in url))
        self.assertEqual(reconciliation.expected_subject, 'operator-subject')
        self.assertEqual(reconciliation.expected_email, 'operator@example.invalid')

    def test_artifact_storage_is_immutable_and_digest_scoped(self):
        class Client:
            def __init__(self): self.items = {}; self.puts = []
            def put_object(self, **kwargs):
                self.puts.append(kwargs)
                if kwargs['Key'] in self.items:
                    error = RuntimeError('existing')
                    error.response = {'Error': {'Code':'PreconditionFailed'}}
                    raise error
                self.items[kwargs['Key']] = kwargs['Body']
            def get_object(self, **kwargs):
                data = self.items[kwargs['Key']]
                return {'ContentLength':len(data),'Body':BytesIO(data)}
        client = Client(); adapter = S3Artifacts('fixed-bucket', client, lambda: None)
        data = b'exact artifact'; key = 'artifacts/test-site/' + sha256(data) + '/site.zip'
        adapter.put_exact(key, data); adapter.put_exact(key, data)
        self.assertEqual(len(client.items), 1)
        self.assertTrue(all(p['IfNoneMatch'] == '*' and p['ServerSideEncryption'] == 'AES256' for p in client.puts))
        with self.assertRaises(ProviderError):
            adapter.put_exact(key, b'other bytes')
        with self.assertRaises(ProviderError):
            adapter.get_exact('../site.zip', sha256(data))


if __name__ == '__main__':
    unittest.main()
