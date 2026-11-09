"""WordPress.com OAuth and verified access to one existing homepage."""
from dataclasses import dataclass, field
from hashlib import sha256
import json
import re
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener

from domain_verification import site_host
from licensing import NoRedirect


ORIGIN = 'https://public-api.wordpress.com'
_opener = build_opener(NoRedirect())


class WordPressConnectionError(ValueError):
    pass


def request_json(method, path, *, token=None, form=None, payload=None):
    if not path.startswith('/') or path.startswith('//'):
        raise WordPressConnectionError('wordpress_bad_provider_path')
    headers = {'Accept': 'application/json'}
    if token is not None:
        headers['Authorization'] = 'Bearer ' + token
    body = None
    if form is not None:
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        body = urlencode(form).encode()
    elif payload is not None:
        headers['Content-Type'] = 'application/json'
        body = json.dumps(payload).encode()
    try:
        request = Request(ORIGIN + path, headers=headers, data=body, method=method)
        with _opener.open(request, timeout=4) as response:
            data = response.read(2_097_153)
        if len(data) > 2_097_152:
            raise ValueError()
        result = json.loads(data)
        if not isinstance(result, dict):
            raise ValueError()
        return result
    except (OSError, ValueError):
        raise WordPressConnectionError('wordpress_provider_unavailable') from None


def positive_id(value):
    if type(value) is int and 0 < value < 10**18:
        return value
    if isinstance(value, str) and re.fullmatch('[1-9][0-9]{0,17}', value):
        return int(value)
    raise WordPressConnectionError('wordpress_invalid_resource')


@dataclass(frozen=True)
class HomepageConnection:
    site_id: int
    page_id: int
    origin: str
    content: str = field(repr=False)
    access_token: str = field(repr=False)


@dataclass(frozen=True)
class HomepageDraft:
    revision_id: int
    base_sha256: str
    content_sha256: str


def content_digest(content):
    return sha256(content.encode()).hexdigest()


def page_path(site_id, page_id):
    return f'/wp/v2/sites/{positive_id(site_id)}/pages/{positive_id(page_id)}'


def raw_content(page):
    content = page.get('content')
    if not isinstance(content, dict) or not isinstance(content.get('raw'), str):
        raise WordPressConnectionError('wordpress_homepage_access_required')
    return content['raw']


class WordPressProvider:
    def __init__(self, client_id, client_secret, callback, transport=request_json):
        url = urlsplit(callback)
        if (not client_id or not client_secret or url.scheme != 'https' or not url.hostname
                or url.username or url.password or url.query or url.fragment):
            raise WordPressConnectionError('wordpress_connection_not_configured')
        self.client_id, self.client_secret, self.callback = client_id, client_secret, callback
        self.transport = transport

    def authorization_url(self, site_url, state):
        if not isinstance(state, str) or not re.fullmatch('[A-Za-z0-9_-]{32,128}', state):
            raise WordPressConnectionError('wordpress_invalid_state')
        return ORIGIN + '/oauth2/authorize?' + urlencode({
            'client_id': self.client_id, 'redirect_uri': self.callback, 'response_type': 'code',
            'blog': site_host(site_url), 'state': state,
        })

    def connect(self, code, site_url):
        host = site_host(site_url)
        if not isinstance(code, str) or not 1 <= len(code) <= 2048 or any(c.isspace() for c in code):
            raise WordPressConnectionError('wordpress_invalid_code')
        grant = self.transport('POST', '/oauth2/token', form={
            'client_id': self.client_id, 'client_secret': self.client_secret, 'redirect_uri': self.callback,
            'grant_type': 'authorization_code', 'code': code,
        })
        token = grant.get('access_token')
        if (not isinstance(token, str) or not re.fullmatch('[!-~]{1,4096}', token)
                or str(grant.get('token_type', '')).lower() != 'bearer'
                or 'global' in str(grant.get('scope', '')).lower().split()):
            raise WordPressConnectionError('wordpress_site_grant_required')
        site_id = positive_id(grant.get('blog_id'))
        sites = self.transport('GET', '/rest/v1.1/me/sites', token=token).get('sites')
        if not isinstance(sites, list):
            raise WordPressConnectionError('wordpress_site_access_required')
        site = next((site for site in sites if isinstance(site, dict) and site.get('ID') == site_id), None)
        if not site or not same_public_origin(site.get('URL'), host) or site.get('is_private') is not False:
            raise WordPressConnectionError('wordpress_wrong_site')
        prefix = '/wp/v2/sites/' + str(site_id)
        caps = self.transport('GET', prefix + '/users/me?context=edit', token=token).get('capabilities')
        if not isinstance(caps, dict) or any(caps.get(cap) is not True for cap in ('edit_pages', 'publish_pages')):
            raise WordPressConnectionError('wordpress_publish_permission_required')
        settings = self.transport('GET', prefix + '/settings', token=token)
        if settings.get('show_on_front') != 'page':
            raise WordPressConnectionError('wordpress_static_homepage_required')
        page_id = positive_id(settings.get('page_on_front'))
        page = self.transport('GET', page_path(site_id, page_id) + '?context=edit', token=token)
        if (page.get('id') != page_id or page.get('status') != 'publish'
                or not same_public_origin(page.get('link'), host)):
            raise WordPressConnectionError('wordpress_homepage_access_required')
        return HomepageConnection(site_id, page_id, 'https://' + host, raw_content(page), token)

    def _read_homepage(self, connection):
        prefix = f'/wp/v2/sites/{positive_id(connection.site_id)}'
        settings = self.transport('GET', prefix + '/settings', token=connection.access_token)
        if settings.get('show_on_front') != 'page' or settings.get('page_on_front') != connection.page_id:
            raise WordPressConnectionError('wordpress_homepage_changed')
        path = page_path(connection.site_id, connection.page_id)
        page = self.transport('GET', path + '?context=edit', token=connection.access_token)
        if (page.get('id') != connection.page_id or page.get('status') != 'publish'
                or not same_public_origin(page.get('link'), site_host(connection.origin))):
            raise WordPressConnectionError('wordpress_homepage_changed')
        return raw_content(page)

    def save_draft(self, connection, content):
        if not isinstance(content, str) or not content or len(content.encode()) > 1_000_000:
            raise WordPressConnectionError('wordpress_invalid_content')
        if self._read_homepage(connection) != connection.content:
            raise WordPressConnectionError('wordpress_homepage_changed')
        path = page_path(connection.site_id, connection.page_id)
        result = self.transport('POST', path + '/autosaves?context=edit',
                                token=connection.access_token, payload={'content': content})
        if result.get('parent') != connection.page_id or raw_content(result) != content:
            raise WordPressConnectionError('wordpress_draft_readback_mismatch')
        return HomepageDraft(positive_id(result.get('id')), content_digest(connection.content), content_digest(content))

    def publish_approved_draft(self, connection, draft, approved_sha256):
        if (approved_sha256 != draft.content_sha256
                or draft.base_sha256 != content_digest(connection.content)):
            raise WordPressConnectionError('wordpress_approval_mismatch')
        path = page_path(connection.site_id, connection.page_id)
        revision = self.transport('GET', path + f'/autosaves/{positive_id(draft.revision_id)}?context=edit',
                                  token=connection.access_token)
        content = raw_content(revision)
        if (revision.get('id') != draft.revision_id or revision.get('parent') != connection.page_id
                or content_digest(content) != approved_sha256):
            raise WordPressConnectionError('wordpress_draft_changed')
        current = self._read_homepage(connection)
        if current == content:
            return
        if content_digest(current) != draft.base_sha256:
            raise WordPressConnectionError('wordpress_homepage_changed')
        # Core WordPress does not provide an atomic compare-and-update here.
        # The caller must serialize publication and reconcile any uncertain write.
        self.transport('POST', path, token=connection.access_token, payload={'content': content})
        if self._read_homepage(connection) != content:
            raise WordPressConnectionError('wordpress_publication_readback_mismatch')


def same_public_origin(value, host):
    try:
        if not isinstance(value, str):
            return False
        url = urlsplit(value)
        return (url.scheme == 'https' and url.path in ('', '/') and not url.query and not url.fragment
                and site_host(value) == host)
    except ValueError:
        return False
