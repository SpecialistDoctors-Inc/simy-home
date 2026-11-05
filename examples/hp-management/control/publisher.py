"""Fenced immutable-release publisher; construction performs no provider calls.

Only an explicitly configured role in the approved AWS account may publish.
CloudFront configuration uses a frozen ETag/config compare-and-swap. Edge rollout
and cache invalidation propagate; a verified receipt describes observed readback,
not a globally atomic switch at every edge.

Intents are limited to 300 KiB of canonical JSON (below DynamoDB's 400 KiB
item limit). Oversized config/manifest plans are deterministically rejected
before publication writes. A switched release awaiting invalidation requires
active authority to resume; cancellation never authorizes cache-cleanup writes.
"""
from __future__ import annotations

from copy import deepcopy
import io
import json
import mimetypes
import re
import ssl
import stat
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile

from bundles import MAX_TRANSPORT, MAX_FILE, MAX_FILES, MAX_TOTAL, sha256, validate_path, validate_files
from executor import Busy, IntegrationUnavailable
from service import Rejected, fingerprint
from store import Conflict, Write

ACCOUNT = '209300895845'
MAX_INTENT_BYTES = 300 * 1024


class PublicationPending(RuntimeError):
    wait_required = True
    retry_after = 30

    def __init__(self, reason, deadline=None):
        super().__init__(reason)
        self.deadline = deadline or int(time.time()) + 3600


class PublicationRejected(Rejected):
    pass


class ServedNotFound(RuntimeError):
    """The injected/default readback transport observed an actual HTTP 404."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_https(url, limit):
    request = urllib.request.Request(url, headers={'Cache-Control': 'no-cache', 'Pragma': 'no-cache'}, method='GET')
    opener = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    try:
        with opener.open(request, timeout=20) as response:
            if response.status != 200:
                raise PublicationPending('served_file_not_ready')
            content = response.read(limit + 1)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise ServedNotFound('served_http_404') from None
        raise PublicationPending('served_file_http_' + str(error.code)) from None
    except urllib.error.URLError:
        raise PublicationPending('served_origin_unreachable') from None
    if len(content) > limit:
        raise PublicationPending('served_file_size_mismatch')
    return content


def aws_clients(role_arn, session_name):
    import boto3
    from botocore.config import Config
    config = Config(connect_timeout=10, read_timeout=20, retries={'max_attempts': 0})
    assumed = boto3.client('sts', config=config).assume_role(RoleArn=role_arn,
        RoleSessionName=session_name, DurationSeconds=900)['Credentials']
    session = boto3.Session(aws_access_key_id=assumed['AccessKeyId'],
        aws_secret_access_key=assumed['SecretAccessKey'], aws_session_token=assumed['SessionToken'])
    return {name: session.client(name, config=config) for name in ('sts', 's3', 'cloudfront')}


def config_sha256(config, origin_id):
    """Hash the complete config, excluding ONLY the selected origin's OriginPath."""
    value = deepcopy(config)
    origins = value.get('Origins', {}).get('Items', [])
    matches = [origin for origin in origins if origin.get('Id') == origin_id]
    if len(matches) != 1:
        raise PublicationRejected('deployment_origin_ambiguous')
    matches[0].pop('OriginPath', None)
    return fingerprint(value)


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PublicationRejected('duplicate_artifact_metadata_key')
        result[key] = value
    return result


def unpack_release(data, preview):
    if not isinstance(data, bytes) or len(data) > MAX_TRANSPORT or sha256(data) != preview.get('artifact_sha256'):
        raise PublicationRejected('publication_artifact_hash_mismatch')
    files, total = {}, 0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if not 2 <= len(infos) <= MAX_FILES + 1 or len({info.filename.casefold() for info in infos}) != len(infos):
                raise PublicationRejected('publication_artifact_file_set')
            for info in infos:
                if info.is_dir() or info.flag_bits & 1 or stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG) or info.file_size > MAX_FILE:
                    raise PublicationRejected('publication_artifact_entry')
                if info.filename != 'version.json':
                    validate_path(info.filename)
                total += info.file_size
                if total > MAX_TOTAL + 1024 * 1024:
                    raise PublicationRejected('publication_artifact_size')
                files[info.filename] = archive.read(info)
        source = {path: content for path, content in files.items() if path != 'version.json'}
        validate_files(source)
        records = [{'path': path, 'sha256': sha256(content), 'size': len(content)} for path, content in sorted(source.items())]
        source_hash = fingerprint(records)
        metadata = json.loads(files['version.json'], object_pairs_hook=_object)
        package_id = preview.get('validation', {}).get('package_operation_id', preview.get('package_operation_id'))
        if not isinstance(package_id, str) or str(uuid.UUID(package_id)) != package_id:
            raise PublicationRejected('publication_package_identity_required')
        if type(metadata.get('schema_version')) is not int or metadata != {'schema_version': 1,
                'source_commit': preview['source_commit'], 'operation_id': package_id,
                'source_sha256': source_hash, 'version': source_hash}:
            raise PublicationRejected('publication_version_mismatch')
        if not re.fullmatch('[0-9a-f]{40}', metadata['source_commit']):
            raise PublicationRejected('publication_source_commit_invalid')
        return files, metadata
    except (zipfile.BadZipFile, KeyError, ValueError, TypeError, RuntimeError, NotImplementedError) as error:
        if isinstance(error, PublicationRejected):
            raise
        raise PublicationRejected('publication_artifact_invalid') from None


def _missing(error):
    return getattr(error, 'response', {}).get('Error', {}).get('Code') in ('NoSuchKey', '404', 'NotFound')


def _same_invalidation_batch(expected, observed):
    """CloudFront may reorder paths on readback; preserve exact set identity."""
    if not isinstance(expected, dict) or not isinstance(observed, dict):
        return False
    if set(expected) != {'CallerReference', 'Paths'} or set(observed) != set(expected):
        return False
    if not isinstance(expected['CallerReference'], str) or not expected['CallerReference'] or observed['CallerReference'] != expected['CallerReference']:
        return False
    groups = []
    for batch in (expected, observed):
        paths = batch['Paths']
        if not isinstance(paths, dict) or set(paths) != {'Quantity', 'Items'}:
            return False
        count, items = paths['Quantity'], paths['Items']
        if type(count) is not int or not 1 <= count <= 3000 or not isinstance(items, list) or len(items) != count or any(not isinstance(item, str) for item in items):
            return False
        unique = set(items)
        if len(unique) != count:
            return False
        groups.append(unique)
    return groups[0] == groups[1]


class SitePublisher:
    def __init__(self, environment, role_arn, store, github_factory=None, clients_factory=None, fetch=None):
        if environment not in ('dev', 'prod'):
            raise ValueError('publication_environment_invalid')
        self.environment, self.role_arn, self.store = environment, role_arn, store
        self.clients_factory, self.fetch = clients_factory or aws_clients, fetch or fetch_https

    @staticmethod
    def _record_budget(row, reserve=0):
        encoded = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        if len(encoded) + reserve > MAX_INTENT_BYTES:
            raise PublicationRejected('publication_intent_record_budget_exceeded')

    def preflight(self, site, guard):
        """Read-only admission check, to run before GitHub candidate/ref effects.

        The full candidate-dependent intent budget is checked in publish before
        any intent/object/config write; admission checks all known fixed state.
        """
        binding = self._binding(site)
        clients = self._clients(guard, 'preflight')
        result, origin = self._distribution(clients, binding, guard)
        self._call(clients['s3'], 'head_bucket', guard, Bucket=binding['target']['bucket'], ExpectedBucketOwner=ACCOUNT)
        previous = self._previous_files(binding, origin.get('OriginPath', ''))
        # Reserve the two full frozen configurations and known previous-path
        # inventory; exact candidate records receive the same bound in publish.
        self._record_budget({'binding': binding, 'original_config': result['Distribution']['DistributionConfig'],
            'desired_config': result['Distribution']['DistributionConfig'], 'previous_files': sorted(previous),
            'previous_viewer_paths': sorted(self._viewer_paths(previous))}, reserve=4096)
        if result['Distribution'].get('Status') != 'Deployed':
            raise PublicationPending('cloudfront_not_ready_for_admission')
        return {'ready': True, 'expected_config_sha256': binding['target']['expected_config_sha256'],
            'supported_intent_bytes': MAX_INTENT_BYTES}

    def _binding(self, site):
        if not self.role_arn:
            raise IntegrationUnavailable('dedicated_publisher_role_not_configured')
        if not isinstance(self.role_arn, str) or not re.fullmatch('arn:aws:iam::' + ACCOUNT + r':role/[A-Za-z0-9+=,.@_/-]+', self.role_arn):
            raise PublicationRejected('publisher_role_account_rejected')
        target = site.get('deployment', {}).get(self.environment)
        required = {'bucket', 'distribution_id', 'origin_id', 'expected_config_sha256'}
        if not isinstance(target, dict) or not required <= target.keys() or target.keys() - required - {'initial_file_paths'}:
            raise PublicationRejected('deployment_binding_required')
        if not isinstance(target['bucket'], str) or not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', target['bucket']) or '..' in target['bucket']:
            raise PublicationRejected('deployment_bucket_invalid')
        if not isinstance(target['distribution_id'], str) or not re.fullmatch('[A-Z0-9]{5,32}', target['distribution_id']):
            raise PublicationRejected('deployment_distribution_invalid')
        if not isinstance(target['origin_id'], str) or not target['origin_id'] or len(target['origin_id']) > 128 or not re.fullmatch('[0-9a-f]{64}', target['expected_config_sha256']):
            raise PublicationRejected('deployment_origin_or_config_invalid')
        url = site.get('dev_url' if self.environment == 'dev' else 'prod_url')
        parsed = urllib.parse.urlsplit(url or '')
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
            raise PublicationRejected('deployment_served_url_invalid')
        site_id = site.get('site_id')
        if not isinstance(site_id, str) or not re.fullmatch('[A-Za-z0-9_-]{1,200}', site_id):
            raise PublicationRejected('deployment_site_identity_invalid')
        return {'site_id': site_id, 'environment': self.environment, 'target': deepcopy(target), 'url': url.rstrip('/'), 'role_arn': self.role_arn}

    @staticmethod
    def _viewer_paths(files):
        paths = {'/'}
        for path in files:
            paths.add('/' + urllib.parse.quote(path, safe='/'))
            if path.endswith('/index.html'):
                directory = '/' + urllib.parse.quote(path[:-len('index.html')], safe='/')
                paths.update((directory, directory.rstrip('/')))
        return paths

    def _previous_files(self, binding, origin_path):
        if re.fullmatch(r'/releases/[0-9a-f]{64}', origin_path):
            digest = origin_path.rsplit('/', 1)[1]
            pointer = self.store.get(self._artifact_key(binding, digest))
            prior = self.store.get(pointer['intent_key']) if pointer else None
            if not prior or prior.get('binding') != binding or prior.get('artifact_sha256') != digest or prior.get('prefix') != origin_path[1:]:
                raise PublicationRejected('previous_release_manifest_required')
            paths = [record['path'] for record in prior.get('files', [])]
        elif origin_path == '':
            paths = binding['target'].get('initial_file_paths')
        else:
            raise PublicationRejected('legacy_origin_path_not_reviewed')
        if not isinstance(paths, list) or not paths or len(paths) > MAX_FILES + 1 or any(not isinstance(path, str) for path in paths) or len(set(paths)) != len(paths):
            raise PublicationRejected('previous_release_manifest_required')
        for path in paths:
            if path != 'version.json':
                validate_path(path)
        validate_files({path: b'' for path in paths if path != 'version.json'})
        return set(paths)

    def _clients(self, guard, operation='readback'):
        guard()
        clients = self.clients_factory(self.role_arn, 'hp-' + self.environment + '-' + operation[:36])
        guard()
        identity = clients['sts'].get_caller_identity()
        if identity.get('Account') != ACCOUNT:
            raise PublicationRejected('publisher_assumed_account_mismatch')
        return clients

    @staticmethod
    def _call(client, method, guard, **kwargs):
        guard()
        return getattr(client, method)(**kwargs)

    def _distribution(self, clients, binding, guard):
        target = binding['target']
        result = self._call(clients['cloudfront'], 'get_distribution', guard, Id=target['distribution_id'])
        distribution = result.get('Distribution', {})
        if distribution.get('Id') != target['distribution_id'] or distribution.get('ARN') != 'arn:aws:cloudfront::' + ACCOUNT + ':distribution/' + target['distribution_id']:
            raise PublicationRejected('cloudfront_target_account_mismatch')
        config = distribution.get('DistributionConfig')
        if not isinstance(config, dict) or config_sha256(config, target['origin_id']) != target['expected_config_sha256']:
            raise PublicationRejected('cloudfront_unexpected_config_drift')
        origin = next(o for o in config['Origins']['Items'] if o.get('Id') == target['origin_id'])
        domain = origin.get('DomainName', '')
        if not re.fullmatch(re.escape(target['bucket']) + r'\.s3(?:[.-][a-z0-9-]+)?\.amazonaws\.com', domain) or 'S3OriginConfig' not in origin or 'CustomOriginConfig' in origin:
            raise PublicationRejected('cloudfront_origin_bucket_mismatch')
        aliases = config.get('Aliases', {}).get('Items', [])
        host = urllib.parse.urlsplit(binding['url']).hostname
        if host not in aliases + [distribution.get('DomainName')]:
            raise PublicationRejected('cloudfront_served_alias_mismatch')
        if not isinstance(result.get('ETag'), str) or not result['ETag']:
            raise PublicationRejected('cloudfront_etag_missing')
        return result, origin

    def _key(self, binding, operation):
        return 'publication-intent:' + binding['site_id'] + ':' + self.environment + ':' + operation

    def _artifact_key(self, binding, artifact):
        return 'publication-artifact:' + binding['site_id'] + ':' + self.environment + ':' + artifact

    def _save(self, key, row, guard):
        self._record_budget(row)
        guard()
        return self.store.put(key, {k: v for k, v in row.items() if k != '_version'}, row.get('_version'))

    def _load_intent(self, binding, preview, operation, fence=None):
        row = self.store.get(self._key(binding, operation))
        if row and (row.get('binding') != binding or row.get('artifact_sha256') != preview.get('artifact_sha256') or row.get('source_commit') != preview.get('source_commit') or row.get('operation_id') != operation or (fence is not None and row.get('fence') != fence)):
            raise PublicationRejected('publication_intent_binding_mismatch')
        return row

    def _s3_read(self, clients, row, record, guard):
        result = self._call(clients['s3'], 'get_object', guard, Bucket=row['binding']['target']['bucket'],
            Key=row['prefix'] + '/' + record['path'], ExpectedBucketOwner=ACCOUNT)
        body = result['Body']
        try:
            data = body.read(record['size'] + 1)
        finally:
            body.close()
        if len(data) != record['size'] or sha256(data) != record['sha256']:
            raise PublicationRejected('immutable_release_object_mismatch')
        return data

    def _stage(self, clients, row, files, guard):
        self._call(clients['s3'], 'head_bucket', guard, Bucket=row['binding']['target']['bucket'], ExpectedBucketOwner=ACCOUNT)
        for record in row['files']:
            try:
                self._s3_read(clients, row, record, guard)
                continue
            except Exception as error:
                if not _missing(error):
                    raise
            try:
                self._call(clients['s3'], 'put_object', guard, Bucket=row['binding']['target']['bucket'],
                    Key=row['prefix'] + '/' + record['path'], Body=files[record['path']], ExpectedBucketOwner=ACCOUNT,
                    IfNoneMatch='*', ContentType=mimetypes.guess_type(record['path'])[0] or 'application/octet-stream',
                    CacheControl='no-store' if record['path'] == 'version.json' else 'public, max-age=300',
                    Metadata={'sha256': record['sha256']}, ChecksumSHA256=__import__('base64').b64encode(bytes.fromhex(record['sha256'])).decode())
            except Exception:
                # Conditional conflict and lost acknowledgements both require exact readback.
                self._s3_read(clients, row, record, guard)
            self._s3_read(clients, row, record, guard)

    def _find_invalidation(self, clients, row, guard):
        marker = None
        for _ in range(10):
            arguments = {'DistributionId': row['binding']['target']['distribution_id'], 'MaxItems': '100'}
            if marker:
                arguments['Marker'] = marker
            result = self._call(clients['cloudfront'], 'list_invalidations', guard, **arguments).get('InvalidationList', {})
            for entry in result.get('Items', []):
                invalidation = self._call(clients['cloudfront'], 'get_invalidation', guard,
                    DistributionId=row['binding']['target']['distribution_id'], Id=entry['Id'])['Invalidation']
                batch = invalidation.get('InvalidationBatch', {})
                if batch.get('CallerReference') == row['invalidation']['CallerReference']:
                    if not _same_invalidation_batch(row['invalidation'], batch):
                        raise PublicationRejected('invalidation_identity_collision')
                    return invalidation
            if result.get('IsTruncated') is False:
                return None
            marker = result.get('NextMarker')
            if not marker:
                raise PublicationPending('invalidation_listing_incomplete', row['deadline'])
        raise PublicationPending('invalidation_listing_limit', row['deadline'])

    def publish(self, site, preview, artifact_bytes, operation_id, fence, guard):
        binding = self._binding(site)
        try:
            if str(uuid.UUID(operation_id)) != operation_id:
                raise ValueError()
        except (ValueError, AttributeError):
            raise PublicationRejected('publication_operation_invalid') from None
        if type(fence) is not int or fence <= 0:
            raise PublicationRejected('publication_fence_invalid')
        files, metadata = unpack_release(artifact_bytes, preview)
        clients = self._clients(guard, operation_id)
        key = self._key(binding, operation_id)
        row = self._load_intent(binding, preview, operation_id)
        result, origin = self._distribution(clients, binding, guard)
        if row is not None and row['fence'] != fence:
            current = result['Distribution']['DistributionConfig']
            if fence <= row['fence'] or (current != row['desired_config'] and
                    (current != row['original_config'] or result['ETag'] != row['original_etag'])):
                raise PublicationRejected('publication_fence_upgrade_rejected')
            # Only an actively authorized execution can transfer the exact frozen
            # intent to a renewed lease. Reconciliation never reaches this write.
            row = self._save(key, {**row, 'fence': fence}, guard)
        if row is None:
            prefix = 'releases/' + preview['artifact_sha256']
            desired = deepcopy(result['Distribution']['DistributionConfig'])
            next(o for o in desired['Origins']['Items'] if o['Id'] == binding['target']['origin_id'])['OriginPath'] = '/' + prefix
            previous_files = self._previous_files(binding, origin.get('OriginPath', ''))
            current_paths = self._viewer_paths(files)
            previous_paths = self._viewer_paths(previous_files)
            paths = sorted(current_paths | previous_paths)
            if len(paths) > 3000:
                raise PublicationRejected('exact_invalidation_path_limit')
            row = {'binding': binding, 'operation_id': operation_id, 'fence': fence,
                'source_commit': preview['source_commit'], 'artifact_sha256': preview['artifact_sha256'],
                'prefix': prefix, 'metadata': metadata, 'files': [{'path': p, 'sha256': sha256(v), 'size': len(v)} for p, v in sorted(files.items())],
                'original_config': result['Distribution']['DistributionConfig'], 'original_etag': result['ETag'],
                'desired_config': desired, 'deadline': int(time.time()) + 3600, 'phase': 'staging',
                'retired_files': sorted(previous_files - files.keys()),
                'retired_paths': sorted(previous_paths - current_paths),
                'invalidation': {'CallerReference': 'hp-' + operation_id + '-' + preview['artifact_sha256'],
                    'Paths': {'Quantity': len(paths), 'Items': paths}}}
            # Reserve room for future phase/fence/version updates so an admitted
            # intent cannot cross this supported bound during normal recovery.
            self._record_budget(row, reserve=4096)
            guard()
            self.store.transact([Write(key, row, None), Write(self._artifact_key(binding, row['artifact_sha256']),
                {'intent_key': key}, (self.store.get(self._artifact_key(binding, row['artifact_sha256'])) or {}).get('_version'))])
            row = self.store.get(key)
        self._stage(clients, row, files, guard)
        result, origin = self._distribution(clients, binding, guard)
        current = result['Distribution']['DistributionConfig']
        if current != row['desired_config']:
            if current != row['original_config'] or result['ETag'] != row['original_etag'] or result['Distribution'].get('Status') != 'Deployed':
                raise PublicationRejected('cloudfront_frozen_switch_conflict')
            row = self._save(key, {**row, 'phase': 'switching'}, guard)
            try:
                self._call(clients['cloudfront'], 'update_distribution', guard, Id=binding['target']['distribution_id'],
                    IfMatch=row['original_etag'], DistributionConfig=row['desired_config'])
            except (Rejected, Busy):
                raise
            except Exception:
                # Do not blindly retry: compare actual frozen state on reconciliation.
                raise PublicationPending('cloudfront_switch_acknowledgement_unknown', row['deadline']) from None
        result, _ = self._distribution(clients, binding, guard)
        if result['Distribution']['DistributionConfig'] != row['desired_config']:
            raise PublicationPending('cloudfront_switch_not_observed', row['deadline'])
        if result['Distribution'].get('Status') != 'Deployed':
            raise PublicationPending('cloudfront_propagating', row['deadline'])
        invalidation = self._find_invalidation(clients, row, guard)
        if invalidation is None:
            row = self._save(key, {**row, 'phase': 'invalidating'}, guard)
            try:
                self._call(clients['cloudfront'], 'create_invalidation', guard,
                    DistributionId=binding['target']['distribution_id'], InvalidationBatch=row['invalidation'])
            except (Rejected, Busy):
                raise
            except Exception:
                raise PublicationPending('invalidation_acknowledgement_unknown', row['deadline']) from None
        return self._verify(clients, row, guard)

    def _verify(self, clients, row, guard):
        result, _ = self._distribution(clients, row['binding'], guard)
        if result['Distribution']['DistributionConfig'] != row['desired_config']:
            raise PublicationRejected('cloudfront_release_path_mismatch')
        if result['Distribution'].get('Status') != 'Deployed':
            raise PublicationPending('cloudfront_propagating', row['deadline'])
        invalidation = self._find_invalidation(clients, row, guard)
        if invalidation is None or invalidation.get('Status') != 'Completed':
            raise PublicationPending('cloudfront_cache_invalidation_pending', row['deadline'])
        for record in row['files']:
            self._s3_read(clients, row, record, guard)
            guard()
            url = row['binding']['url'] + '/' + urllib.parse.quote(record['path'], safe='/') + '?hp_artifact=' + row['artifact_sha256']
            try:
                content = self.fetch(url, record['size'])
            except (PublicationPending, ServedNotFound, OSError):
                raise PublicationPending('served_origin_not_ready', row['deadline']) from None
            if not isinstance(content, bytes) or len(content) != record['size'] or sha256(content) != record['sha256']:
                raise PublicationPending('served_static_bytes_mismatch', row['deadline'])
        for path in row['retired_files']:
            try:
                result = self._call(clients['s3'], 'get_object', guard, Bucket=row['binding']['target']['bucket'],
                    Key=row['prefix'] + '/' + path, ExpectedBucketOwner=ACCOUNT)
            except Exception as error:
                if not _missing(error):
                    raise
            else:
                result['Body'].close()
                raise PublicationRejected('retired_object_present_in_new_release')
        for path in row['retired_paths']:
            guard()
            try:
                self.fetch(row['binding']['url'] + path + '?hp_artifact=' + row['artifact_sha256'], 0)
            except ServedNotFound:
                continue
            except (PublicationPending, OSError):
                raise PublicationPending('retired_path_status_unconfirmed', row['deadline']) from None
            raise PublicationPending('retired_path_still_served', row['deadline'])
        # A second control-plane observation fences config changes during the reads.
        final, _ = self._distribution(clients, row['binding'], guard)
        if final['Distribution']['DistributionConfig'] != row['desired_config'] or final['Distribution'].get('Status') != 'Deployed':
            raise PublicationPending('cloudfront_changed_during_readback', row['deadline'])
        return {'verified': True, 'environment': self.environment, 'site_id': row['binding']['site_id'],
            'operation_id': row['operation_id'], 'source_commit': row['source_commit'],
            'artifact_sha256': row['artifact_sha256'], 'source_sha256': row['metadata']['source_sha256'],
            'release_prefix': row['prefix'], 'distribution_id': row['binding']['target']['distribution_id'],
            'invalidation_id': invalidation['Id'], 'url': row['binding']['url'], 'edge_rollout_atomic': False}

    def reconcile(self, site, preview, operation_id, fence, fence_only_guard):
        binding = self._binding(site)
        row = self._load_intent(binding, preview, operation_id, fence)
        if row is None:
            # The strongly consistent Store read proves that no publisher write
            # passed the mandatory persisted-intent boundary. This is a control
            # signal only: the executor must recheck active authority to resume.
            return {'safe_to_resume': True, 'prewrite_proven': True}
        clients = self._clients(fence_only_guard, operation_id)
        result, _ = self._distribution(clients, binding, fence_only_guard)
        config = result['Distribution']['DistributionConfig']
        if config != row['desired_config']:
            if config == row['original_config'] and result['ETag'] == row['original_etag'] and result['Distribution'].get('Status') == 'Deployed':
                return {'safe_to_resume': True}
            raise PublicationRejected('cloudfront_reconciliation_conflict')
        if result['Distribution'].get('Status') != 'Deployed':
            raise PublicationPending('cloudfront_propagating', row['deadline'])
        if self._find_invalidation(clients, row, fence_only_guard) is None:
            # Never issue invalidation under a fence-only/revoked authority.
            # The caller must leave a cancelled run blocked for operator action.
            return {'safe_to_resume': True, 'cache_cleanup_requires_attention': True,
                'observed_release_prefix': row['prefix']}
        return self._verify(clients, row, fence_only_guard)

    def readback(self, site, proof, guard):
        binding = self._binding(site)
        pointer = self.store.get(self._artifact_key(binding, proof.get('artifact_sha256', '')))
        row = self.store.get(pointer['intent_key']) if pointer else None
        if not row or row['binding'] != binding or row['source_commit'] != proof.get('source_commit') or row['artifact_sha256'] != proof.get('artifact_sha256') or row['metadata']['operation_id'] != proof.get('package_operation_id'):
            raise PublicationRejected('preview_publication_intent_missing')
        return self._verify(self._clients(guard), row, guard)
