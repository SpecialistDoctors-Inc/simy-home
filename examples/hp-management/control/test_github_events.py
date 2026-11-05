import hashlib,hmac,json,unittest
from uuid import uuid4
from github_events import handle
from store import MemoryStore

class EventsTest(unittest.TestCase):
 def setUp(self):
  self.store=MemoryStore();self.key='not-a-real-key-'+'a'*40;self.sha='a'*40;self.operation=str(uuid4())
  self.store.put('repository:123',{'site_id':'example-site','installation_id':42})
  self.store.put('gitwait:123:'+self.sha,{'site_id':'example-site','operation_id':self.operation})
  self.store.put('operation:'+self.operation,{'site_id':'example-site','operation_id':self.operation,'status':'retry_wait','stage':'github_validation','retry_generation':1})
 def event(self,**changes):
  payload={'repository':{'id':123},'installation':{'id':42},'workflow_run':{'head_sha':self.sha},**changes};body=json.dumps(payload)
  return {'body':body,'headers':{'x-github-delivery':str(uuid4()),'x-github-event':'workflow_run','x-hub-signature-256':'sha256='+hmac.new(self.key.encode(),body.encode(),hashlib.sha256).hexdigest()}}
 def test_signed_exact_validation_wait_wakes_once(self):
  event=self.event();self.assertEqual(handle(event,self.store,self.key),202);row=self.store.get('operation:'+self.operation);self.assertEqual((row['queue_state'],row['retry_at'],row['retry_generation']),('pending',0,2));self.assertEqual(handle(event,self.store,self.key),202);self.assertEqual(self.store.get('operation:'+self.operation),row)
 def test_wrong_signature_installation_source_and_state(self):
  bad=self.event();bad['headers']['x-hub-signature-256']='sha256=bad';self.assertEqual(handle(bad,self.store,self.key),401)
  self.assertEqual(handle(self.event(installation={'id':99}),self.store,self.key),403)
  self.assertEqual(handle(self.event(workflow_run={'head_sha':'b'*40}),self.store,self.key),202)
  self.assertNotIn('queue_state',self.store.get('operation:'+self.operation))
  row=self.store.get('operation:'+self.operation);self.store.put('operation:'+self.operation,{**row,'status':'completed'},row['_version'])
  self.assertEqual(handle(self.event(),self.store,self.key),202);self.assertEqual(self.store.get('operation:'+self.operation)['status'],'completed')
 def test_event_cannot_create_new_operation(self):
  self.store.rows.pop('operation:'+self.operation);self.assertEqual(handle(self.event(),self.store,self.key),202);self.assertIsNone(self.store.get('operation:'+self.operation))
