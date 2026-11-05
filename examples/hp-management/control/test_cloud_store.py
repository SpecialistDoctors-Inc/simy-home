"""DynamoDB transaction semantics through the real boto3 adapter, mocked AWS."""
import unittest
import boto3
from moto import mock_aws
from store import Check, Conflict, DynamoStore, Write


def table(client, name='hp-control-test'):
    client.create_table(TableName=name,BillingMode='PAY_PER_REQUEST',
        KeySchema=[{'AttributeName':'pk','KeyType':'HASH'}],
        AttributeDefinitions=[{'AttributeName':'pk','AttributeType':'S'},
                             {'AttributeName':'queue_state','AttributeType':'S'},
                             {'AttributeName':'attention_state','AttributeType':'S'},
                             {'AttributeName':'queue_ready_at','AttributeType':'N'}],
        GlobalSecondaryIndexes=[{'IndexName':'queue-state','KeySchema':[{'AttributeName':'queue_state','KeyType':'HASH'}, {'AttributeName':'queue_ready_at','KeyType':'RANGE'}],
                                'Projection':{'ProjectionType':'ALL'}},
                               {'IndexName':'attention-state','KeySchema':[{'AttributeName':'attention_state','KeyType':'HASH'}],
                                'Projection':{'ProjectionType':'KEYS_ONLY'}}])
    return DynamoStore(name,client)


@mock_aws
class CloudStoreTests(unittest.TestCase):
    def setUp(self):
        self.client=boto3.client('dynamodb',region_name='ap-northeast-1')
        self.store=table(self.client)

    def test_create_cas_and_transaction_check_failure_are_atomic(self):
        first=self.store.put('principal:one',{'sites':{'example':['edit']}})
        self.assertEqual(first['_version'],1)
        with self.assertRaises(Conflict): self.store.put('principal:one',{'sites':{}},None)
        self.store.transact([Check('principal:one',1),Write('operation:one',{'status':'queued'},None)])
        self.assertEqual(self.store.get('operation:one')['_version'],1)
        with self.assertRaises(Conflict):
            self.store.transact([Check('principal:one',2),Write('operation:two',{'status':'queued'},None)])
        self.assertIsNone(self.store.get('operation:two'))
        with self.assertRaises(Conflict):
            self.store.transact([Write('operation:one',{'status':'running'},1),Check('principal:one',2)])
        self.assertEqual(self.store.get('operation:one')['status'],'queued')

    def test_update_delete_and_version_do_not_rely_on_body_version(self):
        first=self.store.put('operation:one',{'_version':900,'status':'queued'})
        self.assertEqual(first['_version'],1)
        updated=self.store.put('operation:one',{**first,'status':'completed'},1)
        self.assertEqual(updated['_version'],2)
        self.assertNotIn('_version',__import__('json').loads(self.client.get_item(
            TableName=self.store.table,Key={'pk':{'S':'operation:one'}})['Item']['body']['S']))
        with self.assertRaises(Conflict): self.store.transact([Write('operation:one',None,1)])
        self.store.transact([Write('operation:one',None,2)])
        self.assertIsNone(self.store.get('operation:one'))

    def test_pending_index_projects_authoritative_body_and_ttl(self):
        self.store.put('operation:one',{'status':'retry_wait','queue_state':'pending','expires_at':123456})
        sent=self.store.put('operation:two',{'status':'queued','queue_state':'sent'})
        pending=dict(self.store.pending())
        self.assertEqual(set(pending),{'operation:one'})
        self.assertEqual(pending['operation:one']['expires_at'],123456)
        item=self.client.get_item(TableName=self.store.table,Key={'pk':{'S':'operation:one'}})['Item']
        self.assertEqual(item['expires_at'],{'N':'123456'})
        self.store.put('operation:two',{**sent,'queue_state':'pending'},sent['_version'])
        self.assertEqual(len(self.store.pending(limit=1)),1)

    def test_attention_presence_is_indexed_and_clears_after_resolution(self):
        self.assertFalse(self.store.has_attention())
        waiting=self.store.put('operation:wait',{'status':'reconciling','queue_state':'pending','retry_at':9999999999})
        self.assertFalse(self.store.has_attention())
        attention=self.store.put('operation:attention',{'status':'needs_attention'})
        self.assertTrue(self.store.has_attention())
        self.store.put('operation:attention',{**attention,'status':'completed'},attention['_version'])
        self.assertFalse(self.store.has_attention())
        report=self.store.put('operation:report',{'status':'completed','reporting_state':'needs_attention'})
        self.assertTrue(self.store.has_attention())
        self.store.put('operation:report',{**report,'reporting_state':'completed'},report['_version'])
        self.assertFalse(self.store.has_attention())
        item=self.client.get_item(TableName=self.store.table,Key={'pk':{'S':'operation:report'}})['Item']
        self.assertNotIn('attention_state',item)

    def test_attention_query_is_bounded_keys_only_presence_without_scan(self):
        calls=[]
        class Presence:
            def query(inner,**kwargs): calls.append(kwargs); return {'Count':1}
            def scan(inner,**kwargs): raise AssertionError('must not scan')
        self.assertTrue(DynamoStore('authority',Presence()).has_attention())
        self.assertEqual(calls,[{'TableName':'authority','IndexName':'attention-state',
            'KeyConditionExpression':'attention_state = :required',
            'ExpressionAttributeValues':{':required':{'S':'required'}},'Select':'COUNT','Limit':1}])

    def test_duplicate_or_empty_transaction_rejected_before_aws(self):
        for writes in ([],[Write('same',{},None),Write('same',{},None)]):
            with self.assertRaises(ValueError): self.store.transact(writes)
