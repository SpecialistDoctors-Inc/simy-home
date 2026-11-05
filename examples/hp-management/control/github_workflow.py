"""Exact-head GitHub PR/Actions proof and immutable artifact retrieval.

Nothing runs on construction. Runtime App must request the exact approved
contents/write, pull_requests/write, checks/read and actions/read permissions.
The reviewed root-site workflow checks out the PR HEAD, never the merge ref.
"""
from __future__ import annotations
import hashlib
import io
import json
import re
import ssl
import stat
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid5, NAMESPACE_URL
import zipfile
from bundles import MAX_TRANSPORT, MAX_FILES, MAX_FILE, MAX_TOTAL, validate_path, validate_files, sha256
from executor import IntegrationUnavailable, verify_artifact
from github_app import GitHubError
from service import fingerprint, Rejected


class ValidationPending(RuntimeError):
    wait_required = True
    retry_after = 30
    wait_timeout = 900


class ValidationFailed(Rejected):
    effect_observed = True


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _http(url, headers, limit):
    request = urllib.request.Request(url, headers=headers, method='GET')
    opener = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    try:
        with opener.open(request, timeout=20) as response:
            return response.status, dict(response.headers), response.read(limit + 1)
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read(min(limit, 1024 * 1024) + 1)


def download_artifact(url, headers, guard, transport=_http):
    """Only GitHub may issue the signed URL. Credentials never follow it."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != 'api.github.com' or not re.fullmatch(r'/repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/artifacts/[1-9][0-9]*/zip', parsed.path) or parsed.query or parsed.fragment:
        raise ValidationFailed('artifact_endpoint_rejected')
    guard()
    status, response_headers, data = transport(url, headers, MAX_TRANSPORT + 2 * 1024 * 1024)
    if status != 302:
        raise ValidationFailed('artifact_redirect_required')
    location = next((v for k,v in response_headers.items() if k.lower() == 'location'), None)
    if not isinstance(location, str) or len(location) > 8192:
        raise ValidationFailed('artifact_location_invalid')
    target = urllib.parse.urlsplit(location)
    host = target.hostname or ''
    if target.scheme != 'https' or target.username or target.password or target.port not in (None,443) or target.fragment or not (
        host.endswith('.blob.core.windows.net') or host.endswith('.actions.githubusercontent.com')):
        raise ValidationFailed('artifact_redirect_origin_rejected')
    guard()
    # An empty header dictionary is intentional: no bearer token or cookies.
    status, _, data = transport(location, {}, MAX_TRANSPORT + 2 * 1024 * 1024)
    if status != 200 or len(data) > MAX_TRANSPORT + 2 * 1024 * 1024:
        raise ValidationFailed('artifact_download_failed')
    return data


def unpack_artifact(data, commit, repository):
    """Parse upload-artifact's outer ZIP and bind the inner site ZIP/manifest."""
    if not isinstance(data, bytes) or len(data) > MAX_TRANSPORT + 2 * 1024 * 1024:
        raise ValidationFailed('artifact_transport_size')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) != 2 or {i.filename for i in infos} != {'site.zip','manifest.json'}:
                raise ValidationFailed('outer_artifact_file_set')
            payload = {}
            for info in infos:
                maximum = MAX_TRANSPORT if info.filename == 'site.zip' else 1024 * 1024
                if info.flag_bits & 1 or info.is_dir() or stat.S_IFMT(info.external_attr >> 16) not in (0,stat.S_IFREG) or info.file_size > maximum:
                    raise ValidationFailed('outer_artifact_entry')
                payload[info.filename] = archive.read(info)
        manifest = json.loads(payload['manifest.json'], object_pairs_hook=_unique_object)
        required = {'schema_version','source_commit','operation_id','source_sha256','version','kind','artifact_sha256','files'}
        if not isinstance(manifest,dict) or set(manifest) != required or manifest['schema_version'] != 1 or type(manifest['schema_version']) is not int or manifest['kind'] != 'static-site-artifact' or manifest['source_commit'] != commit or manifest['artifact_sha256'] != sha256(payload['site.zip']):
            raise ValidationFailed('artifact_manifest_mismatch')
        package_id = str(uuid5(NAMESPACE_URL, 'https://github.com/' + repository + '/commit/' + commit))
        if manifest['operation_id'] != package_id:
            raise ValidationFailed('artifact_package_operation_mismatch')
        files = {}
        with zipfile.ZipFile(io.BytesIO(payload['site.zip'])) as archive:
            infos = archive.infolist()
            if not 1 <= len(infos) <= MAX_FILES + 1 or len({i.filename.casefold() for i in infos}) != len(infos):
                raise ValidationFailed('inner_artifact_file_set')
            total = 0
            for info in infos:
                if info.flag_bits & 1 or info.is_dir() or stat.S_IFMT(info.external_attr >> 16) not in (0,stat.S_IFREG) or info.file_size > MAX_FILE:
                    raise ValidationFailed('inner_artifact_entry')
                if info.filename != 'version.json':
                    validate_path(info.filename)
                total += info.file_size
                if total > MAX_TOTAL + 1024 * 1024:
                    raise ValidationFailed('inner_artifact_size')
                files[info.filename] = archive.read(info)
        records = [{'path': p,'sha256':sha256(v),'size':len(v)} for p,v in sorted(files.items())]
        if not isinstance(manifest['files'], list) or any(not isinstance(r, dict) or type(r.get('size')) is not int for r in manifest['files']) or manifest['files'] != records or 'version.json' not in files:
            raise ValidationFailed('artifact_record_mismatch')
        source = {p:v for p,v in files.items() if p != 'version.json'}
        validate_files(source)
        source_hash = fingerprint([{'path':p,'sha256':sha256(v),'size':len(v)} for p,v in sorted(source.items())])
        if manifest['source_sha256'] != source_hash or manifest['version'] != source_hash:
            raise ValidationFailed('artifact_source_digest_mismatch')
        verify_artifact(payload['site.zip'], source, commit, package_id)
        return payload['site.zip'], manifest, fingerprint({p:sha256(v) for p,v in source.items()})
    except (zipfile.BadZipFile, KeyError, UnicodeError, json.JSONDecodeError, RuntimeError, NotImplementedError) as error:
        raise ValidationFailed('artifact_archive_invalid') from None


def _unique_object(pairs):
    result = {}
    for key,value in pairs:
        if key in result:
            raise ValidationFailed('duplicate_artifact_json_key')
        result[key] = value
    return result


class GitHubWorkflow:
    def __init__(self, github_factory, downloader=download_artifact, preview_readback=None):
        self.github_factory, self.downloader, self.preview_readback = github_factory, downloader, preview_readback

    @staticmethod
    def _request(app, guard, method, path, body=None, expected=(200,)):
        if not path.startswith(app.prefix + '/'):
            raise ValidationFailed('cross_repository_workflow_request')
        guard()
        status,result = app.transport(method, 'https://api.github.com' + path, app._headers(app._token()), body)
        if status not in expected:
            raise GitHubError('workflow_request_failed')
        return result

    def _pr(self, app, site, branch, commit, operation, guard, allow_create=True):
        base = site.get('dev_branch', 'dev')
        query = urllib.parse.urlencode({'state':'all','head':app.config.owner + ':' + branch,'base':base,'per_page':100})
        items = self._request(app,guard,'GET',app.prefix + '/pulls?' + query)
        if not isinstance(items,list) or len(items) > 1:
            raise ValidationFailed('candidate_pr_ambiguous')
        marker = 'HP-Operation-Id: ' + operation
        if not items and not allow_create:
            raise ValidationPending('candidate_pr_not_observed')
        if not items:
            # Branch + operation is the durable identity. If POST was accepted
            # but the response was lost, the next attempt reads this same PR.
            self._request(app,guard,'POST',app.prefix + '/pulls', {'title':'HP preview ' + operation,
                'head':branch,'base':base,'body':marker}, (201,))
            raise ValidationPending('candidate_pr_created')
        pr = items[0]
        if pr.get('state') != 'open' or pr.get('body') != marker or pr.get('head',{}).get('ref') != branch or pr.get('head',{}).get('sha') != commit or pr.get('head',{}).get('repo',{}).get('id') != app.config.repository_id or pr.get('base',{}).get('ref') != base or pr.get('base',{}).get('repo',{}).get('id') != app.config.repository_id:
            raise ValidationFailed('candidate_pr_binding_mismatch')
        number = pr.get('number')
        if type(number) is not int or number <= 0:
            raise ValidationFailed('candidate_pr_number_invalid')
        return number

    def validate(self, site, commit, operation, tree_sha256, guard, allow_create=True):
        app = self.github_factory(site,guard)
        required = {'contents':'write','pull_requests':'write','checks':'read','actions':'read'}
        if app.permissions != required:
            raise IntegrationUnavailable('scoped_workflow_permissions_required')
        branch = 'codex/hp/' + str(uuid5(NAMESPACE_URL, 'hp-candidate:' + operation))
        if app.head(branch) != commit:
            raise ValidationFailed('candidate_branch_changed')
        pr = self._pr(app,site,branch,commit,operation,guard,allow_create=allow_create)
        workflow_id = site.get('validation_workflow_id')
        if type(workflow_id) is not int or workflow_id <= 0:
            raise IntegrationUnavailable('trusted_validation_workflow_id_required')
        query = urllib.parse.urlencode({'head_sha':commit,'event':'pull_request','per_page':100})
        response = self._request(app,guard,'GET',app.prefix + '/actions/workflows/' + str(workflow_id) + '/runs?' + query)
        runs = response.get('workflow_runs') if isinstance(response,dict) else None
        if not isinstance(runs,list) or response.get('total_count',0) > 100:
            raise ValidationFailed('validation_runs_invalid_or_unbounded')
        matches = [r for r in runs if r.get('head_sha') == commit and r.get('head_branch') == branch
            and r.get('repository',{}).get('id') == app.config.repository_id
            and r.get('head_repository',{}).get('id') == app.config.repository_id
            and r.get('workflow_id') == workflow_id and r.get('event') == 'pull_request'
            and r.get('path') == '.github/workflows/check-site.yml'
            and any(p.get('number') == pr for p in r.get('pull_requests',[]))]
        if not matches:
            raise ValidationPending('validation_not_started')
        run = max(matches,key=lambda r: (r.get('id',0),r.get('run_attempt',0)))
        if run.get('status') != 'completed':
            raise ValidationPending('validation_running')
        if run.get('conclusion') != 'success':
            raise ValidationFailed('github_validation_failed')
        run_id, attempt = run.get('id'),run.get('run_attempt')
        if type(run_id) is not int or run_id <= 0 or type(attempt) is not int or attempt <= 0:
            raise ValidationFailed('validation_run_identity_invalid')
        artifacts = self._request(app,guard,'GET',app.prefix + '/actions/runs/' + str(run_id) + '/artifacts?per_page=100')
        if not isinstance(artifacts,dict) or artifacts.get('total_count',0) > 100 or not isinstance(artifacts.get('artifacts'),list):
            raise ValidationFailed('validation_artifacts_invalid')
        name = 'static-site-' + commit + '-' + str(attempt)
        candidates = [a for a in artifacts['artifacts'] if a.get('name') == name]
        if len(candidates) != 1:
            raise ValidationFailed('validation_artifact_ambiguous')
        artifact = candidates[0]
        if artifact.get('expired') is not False or artifact.get('workflow_run',{}).get('id') != run_id or artifact.get('workflow_run',{}).get('head_sha') != commit or type(artifact.get('id')) is not int or artifact['id'] <= 0 or not re.fullmatch(r'sha256:[0-9a-f]{64}',artifact.get('digest','')) or type(artifact.get('size_in_bytes')) is not int or not 0 < artifact['size_in_bytes'] <= MAX_TRANSPORT + 2 * 1024 * 1024:
            raise ValidationFailed('validation_artifact_identity_invalid')
        proof = {'repository_id':app.config.repository_id,'repository':app.config.owner + '/' + app.config.repository,
            'run_id':run_id,'run_attempt':attempt,'workflow_id':workflow_id,'pr_number':pr,
            'source_commit':commit,'tree_sha256':tree_sha256,'conclusion':'success',
            'actions_artifact_id':artifact['id'],'actions_artifact_digest':artifact['digest'],
            'actions_artifact_size':artifact['size_in_bytes'], 'site_binding': {
                k:site[k] for k in ('github_app_id','github_installation_id','github_repository_id','github_owner','github_repository') }}
        data,manifest,tree = self._download(app,proof,guard)
        if tree != tree_sha256:
            raise ValidationFailed('validated_source_tree_mismatch')
        proof.update({'artifact_sha256':sha256(data),'package_operation_id':manifest['operation_id']})
        return proof

    def reconcile(self, site, commit, operation, tree_sha256, guard):
        return self.validate(site, commit, operation, tree_sha256, guard, allow_create=False)

    def _download(self, app, proof, guard):
        if app.config.repository_id != proof['repository_id'] or app.config.owner + '/' + app.config.repository != proof['repository']:
            raise ValidationFailed('artifact_repository_mismatch')
        guard()
        data = self.downloader('https://api.github.com' + app.prefix + '/actions/artifacts/' + str(proof['actions_artifact_id']) + '/zip', app._headers(app._token()), guard)
        if len(data) != proof['actions_artifact_size'] or 'sha256:' + sha256(data) != proof['actions_artifact_digest']:
            raise ValidationFailed('actions_artifact_digest_mismatch')
        return unpack_artifact(data,proof['source_commit'],proof['repository'])

    def artifact(self, proof, guard):
        app = self.github_factory(proof['site_binding'],guard)
        data,manifest,tree = self._download(app,proof,guard)
        if sha256(data) != proof['artifact_sha256'] or tree != proof['tree_sha256'] or manifest['operation_id'] != proof['package_operation_id']:
            raise ValidationFailed('saved_validation_proof_mismatch')
        return data

    def readback(self, site, proof, guard):
        if self.preview_readback is None:
            raise IntegrationUnavailable('exact_preview_publication_readback_required')
        guard()
        return self.preview_readback(site,proof,guard)
