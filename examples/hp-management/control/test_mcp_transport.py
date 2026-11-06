"""Official mcp==2.3.0 client over actual loopback HTTP; no provider effects.

This verifies JSON Streamable HTTP interoperability and raw private metadata,
not a Codex app host's human-action/private-context enforcement or real OAuth.
The dependency is mandatory: do not silently skip this transport coverage.
"""
import asyncio
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from uuid import uuid4

import httpx2
from mcp import ClientSession
# Official SDK 2 renamed the older streamablehttp_client API.
from mcp.client.streamable_http import streamable_http_client

from identity import Identity
from mcp_adapter import App, UI_URI
from service import Service
from store import MemoryStore


class MCPTransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.preview_id = str(uuid4())
        self.claims = {'sub': 'transport-subject', 'email': 'member@example.invalid',
            'email_verified': True, 'scope': 'openid email hp:read hp:write'}
        self.store.put('principal:transport-subject', {'sites': {'sample-site': ['read', 'edit', 'publish']}})
        self.store.put('site:sample-site', {'name': 'Sample Site', 'config_version': 1,
            'initial_main_commit': 'a' * 40, 'dev_url': 'https://preview.example.invalid',
            'prod_url': 'https://site.example.invalid', 'current_preview': self.preview_id})
        self.store.put('preview:' + self.preview_id, {'site_id': 'sample-site', 'status': 'verified',
            'source_commit': 'a' * 40, 'artifact_sha256': 'b' * 64,
            'url': 'https://preview.example.invalid/current', 'summary': 'Opening hours'})
        self.requests = []
        self.initialized = threading.Event()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'
            def dispatch(self):
                length = int(self.headers.get('Content-Length', '0'))
                if length > 65536:
                    self.send_error(413)
                    return
                body = self.rfile.read(length).decode('utf-8')
                parsed = urlsplit(self.path)
                event = {'rawPath': parsed.path, 'rawQueryString': parsed.query,
                    'requestContext': {'http': {'method': self.command}},
                    'headers': dict(self.headers), 'body': body}
                result = owner.app(event)
                # Never capture Authorization or complete request/result bodies.
                rpc_method = json.loads(body).get('method') if body else None
                owner.requests.append((self.command, rpc_method, result['statusCode']))
                if rpc_method == 'notifications/initialized':
                    owner.initialized.set()
                data = result['body'].encode('utf-8')
                self.send_response(result['statusCode'])
                for key, value in result['headers'].items():
                    self.send_header(key, value)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            do_POST = dispatch
            do_GET = dispatch
            do_DELETE = dispatch
            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.url = 'http://127.0.0.1:' + str(self.server.server_port) + '/mcp'
        def no_provider(*args):
            raise AssertionError('No OAuth exchange, signer or external provider may run')
        identity = Identity(self.store, self.url.removesuffix('/mcp'), 'fake-google-client', no_provider, no_provider)
        service = Service(self.store, publication_enabled=True)  # MemoryStore/card preparation only.
        def verify(token):
            if token != 'fake-bearer-for-loopback-test':
                raise ValueError('invalid test bearer')
            return dict(self.claims)
        self.app = App(identity, service, verify, {'keys': []}, '<!doctype html><title>Local transport fixture</title>')
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=0.01), name='hp-owned-loopback-mcp-test')
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        # Explicitly owned server/thread handles. No OS process signals or lookup.
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.assertFalse(self.thread.is_alive(), 'Owned loopback server did not stop')

    def client(self, authenticated=True):
        return httpx2.AsyncClient(headers={'Authorization': 'Bearer fake-bearer-for-loopback-test'} if authenticated else {},
            timeout=httpx2.Timeout(3), trust_env=False, follow_redirects=False)

    async def test_official_client_initializes_lists_reads_calls_and_preserves_only_raw_private_meta(self):
        async with asyncio.timeout(15):
            async with self.client(authenticated=False) as plain:
                denied = await plain.post(self.url, json={'jsonrpc': '2.0', 'id': 1, 'method': 'ping'})
                self.assertEqual(denied.status_code, 401)
                self.assertEqual(denied.json(), {'error': 'invalid_token'})
                self.assertIn('/.well-known/oauth-protected-resource/mcp', denied.headers['www-authenticate'])
            async with self.client() as http:
                async with streamable_http_client(self.url, http_client=http, terminate_on_close=False) as (read, write):
                    async with ClientSession(read, write, read_timeout_seconds=3) as session:
                        initialized = await session.initialize()
                        self.assertEqual(initialized.server_info.name, 'hp-local-editor')
                        self.assertTrue(await asyncio.to_thread(self.initialized.wait, 2))
                        self.assertIn(('POST', 'notifications/initialized', 202), self.requests)
                        listing = await session.list_tools()
                        tools = {tool.name: tool.model_dump(by_alias=True, exclude_none=True) for tool in listing.tools}
                        self.assertEqual(tools['hp_confirm_publish']['_meta']['ui']['visibility'], ['app'])
                        self.assertEqual(tools['hp_prepare_publish']['_meta']['ui']['resourceUri'], UI_URI)
                        resources = await session.list_resources()
                        self.assertEqual(str(resources.resources[0].uri), UI_URI)
                        resource = await session.read_resource(UI_URI)
                        self.assertIn('Local transport fixture', resource.contents[0].text)
                        profile = await session.call_tool('hp_profile', {})
                        self.assertEqual(profile.structured_content['subject'], self.claims['sub'])
                        operation_id = str(uuid4())
                        opened = await session.call_tool('hp_open_workspace', {'site_id': 'sample-site', 'operation_id': operation_id})
                        self.assertEqual(opened.structured_content['status'], 'queued')
                        readback = await session.call_tool('hp_get_operation', {'operation_id': operation_id})
                        self.assertEqual(readback.structured_content['operation_id'], operation_id)
                        prepared = await session.call_tool('hp_prepare_publish', {'site_id': 'sample-site', 'preview_id': self.preview_id})
                        raw = prepared.model_dump(by_alias=True, exclude_none=True)
                        nonce = raw['_meta']['confirmation_nonce']
                        self.assertTrue(isinstance(nonce, str) and len(nonce) >= 32)
                        self.assertNotIn(nonce, json.dumps(raw.get('structuredContent')))
                        self.assertNotIn(nonce, json.dumps(raw.get('content')))
                        # App-only metadata is observable, not authenticated human proof.
                        rejected = await session.call_tool('hp_confirm_publish', {'approval_id': prepared.structured_content['approval_id'], 'confirmation_nonce': 'guessed-not-private-meta'})
                        self.assertTrue(rejected.is_error)
                        self.assertFalse(any(value.get('kind') == 'publish' for key, value in self.store.rows.items() if key.startswith('operation:')))

    async def test_initialize_accepts_legitimate_mcp_request_meta(self):
        async with asyncio.timeout(10):
            async with self.client() as http:
                result = await http.post(self.url, json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                    'params': {'protocolVersion': '2025-11-25', 'capabilities': {},
                        'clientInfo': {'name': 'official-client-meta-fixture', 'version': '1'},
                        '_meta': {'progressToken': 'init-progress'}}})
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()['result']['serverInfo']['name'], 'hp-local-editor')

    async def test_official_resource_request_accepts_standard_meta(self):
        async with asyncio.timeout(15):
            async with self.client() as http:
                async with streamable_http_client(self.url, http_client=http, terminate_on_close=False) as (read, write):
                    async with ClientSession(read, write, read_timeout_seconds=3) as session:
                        await session.initialize()
                        result = await session.read_resource(UI_URI, meta={'progressToken': 'resource-progress'})
                        self.assertIn('Local transport fixture', result.contents[0].text)


if __name__ == '__main__':
    unittest.main()
