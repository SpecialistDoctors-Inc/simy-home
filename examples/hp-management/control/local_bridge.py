#!/usr/bin/env python3
"""Run HP Control's license bridge on loopback for local end-to-end checks.

This is a developer tool and is not packaged by build_lambda.py. It serves the
same App as the Lambda with an in-memory store, one prepared site for one
verified Google subject, and the real EntitlementResolver pointed at a local
Supabase. It lets a local SIMY Web + Stripe test checkout show the path
"payment -> entitlement -> HP Control access" without touching any deployment.

Required environment (never printed):
  HP_CONTROL_PREFLIGHT_TOKEN    shared with SIMY Web's HP_CONTROL_PREFLIGHT_TOKEN
  HP_CONTROL_ENTITLEMENT_TOKEN  shared with the local hp-control-entitlement function

The access token for MCP calls on behalf of the seeded subject is written to
--token-file (mode 0600). MCP requests use it as a normal Bearer token.

--mode clinic instead exercises the simy.one clinic purchase: a Stripe test
Payment Link redirects to /start, the clinic signs in and enters its homepage.
With --owner-email the site is pre-registered for that mailbox (pattern 1) and
is granted at once when the sign-in email matches; otherwise the URL becomes an
intake whose public homepage is copied (pattern 2). It needs STRIPE_SECRET_KEY
(test mode only), STRIPE_WEBHOOK_SECRET and --payment-links. Google sign-in is
replaced by a local stand-in page that says so. Two loopback-only operator
stand-ins exist only in this tool:
  POST /dev/copy             run the scheduled copier once; the homepage is read
                             from --copy-origin and the zip written under --copy-dir
  POST /dev/register?host=H  register the local site for H with --google-email
                             as owner, as the operator CLI would
"""
from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from cloud_auth import Tokens
from identity import Identity
from licensing import EntitlementResolver, valid_google_subject, valid_org_id
from mcp_adapter import App
from provision_site import seed
from service import Service
from store import MemoryStore

SITE_ID = 'local-clinic'
LOOPBACK = ('127.0.0.1', 'localhost')


def local_site(org_id, host='example.invalid'):
    deployment = {env: {'bucket': 'local-' + env, 'distribution_id': 'ELOCAL', 'origin_id': 'site',
                        'expected_config_sha256': '0' * 64, 'initial_file_paths': ['index.html']}
                  for env in ('dev', 'prod')}
    return {'site_id': SITE_ID, 'name': 'Local clinic', 'config_version': 1, 'github_app_id': 1,
            'github_installation_id': 1, 'github_repository_id': 1, 'github_owner': 'local',
            'github_repository': 'clinic', 'validation_workflow_id': 1, 'initial_main_commit': '0' * 40,
            'drive_workspace_folder_id': 'local-snapshot', 'drive_changes_folder_id': 'local-incoming',
            'sheet_id': 'local-sheet-id', 'recipient': 'owner@example.invalid',
            'operator_subject': 'local-operator', 'operator_email': 'operator@example.invalid',
            'dev_url': 'https://dev.example.invalid', 'prod_url': 'https://' + host,
            'direct_transfer_enabled': True, 'mail_enabled': False, 'reporting_enabled': False,
            'deployment': deployment,
            **({'license_policy': {'mode': 'simy', 'org_id': org_id}} if org_id is not None else {})}


def build(entitlement_endpoint, entitlement_token, preflight_token, org_id, google_subject, port, clock=time.time):
    """Return (app, access_token) for one seeded subject; no network at build time."""
    if not valid_org_id(org_id) or not valid_google_subject(google_subject):
        raise SystemExit('a SIMY organization UUID and Google subject are required')
    issuer = f'http://127.0.0.1:{port}'
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    tokens = Tokens(key, issuer)
    store = MemoryStore()
    # The site is prepared before checkout, exactly like an operator or signup claim.
    seed(store, local_site(org_id), None, ['read', 'edit', 'publish'], int(clock()), google_subject=google_subject)
    resolver = EntitlementResolver(entitlement_endpoint, lambda: entitlement_token, allow_loopback=True)
    service = Service(store, license_resolver=resolver)
    identity = Identity(store, issuer, 'local-client', tokens.sign, None)
    app = App(identity, service, tokens.verify, {'keys': [tokens.jwk]}, '<!doctype html>',
              preflight_token=lambda: preflight_token)
    now = int(clock())
    access_token = tokens.sign({'iss': issuer, 'aud': issuer + '/mcp', 'sub': google_subject,
                                'scope': 'hp:read hp:write', 'iat': now, 'exp': now + 3600,
                                'jti': str(uuid.uuid4())})
    return app, access_token


def build_clinic(stripe_secret_key, webhook_secret, payment_links, google_subject, google_email, site_host_name,
                 port, clock=time.time, stripe_api=None, owner_email=None, copy_origin=None, copy_dir=None):
    """Return (app, mcp_token_factory) for the clinic Payment Link flow on loopback."""
    from clinic_onboarding import ClinicOnboarding
    from cryptography.fernet import Fernet
    from provision_site import enable_domain_registration
    from stripe_billing import StripeApi, StripeBilling
    if not str(stripe_secret_key).startswith(('sk_test_', 'rk_test_')) or not str(webhook_secret).startswith('whsec_'):
        raise SystemExit('a Stripe test-mode secret key and webhook secret are required')
    if not valid_google_subject(google_subject):
        raise SystemExit('a Google subject is required')
    issuer = f'http://127.0.0.1:{port}'
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    tokens = Tokens(key, issuer)
    store = MemoryStore()
    site = local_site(None, site_host_name)
    if owner_email is not None:
        # Pattern 1: the operator prepared this clinic's site for its owner's mailbox.
        enable_domain_registration(store, site, owner_email=owner_email)
    targets = {env: {'bucket': item['bucket'], 'distribution': item['distribution_id']}
               for env, item in site['deployment'].items()}
    service = Service(store, publication_enabled=True, claim_targets={SITE_ID: targets})
    profile = {'sub': google_subject, 'email': google_email, 'email_verified': True}
    identity = Identity(store, issuer, 'local-client', tokens.sign, lambda code, redirect, nonce: dict(profile))
    billing = StripeBilling(store, stripe_api or StripeApi(lambda: stripe_secret_key), payment_links, clock=clock)
    onboarding = ClinicOnboarding(store, billing, service, identity, Fernet.generate_key().decode(),
                                  google_authorize=issuer + '/dev/google', secure_cookie=False, clock=clock)
    app = App(identity, service, tokens.verify, {'keys': [tokens.jwk]}, '<!doctype html>', onboarding=onboarding,
              stripe_webhook=lambda payload, signature: billing.webhook(payload, signature, webhook_secret))

    def mcp_token():
        now = int(clock())
        return tokens.sign({'iss': issuer, 'aud': issuer + '/mcp', 'sub': google_subject,
                            'scope': 'hp:read hp:write', 'iat': now, 'exp': now + 3600, 'jti': str(uuid.uuid4())})
    app.local_google_email = google_email
    app.local_dev = {'copy': lambda query: local_copy(store, copy_origin, copy_dir),
                     'register': lambda query: enable_domain_registration(
                         store, local_site(None, query.get('host', '')), owner_email=google_email)}
    return app, mcp_token


def local_copy(store, origin, out_dir):
    """Run the copier once against a loopback origin standing in for https://<host>."""
    from urllib.request import urlopen
    from urllib.parse import urlsplit
    from site_copy import copy_public_site, run_one
    if not origin or not out_dir or urlsplit(origin).hostname not in LOOPBACK:
        raise SystemExit('--copy-origin (loopback) and --copy-dir are required for /dev/copy')

    def fetch(url):
        parts = urlsplit(url)
        try:
            with urlopen(origin.rstrip('/') + (parts.path or '/') + ('?' + parts.query if parts.query else ''),
                         timeout=10) as response:
                return response.status, dict(response.headers), response.read()
        except Exception as error:  # HTTPError carries the status
            return getattr(error, 'code', 599), {}, b''

    def put(key, data):
        path = Path(out_dir) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    handled = run_one(store, put, copier=lambda host: copy_public_site(host, fetch=fetch))
    return {'handled': handled}


def dev_google_page(query, email):
    """Local stand-in for Google's account chooser. Never part of the Lambda."""
    from html import escape
    from urllib.parse import urlencode
    state = query.get('state', '')
    target = '/oauth/google/callback?' + urlencode({'state': state, 'code': 'local-google-code'})
    body = ('<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>Google でログイン（ローカル検証）</title>'
            '<style>body{font-family:-apple-system,"Hiragino Sans",sans-serif;background:#f0f4f9;margin:0}'
            'main{max-width:420px;margin:80px auto;background:#fff;border-radius:28px;padding:36px}'
            'h1{font-size:22px;font-weight:500;margin:12px 0 6px}p{color:#444;font-size:14px;margin:0 0 24px}'
            'a{display:flex;gap:12px;align-items:center;border-top:1px solid #e3e3e3;border-bottom:1px solid #e3e3e3;'
            'padding:14px 4px;color:#1f1f1f;text-decoration:none}.av{width:32px;height:32px;border-radius:50%;'
            'background:#0b57d0;color:#fff;display:grid;place-items:center;font-weight:600}'
            'small{display:block;color:#777;font-size:12px;margin-top:20px}</style></head><body><main>'
            '<div style="font-weight:600;color:#555">Google</div><h1>アカウントの選択</h1>'
            '<p>HP管理（SIMY）に移動</p>'
            f'<a href="{escape(target, quote=True)}"><span class="av">{escape(email[:1].upper())}</span>'
            f'<span>{escape(email)}</span></a>'
            '<small>ローカル検証用の代替画面です（本番では Google のログイン画面が表示されます）。</small>'
            '</main></body></html>')
    return {'statusCode': 200, 'headers': {'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store'},
            'body': body}


def handler_for(app):
    class Handler(BaseHTTPRequestHandler):
        def _serve(self):
            length = int(self.headers.get('content-length') or 0)
            body = self.rfile.read(min(length, 1 << 20)).decode('utf-8', 'replace')
            path, _, query = self.path.partition('?')
            from urllib.parse import parse_qsl
            dev = getattr(app, 'local_dev', None)
            if path == '/dev/google' and getattr(app, 'local_google_email', None):
                result = dev_google_page(dict(parse_qsl(query)), app.local_google_email)
            elif dev and self.command == 'POST' and path in ('/dev/copy', '/dev/register'):
                outcome = dev[path.rsplit('/', 1)[1]](dict(parse_qsl(query)))
                result = {'statusCode': 200, 'headers': {'content-type': 'application/json'},
                          'body': json.dumps(outcome)}
            else:
                result = app({'rawPath': path, 'rawQueryString': query, 'headers': dict(self.headers.items()),
                              'body': body, 'requestContext': {'http': {'method': self.command}}})
            payload = result.get('body', '').encode()
            self.send_response(result['statusCode'])
            for name, value in result.get('headers', {}).items():
                self.send_header(name, value)
            for cookie in result.get('cookies', []):
                self.send_header('set-cookie', cookie)
            self.send_header('content-length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        do_GET = do_POST = _serve

        def log_message(self, fmt, *args):
            # Log method/path/status only; never headers or bodies.
            print(json.dumps({'request': self.requestline.split(' HTTP')[0], 'status': args[1] if len(args) > 1 else None}),
                  flush=True)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--host', default='127.0.0.1', choices=LOOPBACK)
    parser.add_argument('--port', type=int, default=8787)
    parser.add_argument('--entitlement-endpoint', default='http://127.0.0.1:54321/functions/v1/hp-control-entitlement')
    parser.add_argument('--mode', choices=('simy', 'clinic'), default='simy')
    parser.add_argument('--org-id')
    parser.add_argument('--google-subject', required=True)
    parser.add_argument('--google-email', default='clinic-owner@example.test')
    parser.add_argument('--payment-links', type=Path, help='clinic mode: JSON {plink_id: plan}')
    parser.add_argument('--site-host', default='sakura-clinic.example', help='clinic mode: prepared site host')
    parser.add_argument('--owner-email', help='clinic mode: pre-register --site-host for this owner mailbox')
    parser.add_argument('--copy-origin', help='clinic mode: loopback origin served as every copied homepage')
    parser.add_argument('--copy-dir', type=Path, help='clinic mode: where /dev/copy writes intake zips')
    parser.add_argument('--token-file', type=Path, required=True)
    args = parser.parse_args()
    if args.mode == 'clinic':
        app, token_factory = build_clinic(os.environ.get('STRIPE_SECRET_KEY', ''),
                                          os.environ.get('STRIPE_WEBHOOK_SECRET', ''),
                                          json.loads(args.payment_links.read_text()), args.google_subject,
                                          args.google_email, args.site_host, args.port,
                                          owner_email=args.owner_email, copy_origin=args.copy_origin,
                                          copy_dir=args.copy_dir)
        access_token = token_factory()
    else:
        if not args.org_id:
            raise SystemExit('--org-id is required in simy mode')
        app, access_token = build(args.entitlement_endpoint, os.environ.get('HP_CONTROL_ENTITLEMENT_TOKEN', ''),
                                  os.environ.get('HP_CONTROL_PREFLIGHT_TOKEN', ''), args.org_id, args.google_subject,
                                  args.port)
    args.token_file.touch(mode=0o600, exist_ok=True)
    args.token_file.chmod(0o600)
    args.token_file.write_text(access_token)
    server = ThreadingHTTPServer((args.host, args.port), handler_for(app))
    print(json.dumps({'listening': f'http://{args.host}:{args.port}', 'site_id': SITE_ID, 'pid': os.getpid()}),
          flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
