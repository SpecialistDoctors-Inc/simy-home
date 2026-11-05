from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import time
import unittest
import zipfile

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
    def __init__(self): self.objects={};self.calls=[]
    def head_bucket(self,**args):
        self.calls.append(('head_bucket',args))
        assert args['ExpectedBucketOwner']==ACCOUNT
        return {}
    def get_object(self,**args):
        self.calls.append(('get_object',args))
        assert args['ExpectedBucketOwner']==ACCOUNT
        if (args['Bucket'],args['Key']) not in self.objects: raise Missing()
        return {'Body':io.BytesIO(self.objects[args['Bucket'],args['Key']])}
    def generate_presigned_url(self,method,Params,ExpiresIn):
        self.calls.append(('presign',{'method':method,'params':Params,'expiry':ExpiresIn}))
        assert ExpiresIn==900
        assert Params['ExpectedBucketOwner']==ACCOUNT
        if method=='put_object': assert Params['IfNoneMatch']=='*'
        return 'https://'+Params['Bucket']+'.s3.amazonaws.com/'+Params['Key']+'?signature=FAKE'


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
        job=json.loads(args['overrides']['containerOverrides'][0]['environment'][0]['value'])
        assert job['validation_id']==args['clientToken']
        if self.task is None:
            self.task={'taskArn':'arn:aws:ecs:ap-northeast-1:'+ACCOUNT+':task/hp-validation/'+'c'*32,
                'clusterArn':CLUSTER,'taskDefinitionArn':DEFINITION,'startedBy':args['startedBy'],'group':'family:hp-validator',
                'lastStatus':'RUNNING' if self.running else 'STOPPED',
                'containers':[{'name':'validator','exitCode':0,'imageDigest':IMAGE}]}
        if not self.missing_output:
            input_key=job['artifact_get_url'].split('.amazonaws.com/',1)[1].split('?',1)[0]
            metadata=unpack(self.s3.objects['artifact-bucket',input_key],None,job['artifact_sha256'],job['source_commit'])
            report={key:job[key] for key in ('site_id','operation_id','validation_id','artifact_sha256','source_commit')}
            report.update({'schema_version':1,'kind':'browser-validation','source_sha256':metadata['source_sha256'],'verified':True,'chromium_os_sandbox':False,'viewports':[]})
            for name,width,height in [('desktop',1440,1000),('mobile',390,844)]:
                image=b'\x89PNG\r\n\x1a\nFAKE-'+name.encode()
                report['viewports'].append({'name':name,'width':width,'height':height,'ok':True,'errors':[],
                    'blocked_request_count':0,'metrics':{'width':width,'scrollWidth':width,'height':height,'text':7},
                    'screenshot_sha256':sha256(image),'screenshot_size':len(image)})
                output_key=job['output_put_urls'][name].split('.amazonaws.com/',1)[1].split('?',1)[0]
                self.s3.objects['output-bucket',output_key]=image
            if self.bad_report: report['artifact_sha256']='f'*64
            report_key=job['output_put_urls']['report'].split('.amazonaws.com/',1)[1].split('?',1)[0]
            self.s3.objects['output-bucket',report_key]=json.dumps(report).encode()
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
            self.assertFalse(any(method=='presign' for method,_ in self.s3.calls[s3_calls:]))

    def test_exact_input_output_and_successful_readonly_reconciliation(self):
        receipt=self.validate()
        self.assertTrue(receipt['verified'])
        self.assertEqual(receipt['artifact_sha256'],sha256(self.data))
        self.assertEqual(receipt['source_sha256'],self.metadata['source_sha256'])
        self.assertEqual(len(receipt['screenshot_keys']),2)
        self.assertTrue(self.reconcile()['verified'])
        self.assertEqual(len(self.ecs.requests),1)
        presigns=[args for method,args in self.s3.calls if method=='presign']
        self.assertEqual(len(presigns),4)
        self.assertEqual({args['params']['Bucket'] for args in presigns},{'artifact-bucket','output-bucket'})

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
