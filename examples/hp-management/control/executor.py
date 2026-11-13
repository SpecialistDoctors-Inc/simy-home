"""Deterministic command execution over the authoritative Store.

Provider adapters must reconcile ambiguous writes by the supplied stable identity.
GitHub transports must call guard before *each* request, not merely each method.
No client input chooses a repository, parent folder, recipient or publisher role.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import io
import json
import stat
import zipfile
import time
from uuid import uuid4, uuid5, NAMESPACE_URL
from licensing import site_license_allowed
from stripe_billing import StripeLicenses
from bundles import build_snapshot, validate_snapshot, validate_changes, reconcile, sha256, BundleError
from service import Service, Rejected, effective_roles, fingerprint, main_commit
from change_summary import summarize_changes
from store import Check, Write, Conflict


class Busy(RuntimeError):
    pass


class IntegrationUnavailable(RuntimeError):
    pass


class ReconciliationRequired(RuntimeError):
    pass


class SafeToResume(ReconciliationRequired):
    pass


class Executor:
    def __init__(self, store, github_factory, drive, artifacts, validator=None,
                 publisher=None, clock=time.time, publication_enabled=False, lease_seconds=300, preview_publisher=None, max_retry_attempts=8, browser_validator=None,
                 license_resolver=None, wordpress=None, wordpress_test_origin=None):
        self.store, self.github_factory, self.drive, self.artifacts = store, github_factory, drive, artifacts
        self.validator, self.publisher, self.clock = validator, publisher, clock
        if type(max_retry_attempts) is not int or not 1 <= max_retry_attempts <= 20:
            raise ValueError("invalid_retry_budget")
        self.max_retry_attempts = max_retry_attempts
        self.preview_publisher = preview_publisher
        self.browser_validator = browser_validator
        self.license_resolver = license_resolver
        self.wordpress = wordpress
        self.wordpress_test_origin = wordpress_test_origin if publication_enabled and wordpress else None
        self.publication_enabled, self.lease_seconds = publication_enabled, lease_seconds

    def execute(self, operation_id):
        key = 'operation:' + operation_id
        op = self.store.get(key)
        if not op:
            raise Rejected('operation_missing')
        if op['status'] in ('completed', 'failed', 'cancelled', 'published_after_cancel_or_revocation', 'needs_attention'):
            return op
        if op.get('retry_at', 0) > self.clock():
            return op
        owner = str(uuid4())
        lock_key = 'lease:site:' + op['site_id']
        lock = self.store.get(lock_key)
        if lock and (lock.get('until', 0) > self.clock() or lock.get('blocked_operation') not in (None, operation_id)):
            if op['status'] in ('queued', 'retry_wait') and not op.get('pending_effect'):
                self.store.transact([Write(key, {**op, 'status': 'retry_wait', 'stage': 'waiting_site',
                    'queue_state': 'pending', 'retry_at': self.clock() + 30,
                    'retry_generation': op.get('retry_generation', 0) + 1, 'error': 'site_busy'}, op['_version']),
                    Check(lock_key, lock['_version'])])
                return self.store.get(key)
            raise Busy('site_busy')
        epoch = (lock or {}).get('epoch', 0) + 1
        self.store.transact([Write(lock_key, {'owner': owner, 'operation_id': operation_id,
            'epoch': epoch, 'until': self.clock() + self.lease_seconds,
            'blocked_operation': operation_id if op.get('pending_effect') or op.get('reconciliation_required') else None}, (lock or {}).get('_version')),
            Write(key, {**op, 'status': 'running', 'lease_owner': owner, 'lease_epoch': epoch}, op['_version'])])
        run = _Run(self, key, lock_key, owner, epoch)
        try:
            provider_site = op.get('execution_site') or self.store.get('site:' + op['site_id'])
            run.drive = (self.drive.for_site(provider_site, run.guard) if provider_site and provider_site.get('provider') != 'wordpress' and hasattr(self.drive, 'for_site')
                         else self.drive.for_run(run.guard) if hasattr(self.drive, 'for_run') else self.drive)
            run.artifacts = self.artifacts.for_run(run.guard) if hasattr(self.artifacts, "for_run") else self.artifacts
            try:
                run.guard()
            except Rejected:
                if run.op.get('pending_effect'):
                    run.reconcile_pending()
                raise
            if not run.op.get('execution_site'):
                self.store.put(key, {**run.op, 'execution_site': run.site}, run.op['_version'])
                run.guard()
            if run.site.get('provider') == 'wordpress':
                result, writes = getattr(self.wordpress, op['kind'])(run)
                run.finish('completed', result, writes)
                return self.store.get(key)
            github = self.github_factory(run.site, run.guard)
            if op['kind'] == 'open_workspace':
                result, writes = self._open(run, github)
            elif op['kind'] == 'save_draft':
                result, writes = self._save(run, github)
            elif op['kind'] == 'submit_preview':
                result, writes = self._preview(run, github)
            elif op['kind'] == 'publish':
                result, writes = self._publish(run, github)
            else:
                raise Rejected('unsupported_operation')
            run.finish('completed', result, writes)
        except (Rejected, BundleError) as error:
            if self.store.get(key).get('pending_effect'):
                try:
                    run.reconcile_pending()
                except Exception as reconciliation:
                    run.retry(wait=bool(getattr(reconciliation, 'wait_required', False)),
                        retry_after=getattr(reconciliation, 'retry_after', 30),
                        deadline=getattr(reconciliation, 'deadline', None),
                        wait_timeout=getattr(reconciliation, 'wait_timeout', 900))
                    raise ReconciliationRequired('revoked_external_effect_unresolved') from None
            current = self.store.get(key)
            if current['kind'] == 'publish' and current.get('phases', {}).get('main_commit'):
                try:
                    run.record_main_pointer()
                except Exception:
                    run.retry(force_blocked=True)
                    raise ReconciliationRequired('main_authority_reconciliation_required') from None
            if current['kind'] == 'publish' and current.get('phases', {}).get('publish', {}).get('verified') is True:
                try:
                    run.record_factual_publication(str(error))
                except Exception:
                    run.retry(force_blocked=True)
                    raise ReconciliationRequired('publication_authority_reconciliation_required') from None
            else:
                run.finish('cancelled' if str(error) == 'operation_cancelled' else 'failed', None, error=str(error))
        except Exception as error:
            # Unknown provider outcomes remain resumable under the same intent.
            # Never expose exception strings (which may include provider tokens).
            run.retry(wait=bool(getattr(error, 'wait_required', False)),
                retry_after=getattr(error, 'retry_after', 30), deadline=getattr(error, 'deadline', None),
                wait_timeout=getattr(error, 'wait_timeout', 900))
            raise
        return self.store.get(key)

    @staticmethod
    def _timestamp(op):
        return dt.datetime.fromtimestamp(op['created_at'], dt.timezone.utc).isoformat(timespec='seconds')

    def _snapshot(self, run, github, commit):
        run.guard()
        source = github.read_site_at(commit)
        return validate_snapshot(build_snapshot(run.op['site_id'], run.workspace_id, commit, source.files))

    def _open(self, run, github):
        workspace = run.workspace()
        base = run.intent('open_base', lambda: {'commit': github.head(run.site.get('dev_branch', 'dev'))})['commit']
        snapshot = self._snapshot(run, github, base)
        run.effect('branch', lambda: {'branch': github.ensure_workspace_branch(run.workspace_id, base)},
            {'kind': 'branch', 'branch': 'codex/hp/' + run.workspace_id, 'commit': base})
        file_id = run.intent('snapshot_file', lambda: {'id': run.drive.reserve_id()})['id']
        data = build_snapshot(run.op['site_id'], run.workspace_id, base, snapshot.files)
        uploaded = run.effect('snapshot_upload', lambda: run.drive.create_exact(
            run.site['drive_workspace_folder_id'], file_id, data, run.op['operation_id']),
            {'kind': 'drive', 'parent': run.site['drive_workspace_folder_id'], 'file_id': file_id, 'sha256': sha256(data)})
        result = {'schema_version': 1, 'kind': 'workspace', 'site_id': run.op['site_id'],
            'workspace_id': run.workspace_id, 'base_commit': base, 'snapshot_file_id': file_id,
            'snapshot_sha256': sha256(data), 'download_url': uploaded['download_url'],
            'upload_folder_id': run.site['drive_changes_folder_id']}
        row = {**workspace, 'status': 'ready', 'base_on_dev': base, 'head_commit': base,
            'branch': 'codex/hp/' + run.workspace_id, 'snapshot_file_id': file_id, 'snapshot_sha256': sha256(data)}
        if run.site.get('direct_transfer_enabled'):
            key = 'artifacts/' + run.op['site_id'] + '/' + sha256(data) + '/site.zip'
            run.effect('snapshot_artifact', lambda: run.artifacts.put_exact(key, data),
                {'kind': 'artifact', 'key': key, 'sha256': sha256(data)})
            row['snapshot_artifact_key'] = key
        return result, [Write('workspace:' + run.workspace_id, row, workspace['_version'])]

    def _save(self, run, github):
        workspace = run.workspace()
        body = run.op['input']
        # Resuming after a commit but before final Store transaction uses the
        # persisted expected head, never a newly observed branch head.
        if workspace.get('head_commit') != body['base_commit']:
            raise Rejected('workspace_changed')
        acknowledged = run.op.get('phases', {}).get('draft_commit')
        no_changes = run.op.get('intents', {}).get('save', {}).get('no_changes')
        if acknowledged or no_changes:
            saved = acknowledged['commit'] if acknowledged else body['base_commit']
            return self._saved(run, workspace, saved)
        snapshot = self._snapshot(run, github, body['base_commit'])
        run.guard()
        if body['bundle_file_id'].startswith('hp-upload-'):
            data = run.transferred_changes()
        else:
            data = run.drive.read_exact(run.site['drive_changes_folder_id'], body['bundle_file_id'])
        if sha256(data) != body['bundle_sha256']:
            raise Rejected('bundle_hash_mismatch')
        changes = validate_changes(data, snapshot, run.op['operation_id'])
        run.intent('save', lambda: {'bundle_sha256': sha256(data), 'base_commit': body['base_commit'],
            'no_changes': changes.candidate_files == snapshot.files})
        supplied = changes.manifest.get('change_summary') or ''
        summary = ' '.join(supplied.split())[:200]
        if not summary:
            summary = str(len(changes.manifest['changes'])) + 'ファイルを更新'
        title = summary + ' [' + run.op['site_id'] + ']'
        saved = {'commit': body['base_commit']} if changes.candidate_files == snapshot.files else run.effect('draft_commit', lambda: {'commit': github.commit_site(workspace['branch'],
            body['base_commit'], changes.candidate_files, title, run.op['operation_id'], self._timestamp(run.op)).commit},
            run.commit_intent(workspace['branch'], body['base_commit'], changes.candidate_files, title))
        return self._saved(run, workspace, saved['commit'])

    @staticmethod
    def _saved(run, workspace, saved_commit):
        body = run.op['input']
        result = {'schema_version': 1, 'kind': 'saved', 'site_id': run.op['site_id'],
            'workspace_id': run.workspace_id, 'operation_id': run.op['operation_id'],
            'base_commit': body['base_commit'], 'saved_commit': saved_commit, 'bundle_sha256': body['bundle_sha256']}
        return result, [Write('workspace:' + run.workspace_id, {**workspace, 'head_commit': saved_commit,
            'last_saved_operation': run.op['operation_id']}, workspace['_version'])]

    def _preview(self, run, github):
        workspace = run.workspace()
        if workspace.get('head_commit') != run.op['input']['saved_commit']:
            raise Rejected('workspace_changed')
        base = self._snapshot(run, github, workspace['base_on_dev']).files
        user = self._snapshot(run, github, workspace['head_commit']).files
        remote = run.intent('preview_base', lambda: {'commit': github.head(run.site.get('dev_branch', 'dev'))})['commit']
        current = self._snapshot(run, github, remote).files
        merged = reconcile(base, user, current)
        if merged.conflicts:
            return {'kind': 'conflicts', 'workspace_id': run.workspace_id, 'base_commit': remote,
                'paths': list(merged.conflicts)}, []
        if merged.files == current:
            result = {'kind': 'no_changes', 'workspace_id': run.workspace_id, 'source_commit': remote}
            existing_id = run.site.get('current_preview')
            existing = self.store.get('preview:' + existing_id) if existing_id else None
            if existing and existing.get('status') == 'verified' and existing.get('site_id') == run.op['site_id'] and existing.get('source_commit') == remote and existing.get('url') == run.site['dev_url']:
                result.update(preview_id=existing_id, preview_url=existing['url'], artifact_sha256=existing['artifact_sha256'])
            return result, []
        if self.validator is None:
            raise IntegrationUnavailable('github_validation_not_configured')
        if self.preview_publisher is None or not hasattr(self.preview_publisher, 'preflight'):
            raise IntegrationUnavailable('preview_publisher_not_configured')
        if self.browser_validator is None or not hasattr(self.browser_validator, 'preflight'):
            raise IntegrationUnavailable('browser_validator_not_configured')
        run.guard()
        self.preview_publisher.preflight(run.site, run.guard)
        self.browser_validator.preflight(run.site, run.guard)
        preview_id = str(uuid5(NAMESPACE_URL, 'hp-preview:' + run.op['operation_id']))
        branch_id = str(uuid5(NAMESPACE_URL, 'hp-candidate:' + run.op['operation_id']))
        intent = run.intent('candidate', lambda: {'preview_id': preview_id, 'branch_id': branch_id,
            'base_commit': remote, 'tree_sha256': fingerprint({p: sha256(v) for p, v in merged.files.items()})})
        branch = 'codex/hp/' + intent['branch_id']
        # ensure_workspace_branch accepts only the initial exact base. Once the
        # candidate commit receipt is stored, do not recreate/reclaim the ref.
        if not run.op.get('phases', {}).get('candidate_commit'):
            existing_branch = run.op.get('phases', {}).get('candidate_branch')
            if not existing_branch:
                run.effect('candidate_branch', lambda: {'branch': github.ensure_workspace_branch(intent['branch_id'], remote)},
                    {'kind': 'branch', 'branch': branch, 'commit': remote})
        title = 'HP preview ' + run.op['site_id'] + ' [' + run.op['operation_id'] + ']'
        candidate = run.effect('candidate_commit', lambda: {'commit': github.commit_site(branch, remote,
            merged.files, title, run.op['operation_id'], self._timestamp(run.op)).commit},
            run.commit_intent(branch, remote, merged.files, title))['commit']
        if run.site.get('github_repository_id'):
            wait_key = 'gitwait:' + str(run.site['github_repository_id']) + ':' + candidate
            old_wait = self.store.get(wait_key)
            if not old_wait or old_wait.get('operation_id') != run.op['operation_id']:
                self.store.put(wait_key, {'site_id': run.op['site_id'], 'operation_id': run.op['operation_id'],
                    'expires_at': int(self.clock()) + 86400}, (old_wait or {}).get('_version'))
        proof = run.effect('github_validation', lambda: self.validator.validate(run.site, candidate,
            run.op['operation_id'], intent['tree_sha256'], run.guard),
            {'kind': 'validation', 'commit': candidate, 'tree_sha256': intent['tree_sha256']})
        if proof.get('source_commit') != candidate or proof.get('tree_sha256') != intent['tree_sha256'] or proof.get('conclusion') != 'success':
            raise Rejected('validation_proof_mismatch')
        run.guard()
        artifact_key = 'artifacts/' + run.op['site_id'] + '/' + proof['artifact_sha256'] + '/site.zip'
        uploaded = run.op.get('phases', {}).get('artifact_upload')
        if uploaded:
            artifact = run.artifacts.get_exact(uploaded['key'], proof['artifact_sha256'])
        else:
            artifact = self.validator.artifact(proof, run.guard)
        if sha256(artifact) != proof.get('artifact_sha256'):
            raise Rejected('validation_artifact_mismatch')
        verify_artifact(artifact, merged.files, candidate, proof.get('package_operation_id', run.op['operation_id']))
        stored = run.effect('artifact_upload', lambda: run.artifacts.put_exact(artifact_key, artifact),
            {'kind': 'artifact', 'key': artifact_key, 'sha256': sha256(artifact)})
        if not isinstance(proof.get('package_operation_id'), str):
            raise Rejected('validation_package_identity_required')
        changes = None
        try:
            summary_base = run.intent('summary_base', lambda: {'commit': main_commit(run.site)})['commit']
            previous_files = self._snapshot(run, github, summary_base).files
            changes = {'base_commit': summary_base, **summarize_changes(previous_files, merged.files)}
        except BundleError:
            pass  # A legacy production tree may not support a source summary.
        except Rejected as error:
            if str(error) != 'publication_source_not_configured':
                raise
        version_key = 'content-version:' + run.op['site_id'] + ':' + proof['artifact_sha256']
        known_version = self.store.get(version_key)
        last_version = run.site.get('last_content_version', 0)
        if type(last_version) is not int or last_version < 0:
            raise Rejected('content_version_corrupt')
        version = known_version.get('version') if known_version else last_version + 1
        if type(version) is not int or version < 1:
            raise Rejected('content_version_corrupt')
        browser_preview = {'preview_id': preview_id, 'site_id': run.op['site_id'],
            'package_operation_id': proof['package_operation_id'],
            'source_commit': candidate, 'artifact_sha256': proof['artifact_sha256'],
            'artifact_key': stored['key'], 'validation': proof, 'url': run.site['dev_url']}
        browser = run.effect('browser_validation', lambda: self.browser_validator.validate(
            run.site, browser_preview, stored['key'], run.op['operation_id'], run.guard),
            {'kind': 'browser_validation', 'preview': browser_preview, 'artifact_key': stored['key']})
        if browser.get('verified') is not True or browser.get('source_commit') != candidate or browser.get('artifact_sha256') != proof['artifact_sha256'] or not isinstance(browser.get('report_key'), str) or not isinstance(browser.get('screenshot_keys'), list) or not browser['screenshot_keys']:
            raise Rejected('browser_validation_proof_mismatch')
        # Same parent/tree/message/author/time produces the identical Git object.
        advanced = run.effect('dev_commit', lambda: {'commit': github.commit_site(run.site.get('dev_branch', 'dev'),
            remote, merged.files, title, run.op['operation_id'], self._timestamp(run.op)).commit},
            run.commit_intent(run.site.get('dev_branch', 'dev'), remote, merged.files, title))
        if advanced['commit'] != candidate:
            raise Rejected('validated_commit_mismatch')
        preview_intent = {'preview_id': preview_id, 'site_id': run.op['site_id'],
            'source_commit': candidate, 'artifact_sha256': proof['artifact_sha256'],
            'artifact_key': stored['key'], 'validation': proof, 'url': run.site['dev_url']}
        run.invalidate_preview()
        deployment = run.effect('preview_deploy', lambda: self.preview_publisher.publish(
            run.site, preview_intent, artifact, run.op['operation_id'], run.epoch, run.guard),
            {'kind': 'preview_deploy', 'preview': preview_intent})
        if deployment.get('verified') is not True or deployment.get('artifact_sha256') != proof['artifact_sha256']:
            raise Rejected('preview_deployment_readback_mismatch')
        live = run.effect('preview_readback', lambda: self.validator.readback(run.site, proof, run.guard), {'kind': 'preview_readback', 'proof': proof})
        if live.get('artifact_sha256') != proof['artifact_sha256'] or live.get('source_commit') != candidate or live.get('verified') is not True:
            raise Rejected('preview_readback_mismatch')
        preview = {'preview_id': preview_id, 'site_id': run.op['site_id'], 'status': 'verified',
            'updated_at': int(self.clock()),
            'source_commit': candidate, 'artifact_sha256': proof['artifact_sha256'],
            'artifact_key': stored['key'], 'validation': proof, 'browser_validation': browser, 'url': run.site['dev_url'],
            'summary': '保存した変更を反映', 'publication_changes': changes, 'operation_id': run.op['operation_id']}
        old = self.store.get('preview:' + preview_id)
        writes = [Write('preview:' + preview_id, preview, (old or {}).get('_version')),
            Write('site:' + run.op['site_id'], {**run.site, 'current_preview': preview_id, 'last_verified_preview': preview_id,
                'last_content_version': max(last_version, version)}, run.site['_version']),
            # A later edit starts from the user's accepted contribution. Keep the
            # draft head/local receipt intact: unrelated dev edits remain remote
            # changes in the next three-way reconciliation.
            Write('workspace:' + run.workspace_id, {**workspace,
                'base_on_dev': run.op['input']['saved_commit']}, workspace['_version'])]
        if not known_version:
            writes.append(Write(version_key, {'version': version}, None))
        return {'kind': 'preview', 'preview_id': preview_id, 'source_commit': candidate,
            'artifact_sha256': proof['artifact_sha256'], 'preview_url': run.site['dev_url']}, writes

    def _publish(self, run, github):
        if not self.publication_enabled or self.publisher is None:
            raise Rejected('publication_not_enabled')
        approval = self.store.get('approval:' + run.op['input']['approval_id'])
        if not approval or approval.get('state') != 'accepted' or approval.get('operation_id') != run.op['operation_id']:
            raise Rejected('approval_not_accepted')
        preview = self.store.get('preview:' + approval['preview_id'])
        if approval.get('site_id') != run.op['site_id'] or not preview or preview.get('site_id') != run.op['site_id'] or preview.get('status') != 'verified' or any(approval[k] != preview[k] for k in ('source_commit','artifact_sha256')):
            raise Rejected('approval_artifact_mismatch')
        if approval['subject'] != run.op['subject'] or approval['member_version'] != run.member['_version'] or approval['site_config_version'] != run.site['config_version'] or run.site.get('current_preview') != preview['preview_id'] or run.site.get('current_publication') != approval['expected_publication']:
            raise Rejected('approval_stale')
        run.guard()
        artifact = run.artifacts.get_exact(preview['artifact_key'], preview['artifact_sha256'])
        if sha256(artifact) != preview['artifact_sha256']:
            raise Rejected('publication_artifact_mismatch')
        expected_main = approval.get('expected_main_commit')
        if not isinstance(expected_main, str) or len(expected_main) != 40 or any(c not in '0123456789abcdef' for c in expected_main):
            raise Rejected('approved_main_commit_required')
        own_main = run.op.get('phases', {}).get('main_commit', {}).get('commit')
        if main_pointer(run.site) != expected_main and (own_main is None or main_pointer(run.site) != own_main):
            raise Rejected('approved_main_commit_stale')
        source = artifact_source(artifact)
        verify_artifact(artifact, source, preview['source_commit'],
            preview.get('validation', {}).get('package_operation_id', preview['operation_id']))
        run.intent('publication', lambda: {'approval_id': approval['approval_id'],
            'expected_publication': approval['expected_publication'], 'expected_main_commit': expected_main, 'preview': preview,
            'site_config_version': run.site['config_version']})
        title = 'HP production ' + run.op['site_id'] + ' [' + run.op['operation_id'] + ']'
        main = run.effect('main_commit', lambda: {'commit': github.commit_site('main', expected_main,
            source, title, run.op['operation_id'], self._timestamp(run.op)).commit},
            run.commit_intent('main', expected_main, source, title))
        run.record_main_pointer()
        run.guard()
        receipt = run.effect('publish', lambda: self.publisher.publish(run.site, preview, artifact,
            run.op['operation_id'], run.epoch, run.guard), {'kind': 'publish', 'preview': preview})
        if receipt.get('artifact_sha256') != preview['artifact_sha256'] or receipt.get('verified') is not True:
            raise Rejected('publication_readback_mismatch')
        publication = {'operation_id': run.op['operation_id'], 'preview_id': preview['preview_id'],
            'updated_at': int(self.clock()),
            'artifact_sha256': preview['artifact_sha256'], 'source_commit': preview['source_commit'],
            'main_commit': main['commit'], 'receipt': receipt}
        return {'kind': 'published', **publication}, [
            Check('approval:' + approval['approval_id'], approval['_version']),
            Check('preview:' + preview['preview_id'], preview['_version']),
            Write('site:' + run.op['site_id'], {**run.site, 'current_publication': publication}, run.site['_version'])]


class _Run:
    def __init__(self, executor, key, lock_key, owner, epoch):
        self.executor, self.store, self.key, self.lock_key = executor, executor.store, key, lock_key
        self.owner, self.epoch = owner, epoch
        self.op = self.store.get(key)
        self.workspace_id = self.op.get('workspace_id', self.op.get('input', {}).get('workspace_id'))

    def fence_guard(self):
        self.op, self.lock = self.store.get(self.key), self.store.get(self.lock_key)
        if not self.lock or self.lock.get('owner') != self.owner or self.lock['epoch'] != self.epoch or self.lock['until'] <= self.executor.clock() or self.op.get('lease_owner') != self.owner:
            raise Busy('lease_lost')

    def guard(self):
        self.fence_guard()
        if self.op.get('cancel_requested'):
            raise Rejected('operation_cancelled')
        self.member = self.store.get('principal:' + self.op['subject'])
        self.site = self.store.get('site:' + self.op['site_id'])
        role = 'publish' if self.op['kind'] == 'publish' else 'edit'
        if not self.member or self.member.get('disabled') or self.member['_version'] != self.op['member_version']:
            raise Rejected('access_revoked')
        if not self.site or self.site.get('disabled') or self.site.get('config_version') != self.op['site_config_version']:
            raise Rejected('site_configuration_changed')
        if role not in effective_roles(self.member, {**self.site, 'site_id': self.op['site_id']},
                                       self.op['subject'], self.executor.wordpress_test_origin):
            raise Rejected('access_revoked')
        if not site_license_allowed(self.site, self.op['subject'], self.executor.license_resolver,
                                    StripeLicenses(self.executor.store)):
            raise Rejected('hp_license_required')

    def transferred_changes(self):
        from transfers import upload_binding

        service = Service(self.store, publication_enabled=self.executor.publication_enabled,
            license_resolver=self.executor.license_resolver, wordpress_test_origin=self.executor.wordpress_test_origin)
        body = self.op['input']
        transfer = upload_binding(service, {'sub': self.op['subject'], 'scope': 'hp:read hp:write'}, body)
        data = self.artifacts.get_exact(transfer['key'], body['bundle_sha256'])
        if len(data) != int(transfer['size']):
            raise Rejected('bundle_size_mismatch')
        return data

    def workspace(self):
        self.guard()
        value = self.store.get('workspace:' + self.workspace_id)
        if not value or value['subject'] != self.op['subject'] or value['site_id'] != self.op['site_id'] or value.get('closed'):
            raise Rejected('workspace_access_denied')
        return value

    def intent(self, name, create):
        self.guard()
        if name in self.op.get('intents', {}):
            return self.op['intents'][name]
        value = create()
        self.guard()
        self.store.put(self.key, {**self.op, 'intents': {**self.op.get('intents', {}), name: value}}, self.op['_version'])
        self.guard()
        return value

    def commit_intent(self, branch, parent, files, title):
        return {'kind': 'commit', 'branch': branch, 'parent': parent,
            'file_hashes': {p:sha256(v) for p,v in files.items()}, 'title': title,
            'operation_id': self.op['operation_id'], 'timestamp': self.executor._timestamp(self.op)}

    def reconcile_pending(self):
        """Observe prior effects after cancellation/revocation; never write providers."""
        self.fence_guard()
        pending = self.op.get('pending_effect')
        if not pending:
            return
        descriptor = pending['reconciliation']
        site = self.op['execution_site']
        github = (self.executor.github_factory(site, self.fence_guard) if site.get('provider') != 'wordpress' else None)
        drive = self.drive.for_run(self.fence_guard) if hasattr(self.drive, 'for_run') else self.drive
        artifacts = self.executor.artifacts.for_run(self.fence_guard) if hasattr(self.executor.artifacts, 'for_run') else self.executor.artifacts
        kind = descriptor['kind']
        result = None
        if kind == 'branch':
            if github.head(descriptor['branch']) == descriptor['commit']:
                result = {'branch': descriptor['branch']}
        elif kind == 'commit' and hasattr(github, 'reconcile_site_commit'):
            result = github.reconcile_site_commit(descriptor['branch'], descriptor['parent'], descriptor['file_hashes'],
                descriptor['title'], descriptor['operation_id'], descriptor['timestamp'])
        elif kind == 'drive':
            data = drive.read_exact(descriptor['parent'], descriptor['file_id'])
            if sha256(data) == descriptor['sha256']:
                result = {'file_id': descriptor['file_id'], 'sha256': descriptor['sha256'],
                    'download_url': 'https://drive.google.com/file/d/' + descriptor['file_id'] + '/view'}
        elif kind == 'artifact':
            data = artifacts.get_exact(descriptor['key'], descriptor['sha256'])
            if sha256(data) == descriptor['sha256']:
                result = {'key': descriptor['key'], 'sha256': descriptor['sha256']}
        elif kind == 'validation' and hasattr(self.executor.validator, 'reconcile'):
            try:
                result = self.executor.validator.reconcile(site, descriptor['commit'], self.op['operation_id'], descriptor['tree_sha256'], self.fence_guard)
            except Rejected as error:
                if getattr(error, 'effect_observed', False):
                    self.record_receipt(pending['name'], {'observed_failure': str(error)})
                raise
        elif kind == 'browser_validation' and hasattr(self.executor.browser_validator, 'reconcile'):
            try:
                result = self.executor.browser_validator.reconcile(site, descriptor['preview'], descriptor['artifact_key'], self.op['operation_id'], self.fence_guard)
            except Rejected as error:
                if getattr(error, 'effect_observed', False):
                    self.record_receipt(pending['name'], {'observed_failure': str(error)})
                raise
        elif kind == 'preview_deploy' and hasattr(self.executor.preview_publisher, 'reconcile'):
            result = self.executor.preview_publisher.reconcile(site, descriptor['preview'], self.op['operation_id'], pending['lease_epoch'], self.fence_guard)
        elif kind == 'publish' and hasattr(self.executor.publisher, 'reconcile'):
            result = self.executor.publisher.reconcile(site, descriptor['preview'], self.op['operation_id'], pending['lease_epoch'], self.fence_guard)
        elif kind == 'wordpress_publish' and self.executor.wordpress:
            result = self.executor.wordpress.reconcile_publish(site, self.op['subject'], descriptor['preview'])
        elif kind == 'preview_readback' and hasattr(self.executor.validator, 'reconcile_readback'):
            result = self.executor.validator.reconcile_readback(site, descriptor['proof'], self.fence_guard)
        if isinstance(result, dict) and result.get('safe_to_resume') is True:
            if kind == 'browser_validation' and result.get('launch_prewrite_proven') is True:
                try:
                    self.guard()
                except Rejected:
                    # The explicit renderer launch marker proves no child task
                    # was admitted. Account for that fact when authority ended;
                    # never turn it into successful validation or a new launch.
                    self.record_receipt(pending['name'], {'not_started': True,
                        'launch_prewrite_proven': True, 'manifest_state': result.get('manifest_state'),
                        'job_sha256': result.get('job_sha256')})
                    return
            if result.get('cache_cleanup_requires_attention') is True:
                self.fence_guard()
                self.store.put(self.key, {**self.op, 'reconciliation_reason': 'cache_cleanup_requires_attention'}, self.op['_version'])
                self.fence_guard()
            raise SafeToResume('conditional_effect_safe_to_resume')
        if result is None or (kind in ('publish', 'preview_deploy', 'wordpress_publish') and (result.get('verified') is not True or result.get('artifact_sha256') != descriptor['preview']['artifact_sha256'])):
            raise ReconciliationRequired('external_effect_unresolved')
        self.record_receipt(pending['name'], result)

    def invalidate_preview(self):
        """Withdraw old approval authority before the dev URL can change."""
        self.guard()
        if self.op.get('intents', {}).get('preview_invalidation'):
            if self.site.get('current_preview') is not None:
                raise Rejected('preview_authority_changed')
            return
        self.store.transact([
            Write('site:' + self.op['site_id'], {**self.site, 'current_preview': None,
                'last_verified_preview': self.site.get('current_preview') or self.site.get('last_verified_preview')}, self.site['_version']),
            Write(self.key, {**self.op, 'intents': {**self.op.get('intents', {}),
                'preview_invalidation': {'previous': self.site.get('current_preview')}}}, self.op['_version']),
            Check(self.lock_key, self.lock['_version']), Check('principal:' + self.op['subject'], self.member['_version'])])
        self.guard()

    def record_receipt(self, name, result):
        # Persist an observed result under the original fence even when authority
        # was revoked while the bounded provider request was in flight.
        self.fence_guard()
        row = {**self.op, 'phases': {**self.op.get('phases', {}), name: result}}
        row.pop('pending_effect', None)
        if isinstance(result, dict) and result.get('verified') is True:
            row.pop('reconciliation_reason', None)
        self.store.transact([Write(self.key, row, self.op['_version']),
            Write(self.lock_key, {**self.lock, 'blocked_operation': None}, self.lock['_version'])])
        self.fence_guard()

    def effect(self, name, perform, reconciliation):
        self.guard()
        if name in self.op.get('phases', {}):
            return self.op['phases'][name]
        if self.op.get('pending_effect'):
            try:
                self.reconcile_pending()
            except SafeToResume:
                # This is a conditional replay admission, never a success receipt.
                self.guard()
            except (Busy, Rejected):
                raise
            except Exception:
                # These adapters have provider-enforced stable identities. A
                # publisher/readback callback must explicitly reconcile instead.
                if reconciliation['kind'] not in ('branch','commit','drive','artifact','validation'):
                    raise
            self.guard()
            if name in self.op.get('phases', {}):
                return self.op['phases'][name]
        self.store.transact([Write(self.key, {**self.op, 'effects': True, 'stage': name,
            'pending_effect': {'name': name, 'reconciliation': reconciliation, 'admitted_at': self.executor.clock(),
                'lease_epoch': self.epoch}}, self.op['_version']),
            Write(self.lock_key, {**self.lock, 'blocked_operation': self.op['operation_id']}, self.lock['_version']),
            Check('principal:' + self.op['subject'], self.member['_version']),
            Check('site:' + self.op['site_id'], self.site['_version'])])
        try:
            self.guard()
        except Rejected:
            # The callback has not started, so there is no ambiguous effect.
            self.record_receipt(name, {'not_started': True})
            raise
        try:
            result = perform()
        except Rejected as error:
            if getattr(error, 'effect_observed', False):
                self.record_receipt(name, {'observed_failure': str(error)})
            raise
        if reconciliation['kind'] in ('publish', 'preview_deploy', 'wordpress_publish') and (not isinstance(result, dict) or result.get('verified') is not True or result.get('artifact_sha256') != reconciliation['preview']['artifact_sha256']):
            raise ReconciliationRequired('publisher_result_unverified')
        self.record_receipt(name, result)
        self.guard()
        return result

    def finish(self, status, result, writes=(), error=None):
        # Completion is a single authority transaction, including workspace/site.
        self.op, self.lock = self.store.get(self.key), self.store.get(self.lock_key)
        if self.lock.get('owner') != self.owner or self.lock['epoch'] != self.epoch or self.lock['until'] <= self.executor.clock():
            raise Busy('lease_lost')
        if status == 'completed':
            self.guard()
        operation = {**self.op, 'status': status, 'stage': status, 'result': result, 'error': error}
        operation.pop('queue_state', None)
        operation.pop('reconciliation_required', None)
        operation.pop('reconciliation_reason', None)
        if status == 'completed':
            operation['completed_at'] = int(self.executor.clock())
            if self.site.get('reporting_enabled') is True and result.get('kind') not in ('conflicts', 'no_changes'):
                operation.update(reporting_required=True, reporting_state='pending', queue_state='pending')
        site_write = any(w.key == 'site:' + self.op['site_id'] for w in writes)
        checks = [] if status != 'completed' else [Check('principal:' + self.op['subject'], self.member['_version'])]
        if status == 'completed' and not site_write:
            checks.append(Check('site:' + self.op['site_id'], self.site['_version']))
        self.store.transact([Write(self.key, operation, self.op['_version']),
            Write(self.lock_key, {**self.lock, 'until': 0, 'blocked_operation': None}, self.lock['_version']), *checks, *writes])

    def record_main_pointer(self):
        self.fence_guard()
        intent = self.op.get('intents', {}).get('publication')
        observed = self.op.get('phases', {}).get('main_commit', {}).get('commit')
        if not intent or not observed:
            raise ReconciliationRequired('main_receipt_required')
        site_key = 'site:' + self.op['site_id']
        site = self.store.get(site_key)
        if not site or site['config_version'] != intent['site_config_version']:
            raise ReconciliationRequired('main_configuration_changed')
        if main_pointer(site) == observed:
            return
        if main_pointer(site) != intent['expected_main_commit']:
            raise ReconciliationRequired('main_authority_changed')
        self.store.transact([Write(site_key, {**site, 'current_main_commit': observed}, site['_version']),
            Check(self.key, self.op['_version']), Check(self.lock_key, self.lock['_version'])])

    def record_factual_publication(self, reason):
        """Account for an already-observed write; this grants no provider authority."""
        self.fence_guard()
        receipt = self.op.get('phases', {}).get('publish', {})
        intent = self.op.get('intents', {}).get('publication')
        if not intent or receipt.get('verified') is not True or receipt.get('artifact_sha256') != intent['preview']['artifact_sha256']:
            raise ReconciliationRequired('publication_receipt_not_verified')
        site_key = 'site:' + self.op['site_id']
        site = self.store.get(site_key)
        if not site or site['config_version'] != intent['site_config_version'] or site.get('current_publication') != intent['expected_publication']:
            raise ReconciliationRequired('publication_authority_changed')
        preview = intent['preview']
        publication = {'operation_id': self.op['operation_id'], 'preview_id': preview['preview_id'],
            'updated_at': int(self.executor.clock()),
            'artifact_sha256': preview['artifact_sha256'], 'source_commit': preview['source_commit'],
            'main_commit': (preview['source_commit'] if site.get('provider') == 'wordpress'
                            else self.op['phases']['main_commit']['commit']),
            'receipt': receipt, 'outcome': 'published_after_cancel_or_revocation'}
        result = {'kind': 'published_after_cancel_or_revocation', **publication, 'reason': reason}
        operation = {**self.op, 'status': 'published_after_cancel_or_revocation',
            'stage': 'published_after_cancel_or_revocation', 'result': result, 'error': None}
        operation.pop('queue_state', None)
        operation.pop('reconciliation_required', None)
        self.store.transact([Write(self.key, operation, self.op['_version']),
            Write(site_key, {**site, 'current_publication': publication,
                             'current_main_commit': publication['main_commit']}, site['_version']),
            Write(self.lock_key, {**self.lock, 'until': 0, 'blocked_operation': None}, self.lock['_version'])])

    def retry(self, force_blocked=False, wait=False, retry_after=30, deadline=None, wait_timeout=900):
        op, lock = self.store.get(self.key), self.store.get(self.lock_key)
        if not op or op.get('status') != 'running' or op.get('lease_owner') != self.owner or not lock or lock.get('owner') != self.owner or lock['epoch'] != self.epoch:
            return
        observed_publication = op['kind'] == 'publish' and op.get('phases', {}).get('publish', {}).get('verified') is True
        main_unrecorded = op['kind'] == 'publish' and bool(op.get('phases', {}).get('main_commit'))
        needs_reconciliation = bool(force_blocked or op.get('reconciliation_required') or observed_publication or main_unrecorded)
        blocked = self.op['operation_id'] if op.get('pending_effect') or needs_reconciliation else None
        now = self.executor.clock()
        attempts = op.get('retry_attempts', 0) + (0 if wait else 1)
        generation = op.get('retry_generation', 0) + 1
        wait_deadline = None
        if wait:
            candidate_deadline = deadline or now + min(max(float(wait_timeout), 30), 3600)
            existing_deadline = op.get('wait_deadline') if op.get('wait_stage') == op.get('stage') else None
            wait_deadline = min(candidate_deadline, existing_deadline) if existing_deadline is not None else candidate_deadline
        exhausted = attempts >= self.executor.max_retry_attempts or (wait and now >= wait_deadline)
        delay = min(max(float(retry_after), 1), 300) if wait else min(300, 5 * 2 ** (attempts - 1))
        row = {**op, 'status': 'needs_attention' if exhausted else ('reconciling' if blocked else 'retry_wait'),
            'retry_attempts': attempts, 'retry_generation': generation, 'retry_at': now + delay,
            'error': ('wait_deadline_exceeded' if wait else 'retry_budget_exhausted') if exhausted else ('provider_wait' if wait else 'provider_retry_required'),
            'reconciliation_required': needs_reconciliation}
        if op.get('reconciliation_reason'):
            row['error'] = op['reconciliation_reason']
        if wait:
            row['wait_deadline'] = wait_deadline
            row['wait_stage'] = op.get('stage')
        if exhausted:
            row.pop('queue_state', None)
        else:
            row['queue_state'] = 'pending'
        self.store.transact([Write(self.key, row, op['_version']),
            Write(self.lock_key, {**lock, 'until': 0, 'blocked_operation': blocked}, lock['_version'])])


def main_pointer(site):
    publication = site.get('current_publication')
    publication = publication if isinstance(publication, dict) else {}
    return site.get('current_main_commit') or publication.get('main_commit') or publication.get('receipt', {}).get('main_commit') or site.get('initial_main_commit')


def artifact_source(data):
    from bundles import MAX_TRANSPORT, MAX_FILE, MAX_FILES, MAX_TOTAL, validate_path, validate_files
    if not isinstance(data, bytes) or len(data) > MAX_TRANSPORT:
        raise Rejected('artifact_size_exceeded')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_FILES + 1 or len({i.filename.casefold() for i in infos}) != len(infos):
                raise Rejected('artifact_file_set_mismatch')
            files, total = {}, 0
            for info in infos:
                if info.is_dir() or info.flag_bits & 1 or stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG) or info.file_size > MAX_FILE:
                    raise Rejected('artifact_entry_invalid')
                total += info.file_size
                if total > MAX_TOTAL + 1024 * 1024:
                    raise Rejected('artifact_size_exceeded')
                if info.filename == 'version.json':
                    continue
                validate_path(info.filename)
                files[info.filename] = archive.read(info)
        return validate_files(files)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as error:
        raise Rejected('artifact_invalid') from None



def verify_artifact(data, files, commit, operation_id):
    """Bind the downloaded CI ZIP to every reconciled byte and package metadata."""
    from bundles import MAX_TRANSPORT, MAX_FILE
    if not isinstance(data, bytes) or len(data) > MAX_TRANSPORT:
        raise Rejected('artifact_size_exceeded')
    expected = set(files) | {'version.json'}
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) != len(expected) or {i.filename for i in infos} != expected:
                raise Rejected('artifact_file_set_mismatch')
            content = {}
            for info in infos:
                if info.is_dir() or info.flag_bits & 1 or stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG) or info.file_size > MAX_FILE:
                    raise Rejected('artifact_entry_invalid')
                value = archive.read(info)
                if info.filename != 'version.json' and value != files[info.filename]:
                    raise Rejected('artifact_source_mismatch')
                content[info.filename] = value
            metadata = json.loads(content['version.json'])
        records = [{'path': p, 'sha256': sha256(v), 'size': len(v)} for p, v in sorted(files.items())]
        expected_hash = fingerprint(records)
        if not isinstance(metadata, dict) or type(metadata.get('schema_version')) is not int or metadata != {'schema_version': 1, 'source_commit': commit, 'operation_id': operation_id,
                        'source_sha256': expected_hash, 'version': expected_hash}:
            raise Rejected('artifact_metadata_mismatch')
    except (zipfile.BadZipFile, ValueError, KeyError, RuntimeError, NotImplementedError) as error:
        if isinstance(error, Rejected):
            raise
        raise Rejected('artifact_invalid') from None
