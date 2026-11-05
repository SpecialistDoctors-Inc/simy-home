"""Signed GitHub delivery wakes only an existing exact-source validation wait."""
import base64
import hashlib
import hmac
import json
import re
import time
from uuid import UUID
from store import Write, Check, Conflict


def handle(event, store, secret, clock=time.time):
    headers={k.lower():v for k,v in event.get('headers',{}).items()}
    raw=event.get('body','')
    try:body=base64.b64decode(raw,validate=True) if event.get('isBase64Encoded') else raw.encode()
    except (ValueError,AttributeError):return 400
    if len(body)>1024*1024:return 413
    signature=headers.get('x-hub-signature-256','')
    if not isinstance(secret,str) or len(secret)<32 or not hmac.compare_digest(signature,'sha256='+hmac.new(secret.encode(),body,hashlib.sha256).hexdigest()):return 401
    delivery=headers.get('x-github-delivery','')
    try:
        if str(UUID(delivery))!=delivery:return 400
        payload=json.loads(body)
        repository_id=payload['repository']['id'];installation_id=payload['installation']['id']
        if type(repository_id) is not int or type(installation_id) is not int:return 400
    except (ValueError,TypeError,KeyError):return 400
    kind=headers.get('x-github-event')
    if kind=='workflow_run':source=payload.get('workflow_run',{}).get('head_sha')
    elif kind in ('check_run','check_suite'):source=payload.get(kind,{}).get('head_sha')
    else:return 202
    if not isinstance(source,str) or not re.fullmatch('[0-9a-f]{40}',source):return 400
    binding=store.get('repository:'+str(repository_id))
    if not binding or binding.get('installation_id')!=installation_id:return 403
    value_hash=hashlib.sha256(body).hexdigest();delivery_key='github-delivery:'+delivery
    existing=store.get(delivery_key)
    if existing:return 202 if existing['body_sha256']==value_hash else 409
    wait=store.get('gitwait:'+str(repository_id)+':'+source)
    writes=[Write(delivery_key,{'body_sha256':value_hash,'received_at':int(clock()),'expires_at':int(clock())+7*86400},None)]
    if wait and wait.get('site_id')==binding['site_id']:
        key='operation:'+wait['operation_id'];op=store.get(key)
        if op and op['site_id']==binding['site_id'] and op.get('status') in ('retry_wait','reconciling') and op.get('stage')=='github_validation':
            writes.extend([Write(key,{**op,'queue_state':'pending','retry_at':0,
                'retry_generation':op.get('retry_generation',0)+1},op['_version']),Check('repository:'+str(repository_id),binding['_version'])])
    try:store.transact(writes)
    except Conflict:return 409
    return 202
