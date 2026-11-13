import json
import unittest
from io import BytesIO
from unittest.mock import Mock, patch

from provision_site import enable_domain_registration, prepare_claim, seed, validate
from identity import sha
from domain_verification import dns_has_value
from licensing import LicenseUnavailable
from mcp_adapter import App, TOOL_FIELDS
from service import Service, Rejected
from store import MemoryStore,Conflict

ORG = 'f4dbf297-4526-41f5-bd7b-2ba20b4736d9'
SUBJECT = 'google-subject'
OTHER_ORG = '65a63523-8d2b-46ac-b01d-3b34f3f6d277'

class ProvisionTest(unittest.TestCase):
 def test_search_console_owner_cannot_claim_a_site_without_publisher_authorization(self):
  store = MemoryStore()
  site = self.site()
  targets = {env: {'bucket': item['bucket'], 'distribution': item['distribution_id']}
             for env, item in site['deployment'].items()}
  service = Service(store, publication_enabled=True, license_resolver=lambda *_: False,
                    claim_targets={site['site_id']: targets})
  def register(org=ORG, subject=SUBJECT):
   return service.register_site(org, subject, site['prod_url'], verify=False, owner_verified=True)
  self.assertEqual(register(), {'status': 'hosting_connection_required'})
  enable_domain_registration(store, site)
  self.assertEqual(register(), {'status': 'hosting_connection_required'})
  self.assertIsNone(store.get('site:example-site'))
  enable_domain_registration(store, site, allow_search_console_owners=True)
  with patch('service.dns_has_value') as dns:
   self.assertEqual(register(), {'status': 'claimed'})
   self.assertEqual(register(), {'status': 'claimed'})
   self.assertEqual(register(OTHER_ORG, 'other-subject'), {'status': 'registration_unavailable'})
   dns.assert_not_called()
 def test_dns_proof_requires_a_txt_answer_for_the_exact_hostname(self):
  name = '_simy-hp.example.invalid'
  value = 'simy-hp=test-proof'
  answer = {'name': name + '.', 'type': 16, 'data': '"' + value + '"'}
  for record, expected in ((answer, True), ({**answer, 'name': 'other.example.invalid.'}, False),
                           ({**answer, 'type': 5}, False), ({**answer, 'data': 'other'}, False)):
   payload = json.dumps({'Status': 0, 'Answer': [record]}).encode()
   with patch('domain_verification._dns.open', return_value=BytesIO(payload)):
    self.assertIs(dns_has_value(name, value), expected)
 def site(self):
  return {'site_id':'example-site','name':'Example','config_version':1,'github_app_id':1,'github_installation_id':2,'github_repository_id':3,'github_owner':'Example','github_repository':'site','validation_workflow_id':4,'initial_main_commit':'a'*40,'drive_workspace_folder_id':'snapshot-folder','drive_changes_folder_id':'incoming-folder','sheet_id':'example-sheet-id','recipient':'owner@example.invalid','operator_subject':'example-operator','operator_email':'operator@example.invalid','dev_url':'https://dev.example.invalid','prod_url':'https://example.invalid','direct_transfer_enabled':True,'mail_enabled':True,'reporting_enabled':True,'deployment':{env:{'bucket':'example-'+env,'distribution_id':'EEXAMPLE','origin_id':'site','expected_config_sha256':'b'*64,'initial_file_paths':['index.html']} for env in ('dev','prod')}}
 def test_initial_binding_and_invitation_created_atomically_without_message(self):
  store=MemoryStore();result=seed(store,self.site(),'owner@example.invalid',['read','edit','publish'],1000)
  self.assertEqual(result['site_id'],'example-site');self.assertEqual(store.get('invitation:'+sha('owner@example.invalid'))['sites'],{'example-site':['edit','publish','read']})
  with self.assertRaises(Conflict):seed(store,self.site(),'second@example.invalid',['read'],1001)
  self.assertIsNone(store.get('invitation:'+sha('second@example.invalid')))
 def test_unknown_fields_and_unsafe_bindings_rejected(self):
  for change in ({'private_key':'not allowed'},{'drive_changes_folder_id':'snapshot-folder'},{'prod_url':'http://example.invalid'},{'github_app_id':True}):
   with self.subTest(change=list(change)),self.assertRaises(ValueError):validate({**self.site(),**change})

 def test_verified_subject_can_use_prepared_site_when_payment_becomes_active(self):
  store = MemoryStore()
  site = {**self.site(), 'license_policy': {'mode': 'simy', 'org_id': ORG}}
  store.put('principal:' + SUBJECT, {'sites': {'existing-site': ['read']}})
  seed(store, site, None, ['read', 'edit'], 1000, google_subject=SUBJECT)
  self.assertEqual(store.get('principal:' + SUBJECT)['sites'],
                   {'existing-site': ['read'], 'example-site': ['edit', 'read']})
  allowed = False
  service = Service(store, license_resolver=lambda org, sub: allowed and (org, sub) == (ORG, SUBJECT))
  claims = {'sub': SUBJECT, 'scope': 'hp:read hp:write'}
  self.assertEqual(service.license_preflight(ORG, SUBJECT), {'ready': True})
  with self.assertRaisesRegex(Rejected, 'hp_license_required'):
   service.authorized(claims, site['site_id'], 'edit')
  allowed = True
  service.authorized(claims, site['site_id'], 'edit')
  with self.assertRaisesRegex(Rejected, 'site_access_denied'):
   service.authorized(claims, site['site_id'], 'publish')

 def test_subject_provision_rejects_disabled_principal_and_preserves_conflicting_records(self):
  store = MemoryStore()
  site = {**self.site(), 'license_policy': {'mode': 'simy', 'org_id': ORG}}
  key = 'principal:' + SUBJECT
  store.put(key, {'sites': {}, 'disabled': True})
  with self.assertRaisesRegex(ValueError, 'existing principal'):
   seed(store, site, None, ['read', 'edit'], 1000, google_subject=SUBJECT)
  self.assertIsNone(store.get('site:example-site'))
  self.assertIsNone(store.get('repository:3'))
  store.put('repository:3', {'site_id': 'another-site', 'installation_id': 2})
  with self.assertRaises(Conflict):
   seed(store, site, None, ['read', 'edit'], 1001, google_subject='new-subject')
  self.assertIsNone(store.get('principal:new-subject'))
  self.assertIsNone(store.get('site:example-site'))

 def test_prepared_site_claim_then_checkout_and_publication_roles(self):
  store = MemoryStore()
  site = self.site()
  code = prepare_claim(store, site, SUBJECT, 1000)['setup_code']
  self.assertNotIn(code, json.dumps(store.rows))
  resolver = Mock(return_value=False)
  targets = {'example-site': {environment: {'bucket': binding['bucket'], 'distribution': binding['distribution_id']}
                              for environment, binding in site['deployment'].items()}}
  service = Service(store, clock=lambda: 1001, publication_enabled=True, license_resolver=resolver)
  app = App(None, service, None, None, None, preflight_token=lambda: 'a' * 32)

  def request(org=ORG, subject=SUBJECT, token='a' * 32, *, transfer_ready=True):
   event = {'rawPath': '/internal/site/claim', 'httpMethod': 'POST',
            'headers': {'authorization': 'Bearer ' + token, 'content-type': 'application/json'},
            'body': json.dumps({'org_id': org, 'google_subject': subject, 'setup_code': code})}
   transfer = {'hp_download_workspace': (), 'hp_prepare_upload': ()} if transfer_ready else {}
   with patch.dict(TOOL_FIELDS, transfer):
    response = app(event)
   return response['statusCode'], json.loads(response['body'])

  self.assertEqual(service.license_preflight(ORG, SUBJECT)['status'], 'connection_required')
  self.assertEqual(request(token='b' * 32)[0], 401)
  self.assertEqual(request(transfer_ready=False)[0], 503)
  self.assertEqual(request(subject='other-subject'), (409, {'error': 'site_claim_unavailable'}))
  self.assertEqual(request()[0], 503)
  resolver.assert_not_called()
  service.claim_targets = targets
  resolver.side_effect = LicenseUnavailable('hp_license_unavailable')
  self.assertEqual(request()[0], 503)
  self.assertIsNone(store.get('site:example-site'))
  resolver.side_effect = None
  self.assertEqual(request(), (200, {'status': 'claimed'}))
  snapshot = store.rows.copy()
  self.assertEqual(request(), (200, {'status': 'claimed'}))
  self.assertEqual(request(org=OTHER_ORG), (409, {'error': 'site_claim_unavailable'}))
  self.assertEqual(store.rows, snapshot)
  self.assertEqual(service.license_preflight(ORG, SUBJECT), {'ready': True})
  service.claim_targets = {}
  with self.assertRaises(LicenseUnavailable):
   service.license_preflight(ORG, SUBJECT)
  claims = {'sub': SUBJECT, 'scope': 'hp:read hp:write'}
  with self.assertRaisesRegex(Rejected, 'hp_license_required'):
   service.authorized(claims, 'example-site', 'edit')
  resolver.return_value = True
  service.authorized(claims, 'example-site', 'edit')
  service.authorized(claims, 'example-site', 'publish')

 def test_domain_registration_checks_account_and_dns_before_granting_access(self):
  store = MemoryStore()
  site = self.site()
  enable_domain_registration(store, site)
  targets = {env: {'bucket': item['bucket'], 'distribution': item['distribution_id']}
             for env, item in site['deployment'].items()}
  service = Service(store, clock=lambda: 1001, publication_enabled=True,
                    license_resolver=lambda *_: False, claim_targets={site['site_id']: targets})
  app = App(None, service, None, None, None, preflight_token=lambda: 'a' * 32)

  def request(action, org=ORG, subject=SUBJECT, url='https://example.invalid/clinic', token='a' * 32):
   event = {'rawPath': '/internal/site/claim', 'httpMethod': 'POST',
            'headers': {'authorization': 'Bearer ' + token, 'content-type': 'application/json'},
            'body': json.dumps({'org_id': org, 'google_subject': subject, 'action': action, 'site_url': url})}
   with patch.dict(TOOL_FIELDS, {'hp_download_workspace': (), 'hp_prepare_upload': ()}):
    response = app(event)
   return response['statusCode'], json.loads(response['body'])

  self.assertEqual(request('start', token='b' * 32)[0], 401)
  self.assertEqual(request('start', url='https://unlisted.invalid')[1]['status'], 'site_not_supported')
  self.assertEqual(request('start', url='https://x@example.invalid')[1]['status'], 'invalid_url')
  status, proof = request('start')
  self.assertEqual(status, 200)
  self.assertEqual(proof['name'], '_simy-hp.example.invalid')
  self.assertEqual(request('start', url='EXAMPLE.INVALID'), (200, proof))
  self.assertEqual(request('verify', org=OTHER_ORG)[1]['status'], 'verification_expired')
  self.assertEqual(request('verify', subject='other-subject')[1]['status'], 'verification_expired')
  with patch('service.dns_has_value', return_value=False):
   self.assertEqual(request('verify')[1]['status'], 'verification_pending')
  self.assertIsNone(store.get('site:example-site'))
  self.assertIsNone(store.get('principal:' + SUBJECT))
  with patch('service.dns_has_value', return_value=True) as resolver:
   self.assertEqual(request('verify'), (200, {'status': 'claimed'}))
   self.assertEqual(request('verify'), (200, {'status': 'claimed'}))
   self.assertEqual(request('verify', org=OTHER_ORG)[1]['status'], 'registration_unavailable')
   resolver.assert_called_once_with(proof['name'], proof['value'])
  self.assertEqual(service.license_preflight(ORG, SUBJECT), {'ready': True})
  with self.assertRaisesRegex(Rejected, 'hp_license_required'):
   service.authorized({'sub': SUBJECT, 'scope': 'hp:read hp:write'}, site['site_id'], 'edit')

 def test_claim_conflict_and_expiry_leave_bindings_untouched(self):
  store = MemoryStore()
  site = self.site()
  code = prepare_claim(store, site, SUBJECT, 1000)['setup_code']
  another = prepare_claim(store, {**site, 'site_id': 'other-site'}, 'other-subject', 1000)['setup_code']
  now = 1001
  targets = {environment: {'bucket': binding['bucket'], 'distribution': binding['distribution_id']}
             for environment, binding in site['deployment'].items()}
  service = Service(store, clock=lambda: now, publication_enabled=True, license_resolver=lambda *_: False,
                    claim_targets={'example-site': targets, 'other-site': targets})
  service.claim_prepared_site(ORG, SUBJECT, code)
  snapshot = store.rows.copy()
  with self.assertRaisesRegex(Rejected, 'site_claim_unavailable'):
   service.claim_prepared_site(OTHER_ORG, 'other-subject', another)
  self.assertEqual(store.rows, snapshot)
  now = 1000 + 7 * 86400
  with self.assertRaisesRegex(Rejected, 'site_claim_unavailable'):
   service.claim_prepared_site(ORG, SUBJECT, code)
  self.assertEqual(store.rows, snapshot)
