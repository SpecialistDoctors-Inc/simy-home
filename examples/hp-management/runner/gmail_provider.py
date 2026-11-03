"""Direct Gmail API adapter for already-admitted HP notifications."""
from __future__ import annotations

import base64
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.policy import SMTP
import json
import os
from pathlib import Path
import stat
from typing import Any, Mapping
from urllib.parse import quote
import re

from google_provider import EMAIL_SCOPE, OPENID_SCOPE, USERINFO_URL, _RequestsTransport, _require
from provider_errors import AuthenticationRequired, EffectNotStarted, classify_effect, note_write_attempt


GMAIL_SEND_SCOPE = 'https://www.googleapis.com/auth/gmail.send'
GMAIL_READONLY_SCOPE = 'https://www.googleapis.com/auth/gmail.readonly'
GMAIL_API = 'https://gmail.googleapis.com/gmail/v1/users/me/messages'


class Gmail:
    """Gmail sender with exact SENT readback and no automatic retry."""

    def __init__(
        self,
        site_config: Mapping[str, Any],
        credential_path: str | os.PathLike[str],
        expected_subject: str,
        expected_email: str,
        *,
        transport: Any | None = None,
        credentials: Any | None = None,
        notice_admission: Any | None = None,
    ):
        _require(isinstance(site_config, Mapping), 'invalid site configuration')
        recipient = site_config.get('recipient')
        _require(isinstance(recipient, str) and re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', recipient),
                 'invalid trusted recipient')
        self.site_config = dict(site_config)
        self.recipient = recipient
        self.expected_subject = expected_subject
        self.expected_email = expected_email.casefold()
        self.credential_path = Path(credential_path)
        self._credentials = credentials or self._load_credentials()
        self._require_scopes([OPENID_SCOPE, EMAIL_SCOPE, GMAIL_SEND_SCOPE, GMAIL_READONLY_SCOPE])
        self._transport = transport or _RequestsTransport(self._credentials)
        self._notice_admission = notice_admission

    def _load_credentials(self):
        try:
            details = os.stat(self.credential_path, follow_symlinks=False)
            _require(stat.S_ISREG(details.st_mode), 'Google credential file must be regular')
            _require(not details.st_mode & 0o077, 'Google credential file permissions must be 0600')
            with self.credential_path.open(encoding='utf-8') as source:
                payload = json.load(source)
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError('Google credential file is unavailable') from error
        _require(payload.get('type') in (None, 'authorized_user'), 'Gmail requires user OAuth credentials')
        _require({'refresh_token', 'client_id', 'client_secret', 'token_uri'} <= set(payload), 'invalid Google credential file')
        try:
            from google.oauth2.credentials import Credentials
        except ImportError as error:  # pragma: no cover
            raise RuntimeError('google-auth is required for Gmail access') from error
        return Credentials.from_authorized_user_info({**payload, 'type': 'authorized_user'}, scopes=None)

    def _require_scopes(self, required: list[str]) -> None:
        approved = getattr(self._credentials, 'scopes', None)
        _require(isinstance(approved, (list, tuple, set)) and set(required) <= set(approved),
                 'Google credential lacks required scopes')

    def set_notice_admission(self, admission: Any) -> None:
        _require(callable(admission), 'invalid notice admission')
        self._notice_admission = admission

    def _refresh_if_needed(self) -> None:
        if getattr(self._credentials, 'expired', False) or not getattr(self._credentials, 'valid', True):
            try:
                from google.auth.transport.requests import Request
                self._credentials.refresh(Request())
            except Exception as error:
                raise AuthenticationRequired('google', 'google_auth_refresh_required') from error

    def _request(self, method: str, url: str, *, params=None, json_body=None, operation: str) -> dict[str, Any]:
        self._refresh_if_needed()
        try:
            if method not in {'GET', 'HEAD'}:
                note_write_attempt(self)
            response = self._transport.request(method, url, params=params, json=json_body)
        except Exception as error:
            raise RuntimeError(f'Google {operation} request failed') from error
        status = getattr(response, 'status_code', 200)
        if status in {401, 403}:
            raise AuthenticationRequired('google', f'google_http_{status}', status)
        if not 200 <= status < 300:
            raise RuntimeError(f'Google {operation} request failed')
        try:
            payload = response.json()
        except Exception as error:
            raise RuntimeError(f'Google {operation} request failed') from error
        if not isinstance(payload, dict):
            raise RuntimeError(f'Google {operation} request failed')
        return payload

    def authorized_user(self) -> dict[str, str]:
        profile = self._request('GET', USERINFO_URL, operation='userinfo')
        subject, email = profile.get('sub'), profile.get('email')
        _require(isinstance(subject, str) and subject == self.expected_subject, 'Google subject mismatch')
        _require(isinstance(email, str) and email.casefold() == self.expected_email, 'Google email mismatch')
        _require(profile.get('email_verified') is True, 'Google email is not verified')
        return {'sub': subject, 'email': email}

    def _validate_envelope(self, envelope: Mapping[str, Any], key: str) -> dict[str, str]:
        _require(isinstance(key, str) and key, 'invalid notification key')
        _require(isinstance(envelope, Mapping) and set(envelope) == {'to', 'subject', 'body'}, 'invalid envelope')
        _require(all(isinstance(envelope[field], str) and envelope[field] for field in envelope), 'invalid envelope')
        _require(envelope['to'].casefold() == self.recipient.casefold(), 'untrusted notification recipient')
        _require(not any(character in envelope['to'] + envelope['subject'] for character in '\r\n')
                 and f'HP-NOTICE-{key}' in envelope['body'],
                 'invalid envelope')
        return dict(envelope)

    @staticmethod
    def _plain_body(payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None
        if payload.get('mimeType') == 'text/plain' and isinstance(payload.get('body', {}).get('data'), str):
            raw = payload['body']['data']
            try:
                return base64.urlsafe_b64decode(raw + '=' * (-len(raw) % 4)).decode('utf-8')
            except (ValueError, UnicodeDecodeError):
                return None
        for part in payload.get('parts', []) if isinstance(payload.get('parts'), list) else []:
            body = Gmail._plain_body(part)
            if body is not None:
                return body
        return None

    @staticmethod
    def _decoded_subject(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        try:
            return str(make_header(decode_header(value)))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _transport_body(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.replace('\r\n', '\n').replace('\r', '\n')
        # EmailMessage/SMTP represents a text part with one terminal newline.
        return normalized[:-1] if normalized.endswith('\n') else normalized

    def find_notice(self, envelope: Mapping[str, Any], key: str) -> dict[str, Any] | None:
        expected = self._validate_envelope(envelope, key)
        self.authorized_user()
        search = self._request(
            'GET', GMAIL_API, params={'q': f'in:sent "HP-NOTICE-{key}"', 'labelIds': 'SENT', 'maxResults': 2},
            operation='Gmail search',
        )
        messages = search.get('messages', [])
        _require(isinstance(messages, list), 'Gmail search response was invalid')
        _require(len(messages) <= 1 and not search.get('nextPageToken'), 'multiple matching notices')
        if not messages:
            return None
        message_id = messages[0].get('id') if isinstance(messages[0], dict) else None
        _require(isinstance(message_id, str) and message_id, 'Gmail search response was invalid')
        message = self._request('GET', f'{GMAIL_API}/{quote(message_id, safe="")}', params={'format': 'full'}, operation='Gmail readback')
        _require('SENT' in message.get('labelIds', []), 'notice is not sent')
        headers = {item.get('name', '').casefold(): item.get('value') for item in message.get('payload', {}).get('headers', []) if isinstance(item, dict)}
        _require(headers.get('to') == expected['to'] and self._decoded_subject(headers.get('subject')) == expected['subject'], 'notice content mismatch')
        _require(self._transport_body(self._plain_body(message.get('payload'))) == self._transport_body(expected['body']), 'notice content mismatch')
        return {'provider_message_id': message_id, 'readback_verified': True}

    @classify_effect
    def send_notice(self, envelope: Mapping[str, Any], key: str) -> dict[str, Any]:
        expected = self._validate_envelope(envelope, key)
        _require(callable(self._notice_admission), 'durable notice admission is required')
        with self._notice_admission(key):
            existing = self.find_notice(expected, key)
            if existing is not None:
                return {**existing, 'created': False}
            message = EmailMessage(policy=SMTP)
            message['To'] = expected['to']
            message['Subject'] = expected['subject']
            message.set_content(expected['body'], subtype='plain', charset='utf-8')
            raw = message.as_bytes(policy=SMTP)
            try:
                sent = self._request('POST', f'{GMAIL_API}/send', json_body={'raw': base64.urlsafe_b64encode(raw).decode('ascii')}, operation='Gmail send')
                _require(isinstance(sent.get('id'), str) and sent['id'], 'Gmail send response was invalid')
                readback = self.find_notice(expected, key)
            except EffectNotStarted:
                raise
            except Exception as error:
                raise RuntimeError('notice send outcome is uncertain; reconcile before retry') from error
            if readback is None or readback['provider_message_id'] != sent['id']:
                raise RuntimeError('notice send outcome is uncertain; reconcile before retry')
            return {**readback, 'created': True}
