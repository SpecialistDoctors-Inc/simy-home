import json
import time
import unittest

import test_clinic_onboarding as clinic
from domain_transfer import key
from transfer_intake import TransferIntake


class Registrar:
    calls = 0

    def check(self, domain, code):
        self.calls += 1
        return {'transferable': True, 'quote': {'currency': 'USD', 'amount': 15.0}}


class TransferSignupTest(unittest.TestCase):
    def setUp(self):
        self.h = clinic.ClinicOnboardingTest()
        self.h.setUp(); self.h.sign_in()
        self.store = self.h.store
        self.registrar = Registrar()
        self.h.onboarding.transfer = TransferIntake(self.store, self.registrar, self.h.onboarding.cipher)
        self.h.call('POST', '/start/site', form={'session_id': clinic.SESSION,
            'site_url': 'https://clinic.example.jp', 'auth_code': clinic.AUTH_CODE})
        self.dns = {'subject': 'google-subject', 'host': 'clinic.example.jp', 'domain': 'example.jp',
            'status': 'verified', 'checked_at': int(time.time()), 'continuity': 'full_zone_migrated_verified',
            'nameservers': [{'Name': 'ns1.example.test'}, {'Name': 'ns2.example.test'}]}

    def quote(self):
        self.store.put('dns-connection:' + clinic.SUB, self.dns)
        result = self.h.call('POST', '/start/transfer/quote', form={'session_id': clinic.SESSION})
        self.assertEqual(result['statusCode'], 303)
        return self.store.get('transfer-form:' + clinic.SUB)['quote_id']

    def form(self, quote):
        return {'session_id': clinic.SESSION, 'quote_id': quote, 'ContactType': 'COMPANY',
            'FirstName': 'Hanako', 'LastName': 'Example', 'OrganizationName': 'Example Clinic',
            'AddressLine1': '1 Test Road', 'City': 'Minato', 'State': 'Tokyo', 'CountryCode': 'JP',
            'ZipCode': '1050001', 'PhoneNumber': '+81.312345678', 'Email': 'owner@example.test',
            'accept_transfer': 'yes'}

    def test_paid_signup_renders_and_prepares_transfer_with_server_quote(self):
        quote = self.quote()
        html = self.h.call('GET', '/start', {'session_id': clinic.SESSION})['body']
        self.assertIn('/start/transfer', html)
        self.assertIn('15.00 USD', html)
        self.assertNotIn(clinic.AUTH_CODE, html)
        form = {**self.form(quote), 'amount': '0', 'currency': 'JPY'}
        self.assertEqual(self.h.call('POST', '/start/transfer', form=form)['statusCode'], 303)
        job = self.store.get(key(clinic.SUB))
        self.assertEqual(job['status'], 'ready')
        request = json.loads(self.h.onboarding.cipher.decrypt(job['sealed_request'].encode()))
        self.assertEqual(request['quote'], {'currency': 'USD', 'amount': 15.0})
        self.assertFalse(request['auto_renew'])
        self.assertIsNone(self.store.get('transfer-quote:' + quote))

    def test_dns_proof_cannot_be_forged_in_the_form(self):
        self.h.call('POST', '/start/transfer/quote', form={'session_id': clinic.SESSION,
                    'dns_evidence': json.dumps(self.dns)})
        self.assertEqual(self.registrar.calls, 0)
        self.assertIsNone(self.store.get('transfer-form:' + clinic.SUB))

    def test_authentication_and_origin_precede_provider_access(self):
        for overrides in ({'origin': 'https://attacker.example'}, {'cookie': ''}):
            self.h.call('POST', '/start/transfer/quote', form={'session_id': clinic.SESSION}, **overrides)
        self.assertEqual(self.registrar.calls, 0)

    def test_quote_from_other_buyer_or_changed_dns_is_not_consumed(self):
        quote = self.quote()
        dns = self.store.get('dns-connection:' + clinic.SUB)
        self.store.put('dns-connection:' + clinic.SUB, {**dns, 'nameservers': []}, dns['_version'])
        self.h.call('POST', '/start/transfer', form=self.form(quote))
        self.assertEqual(self.store.get(key(clinic.SUB))['status'], 'awaiting_details')
        self.assertIsNotNone(self.store.get('transfer-quote:' + quote))

    def test_contact_or_acceptance_errors_do_not_queue_or_charge(self):
        quote = self.quote()
        for changes in ({'accept_transfer': ''}, {'PhoneNumber': '123'}, {'Email': 'invalid'}):
            self.h.call('POST', '/start/transfer', form={**self.form(quote), **changes})
            self.assertEqual(self.store.get(key(clinic.SUB))['status'], 'awaiting_details')

    def test_quote_is_bound_to_current_authcode(self):
        quote = self.quote()
        intake = self.store.get('clinic-intake:' + clinic.SUB)
        self.store.put('clinic-intake:' + clinic.SUB, {**intake,
            'auth_code': self.h.onboarding.cipher.encrypt(b'changed-code').decode()}, intake['_version'])
        self.h.call('POST', '/start/transfer', form=self.form(quote))
        self.assertEqual(self.store.get(key(clinic.SUB))['status'], 'awaiting_details')

    def test_familiar_japanese_phone_format_is_normalized_without_external_service(self):
        quote = self.quote()
        self.h.call('POST', '/start/transfer', form={**self.form(quote), 'PhoneNumber': '03-1234-5678'})
        job = self.store.get(key(clinic.SUB))
        request = json.loads(self.h.onboarding.cipher.decrypt(job['sealed_request'].encode()))
        self.assertEqual(request['contacts']['RegistrantContact']['PhoneNumber'], '+81.312345678')


if __name__ == '__main__':
    unittest.main()
