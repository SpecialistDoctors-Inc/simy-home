"""WordPress workspace operations over the existing Mac editor protocol."""
from html import escape
from uuid import NAMESPACE_URL, uuid5

from bundles import build_snapshot, sha256, validate_changes, validate_snapshot
from service import Rejected
from store import Check, Conflict, Write
from wordpress_provider import content_digest


class WordPressTransfers:
    def __init__(self, store, client, bucket):
        self.store, self.client, self.bucket = store, client, bucket

    def download(self, key, *, preview=False):
        params = {'Bucket': self.bucket, 'Key': key}
        if preview:
            params['ResponseContentType'] = 'text/html; charset=utf-8'
            params['ResponseContentDisposition'] = 'inline'
        return {'method': 'GET', 'url': self.client.generate_presigned_url('get_object', Params=params,
                  ExpiresIn=900 if preview else 300), 'headers': {}}


class WordPressEditor:
    def __init__(self, onboarding, transfers, service_url):
        self.onboarding, self.transfers, self.service_url = onboarding, transfers, service_url

    def put(self, run, name, data):
        checksum = sha256(data)
        key = 'artifacts/' + run.site['site_id'] + '/' + checksum + '/site.zip'
        receipt = run.effect(name, lambda: run.artifacts.put_exact(key, data),
                             {'kind': 'artifact', 'key': key, 'sha256': checksum})
        return receipt['key'], receipt['sha256']

    def open_workspace(self, run):
        workspace = run.workspace()
        phases = run.op.get('phases', {})
        existing = phases.get('wordpress_snapshot')
        if existing:
            checksum = existing['sha256']
            key = existing['key']
            snapshot = validate_snapshot(run.artifacts.get_exact(key, checksum), run.site['site_id'])
            base = snapshot.manifest['base_commit']
        else:
            run.guard()
            connection = self.onboarding.load(run.site, run.op['subject'])
            base = content_digest(connection.content)[:40]
            data = build_snapshot(run.site['site_id'], run.workspace_id, base, {'index.html': connection.content.encode()})
            key, checksum = self.put(run, 'wordpress_snapshot', data)
            if checksum != sha256(data):
                base = validate_snapshot(run.artifacts.get_exact(key, checksum), run.site['site_id']).manifest['base_commit']
        row = {**workspace, 'status': 'ready', 'head_commit': base, 'base_on_dev': base,
               'snapshot_artifact_key': key, 'snapshot_key': key, 'snapshot_sha256': checksum,
               'head_snapshot_sha256': checksum}
        result = {'schema_version': 1, 'kind': 'workspace', 'site_id': run.site['site_id'],
                  'workspace_id': run.workspace_id, 'base_commit': base, 'snapshot_file_id': checksum,
                  'snapshot_sha256': checksum, 'download_url': self.service_url,
                  'upload_folder_id': run.workspace_id}
        return result, [Write('workspace:' + run.workspace_id, row, workspace['_version'])]

    def save_draft(self, run):
        workspace = run.workspace()
        body = run.op['input']
        if workspace['head_commit'] != body['base_commit']:
            raise Rejected('workspace_changed')
        original = validate_snapshot(run.artifacts.get_exact(workspace['snapshot_key'], workspace['head_snapshot_sha256']), run.site['site_id'])
        changes = validate_changes(run.transferred_changes(), original, run.op['operation_id'])
        if set(changes.candidate_files) != {'index.html'} or not 0 < len(changes.candidate_files['index.html']) <= 1_000_000:
            raise Rejected('wordpress_homepage_content_only')
        saved = sha256(changes.candidate_files['index.html'])[:40]
        data = build_snapshot(run.site['site_id'], run.workspace_id, saved, changes.candidate_files)
        key, checksum = self.put(run, 'wordpress_draft', data)
        result = {'schema_version': 1, 'kind': 'saved', 'site_id': run.site['site_id'], 'workspace_id': run.workspace_id,
                  'operation_id': run.op['operation_id'], 'base_commit': body['base_commit'], 'saved_commit': saved,
                  'bundle_sha256': body['bundle_sha256']}
        row = {**workspace, 'head_commit': saved, 'snapshot_key': key, 'head_snapshot_sha256': checksum,
               'summary': changes.manifest.get('change_summary') or 'トップページの更新'}
        return result, [Write('workspace:' + run.workspace_id, row, workspace['_version'])]

    def submit_preview(self, run):
        workspace = run.workspace()
        if workspace['head_commit'] != run.op['input']['saved_commit']:
            raise Rejected('workspace_changed')
        connection = self.onboarding.load(run.site, run.op['subject'])
        base = content_digest(connection.content)
        if base[:40] != workspace['base_on_dev']:
            raise Rejected('wordpress_homepage_changed')
        data = run.artifacts.get_exact(workspace['snapshot_key'], workspace['head_snapshot_sha256'])
        snapshot = validate_snapshot(data, run.site['site_id'])
        content = snapshot.files['index.html'].decode()
        # Untrusted WordPress markup stays in a scriptless iframe on the artifact origin.
        inner = '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">' + content
        html = ('<!doctype html><meta charset="utf-8"><title>WordPress preview</title>'
                '<iframe title="Homepage preview" sandbox style="width:100%;height:95vh;border:0" srcdoc="'
                + escape(inner, quote=True) + '"></iframe>').encode()
        html_key, _ = self.put(run, 'wordpress_preview', html)
        preview_id = str(uuid5(NAMESPACE_URL, 'hp-wordpress-preview:' + run.op['operation_id']))
        preview = {'preview_id': preview_id, 'site_id': run.site['site_id'], 'status': 'verified',
                   'workspace_id': run.workspace_id,
                   'source_commit': workspace['head_commit'], 'artifact_key': workspace['snapshot_key'],
                   'artifact_sha256': workspace['head_snapshot_sha256'], 'base_sha256': base,
                   'content_sha256': content_digest(content), 'summary': workspace.get('summary', 'トップページの確認'),
                   'preview_html_key': html_key, 'url': self.transfers.download(html_key, preview=True)['url']}
        result = {'kind': 'preview', 'preview_id': preview_id, 'preview_url': preview['url'],
                  'source_commit': preview['source_commit'], 'artifact_sha256': preview['artifact_sha256']}
        return result, [Write('preview:' + preview_id, preview, None),
                        Write('site:' + run.site['site_id'], {**run.site, 'current_preview': preview_id,
                              'current_main_commit': base[:40]}, run.site['_version'])]

    def publish(self, run):
        if not run.executor.publication_enabled:
            raise Rejected('publication_not_enabled')
        approval = self.transfers.store.get('approval:' + run.op['input']['approval_id'])
        if not approval or approval.get('state') != 'accepted' or approval.get('operation_id') != run.op['operation_id']:
            raise Rejected('approval_not_accepted')
        preview = self.transfers.store.get('preview:' + approval['preview_id'])
        if (not preview or preview.get('status') != 'verified' or run.site.get('current_preview') != preview['preview_id']
                or approval.get('site_id') != run.site['site_id'] or preview.get('site_id') != run.site['site_id']
                or approval.get('subject') != run.op['subject'] or run.site.get('current_publication') != approval['expected_publication']
                or any(approval[k] != preview[k] for k in ('source_commit', 'artifact_sha256'))):
            raise Rejected('approval_artifact_mismatch')
        snapshot = validate_snapshot(run.artifacts.get_exact(preview['artifact_key'], preview['artifact_sha256']), run.site['site_id'])
        content = snapshot.files['index.html'].decode()
        if content_digest(content) != preview['content_sha256']:
            raise Rejected('publication_artifact_mismatch')
        run.intent('publication', lambda: {'preview': preview, 'expected_publication': approval['expected_publication'],
                                          'site_config_version': run.site['config_version']})

        def publish_exact():
            run.guard()
            connection = self.onboarding.load(run.site, run.op['subject'])
            if connection.content != content:
                if content_digest(connection.content) != preview['base_sha256']:
                    failure = Rejected('wordpress_homepage_changed')
                    failure.effect_observed = True
                    raise failure
                draft = self.onboarding.provider.save_draft(connection, content)
                run.guard()
                self.onboarding.provider.publish_approved_draft(connection, draft, preview['content_sha256'])
            return self.receipt(preview, run.site)

        receipt = run.effect('publish', publish_exact, {'kind': 'wordpress_publish', 'preview': preview})
        publication = {'operation_id': run.op['operation_id'], 'preview_id': preview['preview_id'],
                       'artifact_sha256': preview['artifact_sha256'], 'source_commit': preview['source_commit'],
                       'main_commit': preview['source_commit'], 'receipt': receipt}
        writes = [
            Check('approval:' + approval['approval_id'], approval['_version']),
            Check('preview:' + preview['preview_id'], preview['_version']),
            Write('site:' + run.site['site_id'], {**run.site, 'current_publication': publication,
                  'current_main_commit': preview['source_commit']}, run.site['_version'])]
        workspace_key = 'workspace:' + preview['workspace_id']
        workspace = self.transfers.store.get(workspace_key)
        if workspace and workspace.get('site_id') == run.site['site_id'] and workspace.get('subject') == run.op['subject']:
            writes.append(Write(workspace_key, {**workspace, 'base_on_dev': preview['source_commit']}, workspace['_version']))
        return {'kind': 'published', **publication}, writes

    @staticmethod
    def receipt(preview, site):
        return {'verified': True, 'artifact_sha256': preview['artifact_sha256'], 'url': site['prod_url']}

    def reconcile_publish(self, site, subject, preview):
        connection = self.onboarding.load(site, subject)
        if content_digest(connection.content) == preview['content_sha256']:
            return self.receipt(preview, site)
        return None
