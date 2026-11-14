import copy
import io
import json
import time
import unittest
import zipfile

import test_provision_site as provision_tests
from activation_template import hosting_template
from bundles import sha256
from service import Service
from site_activation import ActivationWaiting, ImportRejected, enqueue_writes, read_import, run_one
from site_copy import copy_public_site, intake_copy_key
from store import MemoryStore

SUB = 'sub_activation12345'


class Repositories:
    def __init__(self, site): self.site, self.calls = site, 0
    def ensure(self, job, files, guard):
        guard(); self.calls += 1
        self.files = copy.deepcopy(files)
        return {k: v for k, v in self.site.items() if k.startswith('github_') or k in ('validation_workflow_id', 'initial_main_commit')}
    def verify(self, site, files, guard):
        guard()
        if files != self.files: raise ActivationWaiting('import_mismatch')


class Hosting:
    def __init__(self, site): self.site, self.wait, self.on_verify = site, False, None
    def ensure(self, job, dns, guard):
        guard()
        if self.wait: raise ActivationWaiting('creating')
        return {k: self.site[k] for k in ('dev_url', 'prod_url', 'deployment')} | {
            'publisher_roles': {'dev': 'arn:aws:iam::209300895845:role/clinic-dev',
                                'prod': 'arn:aws:iam::209300895845:role/clinic-prod'}}
    def verify(self, site, job, dns, guard):
        if self.on_verify: self.on_verify()
        guard()
    def cutover_plan(self, site, dns, guard):
        guard()
        return {'site_id': site['site_id'], 'host': 'clinic.example.jp.', 'status': 'prepared'}


class ActivationTest(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore(); self.now = int(time.time())
        self.data, manifest = copy_public_site('clinic.example.jp', fetch=lambda url: (200, {'content-type': 'text/html'},
            b'<html><h1>Example Clinic</h1></html>'))
        self.intake = {'subscription_id': SUB, 'subject': 'buyer', 'email': 'owner@example.test',
            'host': 'clinic.example.jp', 'status': 'received', 'auth_code': 'sealed',
            'copy_state': 'done', 'copy_key': intake_copy_key(SUB, self.data)}
        self.store.put('clinic-intake:' + SUB, self.intake)
        self.store.put('stripe-subscription:' + SUB, {'status': 'active', 'subject': 'buyer', 'plan': 'basic'})
        self.store.put('clinic-transfer:' + SUB, {'status': 'complete', 'subject': 'buyer', 'domain': 'example.jp'})
        self.store.put('dns-connection:' + SUB, {'status': 'verified', 'subject': 'buyer', 'host': 'clinic.example.jp',
            'domain': 'example.jp', 'hosted_zone_id': 'ZEXAMPLE', 'nameservers': []})
        self.store.transact(enqueue_writes(self.store, self.intake))
        self.site = provision_tests.ProvisionTest().site()
        self.site['prod_url'] = 'https://clinic.example.jp'
        self.repo, self.hosting = Repositories(self.site), Hosting(self.site)
        self.platform = {k: self.site[k] for k in ('drive_workspace_folder_id', 'drive_changes_folder_id',
                                                   'sheet_id', 'operator_subject', 'operator_email')}

    def tick(self):
        self.now += 61
        return run_one(self.store, lambda key: self.data, self.repo, self.hosting, self.platform, lambda: self.now)

    def test_complete_import_and_resources_grant_paid_owner_without_operator_seed(self):
        self.tick(); self.tick(); self.tick()
        job = self.store.get('clinic-activation:' + SUB)
        self.assertEqual(job['status'], 'ready')
        self.assertNotIn('queue_state', job)
        self.assertEqual(self.repo.calls, 1)
        member = self.store.get('principal:buyer')
        self.assertEqual(member['sites'][job['site_id']], ['read', 'edit', 'publish'])
        self.assertEqual(self.store.get('clinic-intake:' + SUB)['status'], 'claimed')
        service = Service(self.store)
        visible = service.list_sites({'sub': 'buyer', 'scope': 'hp:read hp:write'})
        self.assertEqual(visible[0]['site_id'], job['site_id'])
        self.assertIsNone(self.store.get('operation:publish'))
        self.assertEqual(self.store.get('dns-cutover:' + job['site_id'])['status'], 'prepared')

    def test_provider_wait_does_not_recreate_repository_or_grant_access_early(self):
        self.tick(); self.hosting.wait = True; self.tick(); self.tick()
        self.assertEqual(self.repo.calls, 1)
        self.assertIsNone(self.store.get('principal:buyer'))
        self.hosting.wait = False; self.tick(); self.tick()
        self.assertEqual(self.store.get('clinic-activation:' + SUB)['status'], 'ready')

    def test_transfer_or_buyer_mismatch_prevents_resource_creation(self):
        transfer = self.store.get('clinic-transfer:' + SUB)
        self.store.put('clinic-transfer:' + SUB, {**transfer, 'status': 'transferring'}, transfer['_version'])
        self.tick()
        self.assertEqual(self.repo.calls, 0)

    def test_cancellation_during_final_verification_prevents_site_grant(self):
        self.tick(); self.tick()
        def cancel():
            row = self.store.get('stripe-subscription:' + SUB)
            self.store.put('stripe-subscription:' + SUB, {**row, 'status': 'canceled'}, row['_version'])
        self.hosting.on_verify = cancel; self.tick()
        self.assertIsNone(self.store.get('principal:buyer'))
        self.assertNotEqual(self.store.get('clinic-activation:' + SUB)['status'], 'ready')

    def test_source_or_dns_change_after_first_effect_is_not_overwritten(self):
        self.tick()
        dns = self.store.get('dns-connection:' + SUB)
        self.store.put('dns-connection:' + SUB, {**dns, 'hosted_zone_id': 'ZOTHER'}, dns['_version'])
        self.tick(); self.tick()
        self.assertIsNone(self.store.get('principal:buyer'))

    def test_activation_jobs_do_not_enter_the_existing_command_dispatcher(self):
        self.assertEqual(self.store.pending(25, now=self.now), [])
        self.assertEqual(len(self.store.pending(25, now=self.now, queue_state='clinic_activation')), 1)

    def test_corrupt_partial_or_forged_copy_is_rejected(self):
        with self.assertRaises(ImportRejected): read_import(self.data + b'corrupt', self.intake)
        with zipfile.ZipFile(io.BytesIO(self.data)) as original:
            manifest = json.loads(original.read('manifest.json'))
            content = original.read('site/index.html')
        for change in ({'truncated': True}, {'missing': ['https://clinic.example.jp/failed.css']}, {'host': 'another.example.jp'}):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, 'w') as archive:
                archive.writestr('site/index.html', content)
                archive.writestr('manifest.json', json.dumps({**manifest, **change}))
            data = buf.getvalue()
            with self.assertRaises(ImportRejected): read_import(data, {**self.intake, 'copy_key': intake_copy_key(SUB, data)})


class TemplateTest(unittest.TestCase):
    def test_private_isolated_targets_and_no_early_web_dns_switch(self):
        dns = {'host': 'clinic.example.jp', 'domain': 'example.jp', 'hosted_zone_id': 'ZEXAMPLE', 'status': 'verified'}
        template = hosting_template('hp-clinic-' + 'a' * 20, 'clinic.example.jp', dns,
            consumer_role_arn='arn:aws:iam::209300895845:role/hp-control-consumer',
            permissions_boundary_arn='arn:aws:iam::209300895845:policy/hp-control-boundary')
        self.assertFalse(any(r['Type'] == 'AWS::Route53::RecordSet' for r in template['Resources'].values()))
        for name in ('DevBucket', 'ProdBucket'):
            self.assertTrue(template['Resources'][name]['Properties']['PublicAccessBlockConfiguration']['BlockPublicPolicy'])
        role = template['Resources']['ProdPublisher']['Properties']
        self.assertTrue(role['PermissionsBoundary'].endswith('hp-control-boundary'))
        dns_write = role['Policies'][0]['PolicyDocument']['Statement'][-1]
        self.assertEqual(dns_write['Resource'], 'arn:aws:route53:::hostedzone/ZEXAMPLE')


if __name__ == '__main__': unittest.main()
