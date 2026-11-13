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


def license_org(site):
    # Operator-provisioned sites that predate commercial licensing keep their
    # existing explicit site grants. They cannot pass commercial preflight.
    if 'license_policy' not in site:
        return None
    policy = site['license_policy']
    if (not isinstance(policy, dict) or set(policy) != {'mode', 'org_id'}
            or policy['mode'] != 'simy' or not valid_org_id(policy['org_id'])):
        raise LicenseUnavailable('hp_license_unavailable')
    return policy['org_id']


def resolve_license(resolver, org_id, google_subject):
    if resolver is None or not valid_google_subject(google_subject):
        raise LicenseUnavailable('hp_license_unavailable')
    allowed = resolver(org_id, google_subject)
    if type(allowed) is not bool:
        raise LicenseUnavailable('hp_license_unavailable')
    return allowed


def site_license_allowed(site, google_subject, resolver):
    org_id = license_org(site)
    return org_id is None or resolve_license(resolver, org_id, google_subject)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class EntitlementResolver:
    def __init__(self, endpoint, token):
        if not re.fullmatch(r'https://[a-zA-Z0-9.-]+/functions/v1/hp-control-entitlement', endpoint):
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
