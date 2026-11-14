"""Bind one site's WordPress consent to the signed-in account and its license.

A site is licensed either by a SIMY organization (signup on the SIMY app) or by
a Stripe subscription (a clinic that bought HP management on simy.one). The
consent state, the stored site and its encrypted credential all carry the same
license policy, so a grant can only ever be used under the license it was made for.
"""
from hashlib import sha256
import json
import re
import secrets
import time

from cryptography.fernet import Fernet

from domain_verification import site_host
from licensing import license_policy
from store import Write
from wordpress_provider import HomepageConnection, WordPressConnectionError, WordPressProvider

STATE_SECONDS = 600


def simy_policy(org):
    return {'mode': 'simy', 'org_id': org}


class WordPressOnboarding:
    def __init__(self, store, config, clock=time.time, provider=None):
        self.store, self.clock = store, clock
        self.provider = provider or WordPressProvider(config['client_id'], config['client_secret'], config['callback'])
        self.cipher = Fernet(config['credential_key'].encode())

    # SIMY app signup (internal API called by simy-web with the account's organization).
    def start(self, org, subject, site_url):
        return self.start_for(simy_policy(org), subject, site_url)

    def finish(self, org, subject, state, code):
        self.finish_for(simy_policy(org), subject, state, code)
        return {'status': 'wordpress_connected'}

    def start_for(self, policy, subject, site_url, binding=None):
        """Begin consent for one host under ``policy``; ``binding`` is kept with the state."""
        host = site_host(site_url)
        state = secrets.token_urlsafe(32)
        authorize_url = self.provider.authorization_url(host, state)
        attempt = {'license_policy': policy, 'subject': subject, 'host': host,
                   'expires_at': int(self.clock()) + STATE_SECONDS, **(binding or {})}
        if policy.get('mode') == 'simy':
            attempt['org_id'] = policy['org_id']
        self.store.put(self.state_key(state), attempt)
        return {'status': 'authorization_required', 'url': authorize_url, 'state': state}

    def attempt(self, state):
        """The unexpired, unused consent state, or None."""
        attempt = self.store.get(self.state_key(state))
        if not attempt or attempt['expires_at'] <= self.clock() or attempt.get('used'):
            return None
        return attempt

    def finish_for(self, policy, subject, state, code):
        key = self.state_key(state)
        attempt = self.store.get(key)
        if (not attempt or self.attempt_policy(attempt) != policy or attempt.get('subject') != subject
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
                or existing.get('disabled') or existing.get('license_policy') != policy)):
            raise WordPressConnectionError('wordpress_site_unavailable')
        # Keep the grant with the provider, account, license and target it authorizes.
        sealed = {'site_id': site_id, 'page_id': connection.page_id, 'origin': connection.origin,
                  'subject': subject, 'license_policy': policy, 'access_token': connection.access_token}
        if policy['mode'] == 'simy':
            sealed['org_id'] = policy['org_id']
        credential = self.cipher.encrypt(json.dumps(sealed).encode()).decode()
        site = {'site_id': site_id, 'name': attempt['host'], 'prod_url': connection.origin, 'dev_url': None,
                'provider': 'wordpress', 'owner_subject': subject, 'credential': credential,
                'direct_transfer_enabled': True,
                'config_version': (existing['config_version'] + 1) if existing else 1,
                'license_policy': policy}
        self.store.transact([
            Write(site_key, site, existing['_version'] if existing else None),
            Write(member_key, {**member, 'sites': {**member['sites'], site_id: ['read']}}, member.get('_version')),
        ])
        return {'status': 'wordpress_connected', 'site_id': site_id, 'origin': connection.origin}

    def load(self, site, subject):
        credential = json.loads(self.cipher.decrypt(site['credential'].encode()))
        # Credentials sealed before Stripe licensing carry only the organization.
        sealed_policy = credential.get('license_policy') or simy_policy(credential.get('org_id'))
        if (credential['site_id'] != site['site_id'] or credential['subject'] != subject
                or sealed_policy != license_policy(site) or credential['origin'] != site['prod_url']):
            raise WordPressConnectionError('wordpress_credential_mismatch')
        connection = HomepageConnection(int(site['site_id'].removeprefix('wordpress-')),
            credential['page_id'], credential['origin'], '', credential['access_token'])
        return HomepageConnection(connection.site_id, connection.page_id, connection.origin,
                                  self.provider.read_homepage(connection), connection.access_token)

    @staticmethod
    def attempt_policy(attempt):
        # States written before Stripe licensing carry only the organization.
        return attempt.get('license_policy') or simy_policy(attempt.get('org_id'))

    @staticmethod
    def state_key(state):
        if not isinstance(state, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', state):
            raise WordPressConnectionError('wordpress_invalid_state')
        return 'wordpress-consent:' + sha256(state.encode()).hexdigest()
