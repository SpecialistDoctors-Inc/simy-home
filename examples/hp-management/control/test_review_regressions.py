"""Behavioral regressions from independent auth/package review."""
import io,json,struct,unittest,zipfile
from uuid import uuid4
from bundles import BundleError,validate_files,validate_snapshot
from service import Service,Rejected
from store import MemoryStore

class ReviewRegressions(unittest.TestCase):
 def test_paths_without_extension_and_file_directory_conflicts_rejected(self):
  for extra in ({'html':b'x'},{'x.html':b'a','x.html/y.html':b'b'},{'Images/a.png':b'a','images/b.png':b'b'}):
   with self.subTest(extra=list(extra)),self.assertRaises(BundleError):validate_files({'index.html':b'home',**extra})
 def test_malformed_deflate_and_deep_json_are_bounded_input_errors(self):
  stream=io.BytesIO()
  with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('manifest.json','{}')
  data=bytearray(stream.getvalue());name,extra=struct.unpack_from('<HH',data,26);data[30+name+extra]=7
  with self.assertRaises(BundleError):validate_snapshot(bytes(data))
  stream=io.BytesIO()
  with zipfile.ZipFile(stream,'w') as z:z.writestr('manifest.json','['*2000+'0'+']'*2000)
  with self.assertRaises(BundleError):validate_snapshot(stream.getvalue())
 def fixture(self):
  store=MemoryStore();claims={'sub':'test-sub','scope':'hp:read hp:write'};preview=str(uuid4())
  store.put('principal:test-sub',{'sites':{'test-site':['read','edit','publish']}})
  store.put('site:test-site',{'name':'Test','dev_url':'https://dev.example.invalid','prod_url':'https://example.invalid','config_version':1,'initial_main_commit':'a'*40,'current_preview':preview})
  store.put('preview:'+preview,{'site_id':'test-site','status':'verified','source_commit':'b'*40,'artifact_sha256':'c'*64,'url':'https://dev.example.invalid/one','summary':'Edited content'})
  return store,Service(store,clock=lambda:1000,publication_enabled=True),claims,preview
 def test_two_confirmation_cards_share_one_publication_operation(self):
  store,service,claims,preview=self.fixture();cards=[service.prepare_publish(claims,'test-site',preview) for _ in range(2)]
  receipts=[service.confirm_publish(claims,c['structuredContent']['approval_id'],c['_meta']['confirmation_nonce']) for c in cards]
  self.assertEqual(receipts[0]['operation_id'],receipts[1]['operation_id']);self.assertEqual(len([k for k in store.rows if k.startswith('operation:')]),1)
 def test_cancelled_publication_can_be_confirmed_again_but_unknown_effect_cannot(self):
  store,service,claims,preview=self.fixture()
  def confirm():
   card=service.prepare_publish(claims,'test-site',preview)
   return service.confirm_publish(claims,card['structuredContent']['approval_id'],card['_meta']['confirmation_nonce'])
  first=confirm();service.cancel(claims,first['operation_id']);second=confirm()
  self.assertNotEqual(first['operation_id'],second['operation_id'])
  key='operation:'+second['operation_id'];row=store.get(key)
  store.put(key,{**row,'status':'failed','pending_effect':{'name':'publish'}},row['_version'])
  self.assertEqual(confirm()['operation_id'],second['operation_id'])
 def test_known_main_only_failure_can_get_fresh_approval_without_unrelated_edit(self):
  store,service,claims,preview=self.fixture()
  card=service.prepare_publish(claims,'test-site',preview);first=service.confirm_publish(claims,card['structuredContent']['approval_id'],card['_meta']['confirmation_nonce'])
  key='operation:'+first['operation_id'];row=store.get(key)
  store.put(key,{**row,'status':'failed','phases':{'main_commit':{'commit':'d'*40}}},row['_version'])
  site=store.get('site:test-site');store.put('site:test-site',{**site,'current_main_commit':'d'*40},site['_version'])
  fresh=service.prepare_publish(claims,'test-site',preview);second=service.confirm_publish(claims,fresh['structuredContent']['approval_id'],fresh['_meta']['confirmation_nonce'])
  self.assertNotEqual(first['operation_id'],second['operation_id'])

 def test_profile_needs_read_scope_and_pending_reporting_is_not_completed(self):
  store,service,claims,preview=self.fixture()
  with self.assertRaises(Rejected):service.profile({**claims,'scope':'hp:write'})
  op={'status':'completed','reporting_required':True,'reporting_state':'pending'}
  self.assertEqual(service.public_operation(op)['status'],'reporting')
  self.assertEqual(service.public_operation({**op,'reporting_state':'needs_attention'})['status'],'needs_attention')
