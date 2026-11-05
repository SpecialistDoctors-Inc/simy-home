from copy import deepcopy
import io
import json
import unittest
import urllib.parse
import zipfile

from bundles import sha256
from executor import IntegrationUnavailable
from publisher import ACCOUNT, PublicationPending, PublicationRejected, ServedNotFound, SitePublisher, config_sha256
from service import fingerprint
from service import Rejected
from store import MemoryStore

OPERATION = '23456789-1234-4234-8234-123456789abc'
PACKAGE = '34567890-1234-4234-8234-123456789abc'
COMMIT = 'a' * 40
ROLE = 'arn:aws:iam::' + ACCOUNT + ':role/hp-dedicated-dev'
DISTRIBUTION = 'EXAMPLE123456'


def artifact(source=None, metadata_update=None):
    source = source or {'index.html': b'<!doctype html><title>Home</title>', 'style.css': b'body{}'}
    source_hash = fingerprint([{'path': p, 'sha256': sha256(v), 'size': len(v)} for p, v in sorted(source.items())])
    metadata = {'schema_version': 1, 'source_commit': COMMIT, 'operation_id': PACKAGE, 'source_sha256': source_hash, 'version': source_hash}
    metadata.update(metadata_update or {})
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as archive:
        for path, data in sorted(source.items()):
            archive.writestr(path, data)
        archive.writestr('version.json', json.dumps(metadata))
    return out.getvalue()


class Missing(Exception):
    response = {'Error': {'Code': 'NoSuchKey'}}


class FakeSTS:
    def __init__(self, fake):
        self.fake = fake
    def get_caller_identity(self):
        self.fake.calls.append(('get_caller_identity', {}))
        return {'Account': self.fake.account}


class FakeS3:
    def __init__(self, fake):
        self.fake = fake
    def head_bucket(self, **kwargs):
        self.fake.calls.append(('head_bucket', kwargs))
        assert kwargs == {'Bucket': 'hp-exact-bucket', 'ExpectedBucketOwner': ACCOUNT}
        return {}
    def get_object(self, **kwargs):
        self.fake.calls.append(('get_object', kwargs))
        assert kwargs['ExpectedBucketOwner'] == ACCOUNT
        assert kwargs['Bucket'] == 'hp-exact-bucket'
        key = kwargs['Key']
        assert key.startswith('releases/')
        if key not in self.fake.objects:
            raise Missing()
        return {'Body': io.BytesIO(self.fake.objects[key])}
    def put_object(self, **kwargs):
        self.fake.calls.append(('put_object', kwargs))
        assert kwargs['ExpectedBucketOwner'] == ACCOUNT
        assert kwargs['IfNoneMatch'] == '*'
        assert kwargs['Key'].startswith('releases/')
        self.fake.puts += 1
        if self.fake.partial_put and self.fake.puts == 2:
            raise OSError('upload failed before write')
        if kwargs['Key'] in self.fake.objects:
            raise RuntimeError('conditional conflict')
        self.fake.objects[kwargs['Key']] = kwargs['Body']
        if self.fake.lost_put_ack:
            raise OSError('response lost after upload')
        return {}


class FakeCloudFront:
    def __init__(self, fake):
        self.fake = fake
    def get_distribution(self, **kwargs):
        self.fake.calls.append(('get_distribution', kwargs))
        assert kwargs['Id'] == DISTRIBUTION
        return {'ETag': self.fake.etag, 'Distribution': {'Id': DISTRIBUTION,
            'ARN': 'arn:aws:cloudfront::' + self.fake.distribution_account + ':distribution/' + DISTRIBUTION,
            'DomainName': 'example.cloudfront.net', 'Status': self.fake.status,
            'DistributionConfig': deepcopy(self.fake.config)}}
    def update_distribution(self, **kwargs):
        self.fake.calls.append(('update_distribution', kwargs))
        assert kwargs['Id'] == DISTRIBUTION
        assert kwargs['IfMatch'] == self.fake.etag
        assert config_sha256(kwargs['DistributionConfig'], 'exact-origin') == config_sha256(self.fake.config, 'exact-origin')
        if self.fake.reject_switch:
            raise OSError('lost acknowledgement before switch')
        self.fake.config = deepcopy(kwargs['DistributionConfig'])
        self.fake.etag = 'new-etag'
        if self.fake.propagating:
            self.fake.status = 'InProgress'
        if self.fake.unknown_switch_ack:
            raise OSError('lost acknowledgement after switch')
        return self.get_distribution(Id=DISTRIBUTION)
    def list_invalidations(self, **kwargs):
        self.fake.calls.append(('list_invalidations', kwargs))
        assert kwargs['DistributionId'] == DISTRIBUTION
        return {'InvalidationList': {'IsTruncated': False, 'Items': [{'Id': key} for key in self.fake.invalidations]}}
    def get_invalidation(self, **kwargs):
        self.fake.calls.append(('get_invalidation', kwargs))
        return {'Invalidation': deepcopy(self.fake.invalidations[kwargs['Id']])}
    def create_invalidation(self, **kwargs):
        self.fake.calls.append(('create_invalidation', kwargs))
        assert kwargs['DistributionId'] == DISTRIBUTION
        batch = kwargs['InvalidationBatch']
        assert not any('*' in p for p in batch['Paths']['Items'])
        assert batch['Paths']['Quantity'] == len(batch['Paths']['Items'])
        existing = next((v for v in self.fake.invalidations.values() if v['InvalidationBatch']['CallerReference'] == batch['CallerReference']), None)
        if existing:
            assert existing['InvalidationBatch'] == batch
            return {'Invalidation': deepcopy(existing)}
        invalidation = {'Id': 'I' + str(len(self.fake.invalidations) + 1), 'Status': 'InProgress' if self.fake.invalidation_pending else 'Completed', 'InvalidationBatch': deepcopy(batch)}
        self.fake.invalidations[invalidation['Id']] = invalidation
        if self.fake.unknown_invalidation_ack:
            raise OSError('lost invalidation acknowledgement')
        return {'Invalidation': invalidation}


class FakeAWS:
    def __init__(self):
        self.calls, self.objects, self.invalidations = [], {}, {}
        self.account = self.distribution_account = ACCOUNT
        self.config = {'Enabled': True, 'CallerReference': 'original', 'DefaultRootObject': 'index.html',
            'Origins': {'Quantity': 1, 'Items': [{'Id': 'exact-origin', 'DomainName': 'hp-exact-bucket.s3.ap-northeast-1.amazonaws.com', 'OriginPath': '', 'S3OriginConfig': {'OriginAccessIdentity': ''}}]},
            'Aliases': {'Quantity': 1, 'Items': ['preview.example.invalid']},
            'DefaultCacheBehavior': {'TargetOriginId': 'exact-origin', 'ViewerProtocolPolicy': 'redirect-to-https'}}
        self.etag, self.status = 'original-etag', 'Deployed'
        self.partial_put = self.lost_put_ack = self.reject_switch = self.unknown_switch_ack = False
        self.propagating = self.invalidation_pending = self.unknown_invalidation_ack = False
        self.live_tamper = None
        self.cached_retired = {}
        self.puts = 0
    def clients(self, role, session_name):
        self.calls.append(('assume_role', {'role': role, 'session_name': session_name}))
        assert role == ROLE
        return {'sts': FakeSTS(self), 's3': FakeS3(self), 'cloudfront': FakeCloudFront(self)}
    def fetch(self, url, limit):
        self.calls.append(('fetch', {'url': url, 'limit': limit}))
        parsed = urllib.parse.urlsplit(url)
        assert parsed.hostname == 'preview.example.invalid'
        path = urllib.parse.unquote(parsed.path).lstrip('/')
        if path in self.cached_retired:
            return self.cached_retired[path]
        prefix = self.config['Origins']['Items'][0]['OriginPath'].lstrip('/')
        if prefix + '/' + path not in self.objects:
            raise ServedNotFound('actual HTTP 404')
        value = self.objects[prefix + '/' + path]
        if self.live_tamper == path:
            return b'bad'
        return value


class PublisherTest(unittest.TestCase):
    def setUp(self):
        self.fake, self.store = FakeAWS(), MemoryStore()
        self.data = artifact()
        self.preview = {'source_commit': COMMIT, 'artifact_sha256': sha256(self.data), 'validation': {'package_operation_id': PACKAGE}}
        target = {'bucket': 'hp-exact-bucket', 'distribution_id': DISTRIBUTION, 'origin_id': 'exact-origin', 'expected_config_sha256': config_sha256(self.fake.config, 'exact-origin'), 'initial_file_paths': ['index.html', 'style.css', 'version.json']}
        self.site = {'site_id': 'sample-site', 'dev_url': 'https://preview.example.invalid', 'prod_url': 'https://preview.example.invalid', 'deployment': {'dev': target, 'prod': deepcopy(target)}}
        self.publisher = SitePublisher('dev', ROLE, self.store, clients_factory=self.fake.clients, fetch=self.fake.fetch)
        self.guards = 0
    def guard(self):
        self.guards += 1
    def publish(self, fence=1):
        return self.publisher.publish(self.site, self.preview, self.data, OPERATION, fence, self.guard)
    def reconcile(self, fence=1):
        old_rows = deepcopy(self.store.rows)
        old_calls = len(self.fake.calls)
        try:
            return self.publisher.reconcile(self.site, self.preview, OPERATION, fence, self.guard)
        finally:
            self.assertEqual(self.store.rows, old_rows)
            self.assertFalse(any(method in {'put_object', 'update_distribution', 'create_invalidation'} for method, _ in self.fake.calls[old_calls:]))

    def test_success_stages_only_immutable_prefix_and_reads_all_files(self):
        receipt = self.publish()
        self.assertTrue(receipt['verified'])
        self.assertEqual(receipt['artifact_sha256'], sha256(self.data))
        self.assertFalse(receipt['edge_rollout_atomic'])
        self.assertGreater(self.guards, len(self.fake.calls) - 5)
        prefix = 'releases/' + sha256(self.data)
        self.assertEqual(set(self.fake.objects), {prefix + '/index.html', prefix + '/style.css', prefix + '/version.json'})
        update = [kwargs for method, kwargs in self.fake.calls if method == 'update_distribution'][0]
        self.assertEqual(update['IfMatch'], 'original-etag')
        self.assertEqual(update['DistributionConfig']['Origins']['Items'][0]['OriginPath'], '/' + prefix)
        self.assertTrue(self.reconcile()['verified'])
        proof = {'source_commit': COMMIT, 'artifact_sha256': sha256(self.data), 'package_operation_id': PACKAGE}
        before = deepcopy(self.store.rows)
        self.assertTrue(self.publisher.readback(self.site, proof, self.guard)['verified'])
        self.assertEqual(before, self.store.rows)

    def test_missing_role_wrong_account_and_wrong_target_fail_closed(self):
        publisher = SitePublisher('dev', None, self.store, clients_factory=self.fake.clients)
        with self.assertRaises(IntegrationUnavailable):
            publisher.publish(self.site, self.preview, self.data, OPERATION, 1, self.guard)
        for field in ('account', 'distribution_account'):
            with self.subTest(field=field):
                setattr(self.fake, field, '000000000000')
                with self.assertRaises(PublicationRejected):
                    self.publish()
                setattr(self.fake, field, ACCOUNT)
        self.assertFalse(any(method in ('put_object', 'update_distribution') for method, _ in self.fake.calls))
        self.site['deployment']['dev']['bucket'] = 'other-bucket'
        with self.assertRaises(PublicationRejected):
            self.publish()

    def test_tampered_artifact_and_version_rejected_before_aws(self):
        self.data += b'tamper'
        with self.assertRaises(PublicationRejected):
            self.publish()
        self.assertFalse(self.fake.calls)
        self.data = artifact(metadata_update={'source_sha256': 'f' * 64})
        self.preview['artifact_sha256'] = sha256(self.data)
        with self.assertRaises(PublicationRejected):
            self.publish()
        self.assertFalse(self.fake.calls)
        self.data = artifact(source={'index.html': b'x', '../outside.js': b'x'})
        self.preview['artifact_sha256'] = sha256(self.data)
        with self.assertRaises(PublicationRejected):
            self.publish()

    def test_partial_upload_resume_preserves_frozen_switch_and_fence(self):
        self.fake.partial_put = True
        with self.assertRaises(Exception):
            self.publish()
        self.assertFalse(any(method == 'update_distribution' for method, _ in self.fake.calls))
        self.assertEqual(self.reconcile(), {'safe_to_resume': True})
        original = next(iter(self.store.rows.values()))
        frozen_config = deepcopy(original['original_config'])
        self.fake.partial_put = False
        result = self.publish(fence=2)
        self.assertTrue(result['verified'])
        row = self.store.get('publication-intent:sample-site:dev:' + OPERATION)
        self.assertEqual(row['fence'], 2)
        self.assertEqual(row['original_config'], frozen_config)
        self.assertEqual(row['original_etag'], 'original-etag')
        self.assertEqual(self.fake.puts, 4)

    def test_lost_upload_ack_reconciles_exact_immutable_bytes(self):
        self.fake.lost_put_ack = True
        self.assertTrue(self.publish()['verified'])

    def test_unexpected_config_drift_never_updates_distribution(self):
        self.fake.config['Enabled'] = False
        with self.assertRaises(PublicationRejected):
            self.publish()
        self.assertFalse(any(method in ('put_object', 'update_distribution') for method, _ in self.fake.calls))

    def test_unknown_update_ack_reconcile_does_not_reissue(self):
        self.fake.unknown_switch_ack = True
        with self.assertRaises(PublicationPending):
            self.publish()
        observed = self.reconcile()
        self.assertTrue(observed['safe_to_resume'])
        self.assertTrue(observed['cache_cleanup_requires_attention'])
        self.assertEqual(observed['observed_release_prefix'], 'releases/' + sha256(self.data))
        self.fake.unknown_switch_ack = False
        self.assertTrue(self.publish(fence=2)['verified'])
        self.assertEqual(sum(method == 'update_distribution' for method, _ in self.fake.calls), 1)

    def test_unknown_update_not_accepted_proves_original_etag_before_retry(self):
        self.fake.reject_switch = True
        with self.assertRaises(PublicationPending):
            self.publish()
        self.assertEqual(self.reconcile(), {'safe_to_resume': True})
        self.fake.reject_switch = False
        self.assertTrue(self.publish(fence=2)['verified'])
        self.assertEqual(sum(method == 'update_distribution' for method, _ in self.fake.calls), 2)

    def test_unknown_invalidation_ack_readonly_reconcile_finds_same_request(self):
        self.fake.unknown_invalidation_ack = True
        with self.assertRaises(PublicationPending):
            self.publish()
        self.assertTrue(self.reconcile()['verified'])
        self.assertEqual(sum(method == 'create_invalidation' for method, _ in self.fake.calls), 1)

    def test_propagation_and_invalidation_are_pending_not_success(self):
        self.fake.propagating = True
        with self.assertRaises(PublicationPending) as caught:
            self.publish()
        self.assertTrue(caught.exception.wait_required)
        self.assertGreater(caught.exception.deadline, 0)
        with self.assertRaises(PublicationPending):
            self.reconcile()
        self.fake.status, self.fake.propagating = 'Deployed', False
        self.fake.invalidation_pending = True
        with self.assertRaises(PublicationPending):
            self.publish(fence=2)
        with self.assertRaises(PublicationPending):
            self.reconcile(fence=2)

    def test_partial_live_bytes_and_immutable_object_tamper_never_verified(self):
        self.fake.live_tamper = 'style.css'
        with self.assertRaises(PublicationPending):
            self.publish()
        with self.assertRaises(PublicationPending):
            self.reconcile()
        self.fake.live_tamper = None
        self.fake.objects['releases/' + sha256(self.data) + '/index.html'] = b'wrong'
        with self.assertRaises(PublicationRejected):
            self.reconcile()

    def test_readonly_reconcile_absent_and_wrong_fence(self):
        self.assertEqual(self.reconcile(), {'safe_to_resume': True, 'prewrite_proven': True})
        self.publish()
        with self.assertRaises(PublicationRejected):
            self.reconcile(fence=2)

    def test_revocation_immediately_before_switch_never_calls_update(self):
        def revoked_guard():
            row = self.store.get('publication-intent:sample-site:dev:' + OPERATION)
            if row and row.get('phase') == 'switching':
                raise Rejected('membership_revoked')
        with self.assertRaisesRegex(Rejected, 'membership_revoked'):
            self.publisher.publish(self.site, self.preview, self.data, OPERATION, 1, revoked_guard)
        self.assertFalse(any(method == 'update_distribution' for method, _ in self.fake.calls))
        self.assertEqual(self.reconcile(), {'safe_to_resume': True})

    def test_directory_index_invalidation_covers_viewer_aliases_without_wildcards(self):
        self.data = artifact(source={'index.html': b'home', 'about/index.html': b'about'})
        self.preview['artifact_sha256'] = sha256(self.data)
        self.publish()
        batch = next(iter(self.fake.invalidations.values()))['InvalidationBatch']
        self.assertEqual(batch['Paths']['Items'], ['/', '/about', '/about/', '/about/index.html', '/index.html', '/style.css', '/version.json'])

    def test_removed_legacy_asset_requires_actual_404_after_invalidation(self):
        self.site['deployment']['dev']['initial_file_paths'].append('old photo.png')
        self.fake.cached_retired['old photo.png'] = b'old cache'
        with self.assertRaisesRegex(PublicationPending, 'retired_path_still_served'):
            self.publish()
        batch = next(iter(self.fake.invalidations.values()))['InvalidationBatch']
        self.assertIn('/old%20photo.png', batch['Paths']['Items'])
        self.fake.cached_retired.clear()
        self.assertTrue(self.reconcile()['verified'])
        self.assertTrue(any(method == 'fetch' and '/old%20photo.png?' in values['url'] for method, values in self.fake.calls))

    def test_prior_release_manifest_is_required_and_removed_asset_union_is_preserved(self):
        self.publish()
        prior_artifact = self.preview['artifact_sha256']
        next_operation = '45678901-1234-4234-8234-123456789abc'
        self.data = artifact(source={'index.html': b'new home'})
        self.preview['artifact_sha256'] = sha256(self.data)
        self.assertTrue(self.publisher.publish(self.site, self.preview, self.data, next_operation, 2, self.guard)['verified'])
        batches = list(self.fake.invalidations.values())
        self.assertIn('/style.css', batches[-1]['InvalidationBatch']['Paths']['Items'])
        prior_pointer = 'publication-artifact:sample-site:dev:' + prior_artifact
        self.fake.config['Origins']['Items'][0]['OriginPath'] = '/releases/' + prior_artifact
        self.store.rows.pop(prior_pointer)
        with self.assertRaisesRegex(PublicationRejected, 'previous_release_manifest_required'):
            self.publisher.publish(self.site, self.preview, self.data, '56789012-1234-4234-8234-123456789abc', 3, self.guard)

    def test_legacy_manifest_absence_fails_before_any_object_write(self):
        self.site['deployment']['dev'].pop('initial_file_paths')
        with self.assertRaisesRegex(PublicationRejected, 'previous_release_manifest_required'):
            self.publish()
        self.assertFalse(any(method in ('put_object', 'update_distribution', 'create_invalidation') for method, _ in self.fake.calls))

    def test_preflight_is_readonly_and_checks_actual_role_bucket_and_config(self):
        before = deepcopy(self.store.rows)
        self.assertTrue(self.publisher.preflight(self.site, self.guard)['ready'])
        self.assertEqual(before, self.store.rows)
        self.assertFalse(any(method in ('put_object', 'update_distribution', 'create_invalidation') for method, _ in self.fake.calls))
        self.assertTrue(any(method == 'head_bucket' for method, _ in self.fake.calls))
        self.fake.config['Enabled'] = False
        with self.assertRaisesRegex(PublicationRejected, 'cloudfront_unexpected_config_drift'):
            self.publisher.preflight(self.site, self.guard)

    def test_preflight_missing_binding_fails_before_provider_effects(self):
        self.site['deployment'].pop('dev')
        with self.assertRaisesRegex(PublicationRejected, 'deployment_binding_required'):
            self.publisher.preflight(self.site, self.guard)
        self.assertEqual(self.fake.calls, [])

    def test_candidate_intent_record_budget_rejected_before_any_write(self):
        source = {'index.html': b'home'}
        source.update({str(index) + '-' + '\u3042' * 180 + '.txt': b'x' for index in range(300)})
        self.data = artifact(source=source)
        self.preview['artifact_sha256'] = sha256(self.data)
        with self.assertRaisesRegex(PublicationRejected, 'publication_intent_record_budget_exceeded'):
            self.publish()
        self.assertEqual(self.store.rows, {})
        self.assertFalse(any(method in ('put_object', 'update_distribution', 'create_invalidation') for method, _ in self.fake.calls))

    def test_preflight_known_config_record_budget_rejected_readonly(self):
        self.fake.config['Comment'] = 'x' * 160000
        self.site['deployment']['dev']['expected_config_sha256'] = config_sha256(self.fake.config, 'exact-origin')
        with self.assertRaisesRegex(PublicationRejected, 'publication_intent_record_budget_exceeded'):
            self.publisher.preflight(self.site, self.guard)
        self.assertEqual(self.store.rows, {})


if __name__ == '__main__':
    unittest.main()
