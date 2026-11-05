"""Google-backed OAuth issuer for HP tools. Google tokens never enter tool results."""
from __future__ import annotations
import base64
import hashlib
import json
import re
import secrets
import time
from urllib.parse import urlencode, urlsplit
from store import Write, Check, Conflict


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def random_id():
    return secrets.token_urlsafe(32)


class AuthError(ValueError):
    pass


class Identity:
    def __init__(self, store, issuer, google_client_id, signer, google_exchange, clock=time.time):
        self.store, self.issuer, self.client_id = store, issuer.rstrip('/'), google_client_id
        self.signer, self.exchange, self.clock = signer, google_exchange, clock
        self.resource = self.issuer + '/mcp'

    @staticmethod
    def valid_redirect(uri):
        if not isinstance(uri, str) or not uri or uri != uri.strip() or any(ord(c) < 33 or ord(c) == 127 for c in uri):
            return False
        try:
            p = urlsplit(uri)
            port = p.port
        except ValueError:
            return False
        return (not p.fragment and not p.username and not p.password and (
            (p.scheme == 'https' and p.hostname == 'chatgpt.com' and port in (None, 443)
             and (p.path == '/connector_platform_oauth_redirect' or p.path.startswith('/connector/oauth/'))) or
            (p.scheme == 'http' and p.hostname in ('localhost', '127.0.0.1', '::1') and port is not None)))

    def register(self, body):
        redirects = body.get('redirect_uris', [])
        if not 1 <= len(redirects) <= 5 or not all(isinstance(u, str) and self.valid_redirect(u) for u in redirects):
            raise AuthError('invalid_redirect_uri')
        if body.get('token_endpoint_auth_method', 'none') != 'none':
            raise AuthError('unsupported_client_auth')
        client = 'hp-' + random_id()
        record = {'redirect_uris': redirects, 'client_name': 'HP Codex client', 'created_at': int(self.clock())}
        self.store.put('client:' + client, record)
        return {'client_id': client, 'client_id_issued_at': record['created_at'], **record,
                'token_endpoint_auth_method': 'none', 'grant_types': ['authorization_code', 'refresh_token'],
                'response_types': ['code']}

    def authorize(self, query):
        client = self.store.get('client:' + str(query.get('client_id', '')))
        if not client or query.get('redirect_uri') not in client['redirect_uris']:
            raise AuthError('invalid_client_or_redirect')
        if query.get('response_type') != 'code' or query.get('resource') != self.resource:
            raise AuthError('invalid_authorization_request')
        challenge = query.get('code_challenge', '')
        if query.get('code_challenge_method') != 'S256' or not re.fullmatch(r'[A-Za-z0-9_-]{43}', challenge):
            raise AuthError('pkce_s256_required')
        scopes = set(query.get('scope', 'openid email hp:read hp:write').split())
        if not scopes or not scopes <= {'openid', 'email', 'profile', 'hp:read', 'hp:write'}:
            raise AuthError('invalid_scope')
        state, nonce = random_id(), random_id()
        client_nonce = query.get('nonce')
        if client_nonce is not None and (not isinstance(client_nonce, str) or not 1 <= len(client_nonce) <= 256):
            raise AuthError('invalid_nonce')
        self.store.put('login:' + sha(state), {'client_id': query['client_id'], 'redirect_uri': query['redirect_uri'],
            'client_state': query.get('state', ''), 'challenge': challenge, 'scope': ' '.join(sorted(scopes)),
            'nonce': nonce, 'client_nonce': client_nonce, 'resource': self.resource, 'expires_at': int(self.clock()) + 600})
        return 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({'client_id': self.client_id,
            'redirect_uri': self.issuer + '/oauth/google/callback', 'response_type': 'code', 'scope': 'openid email',
            'state': state, 'nonce': nonce, 'prompt': 'select_account'})

    def callback(self, state, google_code):
        key = 'login:' + sha(state)
        login = self.store.get(key)
        if not login or login['expires_at'] <= self.clock():
            raise AuthError('expired_login')
        profile = self.exchange(google_code, self.issuer + '/oauth/google/callback', login['nonce'])
        subject = profile.get('sub')
        if not isinstance(subject, str) or not profile.get('email_verified') or not isinstance(profile.get('email'), str):
            raise AuthError('invalid_google_identity')
        member = self.store.get('principal:' + subject)
        membership_writes = []
        if not member:
            invitation_key = 'invitation:' + sha(profile['email'].casefold())
            invitation = self.store.get(invitation_key)
            if (not invitation or invitation.get('email', '').casefold() != profile['email'].casefold()
                    or invitation.get('expires_at', 0) <= self.clock() or invitation.get('claimed_subject')
                    or not invitation.get('sites')):
                raise AuthError('site_invitation_required')
            # Only an administrator can create these server-owned invitations.
            # A verified exact mailbox binds once to Google's immutable subject;
            # a recycled email cannot claim the old principal's permissions.
            member = {'sites': invitation['sites'], 'email': profile['email'], 'disabled': False}
            membership_writes = [Write('principal:' + subject, member, None),
                Write(invitation_key, {**invitation, 'claimed_subject': subject}, invitation['_version'])]
        elif member.get('disabled') or not member.get('sites'):
            raise AuthError('site_invitation_required')
        else:
            membership_writes = [Check('principal:' + subject, member['_version'])]
        code = random_id()
        value = {**login, 'subject': subject, 'email': profile['email'], 'expires_at': int(self.clock()) + 120}
        value.pop('_version', None)
        self.store.transact([Write(key, None, login['_version']), Write('code:' + sha(code), value, None),
                             *membership_writes])
        separator = '&' if '?' in login['redirect_uri'] else '?'
        return login['redirect_uri'] + separator + urlencode({'code': code, 'state': login['client_state'], 'iss': self.issuer})

    def token(self, form):
        grant = form.get('grant_type')
        if form.get('resource') != self.resource:
            raise AuthError('invalid_resource')
        if grant == 'authorization_code':
            key = 'code:' + sha(str(form.get('code', '')))
            old = self.store.get(key)
            verifier = form.get('code_verifier', '')
            if not re.fullmatch(r'[A-Za-z0-9._~-]{43,128}', verifier):
                raise AuthError('invalid_grant')
            calculated = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
            if not old or old['expires_at'] <= self.clock() or old['client_id'] != form.get('client_id') or old['redirect_uri'] != form.get('redirect_uri') or not secrets.compare_digest(old['challenge'], calculated):
                raise AuthError('invalid_grant')
            family = random_id()
        elif grant == 'refresh_token':
            key = 'refresh:' + sha(str(form.get('refresh_token', '')))
            old = self.store.get(key)
            if not old or old['expires_at'] <= self.clock() or old['client_id'] != form.get('client_id') or old.get('used'):
                raise AuthError('invalid_grant')
            family = old['family']
        else:
            raise AuthError('unsupported_grant_type')
        member = self.store.get('principal:' + old['subject'])
        if not member or member.get('disabled') or not member.get('sites'):
            raise AuthError('access_revoked')
        refresh, now = random_id(), int(self.clock())
        value = {'subject': old['subject'], 'email': old['email'], 'client_id': old['client_id'],
            'scope': old['scope'], 'family': family, 'expires_at': now + 30 * 86400}
        self.store.transact([Write(key, None, old['_version']), Write('refresh:' + sha(refresh), value, None),
                             Check('principal:' + old['subject'], member['_version'])])
        claims = {'iss': self.issuer, 'aud': self.resource, 'sub': old['subject'], 'email': old['email'],
            'email_verified': True, 'scope': old['scope'], 'iat': now, 'exp': now + 600, 'jti': random_id()}
        result = {'access_token': self.signer(claims), 'token_type': 'Bearer', 'expires_in': 600,
                  'refresh_token': refresh, 'scope': old['scope']}
        if 'openid' in old['scope'].split():
            id_claims = {**claims, 'aud': old['client_id']}
            if grant == 'authorization_code' and old.get('client_nonce') is not None:
                id_claims['nonce'] = old['client_nonce']
            result['id_token'] = self.signer(id_claims)
        return result

    def metadata(self):
        return {'issuer': self.issuer, 'authorization_endpoint': self.issuer + '/oauth/authorize',
            'token_endpoint': self.issuer + '/oauth/token', 'registration_endpoint': self.issuer + '/oauth/register',
            'jwks_uri': self.issuer + '/oauth/jwks', 'userinfo_endpoint': self.issuer + '/oauth/userinfo',
            'response_types_supported': ['code'], 'grant_types_supported': ['authorization_code', 'refresh_token'],
            'code_challenge_methods_supported': ['S256'], 'token_endpoint_auth_methods_supported': ['none'],
            'authorization_response_iss_parameter_supported': True, 'subject_types_supported': ['public'],
            'id_token_signing_alg_values_supported': ['RS256'],
            'scopes_supported': ['openid', 'email', 'profile', 'hp:read', 'hp:write']}
