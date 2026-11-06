import unittest
from provision_site import seed,validate
from identity import sha
from store import MemoryStore,Conflict

class ProvisionTest(unittest.TestCase):
 def site(self):
  return {'site_id':'example-site','name':'Example','config_version':1,'github_app_id':1,'github_installation_id':2,'github_repository_id':3,'github_owner':'Example','github_repository':'site','validation_workflow_id':4,'initial_main_commit':'a'*40,'drive_workspace_folder_id':'snapshot-folder','drive_changes_folder_id':'incoming-folder','sheet_id':'example-sheet-id','recipient':'owner@example.invalid','operator_subject':'example-operator','operator_email':'operator@example.invalid','dev_url':'https://dev.example.invalid','prod_url':'https://example.invalid','mail_enabled':True,'reporting_enabled':True,'deployment':{env:{'bucket':'example-'+env,'distribution_id':'EEXAMPLE','origin_id':'site','expected_config_sha256':'b'*64,'initial_file_paths':['index.html']} for env in ('dev','prod')}}
 def test_initial_binding_and_invitation_created_atomically_without_message(self):
  store=MemoryStore();result=seed(store,self.site(),'owner@example.invalid',['read','edit','publish'],1000)
  self.assertEqual(result['site_id'],'example-site');self.assertEqual(store.get('invitation:'+sha('owner@example.invalid'))['sites'],{'example-site':['edit','publish','read']})
  with self.assertRaises(Conflict):seed(store,self.site(),'second@example.invalid',['read'],1001)
  self.assertIsNone(store.get('invitation:'+sha('second@example.invalid')))
 def test_unknown_fields_and_unsafe_bindings_rejected(self):
  for change in ({'private_key':'not allowed'},{'drive_changes_folder_id':'snapshot-folder'},{'prod_url':'http://example.invalid'},{'github_app_id':True}):
   with self.subTest(change=list(change)),self.assertRaises(ValueError):validate({**self.site(),**change})
