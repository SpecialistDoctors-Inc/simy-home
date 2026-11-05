"""Real botocore presigning, fake credentials, and no S3/network calls."""
import json
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import boto3
from botocore.auth import S3SigV4QueryAuth
from botocore.awsrequest import AWSRequest
from botocore.config import Config
from botocore.credentials import Credentials

from hp_control import regional_s3_client

ACCOUNT = '209300895845'
REGION = 'ap-northeast-1'
TOKEN = 'fake-session-value/with+url=escapes' * 12


class S3SigningTests(unittest.TestCase):
    def setUp(self):
        self.session = boto3.Session(aws_access_key_id='ASIAFAKEACCESSKEY0000',
            aws_secret_access_key='fake-signing-value-not-a-real-key', aws_session_token=TOKEN)

    def client(self):
        actual = self.session.client
        with patch('boto3.client', side_effect=lambda *args, **kwargs: actual(*args, **kwargs)):
            return regional_s3_client(REGION)

    def test_production_factory_binds_sigv4_and_regional_endpoint_despite_ambient_override(self):
        with patch.dict('os.environ', {'AWS_ENDPOINT_URL_S3': 'https://attacker.example.invalid'}):
            client = self.client()
        self.assertEqual(client.meta.region_name, REGION)
        self.assertEqual(client.meta.endpoint_url, 'https://s3.' + REGION + '.amazonaws.com')
        self.assertEqual(client.meta.config.signature_version, 's3v4')
        with self.assertRaises(ValueError):
            regional_s3_client(None)
        with self.assertRaises(ValueError):
            regional_s3_client('https://attacker.example.invalid')

    def test_consumer_reuses_explicit_regional_client_for_artifacts_and_validator(self):
        from hp_control import consumer
        from store import MemoryStore
        s3 = self.client()
        environment = {'HP_TABLE_NAME': 'unit-test-only', 'HP_GOOGLE_OPERATOR_SECRET_ARN': 'unit-test-only',
            'HP_ARTIFACT_BUCKET': 'example-artifacts', 'HP_GITHUB_SECRET_ARN': 'unit-test-only',
            'HP_VALIDATOR_CONFIG': json.dumps({'region': REGION}), 'HP_PUBLISHER_ROLES': '{}',
            'AWS_REGION': 'us-west-2'}
        def aws_client(name, **kwargs):
            self.assertEqual((name, kwargs), ('ecs', {'region_name': REGION}))
            return object()
        with patch.dict('os.environ', environment), patch('hp_control.DynamoStore', return_value=MemoryStore()), \
                patch('hp_control.Secrets', return_value=lambda reference: None), \
                patch('hp_control.regional_s3_client', return_value=s3) as factory, \
                patch('boto3.client', side_effect=aws_client):
            executor = consumer()
        factory.assert_called_once_with(REGION)
        self.assertIs(executor.artifacts.client, s3)
        self.assertIs(executor.browser_validator.s3, s3)

    def test_real_presigned_get_signs_owner_header_once_not_a_duplicate_query_value(self):
        client = self.client()
        url = client.generate_presigned_url('get_object', Params={'Bucket': 'example-validator-artifacts',
            'Key': 'artifacts/example-site/' + 'a' * 64 + '/site.zip', 'ExpectedBucketOwner': ACCOUNT}, ExpiresIn=900)
        parsed = urlsplit(url)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.scheme, 'https')
        self.assertEqual(parsed.hostname, 'example-validator-artifacts.s3.' + REGION + '.amazonaws.com')
        self.assertEqual(query['X-Amz-Algorithm'], ['AWS4-HMAC-SHA256'])
        self.assertEqual(query['X-Amz-SignedHeaders'], ['host;x-amz-expected-bucket-owner'])
        self.assertEqual(query['X-Amz-Security-Token'], [TOKEN])
        self.assertIn('/' + REGION + '/s3/aws4_request', query['X-Amz-Credential'][0])
        self.assertFalse({'AWSAccessKeyId', 'Signature', 'Expires', 'x-amz-expected-bucket-owner'} & query.keys())

    def test_real_presigned_put_binds_owner_create_only_and_exact_content_type(self):
        client = self.client()
        signed = []
        client.meta.events.register('before-sign.s3.PutObject', lambda request, **kwargs: signed.append(request))
        for name, mime in [('desktop.png', 'image/png'), ('report.json', 'application/json')]:
            with self.subTest(name=name):
                url = client.generate_presigned_url('put_object', Params={'Bucket': 'example-validator-results',
                    'Key': 'browser-validation/example-site/' + 'b' * 36 + '/' + 'c' * 64 + '/' + name,
                    'ContentType': mime, 'ExpectedBucketOwner': ACCOUNT, 'IfNoneMatch': '*'}, ExpiresIn=900)
                query = parse_qs(urlsplit(url).query)
                self.assertEqual(query['X-Amz-SignedHeaders'], ['content-type;host;if-none-match;x-amz-expected-bucket-owner'])
                self.assertNotIn('x-amz-expected-bucket-owner', query)
                self.assertEqual(signed[-1].headers['Content-Type'], mime)
                self.assertEqual(signed[-1].headers['If-None-Match'], '*')
                self.assertEqual(signed[-1].headers['x-amz-expected-bucket-owner'], ACCOUNT)
                # The actual request's canonical form changes if a protected
                # transfer header is changed or removed. No S3 request occurs.
                auth = S3SigV4QueryAuth(Credentials('fake', 'fake'), 's3', REGION)
                correct = AWSRequest(method='PUT', url=url, headers={'Content-Type': mime,
                    'If-None-Match': '*', 'x-amz-expected-bucket-owner': ACCOUNT})
                wrong = AWSRequest(method='PUT', url=url, headers={'Content-Type': 'text/plain',
                    'If-None-Match': '*', 'x-amz-expected-bucket-owner': ACCOUNT})
                self.assertNotEqual(auth.canonical_request(correct), auth.canonical_request(wrong))

    def test_single_manifest_envelope_stays_bounded_with_real_sigv4_large_session_token(self):
        from browser_validation import BrowserValidation
        from bundles import sha256
        from store import MemoryStore
        from test_browser_validation import ACCOUNT, CLUSTER, DEFINITION, IMAGE, OPERATION, PACKAGE, COMMIT, FakeECS, FakeS3, artifact
        session=boto3.Session(aws_access_key_id='A'*20,aws_secret_access_key='X'*40,aws_session_token='x'*1800)
        with patch('boto3.client',side_effect=lambda *args,**kwargs:session.client(*args,**kwargs)):
            signer=regional_s3_client(REGION)
        class SignedStorage(FakeS3):
            def generate_presigned_url(self,method,Params,ExpiresIn):
                self.calls.append(('presign',{'method':method,'params':Params}))
                return signer.generate_presigned_url(method,Params=Params,ExpiresIn=ExpiresIn)
        s3=SignedStorage();ecs=FakeECS(s3);store=MemoryStore();site={'site_id':'s'*200}
        ecs.definition['containerDefinitions'][0]['name']='v'*64
        data,_=artifact();key='artifacts/'+site['site_id']+'/'+sha256(data)+'/site.zip'
        s3.objects['a'*63,key]=data
        config={'enabled':True,'account_id':ACCOUNT,'region':REGION,'cluster':CLUSTER,'task_definition':DEFINITION,
            'image_digest':IMAGE,'container_name':'v'*64,'subnet_ids':['subnet-12345678'],
            'security_group_ids':['sg-12345678'],'artifact_bucket':'a'*63,'output_bucket':'b'*63,'deadline_seconds':600}
        preview={'site_id':site['site_id'],'source_commit':COMMIT,'artifact_sha256':sha256(data),'package_operation_id':PACKAGE}
        result=BrowserValidation(store,ecs,s3,config).validate(site,preview,key,OPERATION,lambda:None)
        self.assertTrue(result['verified'])
        row=next(iter(store.rows.values()))
        self.assertGreater(len(row['job_json'].encode()),8000)
        self.assertLess(len(json.dumps(row['request']['overrides']).encode()),8000)
        envelope=json.loads(row['request']['overrides']['containerOverrides'][0]['environment'][0]['value'])
        query=parse_qs(urlsplit(envelope['job_get_url']).query)
        self.assertEqual(query['X-Amz-SignedHeaders'],['host;x-amz-expected-bucket-owner'])
        self.assertEqual(query['X-Amz-Algorithm'],['AWS4-HMAC-SHA256'])
        self.assertNotIn('x-amz-expected-bucket-owner',query)
        # Retain the guard even if a future credential token itself is enormous.
        from browser_validation import BrowserValidationRejected
        oversized=boto3.Session(aws_access_key_id='A'*20,aws_secret_access_key='X'*40,aws_session_token='x'*10000)
        with patch('boto3.client',side_effect=lambda *args,**kwargs:oversized.client(*args,**kwargs)):
            signer=regional_s3_client(REGION)
        empty=MemoryStore();puts=sum(method=='put_object' for method,_ in s3.calls)
        with self.assertRaisesRegex(BrowserValidationRejected,'override_budget'):
            BrowserValidation(empty,ecs,s3,config).validate(site,preview,key,OPERATION,lambda:None)
        self.assertEqual(empty.rows,{})
        self.assertEqual(sum(method=='put_object' for method,_ in s3.calls),puts)

    def test_regression_implicit_legacy_signer_hoists_owner_into_query(self):
        # Reproduce the proven failure shape without ever sending it to S3.
        legacy = self.session.client('s3', region_name=REGION, config=Config(signature_version='s3'))
        url = legacy.generate_presigned_url('get_object', Params={'Bucket': 'example-validator-artifacts',
            'Key': 'site.zip', 'ExpectedBucketOwner': ACCOUNT}, ExpiresIn=900)
        query = parse_qs(urlsplit(url).query)
        self.assertIn('AWSAccessKeyId', query)
        self.assertEqual(query['x-amz-expected-bucket-owner'], [ACCOUNT])


if __name__ == '__main__':
    unittest.main()
