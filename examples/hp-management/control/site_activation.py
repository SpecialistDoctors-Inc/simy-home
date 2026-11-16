"""Automatically turn an owned, complete public-site import into an editable site.

All provider identities are platform configuration, never customer form fields.
Creation receipts are durable; retries resume the same resources and exact copy.
"""
import hashlib
import io
import json
import stat
import time
import zipfile
from uuid import NAMESPACE_URL, uuid5

from bundles import MAX_FILE, MAX_TOTAL, MAX_TRANSPORT, validate_files, sha256
from provision_site import validate
from service import new_site_writes
from store import Check, Conflict, Write
from stripe_billing import ACTIVE, hp_entitlement
from import_normalization import normalize, SourceConnectionRequired

QUEUE_STATE = 'clinic_activation'


class ActivationWaiting(RuntimeError):
    def __init__(self, reason, retry_after=60):
        super().__init__(reason)
        self.retry_after = retry_after


class ImportRejected(ValueError):
    pass


def read_import(data, intake):
    """Validate the exact copier object; never execute imported files or scripts."""
    if (not isinstance(data, bytes) or len(data) > MAX_TRANSPORT
            or not intake['copy_key'].endswith('/' + sha256(data) + '/site.zip')):
        raise ImportRejected('copy_digest_mismatch')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 1001 or len({e.filename for e in entries}) != len(entries):
                raise ImportRejected('copy_inventory_invalid')
            if any(e.file_size > MAX_FILE or stat.S_ISLNK(e.external_attr >> 16) for e in entries):
                raise ImportRejected('copy_inventory_invalid')
            if sum(e.file_size for e in entries) > MAX_TOTAL:
                raise ImportRejected('copy_inventory_invalid')
            manifest = json.loads(archive.read('manifest.json'))
            if manifest.get('copy_schema') != 2:
                raise ImportRejected('copy_unverified')
            if (manifest.get('host') != intake['host'] or manifest.get('truncated') is not False
                    or manifest.get('missing') != [] or not isinstance(manifest.get('files'), list)):
                raise ImportRejected('copy_incomplete')
            records = manifest['files']
            if len({r['path'] for r in records}) != len(records):
                raise ImportRejected('copy_inventory_mismatch')
            if {r['path'] for r in records} != {e.filename for e in entries if e.filename != 'manifest.json'}:
                raise ImportRejected('copy_inventory_mismatch')
            files = {}
            for record in records:
                path = record['path']
                if not path.startswith('site/'):
                    raise ImportRejected('copy_inventory_invalid')
                content = archive.read(path)
                if len(content) != record['bytes'] or sha256(content) != record['sha256']:
                    raise ImportRejected('copy_file_mismatch')
                files[path[5:]] = content
            try:
                files = normalize(records, files, intake['host'])
            except SourceConnectionRequired as error:
                raise ImportRejected(str(error)) from None
            validate_files(files)
            return files
    except ImportRejected:
        raise
    except Exception:
        raise ImportRejected('copy_inventory_invalid') from None


def enqueue_writes(store, intake):
    if intake.get('status') != 'received' or not intake.get('auth_code'):
        return []
    sub = intake['subscription_id']
    if store.get('clinic-activation:' + sub):
        return []
    identifier = str(uuid5(NAMESPACE_URL, 'hp-activation:' + sub))
    return [Write('clinic-activation:' + sub, {'job_id': identifier, 'subscription_id': sub,
                'subject': intake['subject'], 'host': intake['host'], 'status': 'waiting_transfer',
                'created_at': int(time.time()), 'retry_at': 0,
                'queue_state': QUEUE_STATE, 'phases': {}}, None)]


def run_one(store, read_copy, repositories, hosting, platform, clock=time.time):
    """Process one activation stage without per-customer operator registration.

    Repositories and hosting implement real provider adapters below. The only
    grant is atomic with verified resource bindings and the current purchase.
    This function neither changes production DNS nor publishes copied content.
    """
    now = int(clock())
    pending = store.pending(1, now=now, queue_state=QUEUE_STATE)
    if not pending:
        return None
    key, observed = pending[0]
    row = store.get(key)
    if not row or row['_version'] != observed['_version']:
        return 'stale_index'
    sub = row['subscription_id']
    if key != 'clinic-activation:' + sub:
        return 'invalid_index_entry'
    try:
        row = store.put(key, {**row, 'retry_at': now + 60}, row['_version'])
    except Conflict:
        return sub
    if not row or row['status'] in ('ready', 'failed'):
        return sub
    purchase = store.get('stripe-subscription:' + sub)
    intake = store.get('clinic-intake:' + sub)
    transfer = store.get('clinic-transfer:' + sub)
    dns = store.get('dns-connection:' + sub)
    if (hp_entitlement(purchase, row['subject']) is None
            or not intake or intake.get('subject') != row['subject'] or intake.get('host') != row['host']):
        return sub
    if not transfer or transfer.get('status') != 'complete' or transfer.get('subject') != row['subject']:
        return sub
    if (not dns or dns.get('subject') != row['subject'] or dns.get('host') != row['host']
            or dns.get('status') != 'verified' or dns.get('domain') != transfer.get('domain')):
        return sub
    if intake.get('copy_state') != 'done':
        if intake.get('copy_state') == 'pending':
            from site_copy import enqueue
            enqueue(store, sub, intake['copy_generation'])
        return sub
    try:
        def guard():
            current = store.get(key)
            paid = store.get('stripe-subscription:' + sub)
            source = store.get('clinic-intake:' + sub)
            if (not current or current['job_id'] != row['job_id'] or current.get('subject') != row['subject']
                    or current.get('status') in ('ready', 'failed')
                    or hp_entitlement(paid, row['subject']) is None
                    or not source or source.get('copy_key') != intake['copy_key'] or source.get('host') != row['host']):
                raise ActivationWaiting('activation_authority_changed')

        guard()
        files = read_import(read_copy(intake['copy_key']), intake)
        checksum = sha256(json.dumps({p: sha256(b) for p, b in files.items()}, sort_keys=True).encode())
        if row.get('source_sha256') not in (None, checksum):
            raise ActivationWaiting('activation_source_changed')
        dns_binding = {k: dns.get(k) for k in ('domain', 'hosted_zone_id', 'nameservers')}
        if row.get('dns_binding') not in (None, dns_binding):
            raise ActivationWaiting('dns_connection_changed')
        if row.get('source_sha256') is None:
            row = store.put(key, {**row, 'source_sha256': checksum, 'copy_key': intake['copy_key'],
                                  'dns_binding': dns_binding}, row['_version'])
        phases = dict(row['phases'])
        if 'repository' not in phases:
            receipt = repositories.ensure(row, files, guard)
            guard()
            phases['repository'] = receipt
            store.put(key, {**row, 'phases': phases, 'status': 'preparing_hosting'}, row['_version'])
            return sub
        if 'hosting' not in phases:
            receipt = hosting.ensure(row, dns, guard)
            guard()
            phases['hosting'] = receipt
            store.put(key, {**row, 'phases': phases, 'status': 'verifying_connection'}, row['_version'])
            return sub
        guard()
        site_id = 'clinic-' + hashlib.sha256(sub.encode()).hexdigest()[:20]
        hosted = dict(phases['hosting'])
        roles = hosted.pop('publisher_roles')
        site = {**platform, **phases['repository'], **hosted,
                'site_id': site_id, 'name': row['host'], 'config_version': 1,
                'recipient': intake['email'], 'direct_transfer_enabled': True,
                'mail_enabled': False, 'reporting_enabled': False,
                'license_policy': {'mode': 'stripe', 'subscription_id': sub}}
        validate(site)
        repositories.verify(site, files, guard)
        hosting.verify(site, row, dns, guard)
        # Freeze only web DNS records, not MX/TXT/other service records. The
        # actual cutover belongs to the later exact-artifact publish operation.
        dns_plan = hosting.cutover_plan(site, dns, guard)
        member_key = 'principal:' + row['subject']
        member = store.get(member_key) or {'sites': {}, 'disabled': False}
        if member.get('disabled'):
            raise ActivationWaiting('account_unavailable')
        guard()
        paid, intake = store.get('stripe-subscription:' + sub), store.get('clinic-intake:' + sub)
        store.transact([
            Check('stripe-subscription:' + sub, paid['_version']),
            Check('clinic-transfer:' + sub, transfer['_version']), Check('dns-connection:' + sub, dns['_version']),
            *new_site_writes(site),
            Write('managed-publisher:' + site_id, {'site_id': site_id, 'roles': roles,
                  'deployment': site['deployment']}, None),
            Write(member_key, {**member, 'sites': {**member['sites'], site_id: ['read', 'edit', 'publish']}}, member.get('_version')),
            Write('dns-cutover:' + site_id, dns_plan, None),
            Write('clinic-intake:' + sub, {**intake, 'status': 'claimed', 'site_id': site_id, 'updated_at': now}, intake['_version']),
            Write(key, {**{k: v for k, v in row.items() if k != 'queue_state'},
                        'status': 'ready', 'site_id': site_id, 'completed_at': now}, row['_version'])])
    except ActivationWaiting as error:
        current = store.get(key)
        if current and current.get('status') not in ('ready', 'failed') and error.retry_after > 60:
            try:
                store.put(key, {**current, 'retry_at': now + min(error.retry_after, 3600)}, current['_version'])
            except Conflict:
                pass
        return sub
    except Conflict:
        return sub
    except ImportRejected as error:
        current = store.get(key)
        try:
            if str(error) == 'copy_unverified' and not current['phases']:
                source = store.get('clinic-intake:' + sub)
                store.transact([
                    Write('clinic-intake:' + sub, {**source, 'copy_state': 'pending', 'copy_attempts': 0,
                        'copy_generation': source.get('copy_generation', 0) + 1}, source['_version']),
                    Write(key, {**current, 'status': 'waiting_copy', 'reason': None}, current['_version'])])
                return sub
            store.put(key, {**{k: v for k, v in current.items() if k != 'queue_state'},
                            'status': 'failed', 'reason': str(error)}, current['_version'])
        except Conflict:
            pass
    except Exception:
        current = store.get(key)
        try:
            store.put(key, {**current, 'reason': 'connection_preparation_pending'}, current['_version'])
        except Conflict:
            pass
    return sub
