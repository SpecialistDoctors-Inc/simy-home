"""Give a paid clinic an operator-prepared site slot without waiting for the operator.

The operator keeps a small pool of empty clinic sites ("slots"). Each slot is a
complete, reviewed site binding (repository, Drive folders, Sheet, dev and prod
S3/CloudFront, prod served on ``<site_id>.hp.simy.one``) whose claim targets are
already deployed in ``clinic_sites``. The operator stores it as

  site-slot:<site_id>  {'state': 'free', 'site': <binding without owner data>}
  site-slot-pool       {'free': [<site_id>, ...]}

with ``provision_slot.py``. Nothing here creates AWS resources, repositories or
grants beyond what that binding already allows.

When a clinic's public homepage has been copied (site_copy.py) and SIMY has no
registration for its domain, ``assign_one``:

1. reserves one free slot for the intake (conditional write, so two runs never
   share a slot),
2. uploads the publishable part of the copy to the root of the slot's dev and
   prod buckets, which must still hold only the slot's placeholder,
3. records ``registration-site:<host>`` with the intake's verified sign-in email
   as the owner and the uploaded inventory as the initial served files, and
4. asks the API (``clinic_ready``) to claim the site and email the clinic,
   exactly as the operator's ``notify_clinic_ready.py`` would.

Every step is recorded on the intake (``slot_state``) and is safe to repeat, so a
run killed by the Lambda timeout continues on the next schedule.
"""
from __future__ import annotations

import io
import json
import mimetypes
import re
import time
import zipfile

from bundles import BundleError, validate_path
from domain_verification import site_host
from store import Conflict, Write

SLOT_PREFIX = 'site-slot:'
POOL_KEY = 'site-slot-pool'  # {'free': [site_id, ...]} in the order slots were added
PENDING_KEY = 'clinic-slot-pending'
PLACEHOLDER = 'index.html'
# Slot buckets are created by infra/clinic-site and never shared with another site.
BUCKET = re.compile(r'simy-hp-site-[a-z][a-z0-9-]{1,30}-(dev|prod)-[0-9]{12}')
SLOT_HOST = re.compile(r'https://([a-z][a-z0-9-]{1,30})\.hp\.simy\.one/?')
ENVIRONMENTS = ('dev', 'prod')


class SlotError(Exception):
    """A slot or copy cannot be used; the reason is safe to store."""


def valid_slot_site(site):
    """True for a reviewed binding the assigner may hand to a clinic."""
    if not isinstance(site, dict) or not isinstance(site.get('site_id'), str):
        return False
    match = SLOT_HOST.fullmatch(site.get('prod_url') or '')
    if not match or match.group(1) != site['site_id'] or 'license_policy' in site:
        return False
    deployment = site.get('deployment')
    if not isinstance(deployment, dict) or set(deployment) != set(ENVIRONMENTS):
        return False
    for env in ENVIRONMENTS:
        bucket = (deployment[env] or {}).get('bucket') or ''
        # Exactly this slot's own bucket: "slot-a" must never match "slot-a-extra".
        if not re.fullmatch(rf'simy-hp-site-{re.escape(site["site_id"])}-{env}-[0-9]{{12}}', bucket):
            return False
    return True


# -- work list -------------------------------------------------------------

def _update_list(store, change):
    for _ in range(5):
        row = store.get(PENDING_KEY)
        jobs = list(row.get('subscriptions', [])) if row else []
        new = change(jobs)
        if new == jobs:
            return
        try:
            store.put(PENDING_KEY, {'subscriptions': new}, row['_version'] if row else None)
            return
        except Conflict:
            continue
    raise Conflict('concurrent_change')


def enqueue(store, subscription_id):
    _update_list(store, lambda jobs: jobs if subscription_id in jobs else jobs + [subscription_id])


def _dequeue(store, subscription_id):
    _update_list(store, lambda jobs: [j for j in jobs if j != subscription_id])


def _rotate(store, subscription_id):
    _update_list(store, lambda jobs: [j for j in jobs if j != subscription_id] + [subscription_id])


# -- copy -> publishable files ---------------------------------------------

def publishable_files(zip_bytes):
    """Return {path: bytes} from a site_copy archive, keeping only paths the publisher accepts."""
    files, skipped = {}, 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        for name in archive.namelist():
            if not name.startswith('site/') or name.endswith('/'):
                continue
            path = name[len('site/'):]
            try:
                validate_path(path)
            except BundleError:
                skipped += 1
                continue
            if path.startswith('releases/') or path.casefold() in {p.casefold() for p in files}:
                skipped += 1
                continue
            files[path] = archive.read(name)
    if PLACEHOLDER not in files:
        raise SlotError('copy_without_index')
    return files, skipped


# -- assignment ------------------------------------------------------------

class SlotAssigner:
    def __init__(self, store, read_copy, buckets, notify, clock=time.time):
        # read_copy(key) -> zip bytes from the private artifact bucket.
        # buckets: object with list(bucket) -> [keys] and put(bucket, key, data, content_type).
        # notify(subscription_id) -> result of the API's clinic_ready task.
        self.store, self.read_copy, self.buckets, self.notify, self.clock = store, read_copy, buckets, notify, clock

    def run_one(self):
        """Handle the oldest queued subscription. Returns (subscription_id, status) or None."""
        row = self.store.get(PENDING_KEY)
        jobs = row.get('subscriptions', []) if row else []
        if not jobs:
            return None
        sub = jobs[0]
        _rotate(self.store, sub)
        try:
            status = self.assign(sub)
        except SlotError as error:
            status = str(error)
            self._record(sub, {'slot_state': 'failed', 'slot_error': status})
        if status not in ('no_free_slot', 'retry', 'claim_pending'):
            _dequeue(self.store, sub)
        print(json.dumps({'event': 'hp_clinic_slot', 'status': status}))
        return sub, status

    def assign(self, subscription_id):
        key = 'clinic-intake:' + subscription_id
        intake = self.store.get(key)
        if (intake and intake.get('status') == 'claimed' and intake.get('slot_site_id')
                and intake.get('slot_state') != 'ready'):
            # Claimed (here or by the clinic reopening /start) but the ready mail
            # did not go out yet: keep asking until clinic_ready records it.
            return self._finish(subscription_id)
        if not intake or intake.get('status') != 'received' or intake.get('provider') == 'wordpress':
            return 'not_applicable'
        if intake.get('copy_state') != 'done' or not intake.get('copy_key'):
            return 'not_applicable'
        host = site_host(intake['site_url'])
        registration = self.store.get('registration-site:' + host)
        slot_id = intake.get('slot_site_id')
        if registration and (not slot_id or registration.get('slot_site_id') != slot_id):
            # The operator prepared this domain by hand; the existing flow claims it.
            return 'operator_registered'
        if not slot_id:
            intake, slot_id = self._reserve(key, intake)
            if slot_id is None:
                self._record(subscription_id, {'slot_state': 'waiting'})
                return 'no_free_slot'
        slot = self.store.get(SLOT_PREFIX + slot_id)
        if not slot or slot.get('subscription_id') != subscription_id or not valid_slot_site(slot.get('site')):
            raise SlotError('slot_lost')
        if not registration:
            inventory = self._upload(slot['site'], intake['copy_key'])
            self._register(subscription_id, intake, slot, host, inventory)
        return self._finish(subscription_id)

    def _finish(self, subscription_id):
        result = self.notify(subscription_id) or {}
        status = result.get('status')
        if status in ('notified', 'already_notified', 'claimed'):
            self._record(subscription_id, {'slot_state': 'ready'})
            return 'ready'
        if status in ('retry', 'mail_in_progress', 'mail_failed', 'notified_unrecorded'):
            return 'claim_pending'
        raise SlotError('claim_' + str(status))

    def _reserve(self, key, intake):
        for _ in range(5):
            pool = self.store.get(POOL_KEY)
            free = list((pool or {}).get('free', []))
            slot = site_id = None
            for candidate in free:
                row = self.store.get(SLOT_PREFIX + candidate)
                if row and row.get('state') == 'free' and valid_slot_site(row.get('site')):
                    slot, site_id = row, candidate
                    break
            if slot is None:
                return intake, None
            now = int(self.clock())
            reserved = {**{k: v for k, v in slot.items() if k != '_version'}, 'state': 'assigned',
                        'subscription_id': intake['subscription_id'], 'host': intake['host'], 'assigned_at': now}
            marked = {**{k: v for k, v in intake.items() if k != '_version'},
                      'slot_site_id': site_id, 'slot_state': 'assigned', 'slot_error': None}
            try:
                # The pool row, the slot and the intake change together or not at all.
                self.store.transact([Write(POOL_KEY, {'free': [s for s in free if s != site_id]}, pool['_version']),
                                     Write(SLOT_PREFIX + site_id, reserved, slot['_version']),
                                     Write(key, marked, intake['_version'])])
            except Conflict:
                # Another run took this slot, or the clinic changed the intake.
                fresh = self.store.get(key)
                if fresh and fresh.get('slot_site_id'):
                    return fresh, fresh['slot_site_id']
                if not fresh or fresh.get('site_url') != intake.get('site_url'):
                    raise SlotError('intake_changed')
                intake = fresh
                continue
            return self.store.get(key), site_id
        return intake, None

    def _upload(self, site, copy_key):
        files, skipped = publishable_files(self.read_copy(copy_key))
        for env in ENVIRONMENTS:
            bucket = site['deployment'][env]['bucket']
            existing = set(self.buckets.list(bucket))
            # A slot holds only its placeholder (or the same copy from an
            # interrupted earlier run). Anything else means it was used.
            if any(path.startswith('releases/') for path in existing) or not existing <= set(files) | {PLACEHOLDER}:
                raise SlotError('slot_not_empty')
            for path, data in files.items():
                content_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
                self.buckets.put(bucket, path, data, content_type)
        return {'paths': sorted(files), 'skipped': skipped}

    def _register(self, subscription_id, intake, slot, host, inventory):
        site = json.loads(json.dumps(slot['site']))
        for env in ENVIRONMENTS:
            site['deployment'][env]['initial_file_paths'] = inventory['paths']
        site['recipient'] = intake['email']
        binding = {'owner_email': intake['email'], 'allow_search_console_owners': False, 'site': site,
                   'slot_site_id': site['site_id'], 'subscription_id': subscription_id}
        key = 'clinic-intake:' + subscription_id
        current = self.store.get(key)
        if not current or current.get('slot_site_id') != site['site_id']:
            raise SlotError('intake_changed')
        try:
            self.store.transact([
                Write('registration-site:' + host, binding, None),
                Write(key, {**{k: v for k, v in current.items() if k != '_version'}, 'slot_state': 'registered',
                            'copy_skipped': inventory['skipped']}, current['_version']),
            ])
        except Conflict:
            if not self.store.get('registration-site:' + host):
                raise SlotError('retry') from None

    def _record(self, subscription_id, fields):
        key = 'clinic-intake:' + subscription_id
        for _ in range(5):
            current = self.store.get(key)
            if not current:
                return
            try:
                self.store.put(key, {**{k: v for k, v in current.items() if k != '_version'}, **fields},
                               current['_version'])
                return
            except Conflict:
                continue


class S3SlotBuckets:
    """List and write objects only in slot buckets of the expected account."""

    def __init__(self, client, account):
        self.client, self.account = client, account

    def _check(self, bucket):
        if not BUCKET.fullmatch(bucket) or not bucket.endswith('-' + self.account):
            raise SlotError('invalid_slot_bucket')

    def list(self, bucket):
        self._check(bucket)
        keys = []
        for page in self.client.get_paginator('list_objects_v2').paginate(Bucket=bucket, ExpectedBucketOwner=self.account):
            keys += [item['Key'] for item in page.get('Contents', [])]
        return keys

    def put(self, bucket, key, data, content_type):
        self._check(bucket)
        validate_path(key)
        self.client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type,
                               ServerSideEncryption='AES256', ExpectedBucketOwner=self.account)
