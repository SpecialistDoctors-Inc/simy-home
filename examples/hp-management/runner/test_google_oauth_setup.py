import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from google_oauth_setup import SCOPES, _credential_document, _validate_expected_principal


class Credentials:
    def apply(self, headers):
        headers['Authorization'] = 'Bearer test'

    def to_json(self):
        return json.dumps({'refresh_token': 'not-real'})


class Response:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class OAuthSetupTest(unittest.TestCase):
    def test_google_returned_email_scope_matches_requested_scope(self):
        # Observed Google token response: the email alias was expanded to this
        # URI, which oauthlib correctly rejects if the request used the alias.
        returned = {'openid', 'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/spreadsheets'}
        self.assertEqual(returned, set(SCOPES))

    def test_document_forces_authorized_user_and_exact_scopes(self):
        payload = json.loads(_credential_document(Credentials(), SCOPES))
        self.assertEqual('authorized_user', payload['type'])
        self.assertEqual(SCOPES, payload['scopes'])

    def test_expected_principal_must_match_before_save(self):
        calls = []

        def good(url, **kwargs):
            calls.append((url, kwargs))
            return Response({'sub': 'sub-1', 'email': 'operator@example.com', 'email_verified': True})

        _validate_expected_principal(Credentials(), 'sub-1', 'operator@example.com', good)
        self.assertEqual('Bearer test', calls[0][1]['headers']['Authorization'])

        with self.assertRaisesRegex(ValueError, '^Google identity did not match expected subject/email$'):
            _validate_expected_principal(Credentials(), 'other', 'operator@example.com', good)


if __name__ == '__main__':
    unittest.main()
