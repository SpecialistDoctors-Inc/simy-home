"""Web-only DNS switching, invoked only inside an authorized publication."""
from urllib.parse import urlsplit

from publisher import PublicationPending, PublicationRejected

CF_ZONE = 'Z2FDTNDATAQYW2'


class DNSCutover:
    def __init__(self, store, client_factory):
        self.store, self.client_factory = store, client_factory

    def plan(self, binding):
        if binding['environment'] != 'prod':
            return None
        row = self.store.get('dns-cutover:' + binding['site_id'])
        if row and (row.get('site_id') != binding['site_id']
                or row.get('host', '').rstrip('.').lower() != urlsplit(binding['url']).hostname
                or row.get('distribution_id') != binding['target']['distribution_id']):
            raise PublicationRejected('dns_publication_binding_mismatch')
        return row

    @staticmethod
    def desired(row):
        return [{'Name': row['host'], 'Type': t, 'AliasTarget': {
                    'HostedZoneId': CF_ZONE, 'DNSName': row['target'], 'EvaluateTargetHealth': False}}
                for t in ('A', 'AAAA')]

    @staticmethod
    def records(client, row, guard):
        guard()
        result = client.list_resource_record_sets(HostedZoneId=row['zone_id'], StartRecordName=row['host'], MaxItems='100')
        if result.get('IsTruncated') and result.get('NextRecordName', '').lower() == row['host'].lower():
            raise PublicationRejected('dns_inventory_incomplete')
        return [r for r in result['ResourceRecordSets'] if r['Name'].lower() == row['host'].lower()
                and r['Type'] in ('A', 'AAAA', 'CNAME')]

    @staticmethod
    def equivalent(a, b):
        def normalized(r):
            r = dict(r); r['Name'] = r['Name'].rstrip('.').lower()
            if 'AliasTarget' in r:
                r['AliasTarget'] = {**r['AliasTarget'], 'DNSName': r['AliasTarget']['DNSName'].rstrip('.').lower()}
            return r
        return sorted([normalized(r) for r in a], key=lambda r: r['Type']) == sorted([normalized(r) for r in b], key=lambda r: r['Type'])

    def observed(self, binding, guard):
        row = self.plan(binding)
        if not row:
            return True
        client = self.client_factory(binding, guard)
        return self.equivalent(self.records(client, row, guard), self.desired(row))

    def wait_seconds(self, binding):
        row = self.plan(binding)
        if not row:
            return 3600
        ttl = max((r.get('TTL', 0) for r in row['before']), default=0)
        if type(ttl) is not int or not 0 <= ttl <= 86400:
            raise PublicationRejected('dns_ttl_preparation_required')
        return max(3600, ttl + 7200)

    def ensure(self, binding, operation_id, guard):
        row = self.plan(binding)
        if not row:
            return
        client = self.client_factory(binding, guard)
        current, desired = self.records(client, row, guard), self.desired(row)
        if self.equivalent(current, desired):
            if row.get('status') == 'prepared':
                guard()
                self.store.put('dns-cutover:' + binding['site_id'], {**row, 'status': 'observed'}, row['_version'])
            return  # Includes a lost response to our atomic DELETE+CREATE batch.
        if (row.get('status') not in ('prepared', 'changing') or
                (row.get('status') == 'changing' and row.get('operation_id') != operation_id)
                or not self.equivalent(current, row['before'])):
            raise PublicationRejected('dns_changed_since_connection')
        changes = ([{'Action': 'DELETE', 'ResourceRecordSet': r} for r in row['before']]
                   + [{'Action': 'CREATE', 'ResourceRecordSet': r} for r in desired])
        # DELETE requires exact old values; concurrent DNS edits reject the whole
        # transaction instead of being overwritten by an unconditional UPSERT.
        guard()
        if row['status'] == 'prepared':
            row = self.store.put('dns-cutover:' + binding['site_id'],
                {**row, 'status': 'changing', 'operation_id': operation_id}, row['_version'])
        guard()
        try:
            client.change_resource_record_sets(HostedZoneId=row['zone_id'], ChangeBatch={
                'Comment': 'SIMY approved publication ' + operation_id, 'Changes': changes})
        except Exception:
            if self.equivalent(self.records(client, row, guard), desired):
                return
            raise PublicationPending('dns_change_result_pending') from None
        if not self.equivalent(self.records(client, row, guard), desired):
            raise PublicationPending('dns_change_propagating')
