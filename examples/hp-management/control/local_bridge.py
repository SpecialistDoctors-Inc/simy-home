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


def local_site(org_id):
    deployment = {env: {'bucket': 'local-' + env, 'distribution_id': 'ELOCAL', 'origin_id': 'site',
                        'expected_config_sha256': '0' * 64, 'initial_file_paths': ['index.html']}
                  for env in ('dev', 'prod')}
    return {'site_id': SITE_ID, 'name': 'Local clinic', 'config_version': 1, 'github_app_id': 1,
            'github_installation_id': 1, 'github_repository_id': 1, 'github_owner': 'local',
            'github_repository': 'clinic', 'validation_workflow_id': 1, 'initial_main_commit': '0' * 40,
            'drive_workspace_folder_id': 'local-snapshot', 'drive_changes_folder_id': 'local-incoming',
            'sheet_id': 'local-sheet-id', 'recipient': 'owner@example.invalid',
            'operator_subject': 'local-operator', 'operator_email': 'operator@example.invalid',
            'dev_url': 'https://dev.example.invalid', 'prod_url': 'https://example.invalid',
            'direct_transfer_enabled': True, 'mail_enabled': False, 'reporting_enabled': False,
            'deployment': deployment, 'license_policy': {'mode': 'simy', 'org_id': org_id}}


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


def handler_for(app):
    class Handler(BaseHTTPRequestHandler):
        def _serve(self):
            length = int(self.headers.get('content-length') or 0)
            body = self.rfile.read(min(length, 1 << 20)).decode('utf-8', 'replace')
            result = app({'rawPath': self.path.split('?')[0], 'headers': dict(self.headers.items()), 'body': body,
                          'requestContext': {'http': {'method': self.command}}})
            payload = result.get('body', '').encode()
            self.send_response(result['statusCode'])
            for name, value in result.get('headers', {}).items():
                self.send_header(name, value)
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
    parser.add_argument('--org-id', required=True)
    parser.add_argument('--google-subject', required=True)
    parser.add_argument('--token-file', type=Path, required=True)
    args = parser.parse_args()
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
