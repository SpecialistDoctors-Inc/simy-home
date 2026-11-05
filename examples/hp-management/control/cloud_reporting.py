"""Real result-reporting factories; construction alone has no provider effects.

The dedicated operator secret contains client_id/client_secret/refresh_token and
approved scopes (a list, or the provider's space-separated scope string). It may
contain token_uri only when equal to Google's fixed token endpoint. Credentials
exist only in memory. No user login token or customer-supplied URL is accepted.

The legacy providers retain their exact identity/header/readback checks. Their
credential refresh is redirected through this module's bounded no-redirect
transport; provider writes call the reporting guard(True) immediately before
HTTP, while read-only reconciliation and refresh call guard().
"""
from __future__ import annotations
import json
import re
from types import SimpleNamespace
from urllib.parse import urlsplit, quote

from service import Rejected, uuid

TOKEN_URL = 'https://oauth2.googleapis.com/token'
USERINFO_URL = 'https://openidconnect.googleapis.com/v1/userinfo'
MAX_RESPONSE = 2 * 1024 * 1024


def require(condition):
    if not condition:
        raise Rejected('reporting_binding_invalid')


def _material(reference, resolver, guard):
    guard()
    require(isinstance(reference, str) and bool(reference))
    value = resolver(reference)
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            raise Rejected('reporting_binding_invalid') from None
    require(isinstance(value, dict))
    require(all(isinstance(value.get(key), str) and bool(value[key]) for key in ('client_id', 'client_secret', 'refresh_token')))
    require(value.get('token_uri', TOKEN_URL) == TOKEN_URL)
    scopes = value.get('scopes', value.get('scope'))
    if isinstance(scopes, str):
        scopes = scopes.split()
    require(isinstance(scopes, list) and bool(scopes) and all(isinstance(scope, str) and bool(scope) for scope in scopes))
    return value, scopes


def _bounded(response):
    try:
        data = bytearray()
        for chunk in response.iter_content(64 * 1024):
            data.extend(chunk)
            if len(data) > MAX_RESPONSE:
                raise RuntimeError('reporting_response_too_large')
        return bytes(data)
    finally:
        response.close()


class _OAuthRequest:
    def __init__(self, session, guard):
        self.session, self.guard = session, guard

    def __call__(self, url, method='GET', body=None, headers=None, timeout=None, **kwargs):
        require(url == TOKEN_URL and method.upper() == 'POST')
        self.guard()  # Refresh needed for readback remains permitted after revoke.
        response = self.session.request('POST', TOKEN_URL, data=body, headers=headers or {},
            allow_redirects=False, timeout=20, stream=True)
        status, result_headers = response.status_code, dict(response.headers)
        data = _bounded(response)
        if 300 <= status < 400:
            raise RuntimeError('reporting_oauth_redirect_denied')
        return SimpleNamespace(status=status, data=data, headers=result_headers)


class _Credentials:
    """Compose in-memory google.oauth2.Credentials with a fixed refresh request."""
    def __init__(self, credentials, request):
        self.credentials, self.request = credentials, request

    @property
    def scopes(self):
        return self.credentials.scopes

    @property
    def expired(self):
        return self.credentials.expired

    @property
    def valid(self):
        return self.credentials.valid

    def refresh(self, _ignored_request):
        self.credentials.refresh(self.request)

    def apply(self, headers):
        self.credentials.apply(headers)


class _Response:
    def __init__(self, status, data):
        self.status_code, self.data = status, data

    def json(self):
        return json.loads(self.data)


class _Transport:
    def __init__(self, credentials, session, guard, kind, site):
        self.credentials, self.session, self.guard, self.kind, self.site = credentials, session, guard, kind, site

    def request(self, method, url, *, params=None, json=None):
        method = method.upper()
        parsed = urlsplit(url)
        require(parsed.scheme == 'https' and not parsed.fragment and '@' not in parsed.netloc)
        if url == USERINFO_URL:
            require(method == 'GET')
        elif self.kind == 'sheet':
            expected = '/v4/spreadsheets/' + self.site['sheet_id'] + '/'
            require(parsed.netloc == 'sheets.googleapis.com' and parsed.path.startswith(expected) and not parsed.query)
            require((method == 'GET' and parsed.path == expected + 'values:batchGet') or
                (method == 'POST' and parsed.path in {expected + 'values/' + quote(name, safe='') + ':append' for name in ('Requests!A5:N', 'Events!A5:I')}))
        else:
            prefix = '/gmail/v1/users/me/messages'
            require(parsed.netloc == 'gmail.googleapis.com' and not parsed.query and
                ((method == 'GET' and (parsed.path == prefix or parsed.path.startswith(prefix + '/'))) or
                 (method == 'POST' and parsed.path == prefix + '/send')))
        # No ambient auth, proxy credentials, redirects, retries, or arbitrary URLs.
        headers = {}
        self.credentials.apply(headers)
        self.guard(method != 'GET')
        response = self.session.request(method, url, params=params, json=json, headers=headers,
            allow_redirects=False, timeout=20, stream=True)
        status = response.status_code
        data = _bounded(response)
        return _Response(status, data)


class _Provider:
    """Map deterministic legacy binding/readback mismatches to operator attention."""
    def __init__(self, provider):
        self.provider = provider
        self.request_admission = None

    def __getattr__(self, name):
        return getattr(self.provider, name)

    def authorized_user(self):
        try:
            return self.provider.authorized_user()
        except ValueError:
            raise Rejected('reporting_operator_mismatch') from None

    def set_request_admission(self, admission):
        require(callable(admission))
        self.request_admission = admission

    def _request_row(self, row):
        from google_provider import FIELDS
        require(isinstance(row, dict) and set(row) == set(FIELDS) and
            all(isinstance(row[field], str) and bool(row[field]) for field in FIELDS))
        uuid(row['request_id'])
        site = self.provider.site_config
        require(row['revision'] == '1' and row['site_id'] == site.get('site_id') and
            row['proposal_state'] in ('local_draft', 'local_preview', 'local_publication') and
            row['effective_at'] == '確認・公開操作に従う' and row['expires_at'] == 'なし' and row['timezone'] == 'Asia/Tokyo' and
            row['assets_rights'] == 'この操作の提出ファイルを参照' and row['dependencies'] == 'この操作の提出ファイルを参照' and
            row['requester_ref'].startswith('google-sub:') and len(row['requester_ref']) > len('google-sub:') and
            len(row['outcome']) <= 200)
        expected = site.get('prod_url') if row['proposal_state'] == 'local_publication' else site.get('dev_url')
        require(row['target'] == expected and row['notification_recipient_ref'] ==
            (site.get('notification_recipient_ref') or 'site:' + row['site_id'] + ':notification'))
        return dict(row)

    def find_request(self, request_id, revision):
        uuid(request_id)
        require(revision == '1')
        try:
            rows = self.provider.snapshot()['requests']
            matches = [row for row in rows if row['request_id'] == request_id and row['revision'] == revision]
            if len(matches) > 1:
                raise Rejected('reporting_request_mismatch')
            return self._request_row(matches[0]) if matches else None
        except ValueError:
            raise Rejected('reporting_request_mismatch') from None

    def append_request(self, row):
        from google_provider import FIELDS, SHEETS_API
        expected = self._request_row(row)
        require(callable(self.request_admission))
        with self.request_admission(self.provider.spreadsheet_id, expected['request_id'], expected['revision']):
            existing = self.find_request(expected['request_id'], expected['revision'])
            if existing is not None:
                if existing != expected:
                    raise Rejected('reporting_request_mismatch')
                return {'request': existing, 'created': False, 'readback_verified': True}
            # Revalidate both exact row-4 headers and operator before RAW append.
            self.provider.snapshot()
            self.provider._request('POST', SHEETS_API + '/' + quote(self.provider.spreadsheet_id, safe='') +
                '/values/' + quote('Requests!A5:N', safe='') + ':append',
                params={'valueInputOption': 'RAW', 'insertDataOption': 'INSERT_ROWS',
                    'includeValuesInResponse': 'true', 'responseValueRenderOption': 'UNFORMATTED_VALUE'},
                json_body={'majorDimension': 'ROWS', 'values': [[expected[field] for field in FIELDS]]},
                operation='Requests append')
            found = self.find_request(expected['request_id'], expected['revision'])
            if found != expected:
                raise RuntimeError('reporting_request_readback_required')
            return {'request': found, 'created': True, 'readback_verified': True}

    def find_event(self, key):
        try:
            return self.provider.find_event(key)
        except ValueError:
            raise Rejected('reporting_event_mismatch') from None

    def find_notice(self, envelope, key):
        try:
            return self.provider.find_notice(envelope, key)
        except ValueError:
            raise Rejected('reporting_notice_unverified') from None


def factories(secret_reference, secret_resolver, *, session_factory=None, credential_factory=None):
    """Return (sheets_factory, mail_factory) for Reporter, with injectable seams.

    Seams are only for no-network tests. Production uses requests.Session and
    google.oauth2.credentials.Credentials; no credential path is opened.
    """
    def create(site, guard, kind):
        from google_provider import GoogleSheets
        from gmail_provider import Gmail
        if session_factory is None:
            import requests
            session = requests.Session()
            session.trust_env = False
        else:
            session = session_factory()
        values, scopes = _material(secret_reference, secret_resolver, guard)
        if credential_factory is None:
            from google.oauth2.credentials import Credentials
            constructor = Credentials
        else:
            constructor = credential_factory
        require(isinstance(site.get('sheet_id'), str) and re.fullmatch('[A-Za-z0-9_-]{10,256}', site['sheet_id']) and
            all(isinstance(site.get(key), str) and bool(site[key]) for key in ('operator_subject','operator_email','recipient')))
        raw = constructor(token=None, refresh_token=values['refresh_token'], token_uri=TOKEN_URL,
            client_id=values['client_id'], client_secret=values['client_secret'], scopes=scopes)
        credentials = _Credentials(raw, _OAuthRequest(session, guard))
        transport = _Transport(credentials, session, guard, kind, site)
        # The legacy constructor won't read this inert placeholder because the
        # explicit credentials object is supplied. Never create a temp file.
        arguments = (site, '<in-memory-operator-credentials>', site['operator_subject'], site['operator_email'])
        try:
            provider = GoogleSheets(*arguments, credentials=credentials, transport=transport) if kind == 'sheet' else Gmail(*arguments, credentials=credentials, transport=transport)
        except ValueError:
            raise Rejected('reporting_binding_invalid') from None
        return _Provider(provider)
    return (lambda site, guard: create(site, guard, 'sheet'), lambda site, guard: create(site, guard, 'mail'))
