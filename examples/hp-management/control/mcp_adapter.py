"""Stateless Lambda HTTP/MCP boundary. No credentials or provider effects here.

Tool visibility and private _meta are presentation boundaries, not human proof.
The host/client must enforce app-only exposure and private result metadata.
An authorized user constructing a raw request still acts as that same identity;
validate the real host card before enabling Service.publication_enabled.
"""
from __future__ import annotations
import base64
import json
import secrets
from html import escape
from urllib.parse import parse_qs, urlsplit

from identity import AuthError, Identity
from licensing import LicenseUnavailable, valid_google_subject, valid_org_id, valid_service_token
from service import Rejected
from store import Conflict
from wordpress_provider import WordPressConnectionError

MAX_BODY = 64 * 1024
UI_URI = 'ui://hp-control/publish.html'
UI_MIME = 'text/html;profile=mcp-app'


def schema(properties):
    return {'type': 'object', 'properties': {name: {'type': 'string'} for name in properties}, 'required': list(properties), 'additionalProperties': False}


TOOL_FIELDS = {
    'hp_profile': (), 'hp_list_sites': (),
    'hp_open_workspace': ('operation_id', 'site_id'),
    'hp_download_workspace': ('site_id', 'workspace_id'),
    'hp_prepare_upload': ('operation_id', 'site_id', 'workspace_id', 'base_commit', 'bundle_sha256', 'size'),
    'hp_save_draft': ('operation_id', 'site_id', 'workspace_id', 'base_commit', 'bundle_file_id', 'bundle_sha256'),
    'hp_submit_preview': ('operation_id', 'site_id', 'workspace_id', 'saved_commit'),
    'hp_get_operation': ('operation_id',), 'hp_cancel_operation': ('operation_id',),
    'hp_resume_operation': ('operation_id', 'recovery_id'),
    'hp_prepare_publish': ('site_id', 'preview_id'),
    'hp_get_confirmation': ('approval_id',),
    'hp_cancel_confirmation': ('approval_id',),
    'hp_confirm_publish': ('approval_id', 'confirmation_nonce'),
}
DESCRIPTIONS = {
    'hp_profile': 'Read the authenticated member profile and site bindings.',
    'hp_list_sites': 'List the authenticated member’s available sites and roles.',
    'hp_open_workspace': 'Queue a durable workspace snapshot request. Reuse operation_id on retry.',
    'hp_download_workspace': 'Prepare private, short-lived download metadata for an owned workspace. Use the local plugin transport; never copy private URLs to chat.',
    'hp_prepare_upload': 'Prepare immutable upload transport for the original local package operation. Does not save or publish. Reuse the exact input on retry.',
    'hp_save_draft': 'Queue validation and draft saving of an uploaded changes ZIP. Saving does not publish.',
    'hp_submit_preview': 'Queue reconciliation and verification of the exact saved draft for preview.',
    'hp_get_operation': 'Read an owned operation. Queued or running is not complete.',
    'hp_cancel_operation': 'Request cancellation of an owned operation; active effects may require reconciliation.',
    'hp_resume_operation': 'Explicitly resume the same needs-attention execution without changing its input or approval. Reuse recovery_id on retries. May continue previously approved publication; reporting-only attention is not resumable here.',
    'hp_prepare_publish': 'Prepare a short-lived card for one current verified preview. When publication is disabled this is a connection test only; it cannot request publication.',
    'hp_get_confirmation': 'Read an owned confirmation and its existing operation after a lost response. Never returns a private nonce. A prepared result is not authority to resend confirmation.',
    'hp_cancel_confirmation': 'Atomically withdraw an unaccepted owned confirmation. An accepted publication is returned unchanged, not rolled back or cancelled. Re-read the same approval after uncertain results.',
    'hp_confirm_publish': 'App-only confirmation using the private card nonce. Connection-test cards only audit the connection; publication cards queue publication without claiming completion.',
}
READ_TOOLS = {'hp_profile', 'hp_list_sites', 'hp_get_operation', 'hp_get_confirmation'}
DIRECT_TRANSFER_TOOLS = {'hp_download_workspace', 'hp_prepare_upload'}
SAFE_REJECTIONS = set('authentication_required access_revoked invalid_site insufficient_scope site_access_denied site_unavailable hp_license_required invalid_id invalid_input invalid_digest workspace_access_denied unsupported_operation operation_id_conflict invalid_commit workspace_changed invalid_drive_file operation_access_denied preview_not_current publication_not_enabled confirmation_invalid confirmation_expired confirmation_stale resumption_stale resumption_id_conflict resumption_cancel_requested resumption_not_allowed resumption_approval_invalid resumption_site_busy'.split())
SAFE_AUTH_ERRORS = set('invalid_redirect_uri unsupported_client_auth invalid_client_or_redirect invalid_authorization_request pkce_s256_required invalid_scope invalid_nonce expired_login invalid_google_identity site_invitation_required invalid_resource invalid_grant unsupported_grant_type access_revoked invalid_google_nonce'.split())
SAFE_REJECTIONS.update({'transfer_access_denied', 'transfer_binding_changed',
    'direct_transfer_unavailable', 'invalid_transfer_size', 'transfer_id_conflict'})


class BadRequest(ValueError):
    pass


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise BadRequest()
        result[key] = value
    return result


def json_load(data):
    try:
        return json.loads(data, object_pairs_hook=object_pairs, parse_constant=lambda _: (_ for _ in ()).throw(BadRequest()))
    except (ValueError, UnicodeError, RecursionError):
        raise BadRequest() from None


def fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise BadRequest()


def flat_query(raw):
    try:
        values = parse_qs(raw, keep_blank_values=True, strict_parsing=True, max_num_fields=32)
    except ValueError:
        raise BadRequest() from None
    if any(len(value) != 1 for value in values.values()):
        raise BadRequest()
    return {key: value[0] for key, value in values.items()}


def tool_definitions(fields_map=None):
    result = []
    for name, properties in (fields_map if fields_map is not None else TOOL_FIELDS).items():
        readonly = name in READ_TOOLS
        meta = {}
        if name == 'hp_prepare_publish':
            meta = {'ui': {'resourceUri': UI_URI}}
        elif name == 'hp_confirm_publish':
            meta = {'ui': {'visibility': ['app']}}
        result.append({'name': name, 'description': DESCRIPTIONS[name], 'inputSchema': schema(properties),
            'annotations': {'readOnlyHint': readonly,
                'destructiveHint': name in ('hp_confirm_publish', 'hp_resume_operation',
                    'hp_cancel_operation', 'hp_cancel_confirmation'),
                'idempotentHint': name != 'hp_prepare_publish',
                'openWorldHint': name == 'hp_resume_operation'},
            'securitySchemes': [{'type': 'oauth2', 'scopes': ['hp:read', 'hp:write'] if name == 'hp_cancel_confirmation' else ['hp:read' if readonly else 'hp:write']}],
            '_meta': meta})
    return result


def tool_result(value):
    result = value if isinstance(value, dict) else {'sites': value}
    return {'content': [{'type': 'text', 'text': json.dumps(result, ensure_ascii=False, separators=(',', ':'))}], 'structuredContent': result}


def tool_error(code):
    return {'isError': True, 'content': [{'type': 'text', 'text': code}], 'structuredContent': {'error': code}}


class App:
    def __init__(self, identity, service, verify, jwks, ui_html, preflight_token=None, wordpress=None,
                 wordpress_transfers=None, transfers=None, onboarding=None, stripe_webhook=None):
        self.identity, self.service, self.verify = identity, service, verify
        # Clinic purchases from simy.one Payment Links (see clinic_onboarding.py).
        self.onboarding, self.stripe_webhook = onboarding, stripe_webhook
        self.jwks, self.ui_html = jwks, ui_html
        self.preflight_token = preflight_token
        self.wordpress = wordpress
        self.wordpress_transfers = wordpress_transfers
        self.transfers = transfers

    @staticmethod
    def response(status, value=None, headers=None):
        base = {'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'x-content-type-options': 'nosniff'}
        base.update(headers or {})
        return {'statusCode': status, 'headers': base, 'body': '' if value is None else json.dumps(value, ensure_ascii=False, separators=(',', ':'))}

    def claims(self, headers):
        authorization = headers.get('authorization', '')
        if not isinstance(authorization, str) or not authorization.startswith('Bearer ') or len(authorization) > 16384 or not authorization[7:] or any(c.isspace() for c in authorization[7:]):
            raise AuthError('invalid_token')
        try:
            claims = self.verify(authorization[7:])
            self.service.principal(claims)
            return claims
        except Exception:
            raise AuthError('invalid_token') from None

    def __call__(self, event, context=None):
        try:
            return self._handle(event)
        except BadRequest:
            return self.response(400, {'error': 'invalid_request'})
        except AuthError as error:
            code = str(error) if str(error) in SAFE_AUTH_ERRORS else 'invalid_token'
            if code == 'invalid_token':
                return self.response(401, {'error': code}, {'www-authenticate': 'Bearer resource_metadata="' + self.identity.issuer + '/.well-known/oauth-protected-resource/mcp"'})
            return self.response(400, {'error': code})
        except Rejected as error:
            return self.response(403, {'error': str(error) if str(error) in SAFE_REJECTIONS else 'request_rejected'})
        except Conflict:
            return self.response(409, {'error': 'concurrent_change'})
        except Exception:
            return self.response(500, {'error': 'internal_error'})

    def handle(self, event, context=None):
        return self(event, context)

    def _handle(self, event):
        if not isinstance(event, dict):
            raise BadRequest()
        method = event.get('requestContext', {}).get('http', {}).get('method') or event.get('httpMethod')
        path = event.get('rawPath') or event.get('path')
        headers = {key.lower(): value for key, value in event.get('headers', {}).items()}
        raw = event.get('body') or ''
        if not isinstance(raw, str) or len(raw) > MAX_BODY * 2:
            return self.response(413, {'error': 'request_too_large'})
        try:
            data = base64.b64decode(raw, validate=True) if event.get('isBase64Encoded') else raw.encode('utf-8')
        except (ValueError, UnicodeError):
            raise BadRequest() from None
        if len(data) > MAX_BODY:
            return self.response(413, {'error': 'request_too_large'})
        if method == 'GET' and path == '/health':
            return self.response(200, {'status': 'ok'})
        if path in ('/internal/license/preflight', '/internal/site/claim'):
            return self.hp_billing_request(method, headers, data, claim_site=path == '/internal/site/claim')
        if method == 'GET' and path in ('/.well-known/oauth-authorization-server', '/.well-known/openid-configuration'):
            return self.response(200, self.identity.metadata())
        if method == 'GET' and path in ('/.well-known/oauth-protected-resource', '/.well-known/oauth-protected-resource/mcp'):
            return self.response(200, {'resource': self.identity.resource, 'authorization_servers': [self.identity.issuer], 'scopes_supported': ['hp:read', 'hp:write'], 'bearer_methods_supported': ['header']})
        if method == 'GET' and path == '/oauth/jwks':
            return self.response(200, self.jwks() if callable(self.jwks) else self.jwks)
        if method == 'GET' and path == '/oauth/userinfo':
            claims = self.claims(headers)
            return self.response(200, {key: claims[key] for key in ('sub', 'email', 'email_verified') if key in claims})
        raw_query = event.get('rawQueryString')
        query = flat_query(raw_query) if raw_query else event.get('queryStringParameters') or {}
        if not isinstance(query, dict) or any(not isinstance(v, str) for v in query.values()):
            raise BadRequest()
        if path == '/stripe/webhook':
            if method != 'POST':
                return self.response(405, {'error': 'method_not_allowed'}, {'allow': 'POST'})
            if self.stripe_webhook is None:
                return self.response(503, {'error': 'billing_unavailable'})
            return self.response(self.stripe_webhook(data, headers.get('stripe-signature')))
        if path.startswith('/start') and self.onboarding is not None:
            cookie = headers.get('cookie') or '; '.join(c for c in event.get('cookies') or [] if isinstance(c, str))
            return self.onboarding_request(method, path, query, data, headers, cookie)
        if method == 'GET' and path == '/oauth/authorize':
            return self.response(302, headers={'location': self.identity.authorize(query)})
        if method == 'GET' and path == '/oauth/google/callback':
            fields(query, ('state', 'code'), ('scope', 'authuser', 'prompt', 'hd', 'iss'))
            if 'iss' in query and query['iss'] != 'https://accounts.google.com':
                raise BadRequest()
            if self.onboarding is not None and self.onboarding.owns_login(query['state']):
                cookie = headers.get('cookie') or '; '.join(c for c in event.get('cookies') or [] if isinstance(c, str))
                return self.onboarding_call(lambda: self.onboarding.google_callback(query['state'], query['code'], cookie))
            redirect = self.identity.callback(query['state'], query['code'])
            if not Identity.valid_redirect(redirect):
                raise AuthError('invalid_redirect_uri')
            if urlsplit(redirect).hostname == 'chatgpt.com':
                # Google and the initiating ChatGPT session may use different
                # browser profiles. Preserve the original one-time code/state;
                # the registered client still needs its original PKCE verifier.
                response = self.response(200, headers={
                    'content-type': 'text/html; charset=utf-8',
                    'referrer-policy': 'no-referrer', 'x-frame-options': 'DENY',
                    'content-security-policy': "default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"})
                response['body'] = ('<!doctype html><html lang="ja"><head><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1">'
                    '<title>ChatGPTの接続を完了する</title></head><body><main>'
                    '<h1>Google確認が完了しました。</h1>'
                    '<p>接続を始めたChatGPTのブラウザーで続けてください。</p>'
                    '<p>下のリンクをコピーし、接続を始めたChatGPTのブラウザーで開いてください。</p>'
                    '<p><a href="' + escape(redirect, quote=True) + '" rel="noreferrer noopener">'
                    'ChatGPTに戻って接続を完了</a></p></main></body></html>')
                return response
            return self.response(302, headers={'location': redirect})
        content_type = headers.get('content-type', '').split(';')[0].strip().lower()
        if method == 'POST' and path == '/oauth/register':
            if content_type != 'application/json':
                return self.response(415, {'error': 'unsupported_media_type'})
            body = json_load(data)
            if not isinstance(body, dict) or not isinstance(body.get('redirect_uris'), list):
                raise BadRequest()
            try:
                registration = self.identity.register(body)
            except AuthError:
                raise
            except (TypeError, ValueError):
                raise BadRequest() from None
            return self.response(201, registration)
        if method == 'POST' and path == '/oauth/token':
            if content_type != 'application/x-www-form-urlencoded':
                return self.response(415, {'error': 'unsupported_media_type'})
            try:
                form = flat_query(data.decode('utf-8'))
            except UnicodeError:
                raise BadRequest() from None
            return self.response(200, self.identity.token(form))
        if path == '/mcp':
            claims = self.claims(headers)
            if method != 'POST':
                return self.response(405, {'error': 'method_not_allowed'}, {'allow': 'POST'})
            if content_type != 'application/json':
                return self.response(415, {'error': 'unsupported_media_type'})
            return self.rpc(json_load(data), claims, event)
        return self.response(404, {'error': 'not_found'})

    def hp_billing_request(self, method, headers, data, *, claim_site):
        if method != 'POST':
            return self.response(405, {'error': 'method_not_allowed'}, {'allow': 'POST'})
        try:
            token = self.preflight_token() if self.preflight_token is not None else None
        except Exception:
            token = None
        if not valid_service_token(token):
            return self.response(503, {'error': 'hp_license_unavailable'})
        authorization = headers.get('authorization', '')
        if (not isinstance(authorization, str) or not authorization.startswith('Bearer ')
                or not valid_service_token(authorization[7:])
                or not secrets.compare_digest(authorization[7:], token)):
            return self.response(401, {'error': 'invalid_token'})
        if headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
            return self.response(415, {'error': 'unsupported_media_type'})
        body = json_load(data)
        registration = claim_site and isinstance(body, dict) and 'action' in body
        required = ('org_id', 'google_subject')
        if registration and body['action'] in ('wordpress_start', 'wordpress_finish'):
            return self.wordpress_request(body, required)
        if registration:
            required += ('action', 'site_url')
        elif claim_site:
            required += ('setup_code',)
        fields(body, required)
        if not valid_org_id(body['org_id']) or not valid_google_subject(body['google_subject']):
            raise BadRequest()
        if registration and body['action'] not in ('start', 'verify', 'owner_verified'):
            raise BadRequest()
        if not claim_site and self.wordpress_transfers:
            try:
                ready = self.service.license_preflight(body['org_id'], body['google_subject'], wordpress_only=True)
                if ready['ready']:
                    return self.response(200, {**ready, 'provider': 'wordpress'})
            except (Rejected, LicenseUnavailable):
                return self.response(503, {'error': 'hp_license_unavailable'})
        if not DIRECT_TRANSFER_TOOLS <= TOOL_FIELDS.keys():
            return self.response(503, {'error': 'hp_license_unavailable'})
        try:
            if registration:
                result = self.service.register_site(body['org_id'], body['google_subject'],
                    body['site_url'], verify=body['action'] == 'verify',
                    owner_verified=body['action'] == 'owner_verified')
            elif claim_site:
                result = self.service.claim_prepared_site(body['org_id'], body['google_subject'], body['setup_code'])
            else:
                result = self.service.license_preflight(body['org_id'], body['google_subject'])
            return self.response(200, result)
        except Rejected:
            if claim_site:
                return self.response(409, {'error': 'site_claim_unavailable'})
            return self.response(400, {'error': 'invalid_request'})
        except Exception:
            return self.response(503, {'error': 'hp_license_unavailable'})

    def onboarding_request(self, method, path, query, data, headers, cookie):
        if method == 'GET' and path == '/start':
            return self.onboarding_call(lambda: self.onboarding.page(query, cookie))
        if method == 'GET' and path == '/start/google':
            return self.onboarding_call(lambda: self.onboarding.google_start(query))
        if method == 'POST' and path == '/start/site':
            if headers.get('content-type', '').split(';')[0].strip().lower() != 'application/x-www-form-urlencoded':
                return self.response(415, {'error': 'unsupported_media_type'})
            try:
                form = flat_query(data.decode('utf-8'))
            except UnicodeError:
                raise BadRequest() from None
            return self.onboarding_call(lambda: self.onboarding.submit_site(form, cookie, headers.get('origin')))
        if method == 'POST' and path == '/start/wordpress':
            if headers.get('content-type', '').split(';')[0].strip().lower() != 'application/x-www-form-urlencoded':
                return self.response(415, {'error': 'unsupported_media_type'})
            try:
                form = flat_query(data.decode('utf-8'))
            except UnicodeError:
                raise BadRequest() from None
            return self.onboarding_call(lambda: self.onboarding.wordpress_start(form, cookie, headers.get('origin')))
        if method == 'GET' and path == '/start/wordpress/callback':
            return self.onboarding_call(lambda: self.onboarding.wordpress_callback(query, cookie))
        return self.response(404, {'error': 'not_found'})

    def onboarding_call(self, action):
        from stripe_billing import BillingRejected
        try:
            return action()
        except BillingRejected:
            return self.onboarding.html(403, self.onboarding.error(
                'お支払いを確認できませんでした', '決済が完了していないか、このページの対象外のお申し込みです。'))
        except LicenseUnavailable:
            return self.onboarding.html(503, self.onboarding.error(
                'ただいま確認できません', '少し時間をおいて、もう一度お試しください。'))
        except AuthError:
            return self.onboarding.html(400, self.onboarding.error(
                'ログインを完了できませんでした', 'お手数ですが、決済完了画面のリンクからもう一度お試しください。'))
        except Rejected:
            return self.onboarding.html(403, self.onboarding.error(
                'この操作は受け付けられませんでした', 'ページを再読み込みして、もう一度お試しください。'))
        except WordPressConnectionError:
            return self.onboarding.html(503, self.onboarding.error(
                'WordPress.comに接続できませんでした', '少し時間をおいて、決済完了画面のリンクからもう一度お試しください。'))

    def wordpress_request(self, body, required):
        starting = body['action'] == 'wordpress_start'
        fields(body, required + ('action',) + (('site_url',) if starting else ('state', 'code')))
        org, subject = body['org_id'], body['google_subject']
        if not valid_org_id(org) or not valid_google_subject(subject):
            raise BadRequest()
        if self.wordpress is None:
            return self.response(503, {'error': 'wordpress_connection_unavailable'})
        try:
            connection = self.wordpress()
            result = (connection.start(org, subject, body['site_url']) if starting
                      else connection.finish(org, subject, body['state'], body['code']))
            return self.response(200, result)
        except ValueError:
            return self.response(409, {'error': 'wordpress_connection_failed'})
        except Exception:
            return self.response(503, {'error': 'wordpress_connection_unavailable'})

    def rpc(self, request, claims, event):
        tools = TOOL_FIELDS
        fields(request, ('jsonrpc', 'method'), ('id', 'params'))
        if request['jsonrpc'] != '2.0' or not isinstance(request['method'], str):
            raise BadRequest()
        request_id = request.get('id')
        if request_id is not None and (type(request_id) not in (str, int)):
            raise BadRequest()
        params = request.get('params', {})
        if not isinstance(params, dict):
            raise BadRequest()
        method = request['method']
        if method == 'notifications/initialized' and 'id' not in request:
            return self.response(202)
        if 'id' not in request:
            raise BadRequest()
        try:
            if method == 'initialize':
                fields(params, ('protocolVersion', 'capabilities', 'clientInfo'), ('_meta',))
                if '_meta' in params and not isinstance(params['_meta'], dict):
                    raise BadRequest()
                requested = params['protocolVersion']
                result = {'protocolVersion': requested if requested in ('2025-11-25', '2025-06-18', '2024-11-05') else '2025-11-25', 'capabilities': {'tools': {}, 'resources': {}}, 'serverInfo': {'name': 'hp-local-editor', 'version': '1.0.0'}, 'instructions': 'Edit local static files. Saved drafts and queued publication are not completed publication. Confirm only through the authenticated app card.'}
            elif method == 'ping':
                result = {}
            elif method == 'tools/list':
                result = {'tools': tool_definitions(tools)}
            elif method == 'resources/list':
                result = {'resources': [{'uri': UI_URI, 'name': 'HP publication confirmation', 'mimeType': UI_MIME, '_meta': {'ui': {'csp': {'connectDomains': [], 'resourceDomains': []}}}}]}
            elif method == 'resources/read':
                fields(params, ('uri',), ('_meta',))
                if '_meta' in params and not isinstance(params['_meta'], dict):
                    raise BadRequest()
                if params['uri'] != UI_URI:
                    return self.response(200, {'jsonrpc': '2.0', 'id': request_id, 'error': {'code': -32602, 'message': 'Unknown resource'}})
                html = self.ui_html() if callable(self.ui_html) else self.ui_html
                result = {'contents': [{'uri': UI_URI, 'mimeType': UI_MIME, 'text': html, '_meta': {'ui': {'csp': {'connectDomains': [], 'resourceDomains': []}}}}]}
            elif method == 'tools/call':
                fields(params, ('name',), ('arguments', '_meta'))
                name, arguments = params['name'], params.get('arguments', {})
                if not isinstance(name, str):
                    raise BadRequest()
                if name not in tools:
                    return self.response(200, {'jsonrpc': '2.0', 'id': request_id, 'error': {'code': -32602, 'message': 'Unknown tool'}})
                fields(arguments, tools[name])
                if any(not isinstance(v, str) for v in arguments.values()):
                    raise BadRequest()
                result = self.call_tool(name, arguments, claims, params.get('_meta', {}), event)
            else:
                return self.response(200, {'jsonrpc': '2.0', 'id': request_id, 'error': {'code': -32601, 'message': 'Method not found'}})
        except Rejected as error:
            result = tool_error(str(error) if str(error) in SAFE_REJECTIONS else 'request_rejected')
        except LicenseUnavailable:
            result = tool_error('hp_license_unavailable')
        except Conflict:
            result = tool_error('concurrent_change')
        return self.response(200, {'jsonrpc': '2.0', 'id': request_id, 'result': result})

    def call_tool(self, name, arguments, claims, meta, event):
        if name in ('hp_download_workspace', 'hp_prepare_upload'):
            if self.transfers is None:
                raise Rejected('direct_transfer_unavailable')
            if name == 'hp_download_workspace':
                public, private = self.transfers.download(claims, **arguments)
            else:
                public, private = self.transfers.prepare_upload(claims, arguments)
            return {**tool_result(public), '_meta': {'hp_transfer': private}}
        if name == 'hp_profile':
            return tool_result(self.service.profile(claims))
        if name == 'hp_list_sites':
            return tool_result(self.service.list_sites(claims))
        if name in ('hp_open_workspace', 'hp_save_draft', 'hp_submit_preview'):
            return tool_result(self.service.admit(claims, name.removeprefix('hp_'), arguments))
        if name == 'hp_get_operation':
            return tool_result(self.service.operation(claims, arguments['operation_id']))
        if name == 'hp_cancel_operation':
            return tool_result(self.service.cancel(claims, arguments['operation_id']))
        if name == 'hp_resume_operation':
            return tool_result(self.service.resume(claims, arguments['operation_id'], arguments['recovery_id']))
        if name == 'hp_prepare_publish':
            result = self.service.prepare_publish(claims, arguments['site_id'], arguments['preview_id'])
            if self.wordpress_transfers:
                preview = self.service.store.get('preview:' + arguments['preview_id'])
                if preview and preview.get('preview_html_key'):
                    result['structuredContent']['preview_url'] = self.wordpress_transfers.download(
                        preview['preview_html_key'], preview=True)['url']
            result['_meta']['ui'] = {'resourceUri': UI_URI}
            return result
        if name == 'hp_get_confirmation':
            return tool_result(self.service.confirmation(claims, arguments['approval_id']))
        if name == 'hp_cancel_confirmation':
            return tool_result(self.service.cancel_confirmation(claims, arguments['approval_id']))
        if name == 'hp_confirm_publish':
            # The official host enforces app-only exposure; Service binds this
            # nonce to the OAuth subject, live membership and exact artifact.
            return tool_result(self.service.confirm_publish(claims, arguments['approval_id'], arguments['confirmation_nonce']))
        raise Rejected('unsupported_operation')
