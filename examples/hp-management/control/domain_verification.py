"""Verify the owner of a supported HP without visiting user-supplied URLs."""
import json
import re
from urllib.parse import urlencode, urlsplit
from urllib.request import build_opener

from licensing import LicenseUnavailable, NoRedirect

_dns = build_opener(NoRedirect())


def site_host(value):
    if not isinstance(value, str) or len(value) > 2048 or re.search(r'[\s\\]', value):
        raise ValueError('invalid_site_url')
    try:
        url = urlsplit(value if '://' in value else 'https://' + value)
        if (url.scheme not in ('http', 'https') or not url.hostname or url.username is not None
                or url.password is not None or url.port not in (None, 80 if url.scheme == 'http' else 443)):
            raise ValueError()
        host = url.hostname.rstrip('.').encode('idna').decode('ascii')
        # Reserve room for the TXT record's label. Exclude IP addresses and local names.
        labels = host.split('.')
        if (len(host) > 244 or len(labels) < 2 or not re.search(r'[a-z]', labels[-1])
                or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in labels)):
            raise ValueError()
        return host
    except (UnicodeError, ValueError):
        raise ValueError('invalid_site_url') from None


def dns_has_value(name, value):
    query = urlencode({'name': name, 'type': 'TXT', 'edns_client_subnet': '0.0.0.0/0'})
    try:
        with _dns.open('https://dns.google/resolve?' + query, timeout=2) as response:
            data = response.read(65537)
        if len(data) > 65536:
            raise ValueError()
        payload = json.loads(data)
        if not isinstance(payload, dict) or payload.get('TC') or payload.get('Status') not in (0, 3):
            raise ValueError()
        return payload['Status'] == 0 and any(
            answer['name'].lower() == name + '.' and answer['type'] == 16
            and answer['data'] in (value, '"' + value + '"')
            for answer in payload.get('Answer', [])
        )
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        raise LicenseUnavailable('hp_license_unavailable') from None
