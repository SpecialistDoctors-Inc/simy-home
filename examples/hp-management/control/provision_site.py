#!/usr/bin/env python3
"""Register a verified site and its first access grant from the operator CLI."""
import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urlsplit
from identity import sha
from licensing import LicenseUnavailable, license_org, valid_google_subject
from store import DynamoStore, Write

ACCOUNT = '209300895845'
FIELDS = {'site_id','name','config_version','github_app_id','github_installation_id','github_repository_id',
    'github_owner','github_repository','validation_workflow_id','initial_main_commit',
    'drive_workspace_folder_id','drive_changes_folder_id','sheet_id','recipient','operator_subject','operator_email',
    'dev_url','prod_url','mail_enabled','reporting_enabled','deployment'}


def validate(site):
    if not isinstance(site,dict) or set(site)-{'license_policy'}!=FIELDS:raise ValueError('site binding fields differ')
    try:
        license_org(site)
    except LicenseUnavailable:
        raise ValueError('invalid license policy') from None
    if not re.fullmatch('[a-z][a-z0-9-]{1,62}',site['site_id']) or site['config_version']!=1:raise ValueError('new site required')
    for name in ('github_app_id','github_installation_id','github_repository_id','validation_workflow_id'):
        if type(site[name]) is not int or site[name]<=0:raise ValueError('positive provider IDs required')
    if not re.fullmatch('[0-9a-f]{40}',site['initial_main_commit']):raise ValueError('verified initial commit required')
    for name in ('github_owner','github_repository'):
        if not re.fullmatch('[A-Za-z0-9_.-]{1,100}',site[name]):raise ValueError('invalid repository binding')
    for name in ('drive_workspace_folder_id','drive_changes_folder_id','sheet_id'):
        if not re.fullmatch('[A-Za-z0-9_-]{10,256}',site[name]):raise ValueError('provider folder/Sheet ID required')
    if site['drive_workspace_folder_id']==site['drive_changes_folder_id']:raise ValueError('snapshot and incoming folders must differ')
    for name in ('recipient','operator_email'):
        if not isinstance(site[name],str) or not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',site[name]):raise ValueError('verified email required')
    for name in ('dev_url','prod_url'):
        p=urlsplit(site[name])
        if p.scheme!='https' or not p.hostname or p.username or p.password or p.query or p.fragment or p.port not in (None,443) or p.path not in ('','/'):
            raise ValueError('canonical HTTPS site origin required')
    if site['dev_url'].rstrip('/')==site['prod_url'].rstrip('/'):raise ValueError('separate preview and production required')
    if any(type(site[k]) is not bool for k in ('mail_enabled','reporting_enabled')):raise ValueError('explicit reporting flags required')
    if not isinstance(site['operator_subject'],str) or not site['operator_subject'] or any(ord(c)<32 for c in site['operator_subject']):raise ValueError('verified operator subject required')
    if set(site['deployment'])!={'dev','prod'}:raise ValueError('both deployment bindings required')
    for env,target in site['deployment'].items():
        if set(target)!={'bucket','distribution_id','origin_id','expected_config_sha256','initial_file_paths'}:raise ValueError('deployment fields differ')
        if not re.fullmatch('[0-9a-f]{64}',target['expected_config_sha256']):raise ValueError('verified CloudFront config required')
        if not isinstance(target['initial_file_paths'],list) or not target['initial_file_paths']:raise ValueError('initial served inventory required')
    return site


def seed(store, site, email, roles, now, *, google_subject=None):
    validate(site)
    if not roles or not set(roles)<={'read','edit','publish'} or 'read' not in roles:raise ValueError('explicit role set required')
    site_id = site['site_id']
    grant = {site_id: sorted(set(roles))}
    writes = [
        Write('site:' + site_id, site, None),
        Write('repository:' + str(site['github_repository_id']),
              {'site_id': site_id, 'installation_id': site['github_installation_id']}, None),
    ]
    result = {'site_id': site_id}
    if google_subject is not None:
        if email is not None or not valid_google_subject(google_subject) or license_org(site) is None:
            raise ValueError('verified Google subject and SIMY organization required')
        key = 'principal:' + google_subject
        current = store.get(key)
        principal = current if current is not None else {'sites': {}, 'disabled': False}
        if principal.get('disabled') or not isinstance(principal.get('sites'), dict) or site_id in principal['sites']:
            raise ValueError('existing principal cannot receive this site grant')
        writes.append(Write(key, {**principal, 'sites': {**principal['sites'], **grant}},
                            current['_version'] if current is not None else None))
    else:
        if not isinstance(email, str) or not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', email):
            raise ValueError('exact invitation email required')
        expires_at = now + 7 * 86400
        writes.append(Write('invitation:' + sha(email.casefold()),
                            {'email': email, 'sites': grant, 'created_at': now, 'expires_at': expires_at}, None))
        result['invitation_expires_at'] = expires_at
    store.transact(writes)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--site', type=Path, required=True)
    p.add_argument('--table')
    identity = p.add_mutually_exclusive_group(required=True)
    identity.add_argument('--email', help='Send no mail. Create an invitation for this verified mailbox.')
    identity.add_argument('--google-subject', help='Grant access to this previously verified Google subject.')
    p.add_argument('--roles', nargs='+', default=['read', 'edit'])
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    site=validate(json.loads(a.site.read_text()))
    if not a.apply:
        from store import MemoryStore
        seed(MemoryStore(), site, a.email, a.roles, int(time.time()), google_subject=a.google_subject)
        print(json.dumps({'valid': True, 'site_id': site['site_id'], 'applied': False}))
        return
    if a.table!='simy-hp-control':raise SystemExit('use dedicated HP authority table')
    import boto3
    session=boto3.Session(region_name='ap-northeast-1')
    if session.client('sts').get_caller_identity()['Account']!=ACCOUNT:raise SystemExit('wrong AWS account')
    store = DynamoStore(a.table, session.client('dynamodb'))
    print(json.dumps(seed(store, site, a.email, a.roles, int(time.time()), google_subject=a.google_subject)))

if __name__=='__main__':main()
