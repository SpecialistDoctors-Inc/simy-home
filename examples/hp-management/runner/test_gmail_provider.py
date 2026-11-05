"""Fake-transport tests for admitted Gmail notices; no mail is sent."""
import base64
from contextlib import nullcontext
from email import policy
from email.parser import BytesParser
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from gmail_provider import GMAIL_API, GMAIL_READONLY_SCOPE, GMAIL_SEND_SCOPE, Gmail
from google_provider import EMAIL_SCOPE, OPENID_SCOPE, USERINFO_URL
from provider_errors import EffectNotStarted


class Response:
    def __init__(self, payload):
        self.status_code = 200
        self.payload = payload

    def json(self):
        return self.payload


class Credentials:
    valid = True
    expired = False
    scopes = [OPENID_SCOPE, EMAIL_SCOPE, GMAIL_SEND_SCOPE, GMAIL_READONLY_SCOPE]

    def apply(self, headers):
        headers['Authorization'] = 'Bearer fake'


class Transport:
    def __init__(self):
        self.calls = []
        self.message = None
        self.fail_send = False

    def request(self, method, url, *, params=None, json=None):
        self.calls.append((method, url, params, json))
        if url == USERINFO_URL:
            return Response({'sub': 'sub-1', 'email': 'operator@example.com', 'email_verified': True})
        if method == 'GET' and url == GMAIL_API:
            return Response({'messages': [] if self.message is None else [{'id': self.message['id']}]})
        if method == 'GET' and url == f'{GMAIL_API}/message-1':
            return Response(self.message)
        if method == 'POST' and url == f'{GMAIL_API}/send':
            if self.fail_send:
                raise OSError('lost response')
            raw = base64.urlsafe_b64decode(json['raw'] + '=' * (-len(json['raw']) % 4))
            parsed = BytesParser(policy=policy.SMTP).parsebytes(raw)
            body = parsed.get_payload(decode=True).decode('utf-8')
            self.message = {
                'id': 'message-1', 'labelIds': ['SENT'],
                'payload': {
                    'mimeType': 'text/plain',
                    'headers': [{'name': key, 'value': value} for key, value in parsed.items()],
                    'body': {'data': base64.urlsafe_b64encode(body.encode()).decode().rstrip('=')},
                },
            }
            return Response({'id': 'message-1'})
        raise AssertionError((method, url))


class GmailTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.transport = Transport()
        self.adapter = Gmail(
            {'recipient': 'clinic@example.com'}, Path(self.temp.name) / 'private.json',
            'sub-1', 'operator@example.com', transport=self.transport,
            credentials=Credentials(), notice_admission=lambda _key: nullcontext(),
        )

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def envelope():
        return {'to': 'clinic@example.com', 'subject': 'Ready', 'body': 'Preview ready\nHP-NOTICE-key-1'}

    def test_send_once_then_exact_readback_and_replay(self):
        sent = self.adapter.send_notice(self.envelope(), 'key-1')
        self.assertEqual({'provider_message_id': 'message-1', 'readback_verified': True, 'created': True}, sent)
        replay = self.adapter.send_notice(self.envelope(), 'key-1')
        self.assertFalse(replay['created'])
        self.assertEqual(1, len([call for call in self.transport.calls if call[0] == 'POST']))

    def test_rfc2047_subject_and_crlf_body_readback_match(self):
        envelope = {'to': 'clinic@example.com', 'subject': '確認準備完了', 'body': '一行目\n二行目\nHP-NOTICE-key-1'}
        sent = self.adapter.send_notice(envelope, 'key-1')
        self.assertTrue(sent['readback_verified'])
        subject = next(header['value'] for header in self.transport.message['payload']['headers'] if header['name'] == 'Subject')
        self.assertEqual('確認準備完了', subject)

    def test_untrusted_recipient_and_missing_admission_cannot_send(self):
        wrong = {**self.envelope(), 'to': 'other@example.com'}
        with self.assertRaisesRegex(EffectNotStarted, '^send_notice_preflight_failed$') as error:
            self.adapter.send_notice(wrong, 'key-1')
        self.assertEqual('untrusted notification recipient', str(error.exception.__cause__))
        injected = {**self.envelope(), 'subject': 'Ready\nBcc: attacker@example.com'}
        with self.assertRaisesRegex(EffectNotStarted, '^send_notice_preflight_failed$') as error:
            self.adapter.send_notice(injected, 'key-1')
        self.assertEqual('invalid envelope', str(error.exception.__cause__))
        no_admission = Gmail({'recipient': 'clinic@example.com'}, Path(self.temp.name) / 'private.json', 'sub-1', 'operator@example.com', transport=self.transport, credentials=Credentials())
        with self.assertRaisesRegex(EffectNotStarted, '^send_notice_preflight_failed$') as error:
            no_admission.send_notice(self.envelope(), 'key-1')
        self.assertEqual('durable notice admission is required', str(error.exception.__cause__))
        self.assertEqual(0, len([call for call in self.transport.calls if call[0] == 'POST']))

    def test_multiple_or_mismatched_sent_messages_fail_closed(self):
        self.transport.message = {'id': 'message-1', 'labelIds': ['SENT'], 'payload': {'headers': [], 'mimeType': 'text/plain', 'body': {'data': ''}}}
        original = self.transport.request

        def multiple(method, url, *, params=None, json=None):
            if method == 'GET' and url == GMAIL_API:
                return Response({'messages': [{'id': 'one'}, {'id': 'two'}]})
            return original(method, url, params=params, json=json)

        self.transport.request = multiple
        with self.assertRaisesRegex(ValueError, '^multiple matching notices$'):
            self.adapter.find_notice(self.envelope(), 'key-1')

        self.transport.request = original
        with self.assertRaisesRegex(ValueError, '^notice content mismatch$'):
            self.adapter.find_notice(self.envelope(), 'key-1')

    def test_send_transport_failure_is_uncertain_without_retry(self):
        self.transport.fail_send = True
        with self.assertRaisesRegex(RuntimeError, '^notice send outcome is uncertain; reconcile before retry$'):
            self.adapter.send_notice(self.envelope(), 'key-1')
        self.assertEqual(1, len([call for call in self.transport.calls if call[0] == 'POST']))


if __name__ == '__main__':
    unittest.main()
