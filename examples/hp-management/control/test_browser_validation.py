from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import time
import unittest
import zipfile
from urllib.parse import urlsplit,unquote

from browser_validation import ACCOUNT, BrowserValidation, BrowserValidationPending, BrowserValidationRejected
from bundles import sha256
from executor import IntegrationUnavailable
from service import fingerprint
from store import MemoryStore
from validator.render import RenderError, unpack

OPERATION='23456789-1234-4234-8234-123456789abc'
PACKAGE='34567890-1234-4234-8234-123456789abc'
COMMIT='a'*40
IMAGE='sha256:'+'b'*64
CLUSTER='arn:aws:ecs:ap-northeast-1:'+ACCOUNT+':cluster/hp-validation'
DEFINITION='arn:aws:ecs:ap-northeast-1:'+ACCOUNT+':task-definition/hp-validator:1'


def artifact(paths=None):
    paths=paths or {'index.html':b'<!doctype html><html lang="en"><meta charset="utf-8"><title>Preview</title><body><h1>Preview</h1></body></html>'}
    source_hash=fingerprint([{'path':p,'sha256':sha256(v),'size':len(v)} for p,v in sorted(paths.items())])
    metadata={'schema_version':1,'source_commit':COMMIT,'operation_id':PACKAGE,'source_sha256':source_hash,'version':source_hash}
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as archive:
        for name,value in paths.items(): archive.writestr(name,value)
        archive.writestr('version.json',json.dumps(metadata))
    return out.getvalue(),metadata


class Missing(Exception):
    response={'Error':{'Code':'NoSuchKey'}}


class FakeS3:
    def __init__(self):
        self.objects={};self.calls=[];self.unknown_put_ack=False;self.hide_manifest=False;self.before_put=None
    def head_bucket(self,**args):
        self.calls.append(('head_bucket',args))
        assert args['ExpectedBucketOwner']==ACCOUNT
        return {}
    def get_object(self,**args):
        self.calls.append(('get_object',args))
        assert args['ExpectedBucketOwner']==ACCOUNT
        if self.hide_manifest and args['Key'].endswith('/job.json'): raise Missing()
        if (args['Bucket'],args['Key']) not in self.objects: raise Missing()
        return {'Body':io.BytesIO(self.objects[args['Bucket'],args['Key']])}
    def put_object(self,**args):
        self.calls.append(('put_object',args))
        assert args['ExpectedBucketOwner']==ACCOUNT and args['IfNoneMatch']=='*'
        assert args['ContentType']=='application/json' and args['ServerSideEncryption']=='AES256'
        if self.before_put: self.before_put(args)
        key=(args['Bucket'],args['Key'])
        if key in self.objects:
            error=RuntimeError('already exists');error.response={'Error':{'Code':'PreconditionFailed'}};raise error
        self.objects[key]=args['Body']
        if self.unknown_put_ack: raise OSError('manifest PUT response lost')
        return {}
    def generate_presigned_url(self,method,Params,ExpiresIn):
        self.calls.append(('presign',{'method':method,'params':Params,'expiry':ExpiresIn}))
        assert ExpiresIn==900
        assert Params['ExpectedBucketOwner']==ACCOUNT
        if method=='put_object': assert Params['IfNoneMatch']=='*'
        return 'https://'+Params['Bucket']+'.s3.amazonaws.com/'+Params['Key']+'?signature=FAKE'


def s3_location(url):
    parsed=urlsplit(url)
    return parsed.hostname.split('.s3',1)[0],unquote(parsed.path.lstrip('/'))


class FakeECS:
    def __init__(self,s3):
        self.s3,self.calls=s3,[]
        self.task=None;self.requests=[];self.unknown_ack=False;self.hide_tasks=False
        self.missing_output=False;self.bad_report=False;self.running=False
        self.definition={'taskDefinitionArn':DEFINITION,'networkMode':'awsvpc','requiresCompatibilities':['FARGATE'],
            'runtimePlatform':{'operatingSystemFamily':'LINUX','cpuArchitecture':'X86_64'},
            'containerDefinitions':[{'name':'validator','image':'example.invalid/reviewed@'+IMAGE,'readonlyRootFilesystem':True,
                'user':'1000:1000','privileged':False,'environment':[{'name':'AWS_EC2_METADATA_DISABLED','value':'true'}],
                'linuxParameters':{'capabilities':{'drop':['ALL']}},'mountPoints':[{'sourceVolume':'scratch','containerPath':'/tmp','readOnly':False}]}],
            'volumes':[{'name':'scratch'}]}
    def describe_task_definition(self,**args): self.calls.append(('describe_task_definition',args));return {'taskDefinition':deepcopy(self.definition)}
    def list_tasks(self,**args):
        self.calls.append(('list_tasks',args))
        assert args['cluster']==CLUSTER
        return {'taskArns':[] if self.hide_tasks or not self.task else [self.task['taskArn']]}
    def describe_tasks(self,**args): self.calls.append(('describe_tasks',args));return {'tasks':[deepcopy(self.task)]}
    def run_task(self,**args):
        self.calls.append(('run_task',args));self.requests.append(deepcopy(args))
        assert args['taskDefinition']==DEFINITION and args['cluster']==CLUSTER
        assert args['launchType']=='FARGATE' and args['enableExecuteCommand'] is False
        assert 'taskRoleArn' not in args['overrides']
        envelope=json.loads(args['overrides']['containerOverrides'][0]['environment'][0]['value'])
        assert envelope['kind']=='browser-validation-job'
        job_bytes=self.s3.objects[s3_location(envelope['job_get_url'])]
        assert sha256(job_bytes)==envelope['job_sha256']
        job=json.loads(job_bytes)
        assert job['validation_id']==args['clientToken']
        if self.task is None:
            self.task={'taskArn':'arn:aws:ecs:ap-northeast-1:'+ACCOUNT+':task/hp-validation/'+'c'*32,
                'clusterArn':CLUSTER,'taskDefinitionArn':DEFINITION,'startedBy':args['startedBy'],'group':'family:hp-validator',
                'lastStatus':'RUNNING' if self.running else 'STOPPED',
                'containers':[{'name':self.definition['containerDefinitions'][0]['name'],'exitCode':0,'imageDigest':IMAGE}]}
        if not self.missing_output:
            metadata=unpack(self.s3.objects[s3_location(job['artifact_get_url'])],None,job['artifact_sha256'],job['source_commit'])
            report={key:job[key] for key in ('site_id','operation_id','validation_id','artifact_sha256','source_commit')}
            report.update({'job_sha256':envelope['job_sha256'],'schema_version':1,'kind':'browser-validation','source_sha256':metadata['source_sha256'],'verified':True,'chromium_os_sandbox':False,'viewports':[]})
            for name,width,height in [('desktop',1440,1000),('mobile',390,844)]:
                image=b'\x89PNG\r\n\x1a\nFAKE-'+name.encode()
                report['viewports'].append({'name':name,'width':width,'height':height,'ok':True,'errors':[],
                    'blocked_request_count':0,'metrics':{'width':width,'scrollWidth':width,'height':height,'text':7},
                    'screenshot_sha256':sha256(image),'screenshot_size':len(image)})
                self.s3.objects[s3_location(job['output_put_urls'][name])]=image
            if self.bad_report: report['artifact_sha256']='f'*64
            self.s3.objects[s3_location(job['output_put_urls']['report'])]=json.dumps(report).encode()
        if self.unknown_ack: raise OSError('RunTask response lost')
        return {'tasks':[deepcopy(self.task)]}


class BrowserValidationTest(unittest.TestCase):
    def setUp(self):
        self.store,self.s3=MemoryStore(),FakeS3()
        self.ecs=FakeECS(self.s3)
        self.config={'enabled':True,'account_id':ACCOUNT,'region':'ap-northeast-1','cluster':CLUSTER,'task_definition':DEFINITION,
            'image_digest':IMAGE,'container_name':'validator','subnet_ids':['subnet-12345678'],'security_group_ids':['sg-12345678'],
            'artifact_bucket':'artifact-bucket','output_bucket':'output-bucket','deadline_seconds':600}
        self.site={'site_id':'sample-site'}
        self.data,self.metadata=artifact()
        self.key='artifacts/sample-site/'+sha256(self.data)+'/site.zip'
        self.preview={'site_id':'sample-site','artifact_sha256':sha256(self.data),'source_commit':COMMIT,'package_operation_id':PACKAGE}
        self.s3.objects['artifact-bucket',self.key]=self.data
        self.validator=BrowserValidation(self.store,self.ecs,self.s3,self.config)
    def guard(self): pass
    def validate(self): return self.validator.validate(self.site,self.preview,self.key,OPERATION,self.guard)
    def reconcile(self):
        before=deepcopy(self.store.rows);calls=len(self.ecs.calls);s3_calls=len(self.s3.calls)
        try: return self.validator.reconcile(self.site,self.preview,self.key,OPERATION,self.guard)
        finally:
            self.assertEqual(before,self.store.rows)
            self.assertFalse(any(method=='run_task' for method,_ in self.ecs.calls[calls:]))
            self.assertFalse(any(method in ('presign','put_object') for method,_ in self.s3.calls[s3_calls:]))

    def test_exact_input_output_and_successful_readonly_reconciliation(self):
        receipt=self.validate()
        self.assertTrue(receipt['verified'])
        self.assertEqual(receipt['artifact_sha256'],sha256(self.data))
        self.assertEqual(receipt['source_sha256'],self.metadata['source_sha256'])
        self.assertEqual(len(receipt['screenshot_keys']),2)
        self.assertTrue(self.reconcile()['verified'])
        self.assertEqual(len(self.ecs.requests),1)
        presigns=[args for method,args in self.s3.calls if method=='presign']
        self.assertEqual(len(presigns),5)
        self.assertEqual({args['params']['Bucket'] for args in presigns},{'artifact-bucket','output-bucket'})

    def test_manifest_and_exact_request_are_durable_before_conditional_put(self):
        def inspect(args):
            row=next(iter(self.store.rows.values()))
            self.assertEqual(row['manifest_state'],'put_admitted')
            self.assertEqual(row['launch_state'],'not_admitted')
            self.assertEqual(args['Body'],row['job_json'].encode())
            self.assertEqual(sha256(args['Body']),row['job_sha256'])
            self.assertEqual(fingerprint(row['request']),row['request_sha256'])
            envelope=json.loads(row['request']['overrides']['containerOverrides'][0]['environment'][0]['value'])
            self.assertEqual(set(envelope),{'schema_version','kind','job_get_url','job_sha256','deadline'})
            self.assertNotIn('artifact_get_url',envelope)
            self.assertNotIn('output_put_urls',envelope)
            self.assertFalse(self.ecs.requests)
        self.s3.before_put=inspect
        self.assertTrue(self.validate()['verified'])

    def test_unknown_manifest_put_ack_restart_reuses_frozen_object_and_run_request(self):
        self.s3.unknown_put_ack=True
        with self.assertRaises(BrowserValidationPending): self.validate()
        original=deepcopy(next(iter(self.store.rows.values())))
        self.assertEqual(original['launch_state'],'not_admitted')
        self.assertFalse(self.ecs.requests)
        self.assertEqual(sum(method=='put_object' for method,_ in self.s3.calls),1)
        self.s3.unknown_put_ack=False
        self.validator=BrowserValidation(self.store,self.ecs,self.s3,self.config)
        self.assertTrue(self.validate()['verified'])
        self.assertEqual(self.ecs.requests,[original['request']])
        self.assertEqual(sum(method=='put_object' for method,_ in self.s3.calls),1)
        self.assertEqual(sum(method=='presign' for method,_ in self.s3.calls),5)

    def test_tampered_private_manifest_is_rejected_before_launch(self):
        self.s3.unknown_put_ack=True
        with self.assertRaises(BrowserValidationPending): self.validate()
        row=next(iter(self.store.rows.values()))
        self.s3.objects['output-bucket',row['job_key']]+=b' '
        self.s3.unknown_put_ack=False
        with self.assertRaisesRegex(BrowserValidationRejected,'manifest_readback_mismatch'):
            self.validate()
        self.assertFalse(self.ecs.requests)
        self.assertEqual(sum(method=='put_object' for method,_ in self.s3.calls),1)

    def test_prelaunch_readonly_reconciliation_has_explicit_no_launch_proof_without_put(self):
        self.s3.before_put=lambda args: (_ for _ in ()).throw(OSError('write response unknown'))
        with self.assertRaises(BrowserValidationPending): self.validate()
        row=deepcopy(next(iter(self.store.rows.values())))
        self.assertEqual(row['launch_state'],'not_admitted')
        result=self.reconcile()
        self.assertTrue(result['safe_to_resume'])
        self.assertTrue(result['launch_prewrite_proven'])
        self.assertEqual(result['manifest_state'],'put_admitted')
        self.assertFalse(self.ecs.requests)
        self.s3.before_put=None
        self.assertTrue(self.validate()['verified'])
        self.assertEqual(self.ecs.requests[0],row['request'])

    def test_invisible_task_after_launch_admission_never_claims_prewrite_proof(self):
        self.ecs.unknown_ack=True;self.ecs.hide_tasks=True
        with self.assertRaises(BrowserValidationPending): self.validate()
        self.assertEqual(next(iter(self.store.rows.values()))['launch_state'],'admitted')
        self.assertEqual(self.reconcile(),{'safe_to_resume':True})
        self.assertEqual(len(self.ecs.requests),1)

    def test_legacy_row_without_launch_marker_cannot_prove_no_task(self):
        self.ecs.unknown_ack=True;self.ecs.hide_tasks=True
        with self.assertRaises(BrowserValidationPending): self.validate()
        key=next(iter(self.store.rows))
        row=self.store.rows[key]
        for name in ('launch_state','job_json','job_key','job_sha256','manifest_state','request_sha256'):
            row.pop(name,None)
        self.assertEqual(self.reconcile(),{'safe_to_resume':True})
        self.assertEqual(len(self.ecs.requests),1)

    def test_missing_configuration_and_unsafe_task_definition_fail_preflight(self):
        self.config['enabled']=False
        with self.assertRaises(IntegrationUnavailable): self.validator.preflight(self.site,self.guard)
        self.config['enabled']=True
        for field,value in [('taskRoleArn','arn:aws:iam::'+ACCOUNT+':role/application'),('networkMode','host')]:
            original=self.ecs.definition.get(field)
            self.ecs.definition[field]=value
            with self.assertRaises(BrowserValidationRejected): self.validator.preflight(self.site,self.guard)
            if original is None: self.ecs.definition.pop(field)
            else: self.ecs.definition[field]=original
        self.ecs.definition['containerDefinitions'][0]['user']='0'
        with self.assertRaises(BrowserValidationRejected): self.validator.preflight(self.site,self.guard)
        self.assertFalse(self.ecs.requests)

    def test_ambiguous_launch_readonly_finds_task_and_reuses_exact_intent(self):
        self.ecs.unknown_ack=True
        with self.assertRaises(BrowserValidationPending): self.validate()
        self.assertTrue(self.reconcile()['verified'])
        self.assertEqual(len(self.ecs.requests),1)

    def test_aws_empty_host_scratch_volume_is_ephemeral_but_shared_volumes_fail(self):
        self.ecs.definition['volumes']=[{'name':'scratch','host':{}}]
        self.assertTrue(self.validator.preflight(self.site,self.guard)['ready'])
        for volume in ({'name':'scratch','host':{'sourcePath':'/tmp'}},
                       {'name':'scratch','host':None},
                       {'name':'scratch','efsVolumeConfiguration':{'fileSystemId':'fs-other'}},
                       {'name':'scratch','host':{},'dockerVolumeConfiguration':{}},
                       {'name':'other','host':{}}):
            with self.subTest(volume=volume):
                self.ecs.definition['volumes']=[volume]
                with self.assertRaises(BrowserValidationRejected):
                    self.validator.preflight(self.site,self.guard)
        self.assertFalse(self.ecs.requests)

    def test_ambiguous_invisible_stopped_task_can_only_replay_identical_client_token(self):
        self.ecs.unknown_ack=True;self.ecs.hide_tasks=True
        with self.assertRaises(BrowserValidationPending): self.validate()
        self.assertEqual(self.reconcile(),{'safe_to_resume':True})
        self.ecs.unknown_ack=False
        self.assertTrue(self.validate()['verified'])
        self.assertEqual(self.ecs.requests[0],self.ecs.requests[1])

    def test_running_missing_outputs_failed_task_and_tampered_report_never_succeed(self):
        self.ecs.running=True
        with self.assertRaises(BrowserValidationPending): self.validate()
        self.ecs.task['lastStatus']='STOPPED'
        self.ecs.task['containers'][0]['exitCode']=1
        with self.assertRaises(BrowserValidationRejected): self.reconcile()
        self.ecs.task['containers'][0]['exitCode']=0
        report_key=next(key for bucket,key in self.s3.objects if key.endswith('/report.json'))
        self.s3.objects['output-bucket',report_key]=b'{}'
        with self.assertRaises(BrowserValidationRejected): self.reconcile()
        self.s3.objects.pop(('output-bucket',report_key))
        with self.assertRaises(BrowserValidationPending): self.reconcile()

    def test_tampered_screenshot_and_different_source_hash_rejected(self):
        self.validate()
        report_key=next(key for bucket,key in self.s3.objects if key.endswith('/report.json'))
        original_report=self.s3.objects['output-bucket',report_key]
        report=json.loads(original_report)
        report['source_sha256']='f'*64
        self.s3.objects['output-bucket',report_key]=json.dumps(report).encode()
        with self.assertRaises(BrowserValidationRejected): self.reconcile()
        self.s3.objects['output-bucket',report_key]=original_report
        mobile_key=next(key for bucket,key in self.s3.objects if key.endswith('/mobile.png'))
        self.s3.objects['output-bucket',mobile_key]=b'wrong'
        with self.assertRaises(BrowserValidationRejected): self.reconcile()

    def test_deadline_and_input_binding_fail_closed(self):
        self.s3.objects['artifact-bucket',self.key]=b'tampered'
        with self.assertRaises(BrowserValidationRejected): self.validate()
        self.assertFalse(self.ecs.requests)
        self.s3.objects['artifact-bucket',self.key]=self.data
        self.validate()
        row_key=next(iter(self.store.rows))
        self.store.rows[row_key]['deadline']=time.time()-1
        with self.assertRaises(BrowserValidationRejected): self.reconcile()

    def test_renderer_rejects_archive_paths_and_source_metadata(self):
        for paths in ({'index.html':b'ok','../escape.js':b'bad'},{'index.html':b'ok','A.txt':b'one','a.txt':b'two'}):
            data,_=artifact(paths)
            with self.assertRaises(RenderError): unpack(data,None,sha256(data),COMMIT)
        data,_=artifact()
        with self.assertRaises(RenderError): unpack(data,None,'f'*64,COMMIT)
        with self.assertRaises(RenderError): unpack(data,None,sha256(data),'f'*40)


if __name__=='__main__': unittest.main()
