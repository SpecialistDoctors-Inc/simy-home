import copy
import unittest

from dns_cutover import DNSCutover
from publisher import PublicationRejected
from store import MemoryStore


class DNS:
    def __init__(self, records):
        self.values, self.writes, self.lose_response = copy.deepcopy(records), [], False

    def list_resource_record_sets(self, **params):
        return {'ResourceRecordSets': self.values, 'IsTruncated': False}

    def change_resource_record_sets(self, **params):
        self.writes.append(params)
        for change in params['ChangeBatch']['Changes']:
            if change['Action'] == 'DELETE': self.values.remove(change['ResourceRecordSet'])
            else: self.values.append(copy.deepcopy(change['ResourceRecordSet']))
        if self.lose_response: raise TimeoutError()
        return {'ChangeInfo': {'Id': 'change-id', 'Status': 'PENDING'}}


class DNSCutoverTest(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.before = [{'Name': 'clinic.example.jp.', 'Type': 'A', 'TTL': 300,
                        'ResourceRecords': [{'Value': '192.0.2.10'}]}]
        self.mail = {'Name': 'example.jp.', 'Type': 'MX', 'TTL': 300,
                     'ResourceRecords': [{'Value': '10 mail.example.test.'}]}
        self.dns = DNS(self.before + [self.mail])
        self.store.put('dns-cutover:clinic-test', {'site_id': 'clinic-test', 'host': 'clinic.example.jp.',
            'distribution_id': 'ECUSTOMER', 'zone_id': 'ZEXAMPLE', 'target': 'd123example.cloudfront.net',
            'before': self.before, 'status': 'prepared'})
        self.cutover = DNSCutover(self.store, lambda binding, guard: self.dns)
        self.binding = {'site_id': 'clinic-test', 'environment': 'prod', 'url': 'https://clinic.example.jp',
                        'target': {'distribution_id': 'ECUSTOMER'}}

    def test_switches_only_web_records_and_reuses_lost_response(self):
        self.dns.lose_response = True
        self.cutover.ensure(self.binding, 'operation-one', lambda: None)
        self.assertIn(self.mail, self.dns.values)
        self.assertEqual(len(self.dns.writes), 1)
        self.cutover.ensure(self.binding, 'operation-one', lambda: None)
        self.assertEqual(len(self.dns.writes), 1)
        self.assertTrue(self.cutover.observed(self.binding, lambda: None))

    def test_revoked_authority_never_writes_dns(self):
        def denied(): raise PermissionError('revoked')
        with self.assertRaises(PermissionError): self.cutover.ensure(self.binding, 'operation-one', denied)
        self.assertEqual(self.dns.writes, [])

    def test_existing_dns_edits_are_not_overwritten(self):
        self.dns.values[0]['ResourceRecords'][0]['Value'] = '192.0.2.99'
        with self.assertRaises(PublicationRejected): self.cutover.ensure(self.binding, 'operation-one', lambda: None)
        self.assertEqual(self.dns.writes, [])

    def test_read_only_reconciliation_does_not_perform_cutover(self):
        self.assertFalse(self.cutover.observed(self.binding, lambda: None))
        self.assertEqual(self.dns.writes, [])
        self.assertEqual(self.store.get('dns-cutover:clinic-test')['status'], 'prepared')

    def test_preview_never_changes_production_dns(self):
        self.cutover.ensure({**self.binding, 'environment': 'dev'}, 'operation', lambda: None)
        self.assertEqual(self.dns.writes, [])

    def test_another_distribution_cannot_use_a_site_dns_plan(self):
        with self.assertRaises(PublicationRejected):
            self.cutover.ensure({**self.binding, 'target': {'distribution_id': 'EOTHER'}}, 'operation', lambda: None)

    def test_manual_rollback_after_cutover_is_not_silently_overwritten(self):
        self.cutover.ensure(self.binding, 'operation-one', lambda: None)
        self.dns.values = copy.deepcopy(self.before + [self.mail])
        with self.assertRaises(PublicationRejected): self.cutover.ensure(self.binding, 'operation-two', lambda: None)
        self.assertEqual(len(self.dns.writes), 1)


if __name__ == '__main__': unittest.main()
