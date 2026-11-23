"""Move a slot site onto the clinic's own domain with two DNS records from the clinic.

A slot (clinic_slots.py) publishes on ``<site_id>.hp.simy.one``. The clinic keeps
its registrar, DNS provider and mail exactly as they are; it only adds:

1. the ACM validation CNAME for its homepage host, and
2. ``<host> CNAME <prod distribution>.cloudfront.net``.

Everything else is automatic and runs on the copier's schedule:

  requested    the clinic asked on /start; nothing in AWS yet
  awaiting_dns certificate requested for <host> (+ the slot name, validated in
               the simy.one zone by us); /start shows the two records
  attaching    certificate issued; under the site lease the prod distribution
               serves both names with it; waiting for CloudFront to deploy
  attached     the binding's pinned config hash was updated; prod still
               publishes on the slot name until the clinic's DNS points here
  live         https://<host>/ returns a fresh token that only this
               distribution serves: prod_url becomes https://<host> and the
               clinic is told by mail
  failed       certificate expired unvalidated (ACM gives up after 72 h)

Nothing here changes MX or any other record of the clinic's domain, and nothing
is done for a site that is not an assigned slot.

Records:
  domain-cutover:<site_id>  state, host, certificate, records shown to the clinic
  domain-cutover-pending    {'sites': [site_id, ...]} work list
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import time
from copy import deepcopy

from clinic_slots import SLOT_PREFIX, valid_slot_site
from domain_verification import site_host
from publisher import config_sha256
from store import Conflict, Write

PENDING_KEY = 'domain-cutover-pending'
LEASE_SECONDS = 1800  # CloudFront usually deploys in minutes; the lease is renewed while waiting
SLOT_ZONE_SUFFIX = '.hp.simy.one'
HOST = re.compile(r'(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}')


class CutoverRejected(ValueError):
    pass


def cutover_key(site_id):
    return 'domain-cutover:' + site_id


def allowed_host(intake_host, requested):
    """Only the domain the clinic paid for, with or without ``www.``."""
    if not isinstance(requested, str):
        return None
    host = requested.strip().lower().rstrip('.')
    if not HOST.fullmatch(host) or host.endswith('.simy.one') or host.endswith('.cloudfront.net'):
        return None
    strip = lambda h: h[4:] if h.startswith('www.') else h
    return host if strip(host) == strip(intake_host) else None


# -- work list -------------------------------------------------------------

def _update_list(store, change):
    for _ in range(5):
        row = store.get(PENDING_KEY)
        sites = list(row.get('sites', [])) if row else []
        new = change(sites)
        if new == sites:
            return
        try:
            store.put(PENDING_KEY, {'sites': new}, row['_version'] if row else None)
            return
        except Conflict:
            continue
    raise Conflict('concurrent_change')


def request(store, intake, requested_host, clock=time.time):
    """Record the clinic's request from /start. Writes nothing outside the store."""
    site_id = intake.get('slot_site_id')
    if intake.get('status') != 'claimed' or not site_id:
        raise CutoverRejected('slot_site_required')
    host = allowed_host(intake['host'], requested_host)
    if host is None:
        raise CutoverRejected('invalid_cutover_host')
    key = cutover_key(site_id)
    existing = store.get(key)
    if existing and existing.get('state') not in ('failed',):
        if existing.get('host') == host:
            return existing
        if existing.get('state') in ('attaching', 'attached', 'live'):
            raise CutoverRejected('cutover_in_progress')
    row = {'site_id': site_id, 'subscription_id': intake['subscription_id'], 'host': host,
           'state': 'requested', 'requested_at': int(clock()), 'error': None}
    store.put(key, row, existing['_version'] if existing else None)
    _update_list(store, lambda sites: sites if site_id in sites else sites + [site_id])
    return store.get(key)


class DomainCutover:
    def __init__(self, store, acm, route53, cloudfront, probe, zone_id, mail=None, clock=time.time, put_object=None):
        # acm: us-east-1 ACM client. route53: client for the simy.one zone (zone_id).
        # cloudfront: client. probe(url) -> (status, headers, body) without redirects.
        # mail(to, subject, body) sends one plain-text mail, or None.
        self.store, self.acm, self.route53, self.cloudfront = store, acm, route53, cloudfront
        self.probe, self.zone_id, self.mail, self.clock = probe, zone_id, mail, clock
        # put_object(bucket, key, data, content_type) writes the DNS challenge (slot buckets only).
        self.put_object = put_object

    def run_one(self):
        row = self.store.get(PENDING_KEY)
        sites = row.get('sites', []) if row else []
        if not sites:
            return None
        site_id = sites[0]
        _update_list(self.store, lambda s: [x for x in s if x != site_id] + [site_id])
        try:
            state = self.advance(site_id)
        except CutoverRejected as error:
            self._save(site_id, {'state': 'failed', 'error': str(error)})
            state = 'failed'
        except Exception as error:
            # Throttling or a transient AWS error: keep the job queued.
            code = getattr(error, 'response', {}).get('Error', {}).get('Code', type(error).__name__)
            print(json.dumps({'event': 'hp_domain_cutover_retry', 'error': str(code)[:64]}))
            return site_id, 'retry'
        if state in ('live', 'failed', 'not_applicable'):
            _update_list(self.store, lambda s: [x for x in s if x != site_id])
        print(json.dumps({'event': 'hp_domain_cutover', 'state': state}))
        return site_id, state

    def advance(self, site_id):
        row = self.store.get(cutover_key(site_id))
        slot = self.store.get(SLOT_PREFIX + site_id)
        site = self.store.get('site:' + site_id)
        if (not row or not slot or slot.get('state') != 'assigned' or not site
                or slot.get('subscription_id') != row.get('subscription_id')
                or (site.get('license_policy') or {}).get('subscription_id') != row.get('subscription_id')
                or not valid_slot_site({k: v for k, v in site.items() if k not in ('license_policy', 'registered_by_claim', '_version')
                                        and not k.startswith('current_') and not k.startswith('last_')})):
            return 'not_applicable'
        state = row['state']
        if state == 'requested':
            return self._request_certificate(row, site)
        if state == 'awaiting_dns':
            return self._await_certificate(row, site)
        if state == 'attaching':
            return self._finish_attach(row, site)
        if state == 'attached':
            return self._confirm_dns(row, site)
        return state

    # -- certificate ------------------------------------------------------

    def _slot_host(self, site_id):
        return site_id + SLOT_ZONE_SUFFIX

    def _request_certificate(self, row, site):
        site_id = site['site_id']
        arn = row.get('certificate_arn')
        if not arn:
            token = hashlib.sha256(f'{site_id}:{row["host"]}:{row["requested_at"]}'.encode()).hexdigest()[:32]
            arn = self.acm.request_certificate(
                DomainName=row['host'], SubjectAlternativeNames=[self._slot_host(site_id)],
                ValidationMethod='DNS', IdempotencyToken=token,
                Tags=[{'Key': 'simy-hp-site', 'Value': site_id}])['CertificateArn']
            row = self._save(site_id, {'certificate_arn': arn})
        options = self.acm.describe_certificate(CertificateArn=arn)['Certificate'].get('DomainValidationOptions', [])
        records = {o['DomainName']: o.get('ResourceRecord') for o in options}
        if not all(records.get(name) for name in (row['host'], self._slot_host(site_id))):
            return 'requested'  # ACM fills in the records a few seconds after the request
        own = records[self._slot_host(site_id)]
        if not own['Name'].endswith(self._slot_host(site_id) + '.'):
            raise CutoverRejected('unexpected_validation_record')
        # Our half of the validation lives in the simy.one zone.
        self.route53.change_resource_record_sets(HostedZoneId=self.zone_id, ChangeBatch={'Changes': [{
            'Action': 'UPSERT', 'ResourceRecordSet': {
                'Name': own['Name'], 'Type': own['Type'], 'TTL': 300, 'ResourceRecords': [{'Value': own['Value']}]}}]})
        clinic = records[row['host']]
        target = self.cloudfront.get_distribution(Id=site['deployment']['prod']['distribution_id'])['Distribution']['DomainName']
        self._save(site_id, {'state': 'awaiting_dns', 'records': [
            {'name': clinic['Name'], 'type': clinic['Type'], 'value': clinic['Value'], 'purpose': 'certificate'},
            {'name': row['host'] + '.', 'type': 'CNAME', 'value': target + '.', 'purpose': 'homepage'}]})
        return 'awaiting_dns'

    def _await_certificate(self, row, site):
        status = self.acm.describe_certificate(CertificateArn=row['certificate_arn'])['Certificate']['Status']
        if status in ('FAILED', 'VALIDATION_TIMED_OUT', 'REVOKED', 'EXPIRED'):
            raise CutoverRejected('certificate_' + status.lower())
        if status != 'ISSUED':
            return 'awaiting_dns'
        return self._start_attach(row, site)

    # -- distribution -----------------------------------------------------

    def _take_lease(self, site_id):
        key = 'lease:site:' + site_id
        lock = self.store.get(key)
        now = self.clock()
        if lock and lock.get('owner') != 'domain-cutover' and (
                lock.get('until', 0) > now or lock.get('blocked_operation') is not None):
            return None  # a publication or edit is running; try again next run
        epoch = (lock or {}).get('epoch', 0) + (0 if lock and lock.get('owner') == 'domain-cutover' else 1)
        value = {'owner': 'domain-cutover', 'operation_id': None, 'epoch': epoch, 'until': now + LEASE_SECONDS,
                 'blocked_operation': None}
        try:
            return self.store.put(key, value, (lock or {}).get('_version'))
        except Conflict:
            return None

    def _release_lease(self, site_id, writes):
        key = 'lease:site:' + site_id
        lock = self.store.get(key)
        if not lock or lock.get('owner') != 'domain-cutover':
            raise Conflict('lease_lost')
        self.store.transact([*writes, Write(key, {**{k: v for k, v in lock.items() if k != '_version'},
                                                   'until': 0}, lock['_version'])])

    # Rejections CloudFront gives before changing anything. Any other failure
    # (timeout, lost response) may have applied the update and is reconciled.
    REJECTED = ('CNAMEAlreadyExists', 'InvalidViewerCertificate', 'PreconditionFailed', 'InvalidArgument',
                'IllegalUpdate', 'TooManyDistributionCNAMEs', 'AccessDenied')

    def _desired(self, config, row, site_id):
        desired = deepcopy(config)
        names = [self._slot_host(site_id), row['host']]
        desired['Aliases'] = {'Quantity': len(names), 'Items': names}
        desired['ViewerCertificate'] = {
            'ACMCertificateArn': row['certificate_arn'], 'SSLSupportMethod': 'sni-only',
            'MinimumProtocolVersion': 'TLSv1.2_2021', 'Certificate': row['certificate_arn'],
            'CertificateSource': 'acm', 'CloudFrontDefaultCertificate': False}
        return desired

    def _applied(self, config, row, site_id):
        """True when the distribution already serves both names with the new certificate."""
        aliases = (config.get('Aliases') or {}).get('Items') or []
        viewer = config.get('ViewerCertificate') or {}
        return (sorted(aliases) == sorted([self._slot_host(site_id), row['host']])
                and viewer.get('ACMCertificateArn') == row['certificate_arn'])

    @staticmethod
    def _core_sha256(config, origin_id):
        """Hash of everything the cutover must not change (all but aliases and certificate)."""
        core = {k: v for k, v in config.items() if k not in ('Aliases', 'ViewerCertificate', 'CallerReference')}
        return config_sha256(core, origin_id)

    def _update(self, site_id, row, target, config, etag):
        try:
            self.cloudfront.update_distribution(Id=target['distribution_id'], IfMatch=etag,
                                                DistributionConfig=self._desired(config, row, site_id))
        except Exception as error:
            code = getattr(error, 'response', {}).get('Error', {}).get('Code')
            if code in self.REJECTED:
                # e.g. CNAMEAlreadyExists: the host is still attached to another
                # CloudFront distribution (often the clinic's current homepage).
                self._release_lease(site_id, [])
                raise CutoverRejected('cloudfront_update_failed:' + code) from None
            raise  # ambiguous: keep 'attaching' and the lease; the next run reconciles

    def _start_attach(self, row, site):
        site_id = site['site_id']
        if self._take_lease(site_id) is None:
            return 'awaiting_dns'
        target = site['deployment']['prod']
        result = self.cloudfront.get_distribution_config(Id=target['distribution_id'])
        if config_sha256(result['DistributionConfig'], target['origin_id']) != target['expected_config_sha256']:
            # Someone changed the distribution outside HP Control: stop for the operator.
            self._release_lease(site_id, [])
            raise CutoverRejected('cloudfront_unexpected_config_drift')
        # Record the intent before calling CloudFront, so a lost response or an
        # interrupted run is reconciled instead of leaving a stale pinned hash.
        self._save(site_id, {'state': 'attaching', 'original_config_sha256': target['expected_config_sha256'],
                             'core_config_sha256': self._core_sha256(result['DistributionConfig'], target['origin_id'])})
        self._update(site_id, row, target, result['DistributionConfig'], result['ETag'])
        return 'attaching'

    def _finish_attach(self, row, site):
        site_id = site['site_id']
        if self._take_lease(site_id) is None:
            return 'attaching'  # never expected while attaching; wait rather than guess
        target = site['deployment']['prod']
        result = self.cloudfront.get_distribution_config(Id=target['distribution_id'])
        config = result['DistributionConfig']
        current_hash = config_sha256(config, target['origin_id'])
        if self._core_sha256(config, target['origin_id']) != row.get('core_config_sha256'):
            # Something besides the names and certificate changed: never pin it.
            self._release_lease(site_id, [])
            raise CutoverRejected('cloudfront_unexpected_config_drift')
        if not self._applied(config, row, site_id):
            if current_hash == row.get('original_config_sha256'):
                # The update never landed: apply it now.
                self._update(site_id, row, target, config, result['ETag'])
                return 'attaching'
            self._release_lease(site_id, [])
            raise CutoverRejected('cloudfront_unexpected_config_drift')
        distribution = self.cloudfront.get_distribution(Id=target['distribution_id'])['Distribution']
        if distribution.get('Status') != 'Deployed':
            return 'attaching'
        if config_sha256(distribution['DistributionConfig'], target['origin_id']) != current_hash:
            return 'attaching'  # changed between reads; look again next run
        pinned = deepcopy({k: v for k, v in site.items() if k != '_version'})
        pinned['deployment']['prod']['expected_config_sha256'] = current_hash
        current = self.store.get(cutover_key(site_id))
        self._release_lease(site_id, [
            Write('site:' + site_id, pinned, site['_version']),
            Write(cutover_key(site_id), {**{k: v for k, v in current.items() if k != '_version'},
                                         'state': 'attached', 'attached_at': int(self.clock())}, current['_version'])])
        return 'attached'

    # -- the clinic's DNS -------------------------------------------------

    def _challenge(self, row, site):
        """Place a fresh token in the prod bucket under the path CloudFront serves.

        Only this distribution can return it, so the old homepage cannot pass by
        copying the page or a CloudFront header."""
        # The file name and its content are independent secrets, so a host that
        # echoes the requested path cannot produce the expected answer.
        name, token = row.get('challenge_name'), row.get('challenge')
        if not name or not token:
            name, token = secrets.token_hex(16), secrets.token_hex(32)
            row = self._save(site['site_id'], {'challenge_name': name, 'challenge': token})
        target = site['deployment']['prod']
        config = self.cloudfront.get_distribution_config(Id=target['distribution_id'])['DistributionConfig']
        origin = next(o for o in config['Origins']['Items'] if o.get('Id') == target['origin_id'])
        prefix = (origin.get('OriginPath') or '').strip('/')
        path = f'.well-known/simy-cutover/{name}.txt'
        if self.put_object is None:
            raise CutoverRejected('challenge_unavailable')
        self.put_object(target['bucket'], (prefix + '/' if prefix else '') + path, token.encode(), 'text/plain')
        return token, path

    def _serves_this_distribution(self, row, site):
        token, path = self._challenge(row, site)
        target = self.cloudfront.get_distribution(Id=site['deployment']['prod']['distribution_id'])['Distribution']
        try:
            ours = self.probe('https://' + target['DomainName'] + '/' + path)
            theirs = self.probe('https://' + row['host'] + '/' + path)
        except Exception:
            return False
        return ours[0] == 200 and theirs[0] == 200 and ours[2] == theirs[2] == token.encode()

    def _confirm_dns(self, row, site):
        site_id = site['site_id']
        if not self._serves_this_distribution(row, site):
            return 'attached'
        if self._take_lease(site_id) is None:
            return 'attached'
        site = self.store.get('site:' + site_id)
        current = self.store.get(cutover_key(site_id))
        moved = {**{k: v for k, v in site.items() if k != '_version'}, 'prod_url': 'https://' + row['host']}
        self._release_lease(site_id, [
            Write('site:' + site_id, moved, site['_version']),
            Write(cutover_key(site_id), {**{k: v for k, v in current.items() if k != '_version'},
                                         'state': 'live', 'live_at': int(self.clock())}, current['_version'])])
        self._notify(row, site)
        return 'live'

    def _notify(self, row, site):
        if self.mail is None:
            return
        intake = self.store.get('clinic-intake:' + row['subscription_id']) or {}
        if not intake.get('email'):
            return
        try:
            self.mail(intake['email'], '【SIMY】ご自身のドメインでの公開に切り替わりました',
                      f'https://{row["host"]} で、SIMYで編集したホームページが表示されるようになりました。\n\n'
                      '今後の公開は、このドメインに反映されます。メールなど、ほかの設定は変わっていません。\n'
                      'お心当たりのない場合は、SIMYの担当者までご連絡ください。\n')
        except Exception:
            print(json.dumps({'event': 'hp_domain_cutover_mail_failed'}))

    def _save(self, site_id, fields):
        key = cutover_key(site_id)
        for _ in range(5):
            current = self.store.get(key)
            try:
                return self.store.put(key, {**{k: v for k, v in current.items() if k != '_version'}, **fields,
                                            'updated_at': int(self.clock())}, current['_version'])
            except Conflict:
                continue
        raise Conflict('concurrent_change')
