"""Authenticated resume -> real Dynamo transaction -> normal FIFO dispatch, all mocked AWS."""
from copy import deepcopy
import io
import json
import os
from contextlib import redirect_stdout
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

import boto3
from moto import mock_aws

from hp_control import handler, dispatch_pending
from mcp_adapter import App
from service import Service
from test_cloud_store import table


@mock_aws
class ResumeDispatchTests(unittest.TestCase):
    def setUp(self):
        self.store = table(boto3.client('dynamodb', region_name='ap-northeast-1'))
        self.sqs = boto3.client('sqs', region_name='ap-northeast-1')
        self.queue = self.sqs.create_queue(QueueName='resume-test.fifo', Attributes={'FifoQueue': 'true'})['QueueUrl']
        self.now = int(time.time())
        self.claims = {'sub': 'test-subject', 'scope': 'hp:read hp:write'}
        self.store.put('principal:test-subject', {'sites': {'example-site': ['read', 'edit', 'publish']}})
        self.store.put('site:example-site', {'name': 'Example Site', 'config_version': 1})
        self.service = Service(self.store, clock=lambda: self.now)
        self.operation = str(uuid4())
        workspace = str(uuid4())
        self.store.put('workspace:' + workspace, {'workspace_id': workspace, 'site_id': 'example-site',
            'subject': self.claims['sub'], 'head_commit': 'a' * 40})
        admitted = self.service.admit(self.claims, 'submit_preview', {'operation_id': self.operation,
            'site_id': 'example-site', 'workspace_id': workspace, 'saved_commit': 'a' * 40})
        key = 'operation:' + admitted['operation_id']
        row = self.store.get(key)
        self.store.put(key, {**row, 'status': 'needs_attention', 'stage': 'preview_deploy', 'retry_attempts': 8,
            'retry_generation': 5, 'error': 'retry_budget_exhausted', 'wait_deadline': self.now - 10,
            'pending_effect': {'name': 'preview_deploy', 'lease_epoch': 3,
                'reconciliation': {'kind': 'preview_deploy', 'sealed': 'PRIVATE-SEALED-INTENT'}},
            'lease_epoch': 3, 'lease_owner': 'old-owner'}, row['_version'])
        self.lease = self.store.put('lease:site:example-site', {'until': 0, 'owner': 'old-owner', 'epoch': 3,
            'blocked_operation': self.operation, 'operation_id': self.operation})
        class Identity:
            issuer = 'https://control.example.invalid'
        def verify(token):
            if token != 'test-only-bearer':raise ValueError('not authorized')
            return dict(self.claims)
        self.app = App(Identity(), self.service, verify, {'keys': []}, '')
        self.recovery = str(uuid4())

    def event(self):
        return {'rawPath': '/mcp', 'requestContext': {'http': {'method': 'POST'}},
            'headers': {'content-type': 'application/json', 'authorization': 'Bearer test-only-bearer'},
            'body': json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                'params': {'name': 'hp_resume_operation', 'arguments': {'operation_id': self.operation, 'recovery_id': self.recovery}}})}

    def invoke(self, sqs=None):
        environment = {'HP_TABLE_NAME': 'hp-control-test', 'HP_COMMAND_QUEUE_URL': self.queue}
        with patch.dict(os.environ, environment), patch('hp_control.application', return_value=self.app), \
                patch('hp_control.DynamoStore', return_value=self.store), patch('boto3.client', return_value=sqs or self.sqs):
            return handler(self.event(), None)

    def messages(self):
        return self.sqs.receive_message(QueueUrl=self.queue, MaxNumberOfMessages=10, MessageSystemAttributeNames=['All']).get('Messages', [])

    def test_authenticated_resume_atomically_audits_then_immediate_normal_enqueue(self):
        result = self.invoke()
        self.assertEqual(result['statusCode'], 200)
        public = json.loads(result['body'])['result']['structuredContent']
        self.assertEqual((public['operation_id'], public['status']), (self.operation, 'reconciling'))
        row = self.store.get('operation:' + self.operation)
        self.assertEqual((row['retry_generation'], row['retry_attempts'], row['queue_state']), (6, 0, 'sent'))
        self.assertEqual(row['wait_deadline'], self.now - 10)
        self.assertEqual(row['pending_effect']['lease_epoch'], 3)
        self.assertEqual(self.store.get('lease:site:example-site'), self.lease)
        self.assertEqual(self.store.get('resumption:' + self.recovery)['prior_retry_attempts'], 8)
        self.assertNotIn('PRIVATE-SEALED-INTENT', json.dumps(self.store.get('resumption:' + self.recovery)))
        messages = self.messages()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['Attributes']['MessageDeduplicationId'], self.operation + ':6')
        self.assertEqual(messages[0]['Attributes']['MessageGroupId'], 'example-site')
        self.assertEqual(json.loads(messages[0]['Body']), {'operation_id': self.operation})

    def test_failed_immediate_hint_is_recovered_by_normal_dispatcher_without_reset(self):
        class QueueUnavailable:
            def send_message(inner, **kwargs):raise OSError('queue unavailable')
        with redirect_stdout(io.StringIO()):
            result = self.invoke(QueueUnavailable())
        self.assertEqual(result['statusCode'], 200)
        self.assertEqual(self.store.get('operation:' + self.operation)['queue_state'], 'pending')
        with patch.dict(os.environ, {'HP_COMMAND_QUEUE_URL': self.queue}), redirect_stdout(io.StringIO()):
            dispatched = dispatch_pending({}, None, store=self.store, sqs=self.sqs, clock=lambda: self.now)
        self.assertEqual(dispatched, {'enqueued': 1})
        self.assertEqual(len(self.messages()), 1)
        row = self.store.get('operation:' + self.operation)
        self.store.put('operation:' + self.operation, {**row, 'status': 'running', 'retry_attempts': 2}, row['_version'])
        before = deepcopy(self.store.get('operation:' + self.operation))
        repeated = self.invoke()
        self.assertEqual(json.loads(repeated['body'])['result']['structuredContent']['status'], 'running')
        self.assertEqual(self.store.get('operation:' + self.operation), before)
        self.assertEqual(self.store.get('resumption:' + self.recovery)['_version'], 1)

    def test_absent_lease_condition_is_supported_by_real_dynamo_adapter(self):
        row = self.store.get('lease:site:example-site')
        from store import Write
        self.store.transact([Write('lease:site:example-site', None, row['_version'])])
        self.assertEqual(json.loads(self.invoke()['body'])['result']['structuredContent']['status'], 'reconciling')
        self.assertIsNone(self.store.get('lease:site:example-site'))


if __name__ == '__main__':unittest.main()
