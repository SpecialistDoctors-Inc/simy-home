import unittest
from unittest.mock import patch
from hp_control import domain_verification, handler
from store import MemoryStore


class DomainVerificationTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.issuer = 'https://hp-control.simy.one'
        self.event = {'rawPath': '/.well-known/openai-apps-challenge',
                      'requestContext': {'http': {'method': 'GET'}}}
        self.token = 'example-public-domain-proof-for-test'

    def test_exact_plaintext_proof_has_no_wrapper_or_private_fields(self):
        self.store.put('domain-verification:openai', {'issuer': self.issuer,
            'token': self.token, 'private_note': 'must not be returned'})
        result = domain_verification(self.event, self.store, self.issuer)
        self.assertEqual(result['statusCode'], 200)
        self.assertEqual(result['body'], self.token)
        self.assertEqual(result['headers']['Cache-Control'], 'no-store')
        self.assertEqual(result['headers']['Content-Type'], 'text/plain; charset=utf-8')

    def test_missing_wrong_issuer_or_malformed_proof_is_not_served(self):
        for value in ({}, {'issuer': 'https://other.invalid', 'token': self.token},
                      {'issuer': self.issuer, 'token': self.token+'\n'},
                      {'issuer': self.issuer, 'token': {'unexpected': 'object'}},
                      {'issuer': self.issuer, 'token': 'x'*1025}):
            with self.subTest(value=value):
                store = MemoryStore(); store.put('domain-verification:openai', value)
                result = domain_verification(self.event, store, self.issuer)
                self.assertEqual((result['statusCode'], result['body']), (404, ''))

    def test_post_never_reads_or_modifies_authority(self):
        event = {**self.event, 'requestContext': {'http': {'method': 'POST'}}}
        with patch.object(self.store, 'get', side_effect=AssertionError('unexpected read')):
            self.assertEqual(domain_verification(event, self.store, self.issuer)['statusCode'], 405)
        self.assertEqual(self.store.rows, {})

    def test_route_does_not_initialize_oauth_or_other_providers(self):
        self.store.put('domain-verification:openai', {'issuer': self.issuer,'token':self.token})
        with patch.dict('os.environ', {'HP_TABLE_NAME':'test-only','HP_PUBLIC_BASE_URL':self.issuer}), \
             patch('hp_control.DynamoStore', return_value=self.store), \
             patch('hp_control.application', side_effect=AssertionError('no credentials needed')):
            self.assertEqual(handler(self.event, None)['body'], self.token)


if __name__ == '__main__': unittest.main()
