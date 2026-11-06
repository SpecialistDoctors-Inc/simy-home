#!/usr/bin/env python3
"""Operator-only binding/invitation provisioning. No customer MCP exposure."""
import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urlsplit
from identity import sha
from store import DynamoStore, Write, Check

ACCOUNT = '209300895845'
FIELDS = {'site_id','name','config_version','github_app_id','github_installation_id','github_repository_id',
    'github_owner','github_repository','validation_workflow_id','initial_main_commit',
    'drive_workspace_folder_id','drive_changes_folder_id','sheet_id','recipient','operator_subject','operator_email',
    'dev_url','prod_url','mail_enabled','reporting_enabled','deployment'}


def validate(site):
    if not isinstance(site,dict) or set(site)!=FIELDS:raise ValueError('site binding fields differ')
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


def seed(store,site,email,roles,now):
    validate(site)
    if not isinstance(email,str) or not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',email):raise ValueError('exact invitation email required')
    if not roles or not set(roles)<={'read','edit','publish'} or 'read' not in roles:raise ValueError('explicit role set required')
    store.transact([Write('site:'+site['site_id'],site,None),
        Write('repository:'+str(site['github_repository_id']),{'site_id':site['site_id'],'installation_id':site['github_installation_id']},None),
        Write('invitation:'+sha(email.casefold()),{'email':email,'sites':{site['site_id']:sorted(set(roles))},'created_at':now,'expires_at':now+7*86400},None)])
    return {'site_id':site['site_id'],'invitation_expires_at':now+7*86400}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--site',type=Path,required=True);p.add_argument('--table');p.add_argument('--email',required=True);p.add_argument('--roles',nargs='+',default=['read','edit']);p.add_argument('--apply',action='store_true');a=p.parse_args()
    site=validate(json.loads(a.site.read_text()))
    if not a.apply:print(json.dumps({'valid':True,'site_id':site['site_id'],'applied':False}));return
    if a.table!='simy-hp-control':raise SystemExit('use dedicated HP authority table')
    import boto3
    session=boto3.Session(region_name='ap-northeast-1')
    if session.client('sts').get_caller_identity()['Account']!=ACCOUNT:raise SystemExit('wrong AWS account')
    print(json.dumps(seed(DynamoStore(a.table,session.client('dynamodb')),site,a.email,a.roles,int(time.time()))))

if __name__=='__main__':main()
