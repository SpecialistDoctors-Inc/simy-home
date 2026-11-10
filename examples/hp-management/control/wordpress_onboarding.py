"""Bind one site's WordPress consent to the signed-in SIMY account."""
from hashlib import sha256
import json
import re
import secrets
import time

from cryptography.fernet import Fernet

from domain_verification import site_host
from store import Write
from wordpress_provider import HomepageConnection, WordPressConnectionError, WordPressProvider


class WordPressOnboarding:
    def __init__(self, store, config, clock=time.time, provider=None):
        self.store, self.clock = store, clock
        self.provider = provider or WordPressProvider(config['client_id'], config['client_secret'], config['callback'])
        self.cipher = Fernet(config['credential_key'].encode())

    def start(self, org, subject, site_url):
        host = site_host(site_url)
        state = secrets.token_urlsafe(32)
        authorize_url = self.provider.authorization_url(host, state)
        self.store.put(self.state_key(state), {'org_id': org, 'subject': subject, 'host': host,
                                             'expires_at': int(self.clock()) + 600})
        return {'status': 'authorization_required', 'url': authorize_url, 'state': state}

    def finish(self, org, subject, state, code):
        key = self.state_key(state)
        attempt = self.store.get(key)
        if (not attempt or attempt.get('org_id') != org or attempt.get('subject') != subject
                or attempt['expires_at'] <= self.clock() or attempt.get('used')):
            raise WordPressConnectionError('wordpress_invalid_state')
        # Consume the state before exchanging its single-use authorization code.
        self.store.put(key, {**attempt, 'used': True}, attempt['_version'])
        connection = self.provider.connect(code, attempt['host'])
        if attempt['expires_at'] <= self.clock():
            raise WordPressConnectionError('wordpress_invalid_state')
        site_id = 'wordpress-' + str(connection.site_id)
        site_key, member_key = 'site:' + site_id, 'principal:' + subject
        existing = self.store.get(site_key)
        member = self.store.get(member_key) or {'sites': {}, 'disabled': False}
        if member.get('disabled') or (existing and (
                existing.get('provider') != 'wordpress' or existing.get('owner_subject') != subject
                or existing.get('disabled') or existing.get('license_policy', {}).get('org_id') != org)):
            raise WordPressConnectionError('wordpress_site_unavailable')
        # Keep the grant with the provider, account and target it authorizes.
        credential = self.cipher.encrypt(json.dumps({'site_id': site_id, 'page_id': connection.page_id,
            'origin': connection.origin, 'org_id': org, 'subject': subject,
            'access_token': connection.access_token}).encode()).decode()
        site = {'site_id': site_id, 'name': attempt['host'], 'prod_url': connection.origin, 'dev_url': None,
                'provider': 'wordpress', 'owner_subject': subject, 'credential': credential,
                'direct_transfer_enabled': True,
                'config_version': (existing['config_version'] + 1) if existing else 1,
                'license_policy': {'mode': 'simy', 'org_id': org}}
        self.store.transact([
            Write(site_key, site, existing['_version'] if existing else None),
            Write(member_key, {**member, 'sites': {**member['sites'], site_id: ['read']}}, member.get('_version')),
        ])
        return {'status': 'wordpress_connected'}

    def load(self, site, subject):
        credential = json.loads(self.cipher.decrypt(site['credential'].encode()))
        if (credential['site_id'] != site['site_id'] or credential['subject'] != subject
                or credential['org_id'] != site['license_policy']['org_id'] or credential['origin'] != site['prod_url']):
            raise WordPressConnectionError('wordpress_credential_mismatch')
        connection = HomepageConnection(int(site['site_id'].removeprefix('wordpress-')),
            credential['page_id'], credential['origin'], '', credential['access_token'])
        return HomepageConnection(connection.site_id, connection.page_id, connection.origin,
                                  self.provider.read_homepage(connection), connection.access_token)

    @staticmethod
    def state_key(state):
        if not isinstance(state, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', state):
            raise WordPressConnectionError('wordpress_invalid_state')
        return 'wordpress-consent:' + sha256(state.encode()).hexdigest()
