"""Authorized last-successful deployment timestamps, including older records."""
from copy import deepcopy
import unittest
from uuid import uuid4

from service import Service, Rejected
from store import MemoryStore


class DeploymentStatusTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.service = Service(self.store)
        self.claims = {'sub': 'reader', 'scope': 'hp:read'}
        self.store.put('principal:reader', {'sites': {'clinic': ['read']}})
        self.preview_id = str(uuid4())
        self.preview_op = str(uuid4())
        self.publish_op = str(uuid4())
        self.site = {'name': 'Clinic', 'config_version': 1,
                     'dev_url': 'https://dev.example.invalid', 'prod_url': 'https://prod.example.invalid',
                     'current_preview': self.preview_id,
                     'current_publication': {'operation_id': self.publish_op, 'receipt': {'verified': True}}}
        self.store.put('site:clinic', self.site)
        self.store.put('preview:' + self.preview_id, {'site_id': 'clinic', 'status': 'verified',
            'operation_id': self.preview_op})
        for operation, kind, timestamp in [(self.preview_op, 'submit_preview', 1000), (self.publish_op, 'publish', 2000)]:
            self.store.put('operation:' + operation, {'site_id': 'clinic', 'kind': kind,
                'status': 'completed', 'completed_at': timestamp, 'subject': 'another-editor',
                'created_at': timestamp - 100, 'input': {'private': 'do-not-export'}})

    def patch(self, key, **fields):
        row = self.store.get(key)
        self.store.put(key, {**row, **fields}, row['_version'])

    def test_reads_existing_completed_operations_without_mutation(self):
        before = deepcopy(self.store.rows)
        sites = self.service.list_sites(self.claims)
        self.assertEqual(sites[0]['deployments'], {
            'dev': {'updated_at': 1000, 'version': None, 'url': self.site['dev_url']},
            'production': {'updated_at': 2000, 'version': None, 'url': self.site['prod_url']}})
        self.assertEqual(self.store.rows, before)
        self.assertNotIn('do-not-export', str(sites))
        self.assertNotIn('another-editor', str(sites))

    def test_last_verified_dev_date_remains_while_new_preview_is_preparing(self):
        self.patch('site:clinic', current_preview=None, last_verified_preview=self.preview_id)
        self.assertEqual(self.service.list_sites(self.claims)[0]['deployments']['dev']['updated_at'], 1000)

    def test_does_not_use_admission_time_or_unfinished_operations(self):
        self.patch('operation:' + self.preview_op, status='running')
        self.patch('operation:' + self.publish_op, completed_at=None)
        status = self.service.list_sites(self.claims)[0]['deployments']
        self.assertIsNone(status['dev']['updated_at'])
        self.assertIsNone(status['production']['updated_at'])

    def test_uses_verified_record_timestamp_for_new_deployments(self):
        self.patch('preview:' + self.preview_id, updated_at=3000)
        self.patch('site:clinic', current_publication={'updated_at': 4000, 'receipt': {'verified': True}})
        status = self.service.list_sites(self.claims)[0]['deployments']
        self.assertEqual(status['dev']['updated_at'], 3000)
        self.assertEqual(status['production']['updated_at'], 4000)

    def test_invalid_or_foreign_records_do_not_supply_a_date(self):
        self.patch('preview:' + self.preview_id, site_id='other-site', updated_at=9999)
        self.patch('operation:' + self.publish_op, site_id='other-site')
        status = self.service.list_sites(self.claims)[0]['deployments']
        self.assertIsNone(status['dev']['updated_at'])
        self.assertIsNone(status['production']['updated_at'])
        self.patch('site:clinic', current_publication={'updated_at': True, 'receipt': {'verified': False}})
        self.assertIsNone(self.service.list_sites(self.claims)[0]['deployments']['production']['updated_at'])

    def test_revoked_site_is_excluded(self):
        self.patch('principal:reader', sites={})
        with self.assertRaisesRegex(Rejected, 'access_revoked'):
            self.service.list_sites(self.claims)

    def test_versions_are_artifact_bound_and_shared_across_environments(self):
        self.patch('preview:' + self.preview_id, artifact_sha256='a'*64)
        publication = {**self.site['current_publication'], 'artifact_sha256': 'a'*64}
        self.patch('site:clinic', current_publication=publication)
        self.store.put('content-version:clinic:'+'a'*64, {'version': 12})
        status = self.service.list_sites(self.claims)[0]['deployments']
        self.assertEqual(status['dev']['version'], 12)
        self.assertEqual(status['production']['version'], 12)
        self.patch('preview:' + self.preview_id, artifact_sha256='b'*64)
        self.store.put('content-version:clinic:'+'b'*64, {'version': 13})
        status = self.service.list_sites(self.claims)[0]['deployments']
        self.assertEqual(status['dev']['version'], 13)
        self.assertEqual(status['production']['version'], 12)
        self.patch('preview:' + self.preview_id, site_id='foreign')
        self.assertIsNone(self.service.list_sites(self.claims)[0]['deployments']['dev']['version'])
        self.patch('content-version:clinic:'+'a'*64, version=True)
        self.assertIsNone(self.service.list_sites(self.claims)[0]['deployments']['production']['version'])
