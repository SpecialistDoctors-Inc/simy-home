import copy
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.fernet import Fernet

from domain_transfer import QUEUE, Route53Registrar, TransferRejected, enqueue_writes, key, prepare, public_status, run_one
from store import MemoryStore

SUB = 'sub_clinic123456'
NOW = 2000


def details():
    contact = {'FirstName': 'Test', 'LastName': 'Owner', 'ContactType': 'PERSON',
               'AddressLine1': '1 Test Road', 'City': 'Test City', 'CountryCode': 'JP',
               'PhoneNumber': '+81.312345678', 'Email': 'owner@example.test'}
    ns = [{'Name': 'ns1.example.test'}, {'Name': 'ns2.example.test'}]
    return {'domain': 'example.test', 'contacts': {k: copy.deepcopy(contact) for k in
            ('AdminContact', 'RegistrantContact', 'TechContact')}, 'nameservers': ns,
            'dns_evidence': {'domain': 'example.test', 'nameservers': ns,
                'continuity': 'full_zone_migrated_verified', 'checked_at': NOW},
            'quote': {'currency': 'USD', 'amount': 15.0}, 'accepted_at': NOW, 'auto_renew': False}


class Registrar:
    def __init__(self):
        self.submits = 0
        self.result = 'SUBMITTED'
        self.match = None
        self.available = True
        self.price = details()['quote']
        self.timeout = False

    def check(self, domain, code):
        return {'transferable': self.available, 'quote': self.price}

    def submit(self, request, code):
        self.submits += 1
        if self.timeout:
            raise TimeoutError('private code and contact must not be logged')
        return 'provider-operation'

    def reconcile(self, domain, submitted_at):
        return self.match

    def detail(self, operation, domain):
        return self.result


class TransferTest(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.cipher = Fernet(Fernet.generate_key())
        intake = {'subscription_id': SUB, 'subject': 'buyer', 'host': 'www.example.test',
                  'status': 'received', 'auth_code': self.cipher.encrypt(b'private-transfer-code').decode()}
        self.store.put('clinic-intake:' + SUB, intake)
        self.store.transact(enqueue_writes(self.store, intake))
        self.store.put('stripe-subscription:' + SUB, {'status': 'active', 'subject': 'buyer', 'plan': 'basic'})
        self.registrar = Registrar()

    def ready(self):
        prepare(self.store, SUB, details(), self.cipher, NOW)

    def tick(self, now=NOW):
        return run_one(self.store, self.registrar, self.cipher, lambda: now)

    def test_intake_creates_private_details_wait_without_claim_or_transfer(self):
        row = self.store.get(key(SUB))
        self.assertEqual(row['status'], 'awaiting_details')
        self.assertIsNone(self.store.get(QUEUE))
        self.assertEqual(enqueue_writes(self.store, self.store.get('clinic-intake:' + SUB)), [])
        self.assertNotIn('private-transfer-code', json.dumps(row))
        self.assertIsNone(self.store.get('principal:buyer'))

    def test_contact_dns_and_fee_must_be_bound_to_this_domain(self):
        for field, value in [('contacts', {}), ('nameservers', []), ('dns_evidence', {}),
                             ('quote', {}), ('domain', 'someone-else.test')]:
            with self.subTest(field=field):
                request = details(); request[field] = value
                with self.assertRaises(ValueError):
                    prepare(self.store, SUB, request, self.cipher, NOW)
        self.assertIsNone(self.store.get(QUEUE))
        self.assertEqual(self.registrar.submits, 0)

    def test_prepare_encrypts_contacts_and_reserves_domain_before_queueing(self):
        self.ready()
        row = self.store.get(key(SUB))
        self.assertEqual(row['status'], 'ready')
        self.assertNotIn('owner@example.test', json.dumps(row))
        self.assertEqual(self.store.get('domain-transfer-owner:example.test')['subscription_id'], SUB)
        self.assertEqual(self.store.get(QUEUE)['subscriptions'], [SUB])

    def test_other_subscription_cannot_take_the_same_domain(self):
        self.store.put('domain-transfer-owner:example.test', {'subscription_id': 'sub_another12345'})
        with self.assertRaisesRegex(ValueError, 'domain_transfer_in_use'):
            self.ready()
        self.assertIsNone(self.store.get(QUEUE))

    def test_inactive_or_different_buyer_cannot_submit_transfer(self):
        self.ready()
        for status, subject in [('canceled', 'buyer'), ('active', 'different-buyer')]:
            old = self.store.get('stripe-subscription:' + SUB)
            self.store.put('stripe-subscription:' + SUB, {**old, 'status': status, 'subject': subject}, old['_version'])
            self.tick()
        self.assertEqual(self.registrar.submits, 0)

    def test_completion_requires_provider_success_not_only_authcode_or_copy(self):
        self.ready(); self.tick()
        self.assertEqual(self.store.get(key(SUB))['status'], 'transferring')
        self.tick()
        self.assertEqual(self.store.get(key(SUB))['status'], 'transferring')
        self.registrar.result = 'SUCCESSFUL'; self.tick(NOW + 60)
        self.assertEqual(self.store.get(key(SUB))['status'], 'complete')
        self.assertIsNone(self.store.get('principal:buyer'))
        self.tick(NOW + 61)
        self.assertEqual(self.store.get(QUEUE)['subscriptions'], [])
        self.assertEqual(self.registrar.submits, 1)

    def test_lost_submission_response_only_reconciles_never_charges_twice(self):
        self.ready(); self.registrar.timeout = True; self.tick()
        self.assertEqual(self.store.get(key(SUB))['status'], 'submission_unknown')
        self.tick(NOW + 61)
        self.assertEqual(self.registrar.submits, 1)
        self.registrar.match = 'provider-operation'; self.tick(NOW + 122)
        self.assertEqual(self.store.get(key(SUB))['status'], 'transferring')
        self.assertNotIn('private code', json.dumps(self.store.rows))

    def test_crash_between_durable_intent_and_api_call_does_not_resubmit(self):
        self.ready()
        row = self.store.get(key(SUB))
        self.store.put(key(SUB), {**row, 'status': 'submitting', 'submitted_at': NOW}, row['_version'])
        self.tick()
        self.assertEqual(self.registrar.submits, 0)
        self.assertEqual(self.store.get(key(SUB))['status'], 'submission_unknown')

    def test_revised_price_lock_or_stale_dns_require_customer_input(self):
        for change in ('price', 'locked', 'expired'):
            with self.subTest(change=change):
                self.setUp(); self.ready()
                if change == 'price': self.registrar.price = {'currency': 'USD', 'amount': 20}
                if change == 'locked': self.registrar.available = False
                self.tick(NOW + 3601 if change == 'expired' else NOW)
                self.assertEqual(self.registrar.submits, 0)
                self.assertEqual(self.store.get(key(SUB))['status'], 'awaiting_details')

    def test_changed_authcode_cannot_start_a_prepared_transfer(self):
        self.ready(); intake = self.store.get('clinic-intake:' + SUB)
        self.store.put('clinic-intake:' + SUB, {**intake, 'auth_code': self.cipher.encrypt(b'changed').decode()}, intake['_version'])
        self.tick()
        self.assertEqual(self.registrar.submits, 0)
        self.assertEqual(self.store.get(key(SUB))['reason'], 'intake_changed')

    def test_cancellation_racing_preflight_prevents_the_chargeable_request(self):
        self.ready()
        def check(domain, code):
            current = self.store.get('stripe-subscription:' + SUB)
            self.store.put('stripe-subscription:' + SUB, {**current, 'status': 'canceled'}, current['_version'])
            return {'transferable': True, 'quote': details()['quote']}
        self.registrar.check = check
        self.tick()
        self.assertEqual(self.registrar.submits, 0)

    def test_definitive_provider_rejection_allows_customer_to_correct_details(self):
        self.ready()
        def reject(request, code):
            raise TransferRejected('registrar_details_rejected')
        self.registrar.submit = reject
        self.tick()
        self.assertEqual(self.store.get(key(SUB))['status'], 'awaiting_details')
        self.assertEqual(self.store.get(key(SUB))['required'], ['registrar_details'])

    def test_public_projection_excludes_contacts_credentials_and_provider_ids(self):
        self.ready(); self.tick()
        self.assertEqual(public_status(self.store.get(key(SUB))), {
            'stage': 'domain_transfer', 'status': 'transferring', 'required': [], 'reason': None})


class Route53ContractTest(unittest.TestCase):
    def test_scheduled_worker_disables_sdk_retries_for_non_idempotent_transfer(self):
        from hp_control import transfer_clinic_domains
        client = SimpleNamespace(meta=SimpleNamespace(service_model=SimpleNamespace(
            operation_model=lambda name: SimpleNamespace(input_shape=SimpleNamespace(members={'Consent': None})))))
        with patch('boto3.client', return_value=client) as factory:
            result = transfer_clinic_domains({}, None, store=MemoryStore(), cipher=Fernet(Fernet.generate_key()))
        self.assertFalse(result['handled'])
        self.assertEqual(factory.call_args.kwargs['config'].retries, {'total_max_attempts': 1})

    def test_real_sdk_accepts_price_cap_and_complete_contacts_without_network(self):
        import boto3
        from botocore.stub import Stubber
        client = boto3.client('route53domains', region_name='us-east-1', aws_access_key_id='test', aws_secret_access_key='test')
        request = details()
        expected = {'DomainName': request['domain'], 'AuthCode': 'test-code',
                    'Nameservers': request['nameservers'], 'AutoRenew': False, **request['contacts'],
                    'Consent': {'MaxPrice': 15.0, 'Currency': 'USD'}}
        with Stubber(client) as stub:
            stub.add_response('transfer_domain', {'OperationId': 'provider-operation'}, expected)
            self.assertEqual(Route53Registrar(client).submit(request, 'test-code'), 'provider-operation')

    def test_older_sdk_cannot_silently_remove_accepted_price_cap(self):
        client = SimpleNamespace(meta=SimpleNamespace(service_model=SimpleNamespace(
            operation_model=lambda name: SimpleNamespace(input_shape=SimpleNamespace(members={})))) )
        with self.assertRaisesRegex(ValueError, 'registrar_sdk_price_cap_unavailable'):
            Route53Registrar(client)

    def test_reconciliation_requires_all_pages_and_a_unique_matching_domain(self):
        class Client:
            def list_operations(self, **args):
                return {'NextPageMarker': 'next', 'Operations': [{'DomainName': 'example.test', 'OperationId': 'first'}]}
        registrar = object.__new__(Route53Registrar); registrar.client = Client()
        self.assertIsNone(registrar.reconcile('example.test', NOW))
        registrar.client.list_operations = lambda **args: {'Operations': [
            {'DomainName': 'example.test', 'OperationId': 'one'}, {'DomainName': 'example.test', 'OperationId': 'two'}]}
        self.assertIsNone(registrar.reconcile('example.test', NOW))


if __name__ == '__main__':
    unittest.main()
