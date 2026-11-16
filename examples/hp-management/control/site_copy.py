"""Copy a clinic's public homepage into private storage for verified activation.

A paid clinic whose domain SIMY has not prepared yet gives us its homepage URL.
We fetch what the public already sees, starting at ``https://<host>/``, and keep
it as one zip in the private artifact bucket. The activation worker can build the editable
site from a complete verified capture; nothing here publishes or grants access.

Only HTTPS on the same host (with or without ``www.``) is fetched, and hosts that
resolve to private, loopback, link-local or otherwise non-public addresses are
refused, so the copier cannot be pointed at internal services.

Records:
  clinic-copy-pending  {'subscriptions': ['<sub_id>:<generation>', ...]}  work list
  clinic-intake:<sub>  copy_state / copy_generation / copy_attempts / copy_key ...

Each submission of a new homepage bumps the intake's copy_generation and queues
"<sub>:<generation>", so a job is acknowledged only for the generation it copied.
An attempt is recorded and the job moved to the back of the list *before* any
network work, so a run killed by the Lambda timeout still counts as an attempt
and cannot hold up other clinics.
"""
from __future__ import annotations

import hashlib
import http.client
import io
import ipaddress
import json
import re
import socket
import ssl
import time
import zipfile
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.parse import urldefrag, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener

from store import Conflict, Write

MAX_FILES = 200
MAX_TOTAL = 30 * 1024 * 1024
MAX_FILE = 10 * 1024 * 1024
MAX_SECONDS = 90
FETCH_SECONDS = 20  # absolute per-response budget; socket timeouts only bound idle gaps
MAX_ATTEMPTS = 3
PENDING_KEY = 'clinic-copy-pending'
USER_AGENT = 'SIMY-HP-Copy/1.0 (+https://simy.one/hp-management/)'


class CopyFailed(Exception):
    """The homepage could not be copied; the reason is safe to store."""


def same_site(host, other):
    strip = lambda h: h[4:] if h.startswith('www.') else h
    return isinstance(other, str) and strip(other.lower()) == strip(host.lower())


def public_address(host, resolve=socket.getaddrinfo):
    """True only when every address the host resolves to is globally routable."""
    try:
        infos = resolve(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        return False
    addresses = {info[4][0] for info in infos}
    return bool(addresses) and all(ipaddress.ip_address(a.split('%')[0]).is_global for a in addresses)


class _Links(HTMLParser):
    ATTRS = {'href', 'src', 'poster', 'data-src'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if not value:
                continue
            if name in self.ATTRS:
                self.links.append(value)
            elif name in ('srcset', 'data-srcset'):
                self.links.extend(part.strip().split(' ')[0] for part in value.split(',') if part.strip())
            elif name == 'style':
                self.links.extend(css_links(value))

    def handle_data(self, data):
        # Inline <style> blocks.
        if 'url(' in data:
            self.links.extend(css_links(data))


def css_links(text):
    return [m.group(2) for m in re.finditer(r'url\(\s*([\'"]?)([^\'")\s]+)\1\s*\)', text)]


def page_links(content_type, body):
    text = body.decode('utf-8', 'replace')
    if 'html' in content_type:
        parser = _Links()
        parser.feed(text)
        return parser.links
    if 'css' in content_type:
        return css_links(text)
    return []


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class _PublicHTTPSConnection(http.client.HTTPSConnection):
    """Refuse the connection when the address actually dialed is not public.

    Checking after connect closes the gap between our DNS lookup and the one
    urllib does (DNS rebinding)."""

    def connect(self):
        super().connect()
        peer = self.sock.getpeername()[0]
        if not ipaddress.ip_address(peer.split('%')[0]).is_global:
            self.sock.close()
            raise CopyFailed('non_public_host')


class _PublicHTTPSHandler(HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_PublicHTTPSConnection, req, context=ssl.create_default_context())


def default_fetch(url, resolve=socket.getaddrinfo, opener=None, clock=time.monotonic):
    """GET one URL without following redirects. Returns (status, headers, body)."""
    host = urlsplit(url).hostname
    if not host or not public_address(host, resolve):
        raise CopyFailed('non_public_host')
    # No environment proxies: the address check must see the real peer.
    opener = opener or build_opener(ProxyHandler({}), _PublicHTTPSHandler(), _NoRedirect())
    request = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': '*/*'})
    try:
        deadline = clock() + FETCH_SECONDS
        with opener.open(request, timeout=15) as response:
            chunks, size = [], 0
            while size <= MAX_FILE:
                if clock() > deadline:
                    raise CopyFailed('fetch_timeout')
                chunk = response.read(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
            return response.status, dict(response.headers), b''.join(chunks)
    except HTTPError as error:
        return error.code, dict(error.headers or {}), b''


def archive_path(url):
    parts = urlsplit(url)
    path = parts.path or '/'
    if path.endswith('/'):
        path += 'index.html'
    if parts.query:
        path += '__' + hashlib.sha256(parts.query.encode()).hexdigest()[:12]
    # Keep the archive inside one root, whatever the URL path looks like.
    clean = '/'.join(p for p in path.split('/') if p not in ('', '.', '..'))
    return 'site/' + (clean or 'index.html')


def copy_public_site(host, fetch=default_fetch, clock=time.monotonic, now=time.time):
    """Fetch the public site at https://<host>/ within fixed limits; return (zip_bytes, manifest)."""
    if not isinstance(host, str) or not re.fullmatch(r'[a-z0-9.-]{1,253}', host):
        raise CopyFailed('invalid_host')
    started = clock()
    queue, seen, files, total, truncated = ['https://' + host + '/'], set(), [], 0, False
    missing = []
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        while queue:
            if len(files) >= MAX_FILES or clock() - started > MAX_SECONDS:
                truncated = True
                break
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            try:
                status, headers, body = fetch(url)
            except CopyFailed:
                if not files:
                    raise
                missing.append(url)
                continue
            except Exception:
                missing.append(url)
                continue  # one unreachable asset does not stop the copy
            headers = {k.lower(): v for k, v in (headers or {}).items()}
            if status in (301, 302, 303, 307, 308):
                target = urldefrag(urljoin(url, headers.get('location', '')))[0]
                parts = urlsplit(target)
                if parts.scheme == 'https' and same_site(host, parts.hostname) and target not in seen:
                    queue.insert(0, target)
                else:
                    missing.append(url)
                continue
            if status != 200:
                missing.append(url)
                continue
            if len(body) > MAX_FILE:
                truncated = True
                continue
            if total + len(body) > MAX_TOTAL:
                truncated = True
                break
            path = archive_path(url)
            if path in {f['path'] for f in files}:
                continue
            archive.writestr(path, body)
            total += len(body)
            content_type = headers.get('content-type', '')
            files.append({'url': url, 'path': path, 'sha256': hashlib.sha256(body).hexdigest(),
                          'bytes': len(body), 'content_type': content_type[:100]})
            for link in page_links(content_type.lower(), body):
                target = urldefrag(urljoin(url, link.strip()))[0]
                parts = urlsplit(target)
                if parts.scheme == 'https' and same_site(host, parts.hostname) and target not in seen:
                    queue.append(target)
        if not files:
            raise CopyFailed('nothing_fetched')
        manifest = {'copy_schema': 2, 'host': host, 'copied_at': int(now()), 'files': files, 'truncated': truncated,
                    'missing': missing,
                    'total_bytes': total}
        archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    return buffer.getvalue(), manifest


def intake_copy_key(subscription_id, data):
    sub = hashlib.sha256(subscription_id.encode()).hexdigest()
    return f'intake/{sub}/{hashlib.sha256(data).hexdigest()}/site.zip'


# -- work list -------------------------------------------------------------

def job(subscription_id, generation):
    return f'{subscription_id}:{generation}'


def _update_list(store, change):
    for _ in range(5):
        row = store.get(PENDING_KEY)
        jobs = list(row.get('subscriptions', [])) if row else []
        new = change(jobs)
        if new == jobs:
            return
        try:
            store.put(PENDING_KEY, {'subscriptions': new}, row['_version'] if row else None)
            return
        except Conflict:
            continue
    raise Conflict('concurrent_change')


def enqueue(store, subscription_id, generation):
    """Queue one copy generation for a subscription (idempotent)."""
    entry = job(subscription_id, generation)
    _update_list(store, lambda jobs: jobs if entry in jobs else jobs + [entry])


def _dequeue(store, entry):
    _update_list(store, lambda jobs: [j for j in jobs if j != entry])


def _rotate(store, entry):
    _update_list(store, lambda jobs: [j for j in jobs if j != entry] + [entry])


def run_one(store, put_object, copier=copy_public_site, clock=time.time):
    """Copy the oldest queued job. Returns the job handled, or None."""
    row = store.get(PENDING_KEY)
    jobs = row.get('subscriptions', []) if row else []
    if not jobs:
        return None
    entry = jobs[0]
    sub, _, generation = entry.rpartition(':')
    key = 'clinic-intake:' + sub
    intake = store.get(key)
    if (not intake or intake.get('copy_state') != 'pending'
            or str(intake.get('copy_generation')) != generation):
        _dequeue(store, entry)  # finished or superseded by a newer submission
        return entry
    attempts = intake.get('copy_attempts', 0) + 1
    if attempts > MAX_ATTEMPTS:
        update = {'copy_state': 'failed', 'copy_error': intake.get('copy_error') or 'copy_timeout'}
        try:
            store.put(key, {**intake, **update}, intake['_version'])
            _dequeue(store, entry)
        except Conflict:
            pass
        return entry
    # Record the attempt and move the job back before fetching anything.
    try:
        intake = store.put(key, {**intake, 'copy_attempts': attempts}, intake['_version'])
    except Conflict:
        return entry  # the clinic changed the intake; look again next run
    _rotate(store, entry)
    try:
        data, manifest = copier(intake['host'])
        object_key = intake_copy_key(sub, data)
        put_object(object_key, data)
        update = {'copy_state': 'done', 'copy_key': object_key, 'copy_files': len(manifest['files']),
                  'copy_truncated': manifest['truncated'], 'copy_error': None}
    except CopyFailed as error:
        update = {'copy_state': 'pending' if attempts < MAX_ATTEMPTS else 'failed', 'copy_error': str(error)}
    except Exception:
        update = {'copy_state': 'pending' if attempts < MAX_ATTEMPTS else 'failed', 'copy_error': 'copy_error'}
    try:
        # Conditional on the version written above: a newer submission wins.
        store.transact([Write(key, {**intake, **update, 'copied_at': int(clock())}, intake['_version'])])
    except Conflict:
        return entry
    if update['copy_state'] != 'pending':
        _dequeue(store, entry)
    return entry


def s3_put(client, bucket):
    def put(key, data):
        if not re.fullmatch(r'intake/[0-9a-f]{64}/[0-9a-f]{64}/site\.zip', key):
            raise ValueError('invalid_intake_key')
        try:
            client.put_object(Bucket=bucket, Key=key, Body=data, ContentType='application/zip',
                              ServerSideEncryption='AES256', IfNoneMatch='*')
        except Exception as error:
            # The key names the zip's digest, so an existing object is the same copy.
            code = getattr(error, 'response', {}).get('Error', {}).get('Code')
            if code not in ('PreconditionFailed', '412'):
                raise
    return put
