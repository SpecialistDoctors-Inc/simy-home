"""Durable FIFO enqueue/replay tests using moto DynamoDB and SQS."""
import json
import io
from contextlib import redirect_stdout
import os
import unittest
from unittest.mock import patch
import boto3
from moto import mock_aws
from hp_control import dispatch_pending, consume_commands
from test_cloud_store import table


@mock_aws
class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.store=table(boto3.client('dynamodb',region_name='ap-northeast-1'))
        self.sqs=boto3.client('sqs',region_name='ap-northeast-1')
        self.queue=self.sqs.create_queue(QueueName='hp-control-test.fifo',Attributes={'FifoQueue':'true'})['QueueUrl']
        self.env=patch.dict(os.environ,{'HP_COMMAND_QUEUE_URL':self.queue})
        self.env.start(); self.addCleanup(self.env.stop)

    def operation(self,operation='one',**fields):
        return self.store.put('operation:'+operation,{'operation_id':operation,'site_id':'example-site',
            'status':'queued','queue_state':'pending',**fields})

    def dispatch(self,**kwargs):
        return dispatch_pending({},None,store=self.store,sqs=kwargs.get('sqs',self.sqs),clock=lambda:1000)

    def messages(self):
        return self.sqs.receive_message(QueueUrl=self.queue,MaxNumberOfMessages=10,MessageSystemAttributeNames=['All']).get('Messages',[])

    def test_response_loss_keeps_outbox_and_fifo_replay_deduplicates(self):
        self.operation()
        original=self.sqs
        class LostResponse:
            def send_message(inner,**kwargs):
                original.send_message(**kwargs)
                raise RuntimeError('accepted send response lost')
        with self.assertRaises(RuntimeError): self.dispatch(sqs=LostResponse())
        self.assertEqual(self.store.get('operation:one')['queue_state'],'pending')
        self.assertEqual(self.dispatch(),{'enqueued':1})
        self.assertEqual(self.store.get('operation:one')['queue_state'],'sent')
        messages=self.messages()
        self.assertEqual(len(messages),1)
        self.assertEqual(json.loads(messages[0]['Body']),{'operation_id':'one'})
        self.assertEqual(messages[0]['Attributes']['MessageGroupId'],'example-site')
        self.assertEqual(messages[0]['Attributes']['MessageDeduplicationId'],'one:0')

    def test_retry_generation_is_new_message_and_early_retry_is_skipped(self):
        self.operation(retry_at=1100,retry_generation=3,status='retry_wait')
        self.assertEqual(self.dispatch(),{'enqueued':0})
        row=self.store.get('operation:one')
        self.store.put('operation:one',{**row,'retry_at':1000},row['_version'])
        self.assertEqual(self.dispatch(),{'enqueued':1})
        first=self.messages()[0]
        self.sqs.delete_message(QueueUrl=self.queue,ReceiptHandle=first['ReceiptHandle'])
        row=self.store.get('operation:one')
        self.store.put('operation:one',{**row,'queue_state':'pending','retry_generation':4},row['_version'])
        self.assertEqual(self.dispatch(),{'enqueued':1})
        self.assertEqual(self.messages()[0]['Attributes']['MessageDeduplicationId'],'one:4')

    def test_future_retries_do_not_starve_new_due_operations(self):
        for index in range(30):
            self.operation('future-' + str(index), retry_at=9999)
        self.operation('due', retry_at=0)
        self.assertEqual(self.dispatch(), {'enqueued': 1})
        messages = self.messages()
        self.assertEqual(len(messages), 1)
        self.assertIn('due', messages[0]['Body'])

    def test_stale_gsi_state_rechecks_row_and_cannot_enqueue_terminal_work(self):
        observed=self.operation(status='failed')
        self.operation('attention',status='needs_attention')
        self.operation('cancelled',status='cancelled')
        self.assertEqual(self.dispatch(),{'enqueued':0})
        class StaleIndex:
            def pending(inner,limit,now=None): return [('operation:one',{**observed,'status':'queued'})]
            def get(inner,key): return self.store.get(key)
        self.assertEqual(dispatch_pending({},None,store=StaleIndex(),sqs=self.sqs,clock=lambda:1000),{'enqueued':0})
        self.assertFalse(self.messages())

    def test_reconciling_and_completed_reporting_are_dispatchable(self):
        self.operation(status='reconciling')
        self.operation('report',status='completed',reporting_required=True,reporting_state='pending')
        self.assertEqual(self.dispatch(),{'enqueued':2})

    def test_consumer_acknowledges_durable_reschedule_without_waiting_fifo_visibility(self):
        self.operation(queue_state='sent')
        store=self.store
        class Waiting:
            def __init__(inner): inner.store=store
            def execute(inner,operation):
                row=store.get('operation:'+operation)
                store.put('operation:'+operation,{**row,'status':'reconciling','queue_state':'pending',
                    'retry_at':1030,'retry_generation':1},row['_version'])
                raise RuntimeError('bounded provider wait already persisted')
        event={'Records':[{'messageId':'delivery-one','body':json.dumps({'operation_id':'one'})}]}
        self.assertEqual(consume_commands(event,None,executor=Waiting()),{'batchItemFailures':[]})
        row=self.store.get('operation:one')
        self.assertEqual((row['queue_state'],row['retry_generation']),('pending',1))

    def test_consumer_retains_delivery_when_failure_has_no_durable_recovery(self):
        self.operation(queue_state='sent')
        store=self.store
        class Failed:
            def __init__(inner): inner.store=store
            def execute(inner,operation): raise RuntimeError('failed before persisted recovery')
        event={'Records':[{'messageId':'delivery-one','body':json.dumps({'operation_id':'one'})}]}
        self.assertEqual(consume_commands(event,None,executor=Failed()),
            {'batchItemFailures':[{'itemIdentifier':'delivery-one'}]})
        self.assertEqual(self.store.get('operation:one')['queue_state'],'sent')

    def test_reporting_busy_after_sent_is_rescheduled_before_ack(self):
        self.operation(status='completed', reporting_required=True, reporting_state='pending', queue_state='sent')
        store = self.store
        class Finished:
            def __init__(inner): inner.store = store
            def execute(inner, operation): return store.get('operation:' + operation)
        class BusyReporter:
            def report(inner, operation): raise RuntimeError('site busy before reporting lease')
        event = {'Records': [{'messageId': 'delivery-one', 'body': json.dumps({'operation_id': 'one'})}]}
        self.assertEqual(consume_commands(event, None, executor=Finished(), reporter=BusyReporter()), {'batchItemFailures': []})
        row = store.get('operation:one')
        self.assertEqual((row['status'], row['queue_state'], row['reporting_required']), ('completed', 'pending', True))
        self.assertEqual(row['retry_generation'], 1)
        self.assertGreater(row['retry_at'], 1000)

    def test_consumer_attention_ack_is_not_parent_completion(self):
        self.operation(status='needs_attention',queue_state='sent')
        store=self.store
        class Attention:
            def __init__(inner): inner.store=store
            def execute(inner,operation): raise RuntimeError('operator reconciliation required')
        event={'Records':[{'messageId':'delivery-one','body':json.dumps({'operation_id':'one'})}]}
        self.assertEqual(consume_commands(event,None,executor=Attention()),{'batchItemFailures':[]})
        self.assertEqual(self.store.get('operation:one')['status'],'needs_attention')

    def test_success_heartbeat_reports_attention_separately_from_ordinary_waits(self):
        row=self.operation(status='reconciling',retry_at=2000)
        stream=io.StringIO()
        with redirect_stdout(stream): self.dispatch()
        event=json.loads(stream.getvalue())
        self.assertEqual(event,{'event':'hp_dispatch_completed','enqueued':0,'has_attention':False})
        self.store.put('operation:one',{**row,'status':'needs_attention'},row['_version'])
        stream=io.StringIO()
        with redirect_stdout(stream): self.dispatch()
        event=json.loads(stream.getvalue())
        self.assertTrue(event['has_attention'])
        self.assertEqual(event['enqueued'],0)

    def test_consumer_state_change_after_send_is_not_overwritten(self):
        self.operation()
        original=self.sqs
        class Racing:
            def send_message(inner,**kwargs):
                result=original.send_message(**kwargs)
                row=self.store.get('operation:one')
                self.store.put('operation:one',{**row,'status':'retry_wait','queue_state':'pending','retry_generation':1},row['_version'])
                return result
        self.assertEqual(self.dispatch(sqs=Racing()),{'enqueued':1})
        row=self.store.get('operation:one')
        self.assertEqual((row['queue_state'],row['retry_generation']),('pending',1))
