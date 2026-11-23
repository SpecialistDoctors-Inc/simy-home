#!/usr/bin/env python3
"""Add an operator-prepared, unassigned clinic site to the slot pool.

The site is built exactly like any clinic site (CLINIC_SITES.md, "Slot pool"):
repository, Drive folders, Sheet, and ``infra/clinic-site`` with
``prod_hostname = <site_id>.hp.simy.one``. Its bucket roots hold only the
placeholder ``index.html``, its claim target is deployed in ``clinic_sites``, and
``clinic_site_deployment.py`` printed the deployment block. Then:

    python provision_slot.py --site slot.json                 # dry run
    python provision_slot.py --site slot.json --table simy-hp-control --apply

    # queue an intake whose copy finished before slots existed
    python provision_slot.py --enqueue sub_... --table simy-hp-control --apply

Adding a slot grants nothing. ``clinic_slots.py`` assigns it to the next paid
clinic whose domain SIMY has not registered.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from clinic_slots import POOL_KEY, SLOT_PREFIX, enqueue, valid_slot_site
from provision_site import ACCOUNT, validate
from service import new_site_writes
from store import Conflict, DynamoStore, Write


def add_slot(store, site):
    validate(site)
    if not valid_slot_site(site):
        raise ValueError('slot sites are served on <site_id>.hp.simy.one from their own simy-hp-site-* buckets')
    for env in ('dev', 'prod'):
        if site['deployment'][env]['initial_file_paths'] != ['index.html']:
            raise ValueError('a slot bucket must hold only the placeholder index.html')
    site_id = site['site_id']
    if any(store.get(w.key) is not None for w in new_site_writes(site)):
        raise ValueError('site or repository already registered')
    existing = store.get(SLOT_PREFIX + site_id)
    if existing:
        if existing.get('site') == site:
            return {'site_id': site_id, 'state': existing.get('state')}
        raise ValueError('a different slot already exists for this site')
    for _ in range(5):
        pool = store.get(POOL_KEY)
        free = list((pool or {}).get('free', []))
        try:
            store.transact([Write(SLOT_PREFIX + site_id, {'state': 'free', 'site': site}, None),
                            Write(POOL_KEY, {'free': free + [site_id]}, pool['_version'] if pool else None)])
            return {'site_id': site_id, 'state': 'free', 'free_slots': len(free) + 1}
        except Conflict:
            continue
    raise Conflict('concurrent_change')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument('--site', type=Path, help='Slot site binding JSON (no license_policy).')
    action.add_argument('--enqueue', metavar='SUBSCRIPTION_ID', help='Queue an intake for slot assignment.')
    p.add_argument('--table')
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()

    def run(store):
        if a.site is not None:
            return add_slot(store, json.loads(a.site.read_text()))
        enqueue(store, a.enqueue)
        return {'queued': a.enqueue}

    if not a.apply:
        from store import MemoryStore
        print(json.dumps({**run(MemoryStore()), 'applied': False}))
        return
    if a.table != 'simy-hp-control':
        raise SystemExit('use dedicated HP authority table')
    import boto3
    session = boto3.Session(region_name='ap-northeast-1')
    if session.client('sts').get_caller_identity()['Account'] != ACCOUNT:
        raise SystemExit('wrong AWS account')
    print(json.dumps(run(DynamoStore(a.table, session.client('dynamodb')))))


if __name__ == '__main__':
    main()
