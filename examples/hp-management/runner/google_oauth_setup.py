#!/usr/bin/env python3
"""Create one private, task-local Google OAuth credential file.

The operator supplies an installed-application client JSON and personally
completes Google's browser consent.  This program neither reads global ADC nor
overwrites any credential file.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
from typing import Any, Callable


SCOPES = [
    'openid',
    # Google returns the canonical URI even when the OIDC alias is requested.
    # Request that URI so oauthlib can verify the returned scopes exactly.
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/spreadsheets',
]
GMAIL_SEND_SCOPE = 'https://www.googleapis.com/auth/gmail.send'
GMAIL_READONLY_SCOPE = 'https://www.googleapis.com/auth/gmail.readonly'


def _private_new_file(path: Path, content: str) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError('refusing to overwrite credential output')
    if not path.parent.is_dir():
        raise FileNotFoundError('credential output directory must already exist')
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IRUSR | stat.S_IWUSR)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            output.write(content)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _credential_document(credentials: Any, scopes: list[str]) -> str:
    """Normalize google-auth output without changing the supplied credential."""
    payload = json.loads(credentials.to_json())
    if not isinstance(payload, dict):
        raise ValueError('OAuth credential output is invalid')
    payload['type'] = 'authorized_user'
    payload['scopes'] = list(scopes)
    return json.dumps(payload, sort_keys=True)


def _validate_expected_principal(credentials: Any, expected_subject: str, expected_email: str,
                                 request_get: Callable[..., Any]) -> None:
    headers: dict[str, str] = {}
    credentials.apply(headers)
    try:
        response = request_get('https://openidconnect.googleapis.com/v1/userinfo', headers=headers, timeout=30)
        if not 200 <= response.status_code < 300:
            raise RuntimeError('status')
        profile = response.json()
    except Exception as error:
        raise RuntimeError('Google identity verification failed') from error
    if not (isinstance(profile, dict) and profile.get('sub') == expected_subject
            and isinstance(profile.get('email'), str)
            and profile['email'].casefold() == expected_email.casefold()
            and profile.get('email_verified') is True):
        raise ValueError('Google identity did not match expected subject/email')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-client-json', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-subject', required=True)
    parser.add_argument('--expected-email', required=True)
    parser.add_argument('--enable-gmail-send', action='store_true')
    parser.add_argument('--no-browser', action='store_true', help='Print the consent URL so the operator can use the intended browser profile')
    args = parser.parse_args()

    try:
        with args.installed_client_json.open(encoding='utf-8') as source:
            client = json.load(source)
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit('installed-app client JSON is unreadable') from error
    if not isinstance(client, dict) or not isinstance(client.get('installed'), dict):
        raise SystemExit('client JSON must be an installed-app OAuth client')
    if args.output.exists() or args.output.is_symlink():
        raise SystemExit('refusing to overwrite credential output')

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as error:
        raise SystemExit('install google-auth-oauthlib before running setup') from error
    scopes = [*SCOPES, *([GMAIL_SEND_SCOPE, GMAIL_READONLY_SCOPE] if args.enable_gmail_send else [])]
    # Google presents the consent screen; the operator must choose the account
    # and approve it.  The local callback is intentionally loopback-only.
    flow = InstalledAppFlow.from_client_secrets_file(str(args.installed_client_json), scopes=scopes)
    credentials = flow.run_local_server(host='127.0.0.1', port=0,
        open_browser=not args.no_browser, login_hint=args.expected_email,
        prompt='consent')
    try:
        import requests
    except ImportError as error:
        raise SystemExit('install requests before running setup') from error
    _validate_expected_principal(credentials, args.expected_subject, args.expected_email, requests.get)
    _private_new_file(args.output, _credential_document(credentials, scopes))
    print('Credential saved with mode 0600. Gmail send/readback scopes are included only with --enable-gmail-send.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
