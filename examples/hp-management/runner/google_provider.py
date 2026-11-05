"""Portable Google Sheets adapter for the standalone HP delivery service.

This module deliberately has no Codex/MCP dependency.  It uses a credential
file supplied by the service operator and talks to the Sheets REST API directly.
It never prints credential paths, access tokens, or provider response bodies.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
from typing import Any, Mapping
from urllib.parse import quote

from provider_errors import AuthenticationRequired, EffectNotStarted, classify_effect, note_write_attempt


FIELDS = (
    'request_id', 'revision', 'site_id', 'outcome', 'target', 'effective_at',
    'expires_at', 'timezone', 'assets_rights', 'dependencies', 'acceptance',
    'requester_ref', 'notification_recipient_ref', 'proposal_state',
)
EVENT_FIELDS = (
    'event_id', 'request_id', 'revision', 'occurred_at', 'actor', 'kind',
    'body', 'reply_to_event_id', 'event_idempotency_key',
)
SHEETS_SCOPE = 'https://www.googleapis.com/auth/spreadsheets'
OPENID_SCOPE = 'openid'
EMAIL_SCOPE = 'https://www.googleapis.com/auth/userinfo.email'
USERINFO_URL = 'https://openidconnect.googleapis.com/v1/userinfo'
SHEETS_API = 'https://sheets.googleapis.com/v4/spreadsheets'


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


class _RequestsTransport:
    """Minimal transport wrapper so tests can substitute an in-memory fake."""

    def __init__(self, credentials: Any):
        try:
            import requests
        except ImportError as error:  # pragma: no cover - dependency guidance
            raise RuntimeError('requests is required for Google Sheets access') from error
        self._credentials = credentials
        self._session = requests.Session()

    def request(self, method: str, url: str, *, params=None, json=None):
        headers: dict[str, str] = {}
        self._credentials.apply(headers)
        return self._session.request(method, url, params=params, json=json, headers=headers, timeout=30)


class GoogleSheets:
    """Verified Google identity plus bounded Requests/Events Sheet operations.

    ``site_config`` must hold only service-controlled binding values.  In
    particular, the spreadsheet identifier comes from this config, never a
    customer request/event.  ``transport`` and ``credentials`` are test seams;
    production callers should omit both.
    """

    def __init__(
        self,
        site_config: Mapping[str, Any],
        credential_path: str | os.PathLike[str],
        expected_subject: str,
        expected_email: str,
        max_rows: int = 2000,
        *,
        transport: Any | None = None,
        credentials: Any | None = None,
        event_admission: Any | None = None,
    ):
        _require(isinstance(site_config, Mapping), 'invalid site configuration')
        configured_sheet_id = site_config.get('sheet_id')
        legacy_spreadsheet_id = site_config.get('spreadsheet_id')
        _require(
            (configured_sheet_id is None or isinstance(configured_sheet_id, str))
            and (legacy_spreadsheet_id is None or isinstance(legacy_spreadsheet_id, str)),
            'invalid sheet identifier',
        )
        _require(
            bool(configured_sheet_id or legacy_spreadsheet_id)
            and not (configured_sheet_id and legacy_spreadsheet_id and configured_sheet_id != legacy_spreadsheet_id),
            'missing or conflicting sheet identifier',
        )
        spreadsheet_id = configured_sheet_id or legacy_spreadsheet_id
        _require(isinstance(spreadsheet_id, str) and spreadsheet_id.strip(), 'missing sheet identifier')
        _require(isinstance(expected_subject, str) and expected_subject.strip(), 'missing expected subject')
        _require(isinstance(expected_email, str) and expected_email.strip(), 'missing expected email')
        _require(type(max_rows) is int and 1 <= max_rows <= 2000, 'invalid max_rows')
        self.site_config = dict(site_config)
        self.spreadsheet_id = spreadsheet_id
        self.expected_subject = expected_subject
        self.expected_email = expected_email.casefold()
        self.max_rows = max_rows
        self.credential_path = Path(credential_path)
        self._credentials = credentials or self._load_credentials()
        self._require_scopes([SHEETS_SCOPE, OPENID_SCOPE, EMAIL_SCOPE])
        self._transport = transport or _RequestsTransport(self._credentials)
        self._event_admission = event_admission

    def _load_credentials(self):
        """Load only the explicitly named private credential file."""
        try:
            details = os.stat(self.credential_path, follow_symlinks=False)
        except OSError as error:
            raise RuntimeError('Google credential file is unavailable') from error
        _require(stat.S_ISREG(details.st_mode), 'Google credential file must be regular')
        _require(not details.st_mode & 0o077, 'Google credential file permissions must be 0600')
        try:
            with self.credential_path.open(encoding='utf-8') as source:
                payload = json.load(source)
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError('Google credential file is invalid') from error

        credential_type = payload.get('type')
        try:
            if credential_type == 'service_account':
                from google.oauth2 import service_account
                trusted_email = self.site_config.get('trusted_service_account_email')
                _require(isinstance(trusted_email, str) and trusted_email, 'missing trusted service account')
                _require(payload.get('client_email') == trusted_email, 'service account identity mismatch')
                return service_account.Credentials.from_service_account_file(
                    str(self.credential_path), scopes=[SHEETS_SCOPE]
                )
            if credential_type == 'authorized_user':
                from google.oauth2.credentials import Credentials
                return Credentials.from_authorized_user_info(
                    {**payload, 'type': 'authorized_user'}, scopes=None
                )
            if credential_type is None and {'refresh_token', 'client_id', 'client_secret', 'token_uri'} <= set(payload):
                from google.oauth2.credentials import Credentials
                return Credentials.from_authorized_user_info(
                    {**payload, 'type': 'authorized_user'}, scopes=None
                )
        except ImportError as error:  # pragma: no cover - dependency guidance
            raise RuntimeError('google-auth is required for Google Sheets access') from error
        raise ValueError('unsupported Google credential type')

    def _require_scopes(self, required: list[str]) -> None:
        if getattr(self._credentials, 'service_account_email', None) is not None:
            return
        approved = getattr(self._credentials, 'scopes', None)
        _require(isinstance(approved, (list, tuple, set)), 'Google credential scopes are unavailable')
        _require(set(required) <= set(approved), 'Google credential lacks required scopes')

    def set_event_admission(self, admission: Any) -> None:
        """Install the controller's durable, per-sheet/event serialization."""
        _require(callable(admission), 'invalid event admission')
        self._event_admission = admission

    def _refresh_if_needed(self) -> None:
        if getattr(self._credentials, 'expired', False) or not getattr(self._credentials, 'valid', True):
            try:
                from google.auth.transport.requests import Request
                self._credentials.refresh(Request())
            except Exception as error:  # provider details can include sensitive data
                raise AuthenticationRequired('google', 'google_auth_refresh_required') from error

    def _response_json(self, response: Any, operation: str) -> dict[str, Any]:
        status = getattr(response, 'status_code', 200)
        if status in {401, 403}:
            raise AuthenticationRequired('google', f'google_http_{status}', status)
        if not 200 <= status < 300:
            raise RuntimeError(f'Google {operation} request failed')
        try:
            payload = response.json()
        except Exception as error:
            raise RuntimeError(f'Google {operation} response was invalid') from error
        if not isinstance(payload, dict):
            raise RuntimeError(f'Google {operation} response was invalid')
        return payload

    def _request(self, method: str, url: str, *, params=None, json_body=None, operation: str) -> dict[str, Any]:
        self._refresh_if_needed()
        try:
            if method not in {'GET', 'HEAD'}:
                note_write_attempt(self)
            response = self._transport.request(method, url, params=params, json=json_body)
        except Exception as error:
            raise RuntimeError(f'Google {operation} request failed') from error
        return self._response_json(response, operation)

    def authorized_user(self) -> dict[str, str]:
        """Return the configured principal after an actual identity check."""
        service_email = getattr(self._credentials, 'service_account_email', None)
        if service_email is not None:
            trusted_email = self.site_config.get('trusted_service_account_email')
            _require(service_email == trusted_email, 'service account identity mismatch')
            _require(self.expected_subject == trusted_email, 'service account subject mismatch')
            _require(self.expected_email == trusted_email.casefold(), 'service account email mismatch')
            return {'sub': trusted_email, 'email': trusted_email}

        profile = self._request('GET', USERINFO_URL, operation='userinfo')
        subject = profile.get('sub')
        email = profile.get('email')
        _require(isinstance(subject, str) and subject == self.expected_subject, 'Google subject mismatch')
        _require(isinstance(email, str) and email.casefold() == self.expected_email, 'Google email mismatch')
        _require(profile.get('email_verified') is True, 'Google email is not verified')
        return {'sub': subject, 'email': email}

    def _ranges(self) -> list[str]:
        # Ask for one sentinel row beyond the configured maximum so a Sheet
        # growing past the service's bounded-read contract fails closed.
        last_row = self.max_rows + 5
        return [f'Requests!A4:N{last_row}', f'Events!A4:I{last_row}']

    @staticmethod
    def _records(values: Any, headers: tuple[str, ...], name: str, max_rows: int) -> list[dict[str, str]]:
        _require(isinstance(values, list) and values, f'{name} header is missing')
        header = values[0]
        _require(header == list(headers), f'{name} header mismatch')
        _require(len(values) - 1 <= max_rows, f'{name} exceeds max_rows')
        records: list[dict[str, str]] = []
        for row in values[1:]:
            _require(isinstance(row, list) and len(row) <= len(headers), f'{name} row is invalid')
            cells = row + [''] * (len(headers) - len(row))
            _require(all(isinstance(cell, str) for cell in cells), f'{name} row is invalid')
            if any(cells):
                records.append(dict(zip(headers, cells, strict=True)))
        return records

    def snapshot(self) -> dict[str, list[dict[str, str]]]:
        """Verify caller identity and headers, then return small bounded reads."""
        self.authorized_user()
        payload = self._request(
            'GET',
            f'{SHEETS_API}/{quote(self.spreadsheet_id, safe="")}/values:batchGet',
            params={'ranges': self._ranges(), 'majorDimension': 'ROWS', 'valueRenderOption': 'FORMATTED_VALUE'},
            operation='Sheets read',
        )
        ranges = payload.get('valueRanges')
        _require(isinstance(ranges, list) and len(ranges) == 2, 'Sheets read response was invalid')
        return {
            'requests': self._records(ranges[0].get('values'), FIELDS, 'Requests', self.max_rows),
            'events': self._records(ranges[1].get('values'), EVENT_FIELDS, 'Events', self.max_rows),
        }

    def find_event(self, key: str) -> dict[str, str] | None:
        _require(isinstance(key, str) and key, 'invalid event key')
        matches = [event for event in self.snapshot()['events'] if event['event_idempotency_key'] == key]
        _require(len(matches) <= 1, 'duplicate event key')
        return matches[0] if matches else None

    @staticmethod
    def _validated_event(event: Mapping[str, Any]) -> dict[str, str]:
        _require(isinstance(event, Mapping) and set(event) == set(EVENT_FIELDS), 'invalid event shape')
        _require(all(isinstance(event[field], str) for field in EVENT_FIELDS), 'invalid event value')
        _require(bool(event['event_idempotency_key']), 'invalid event key')
        return {field: event[field] for field in EVENT_FIELDS}

    @classify_effect
    def append_event(self, event: Mapping[str, Any]) -> dict[str, Any]:
        """Append exactly once, then prove the exact row by a fresh readback.

        A post-write network or response failure is intentionally treated as
        ambiguous.  The caller must reconcile through ``find_event``/snapshot;
        this method never retries an append automatically.
        """
        expected = self._validated_event(event)
        _require(callable(self._event_admission), 'durable event admission is required')
        # Sheets append has no compare-and-set/idempotency-key primitive.  The
        # service's durable admission must serialize this key from absent-check
        # through post-write readback, including across independent workers.
        with self._event_admission(self.spreadsheet_id, expected['event_idempotency_key']):
            existing = self.find_event(expected['event_idempotency_key'])
            if existing is not None:
                _require(existing == expected, 'event key conflicts with existing row')
                return {'event': existing, 'created': False, 'readback_verified': True}

            # Recheck identity and headers immediately before the provider effect.
            self.snapshot()
            try:
                self._request(
                    'POST',
                    f'{SHEETS_API}/{quote(self.spreadsheet_id, safe="")}/values/{quote("Events!A5:I", safe="")}:append',
                    params={
                        'valueInputOption': 'RAW',
                        'insertDataOption': 'INSERT_ROWS',
                        'includeValuesInResponse': 'true',
                        'responseValueRenderOption': 'UNFORMATTED_VALUE',
                    },
                    json_body={'majorDimension': 'ROWS', 'values': [[expected[field] for field in EVENT_FIELDS]]},
                    operation='Sheets append',
                )
            except EffectNotStarted:
                raise
            except RuntimeError as error:
                raise RuntimeError('event append outcome is uncertain; reconcile before retry') from error

            try:
                readback = self.find_event(expected['event_idempotency_key'])
            except Exception as error:
                raise RuntimeError('event append outcome is uncertain; reconcile before retry') from error
            if readback != expected:
                raise RuntimeError('event append outcome is uncertain; reconcile before retry')
            return {'event': readback, 'created': True, 'readback_verified': True}
