import unittest
import datetime as dt
import hashlib
from unittest.mock import Mock
import boto3
from botocore.stub import ANY, Stubber

from activation_providers import CloudEnvironments, RepositoryBootstrap, tenant_name
from site_activation import ActivationWaiting


class ActivationProviderTest(unittest.TestCase):
    def test_cloudformation_uses_fixed_job_token_and_reviewed_execution_role(self):
        client = boto3.client('cloudformation', region_name='us-east-1', aws_access_key_id='test', aws_secret_access_key='test')
        job = {'subscription_id': 'sub_activation123', 'job_id': '01010101-0101-4101-8101-010101010101', 'host': 'clinic.example.jp'}
        name = tenant_name(job)
        role = 'arn:aws:iam::209300895845:role/hp-control-clinic-stack'
        with Stubber(client) as stub:
            stub.add_client_error('describe_stacks', service_error_code='ValidationError', http_status_code=400,
                                  expected_params={'StackName': name})
            stub.add_response('create_stack', {'StackId': 'arn:aws:cloudformation:us-east-1:209300895845:stack/' + name + '/id'},
                {'StackName': name, 'TemplateBody': ANY, 'RoleARN': role,
                 'ClientRequestToken': 'hp-' + job['job_id'], 'Capabilities': ['CAPABILITY_NAMED_IAM'],
                 'EnableTerminationProtection': True, 'OnFailure': 'DO_NOTHING',
                 'Tags': [{'Key': 'hp_activation_job', 'Value': job['job_id']}]})
            hosting = CloudEnvironments(client, None, None, None, role, lambda *args: {'Resources': {}})
            with self.assertRaises(ActivationWaiting): hosting.ensure(job, {}, lambda: None)

    def test_cross_account_provisioning_role_is_rejected_before_provider_calls(self):
        with self.assertRaises(ValueError):
            CloudEnvironments(None, None, None, None, 'arn:aws:iam::000000000000:role/other', lambda *args: {})

    def test_failed_owned_stack_resumes_without_deleting_the_environment(self):
        client = boto3.client('cloudformation', region_name='us-east-1', aws_access_key_id='test', aws_secret_access_key='test')
        job = {'subscription_id': 'sub_activation123', 'job_id': '01010101-0101-4101-8101-010101010101', 'host': 'clinic.example.jp'}
        name, role = tenant_name(job), 'arn:aws:iam::209300895845:role/hp-control-clinic-stack'
        stamp = dt.datetime(2026, 11, 14, tzinfo=dt.timezone.utc)
        stack_id = 'arn:aws:cloudformation:us-east-1:209300895845:stack/' + name + '/id'
        token = 'hp-retry-' + job['job_id'] + '-' + hashlib.sha256(str(stamp).encode()).hexdigest()[:12]
        with Stubber(client) as stub:
            stub.add_response('describe_stacks', {'Stacks': [{'StackName': name, 'StackId': stack_id,
                'CreationTime': stamp, 'StackStatus': 'CREATE_FAILED', 'RoleARN': role,
                'Tags': [{'Key': 'hp_activation_job', 'Value': job['job_id']}]}]}, {'StackName': name})
            stub.add_response('update_stack', {'StackId': stack_id}, {'StackName': name, 'TemplateBody': ANY,
                'RoleARN': role, 'ClientRequestToken': token, 'DisableRollback': True,
                'Capabilities': ['CAPABILITY_NAMED_IAM']})
            hosting = CloudEnvironments(client, None, None, None, role, lambda *args: {'Resources': {}})
            with self.assertRaises(ActivationWaiting): hosting.ensure(job, {}, lambda: None)
            stub.assert_no_pending_responses()

    def test_existing_repository_with_another_job_marker_is_not_adopted(self):
        calls = []
        def transport(method, url, headers, body):
            calls.append(method)
            return 200, {'full_name': 'Example/' + tenant_name(job), 'private': True,
                         'description': 'another customer', 'default_branch': 'main', 'id': 123}
        config = {'owner': 'Example', 'template_owner': 'Example', 'template_repository': 'template',
                  'template_tree': 'a'*40, 'bootstrap_token_secret_ref': 'test'}
        job = {'subscription_id': 'sub_activation123', 'job_id': 'job', 'host': 'clinic.example.jp'}
        repo = RepositoryBootstrap(config, lambda ref: 'private-token', transport)
        with self.assertRaises(ActivationWaiting): repo.ensure(job, {'index.html': b'Example'}, lambda: None)
        self.assertEqual(calls, ['GET'])

    def test_mail_or_application_dependency_prevents_automatic_dns_binding(self):
        cloud = CloudEnvironments(None, None, None, None,
            'arn:aws:iam::209300895845:role/hp-control-clinic-stack', lambda *args: {})
        with self.assertRaises(ActivationWaiting):
            cloud.cutover_plan({'prod_url': 'https://clinic.example.jp'}, {'web_cutover_safe': False}, lambda: None)


if __name__ == '__main__': unittest.main()
