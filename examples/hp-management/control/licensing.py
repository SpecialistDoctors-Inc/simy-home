"""Check SIMY licenses for sites explicitly mapped by the operator."""
from __future__ import annotations

import json
import re
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID


class LicenseUnavailable(RuntimeError):
    """A license could not be checked. Workers may retry the same command."""


def valid_org_id(value):
    if not isinstance(value, str):
        return False
    try:
        return str(UUID(value)) == value
    except ValueError:
        return False


def valid_google_subject(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,255}', value) is not None


def valid_service_token(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{32,256}', value) is not None


def valid_subscription_id(value):
    return isinstance(value, str) and re.fullmatch(r'sub_[A-Za-z0-9]{8,64}', value) is not None


def license_policy(site):
    """Return the site's commercial license: a SIMY organization or a Stripe subscription."""
    # Operator-provisioned sites that predate commercial licensing keep their
    # existing explicit site grants. They cannot pass commercial preflight.
    if 'license_policy' not in site:
        return None
    policy = site['license_policy']
    if (isinstance(policy, dict) and set(policy) == {'mode', 'org_id'}
            and policy['mode'] == 'simy' and valid_org_id(policy['org_id'])):
        return policy
    if (isinstance(policy, dict) and set(policy) == {'mode', 'subscription_id'}
            and policy['mode'] == 'stripe' and valid_subscription_id(policy['subscription_id'])):
        return policy
    raise LicenseUnavailable('hp_license_unavailable')


def license_org(site):
    policy = license_policy(site)
    return policy['org_id'] if policy is not None and policy['mode'] == 'simy' else None


def resolve_license(resolver, org_id, google_subject):
    if resolver is None or not valid_google_subject(google_subject):
        raise LicenseUnavailable('hp_license_unavailable')
    allowed = resolver(org_id, google_subject)
    if type(allowed) is not bool:
        raise LicenseUnavailable('hp_license_unavailable')
    return allowed


def site_license_allowed(site, google_subject, resolver, stripe=None):
    policy = license_policy(site)
    if policy is None:
        return True
    if policy['mode'] == 'stripe':
        # Clinic sites bought through a Stripe Payment Link are licensed by
        # that subscription alone; no SIMY organization is involved.
        if stripe is None or not valid_google_subject(google_subject):
            raise LicenseUnavailable('hp_license_unavailable')
        return stripe.allowed(policy['subscription_id'], google_subject)
    return resolve_license(resolver, policy['org_id'], google_subject)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


LOOPBACK_ENDPOINT = r'http://(?:127\.0\.0\.1|localhost):[0-9]{1,5}/functions/v1/hp-control-entitlement'


class EntitlementResolver:
    def __init__(self, endpoint, token, *, allow_loopback=False):
        # Deployed HP Control reaches SIMY over HTTPS only. The loopback form is
        # for local_bridge.py against a local Supabase; Lambda never passes it.
        if not (re.fullmatch(r'https://[a-zA-Z0-9.-]+/functions/v1/hp-control-entitlement', endpoint)
                or (allow_loopback and re.fullmatch(LOOPBACK_ENDPOINT, endpoint))):
            raise LicenseUnavailable('hp_license_unavailable')
        self.endpoint, self.token = endpoint, token
        self.opener = build_opener(NoRedirect())

    def __call__(self, org_id, google_subject):
        try:
            token = self.token()
            if not valid_service_token(token):
                raise ValueError()
            request = Request(self.endpoint, method='POST',
                data=json.dumps({'org_id': org_id, 'google_subject': google_subject}).encode(),
                headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json',
                         'Accept': 'application/json'})
            with self.opener.open(request, timeout=3) as response:
                if response.status != 200:
                    raise ValueError()
                payload = response.read(1025)
            if len(payload) > 1024:
                raise ValueError()
            result = json.loads(payload)
            if not isinstance(result, dict) or set(result) != {'allowed'} or type(result['allowed']) is not bool:
                raise ValueError()
            return result['allowed']
        except Exception:
            raise LicenseUnavailable('hp_license_unavailable') from None
