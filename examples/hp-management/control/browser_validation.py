"""Durable launch and readback of secretless, reviewed browser-validation tasks.

No default AWS clients and no network on construction. Presigns are scoped
capabilities for exact immutable input/output objects, never customer URLs.
"""
from __future__ import annotations
import io
import json
import re
import time
import uuid

from bundles import MAX_FILE, MAX_TRANSPORT, sha256
from executor import Busy, IntegrationUnavailable
from service import Rejected, fingerprint
from store import Write

ACCOUNT='209300895845'
MAX_REPORT=64*1024
MAX_SCREENSHOT=8*1024*1024


def _unique(pairs):
    value={}
    for key,item in pairs:
        if key in value:
            raise BrowserValidationRejected('browser_validation_duplicate_report_key')
        value[key]=item
    return value


class BrowserValidationPending(RuntimeError):
    wait_required=True
    retry_after=15
    def __init__(self,reason,deadline):
        super().__init__(reason)
        self.deadline=deadline


class BrowserValidationRejected(Rejected):
    effect_observed=True


class BrowserValidation:
    def __init__(self,store,ecs,s3,config):
        self.store,self.ecs,self.s3,self.config=store,ecs,s3,config

    def _config(self):
        value=self.config
        required={'enabled','account_id','region','cluster','task_definition','image_digest','container_name','subnet_ids','security_group_ids','artifact_bucket','output_bucket','deadline_seconds'}
        if not isinstance(value,dict) or set(value)!=required or value.get('enabled') is not True:
            raise IntegrationUnavailable('browser_validation_not_configured_or_enabled')
        if not isinstance(value['region'],str) or not re.fullmatch('[a-z]{2}(?:-[a-z]+)+-[0-9]',value['region']) or value['account_id']!=ACCOUNT or not re.fullmatch(r'arn:aws:ecs:'+re.escape(value['region'])+':'+ACCOUNT+r':cluster/[A-Za-z0-9_-]+',value.get('cluster','')) or not re.fullmatch(r'arn:aws:ecs:'+re.escape(value['region'])+':'+ACCOUNT+r':task-definition/[A-Za-z0-9_-]+:[1-9][0-9]*',value.get('task_definition','')):
            raise BrowserValidationRejected('browser_validation_target_rejected')
        if not re.fullmatch('sha256:[0-9a-f]{64}',value.get('image_digest','')) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',value.get('container_name','')):
            raise BrowserValidationRejected('browser_validation_image_required')
        for key,prefix in (('subnet_ids','subnet-'),('security_group_ids','sg-')):
            if not isinstance(value[key],list) or not 1<=len(value[key])<=3 or len(set(value[key]))!=len(value[key]) or any(not isinstance(item,str) or not re.fullmatch(prefix+'[0-9a-f]{8,17}',item) for item in value[key]):
                raise BrowserValidationRejected('browser_validation_network_rejected')
        for key in ('artifact_bucket','output_bucket'):
            if not isinstance(value[key],str) or not re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',value[key]) or '..' in value[key]:
                raise BrowserValidationRejected('browser_validation_bucket_rejected')
        if type(value['deadline_seconds']) is not int or not 60<=value['deadline_seconds']<=600:
            raise BrowserValidationRejected('browser_validation_deadline_rejected')
        return value

    @staticmethod
    def _call(client,method,guard,**kwargs):
        guard()
        return getattr(client,method)(**kwargs)

    def preflight(self,site,guard):
        config=self._config()
        if not isinstance(site.get('site_id'),str) or not re.fullmatch('[A-Za-z0-9_-]{1,200}',site['site_id']):
            raise BrowserValidationRejected('browser_validation_site_required')
        response=self._call(self.ecs,'describe_task_definition',guard,taskDefinition=config['task_definition'])
        definition=response.get('taskDefinition',{})
        containers=definition.get('containerDefinitions',[])
        if definition.get('taskDefinitionArn')!=config['task_definition'] or definition.get('taskRoleArn') or definition.get('networkMode')!='awsvpc' or 'FARGATE' not in definition.get('requiresCompatibilities',[]) or definition.get('runtimePlatform')!={'operatingSystemFamily':'LINUX','cpuArchitecture':'X86_64'} or len(containers)!=1:
            raise BrowserValidationRejected('browser_validation_task_isolation_rejected')
        container=containers[0]
        allowed_env={'AWS_EC2_METADATA_DISABLED':'true','HOME':'/tmp','TMPDIR':'/tmp','PYTHONDONTWRITEBYTECODE':'1'}
        actual_env=container.get('environment',[])
        if any(item.get('name') not in allowed_env or item.get('value')!=allowed_env[item['name']] for item in actual_env):
            raise BrowserValidationRejected('browser_validation_task_environment_rejected')
        mounts=container.get('mountPoints',[])
        volumes=definition.get('volumes',[])
        scratch=[mount for mount in mounts if mount.get('containerPath')=='/tmp' and mount.get('readOnly') is False]
        user=container.get('user','').split(':')[0]
        capabilities=container.get('linuxParameters',{}).get('capabilities',{})
        if container.get('name')!=config['container_name'] or not container.get('image','').endswith('@'+config['image_digest']) or container.get('readonlyRootFilesystem') is not True or user not in ('1000','10001') or container.get('privileged',False) or container.get('secrets') or container.get('environmentFiles') or container.get('repositoryCredentials') or container.get('entryPoint') or container.get('command') or capabilities.get('add') or 'ALL' not in capabilities.get('drop',[]) or len(scratch)!=1 or len(mounts)!=1 or len(volumes)!=1 or volumes[0]!={'name':scratch[0]['sourceVolume']}:
            raise BrowserValidationRejected('browser_validation_container_isolation_rejected')
        for bucket in {config['artifact_bucket'],config['output_bucket']}:
            self._call(self.s3,'head_bucket',guard,Bucket=bucket,ExpectedBucketOwner=ACCOUNT)
        return {'ready':True,'task_definition':config['task_definition'],'image_digest':config['image_digest']}

    def _identity(self,site,preview,artifact_key,operation_id):
        config=self._config()
        try:
            if str(uuid.UUID(operation_id))!=operation_id:
                raise ValueError()
        except (ValueError,AttributeError):
            raise BrowserValidationRejected('browser_validation_operation_invalid') from None
        digest=preview.get('artifact_sha256','')
        commit=preview.get('source_commit','')
        try:
            package_id=preview.get('package_operation_id')
            if str(uuid.UUID(package_id))!=package_id:
                raise ValueError()
        except (ValueError,AttributeError,TypeError):
            raise BrowserValidationRejected('browser_validation_package_identity_required') from None
        if not re.fullmatch('[0-9a-f]{64}',digest) or not re.fullmatch('[0-9a-f]{40}',commit) or preview.get('site_id')!=site.get('site_id') or artifact_key!='artifacts/'+site['site_id']+'/'+digest+'/site.zip':
            raise BrowserValidationRejected('browser_validation_artifact_binding_rejected')
        token=fingerprint({'operation_id':operation_id,'artifact_sha256':digest,'source_commit':commit,'site_id':site['site_id'],'package_operation_id':package_id})
        key='browser-validation:'+site['site_id']+':'+operation_id+':'+digest
        prefix='browser-validation/'+site['site_id']+'/'+operation_id+'/'+digest
        return config,key,token,prefix

    def _get(self,bucket,key,limit,guard):
        response=self._call(self.s3,'get_object',guard,Bucket=bucket,Key=key,ExpectedBucketOwner=ACCOUNT)
        body=response['Body']
        try:
            content=body.read(limit+1)
        finally:
            body.close()
        if len(content)>limit:
            raise BrowserValidationRejected('browser_validation_output_size_exceeded')
        return content

    def _row(self,site,preview,artifact_key,operation):
        config,key,token,prefix=self._identity(site,preview,artifact_key,operation)
        row=self.store.get(key)
        if row and (row.get('config_fingerprint')!=fingerprint(config) or row.get('artifact_key')!=artifact_key or row.get('source_commit')!=preview['source_commit'] or row.get('validation_id')!=token or row.get('package_operation_id')!=preview['package_operation_id']):
            raise BrowserValidationRejected('browser_validation_intent_changed')
        return config,key,token,prefix,row

    def _tasks(self,config,row,guard):
        arns=[row['task_arn']] if row.get('task_arn') else None
        if arns is None:
            listed=self._call(self.ecs,'list_tasks',guard,cluster=config['cluster'],startedBy=row['validation_id'][:32],maxResults=10)
            arns=listed.get('taskArns',[])
            if listed.get('nextToken') or len(arns)>1:
                raise BrowserValidationRejected('browser_validation_task_ambiguous')
        if not arns:
            return None
        described=self._call(self.ecs,'describe_tasks',guard,cluster=config['cluster'],tasks=arns)
        tasks=described.get('tasks',[])
        if described.get('failures') or len(tasks)!=1:
            raise BrowserValidationPending('browser_validation_task_not_visible',row['deadline'])
        task=tasks[0]
        if task.get('clusterArn')!=config['cluster'] or task.get('taskDefinitionArn')!=config['task_definition'] or task.get('startedBy')!=row['validation_id'][:32] or task.get('group')!='family:'+config['task_definition'].split('/')[-1].split(':')[0]:
            raise BrowserValidationRejected('browser_validation_task_binding_mismatch')
        return task

    def _result(self,config,row,task,guard):
        if task.get('lastStatus')!='STOPPED':
            raise BrowserValidationPending('browser_validation_running',row['deadline'])
        containers=task.get('containers',[])
        if len(containers)!=1 or containers[0].get('name')!=config['container_name'] or type(containers[0].get('exitCode')) is not int or containers[0].get('exitCode')!=0 or containers[0].get('imageDigest')!=config['image_digest']:
            raise BrowserValidationRejected('browser_validation_task_failed')
        try:
            raw=self._get(config['output_bucket'],row['output_keys']['report'],MAX_REPORT,guard)
        except Exception as error:
            if getattr(error,'response',{}).get('Error',{}).get('Code') in ('NoSuchKey','404','NotFound'):
                raise BrowserValidationPending('browser_validation_report_missing',row['deadline']) from None
            raise
        try:
            report=json.loads(raw,object_pairs_hook=_unique)
        except (ValueError,UnicodeError):
            raise BrowserValidationRejected('browser_validation_report_invalid') from None
        expected={'schema_version':1,'kind':'browser-validation','site_id':row['site_id'],'operation_id':row['operation_id'],
            'validation_id':row['validation_id'],'artifact_sha256':row['artifact_sha256'],'source_commit':row['source_commit'],
            'source_sha256':row['source_sha256']}
        if not isinstance(report,dict) or any(report.get(key)!=value for key,value in expected.items()) or type(report.get('schema_version')) is not int or report.get('verified') is not True or report.get('chromium_os_sandbox') is not False or not re.fullmatch('[0-9a-f]{64}',report.get('source_sha256','')):
            raise BrowserValidationRejected('browser_validation_report_binding_failed')
        states=report.get('viewports')
        if not isinstance(states,list) or len(states)!=2 or any(not isinstance(state,dict) for state in states) or {state.get('name') for state in states}!={'desktop','mobile'}:
            raise BrowserValidationRejected('browser_validation_viewport_evidence_missing')
        for state in states:
            viewport=(1440,1000) if state['name']=='desktop' else (390,844)
            metrics=state.get('metrics',{})
            if not isinstance(metrics,dict) or state.get('ok') is not True or (state.get('width'),state.get('height'))!=viewport or state.get('errors')!=[] or state.get('blocked_request_count')!=0 or metrics.get('width')!=viewport[0] or type(metrics.get('scrollWidth')) not in (int,float) or not 0<metrics['scrollWidth']<=viewport[0]+1 or type(metrics.get('text')) is not int or metrics['text']<=0 or type(metrics.get('height')) not in (int,float) or not 0<metrics['height']<100000 or type(state.get('screenshot_size')) is not int or not 8<=state['screenshot_size']<=MAX_SCREENSHOT:
                raise BrowserValidationRejected('browser_validation_render_failed')
            image=self._get(config['output_bucket'],row['output_keys'][state['name']],MAX_SCREENSHOT,guard)
            if not image.startswith(b'\x89PNG\r\n\x1a\n') or len(image)!=state.get('screenshot_size') or sha256(image)!=state.get('screenshot_sha256'):
                raise BrowserValidationRejected('browser_validation_screenshot_mismatch')
        return {'verified':True,'source_commit':row['source_commit'],'artifact_sha256':row['artifact_sha256'],
            'source_sha256':report['source_sha256'],'validation_id':row['validation_id'],'task_arn':task['taskArn'],
            'report_key':row['output_keys']['report'],'report_sha256':sha256(raw),
            'screenshot_keys':[row['output_keys'][name] for name in ('desktop','mobile')],
            'image_digest':config['image_digest'],'chromium_os_sandbox':False}

    def validate(self,site,preview,artifact_key,operation_id,guard):
        self.preflight(site,guard)
        config,key,token,prefix,row=self._row(site,preview,artifact_key,operation_id)
        if row is None:
            data=self._get(config['artifact_bucket'],artifact_key,MAX_TRANSPORT,guard)
            if sha256(data)!=preview['artifact_sha256']:
                raise BrowserValidationRejected('browser_validation_input_digest_mismatch')
            from publisher import unpack_release
            try:
                _,metadata=unpack_release(data,preview)
            except (ValueError,KeyError):
                raise BrowserValidationRejected('browser_validation_input_invalid') from None
            deadline=int(time.time())+config['deadline_seconds']
            output_keys={'desktop':prefix+'/desktop.png','mobile':prefix+'/mobile.png','report':prefix+'/report.json'}
            guard()
            get_url=self.s3.generate_presigned_url('get_object',Params={'Bucket':config['artifact_bucket'],'Key':artifact_key,'ExpectedBucketOwner':ACCOUNT},ExpiresIn=900)
            put_urls={}
            for name,object_key in output_keys.items():
                guard()
                put_urls[name]=self.s3.generate_presigned_url('put_object',Params={'Bucket':config['output_bucket'],'Key':object_key,'ContentType':'application/json' if name=='report' else 'image/png','ExpectedBucketOwner':ACCOUNT,'IfNoneMatch':'*'},ExpiresIn=900)
            job={'site_id':site['site_id'],'operation_id':operation_id,'validation_id':token,'artifact_sha256':preview['artifact_sha256'],
                'source_commit':preview['source_commit'],'package_operation_id':preview.get('package_operation_id'),'artifact_get_url':get_url,'output_put_urls':put_urls,'deadline':deadline}
            request={'cluster':config['cluster'],'taskDefinition':config['task_definition'],'launchType':'FARGATE','platformVersion':'1.4.0','count':1,
                'clientToken':token,'startedBy':token[:32],'enableExecuteCommand':False,
                'networkConfiguration':{'awsvpcConfiguration':{'subnets':config['subnet_ids'],'securityGroups':config['security_group_ids'],'assignPublicIp':'ENABLED'}},
                'overrides':{'containerOverrides':[{'name':config['container_name'],'environment':[{'name':'HP_VALIDATION_JOB','value':json.dumps(job,sort_keys=True,separators=(',',':'))}]}]}}
            if len(json.dumps(request['overrides']).encode())>8000:
                raise BrowserValidationRejected('browser_validation_launch_override_budget')
            row={'site_id':site['site_id'],'operation_id':operation_id,'source_commit':preview['source_commit'],
                'package_operation_id':preview['package_operation_id'],
                'artifact_sha256':preview['artifact_sha256'],'artifact_key':artifact_key,'validation_id':token,
                'source_sha256':metadata['source_sha256'],
                'config_fingerprint':fingerprint(config),'deadline':deadline,'output_keys':output_keys,'request':request}
            guard()
            self.store.put(key,row,None)
            row=self.store.get(key)
        if time.time()>row['deadline']:
            raise BrowserValidationRejected('browser_validation_deadline_exceeded')
        task=self._tasks(config,row,guard)
        if task is None:
            # ClientToken plus the exact persisted request makes lost RunTask
            # acknowledgements safely replayable only under active authority.
            try:
                result=self._call(self.ecs,'run_task',guard,**row['request'])
            except (Rejected,Busy):
                raise
            except Exception:
                raise BrowserValidationPending('browser_validation_launch_ack_unknown',row['deadline']) from None
            if result.get('failures'):
                raise BrowserValidationRejected('browser_validation_launch_failed')
            launched=result.get('tasks',[])
            if len(launched)!=1 or not isinstance(launched[0].get('taskArn'),str):
                raise BrowserValidationPending('browser_validation_launch_identity_unknown',row['deadline'])
            guard()
            row=self.store.put(key,{**row,'task_arn':launched[0]['taskArn']},row['_version'])
            task=self._tasks(config,row,guard)
            if task is None:
                raise BrowserValidationPending('browser_validation_launch_not_visible',row['deadline'])
        return self._result(config,row,task,guard)

    def reconcile(self,site,preview,artifact_key,operation_id,guard):
        config,key,token,prefix,row=self._row(site,preview,artifact_key,operation_id)
        if row is None:
            return {'safe_to_resume':True,'prewrite_proven':True}
        if time.time()>row['deadline']:
            raise BrowserValidationRejected('browser_validation_deadline_exceeded')
        task=self._tasks(config,row,guard)
        if task is None:
            return {'safe_to_resume':True}
        return self._result(config,row,task,guard)
