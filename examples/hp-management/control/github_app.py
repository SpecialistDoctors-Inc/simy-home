"""Repository-scoped GitHub App adapter. No customer OAuth or shell execution.

Transport: callable(method, url, headers, JSON body) -> (status, JSON object).
Secret resolver: callable(secret_reference) -> PEM private key. The default HTTPS
transport never follows redirects and limits response sizes/timeouts.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass

try:
    from .bundles import MAX_FILE, MAX_FILES, MAX_TOTAL, validate_files, validate_path
except ImportError:
    from bundles import MAX_FILE, MAX_FILES, MAX_TOTAL, validate_files, validate_path


class GitHubError(RuntimeError):
    pass


class StaleHead(GitHubError):
    pass


class AmbiguousWrite(GitHubError):
    """Caller must retain its operation and reconcile, never create a new intent."""


@dataclass(frozen=True)
class AppConfig:
    app_id: int
    installation_id: int
    repository_id: int
    owner: str
    repository: str
    private_key_secret_ref: str
    allowed_branches: tuple[str, ...] = ('dev', 'main')
    author_name: str = 'SIMY HP'
    author_email: str = 'hp@simy.one'


@dataclass(frozen=True)
class SourceSnapshot:
    commit: str
    files: dict[str, bytes]


@dataclass(frozen=True)
class CommitResult:
    commit: str
    tree: str
    replayed: bool


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def https_transport(method, url, headers, body):
    if not url.startswith('https://api.github.com/'):
        raise GitHubError('unexpected GitHub endpoint')
    payload = None if body is None else json.dumps(body, separators=(',', ':')).encode()
    request = urllib.request.Request(url, data=payload, headers=headers, method=method)
    opener = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    try:
        with opener.open(request, timeout=20) as response:
            status = response.status
            content = response.read(20 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as error:
        status = error.code
        content = error.read(1024 * 1024)
    if len(content) > 20 * 1024 * 1024:
        raise GitHubError('GitHub response too large')
    try:
        return status, json.loads(content) if content else {}
    except (UnicodeError, ValueError) as error:
        raise GitHubError('invalid GitHub response') from error


def _sign(claims, private_key):
    import jwt
    return jwt.encode(claims, private_key, algorithm='RS256')


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value):
        raise GitHubError('invalid Git object id')
    return value


def _git_hash(kind, content):
    return hashlib.sha1(kind.encode() + b' ' + str(len(content)).encode() + b'\0' + content).hexdigest()


class GitHubApp:
    def __init__(self, config: AppConfig, secret_resolver, transport=None, clock=time.time, signer=None, permissions=None):
        for value in (config.app_id, config.installation_id, config.repository_id):
            if type(value) is not int or value <= 0:
                raise GitHubError('positive app, installation and repository IDs required')
        if not re.fullmatch('[A-Za-z0-9_.-]+', config.owner) or not re.fullmatch('[A-Za-z0-9_.-]+', config.repository) or not config.private_key_secret_ref:
            raise GitHubError('invalid repository configuration')
        if any(c in config.author_name + config.author_email for c in '\r\n\0<>'):
            raise GitHubError('invalid trusted author')
        self.permissions = dict({'contents': 'write'} if permissions is None else permissions)
        approved = {'contents': 'write', 'pull_requests': 'write', 'checks': 'read', 'actions': 'read'}
        if self.permissions.get('contents') != 'write' or any(approved.get(key) != value for key, value in self.permissions.items()):
            raise GitHubError('unapproved installation token permissions')
        self.config, self.secret_resolver = config, secret_resolver
        self.transport, self.clock, self.signer = transport or https_transport, clock, signer or _sign
        self._cached_token = None
        self._token_expiry = 0
        self.prefix = '/repos/' + config.owner + '/' + config.repository

    def _branch(self, branch):
        if not isinstance(branch, str):
            raise GitHubError('branch not allowed')
        workspace = re.fullmatch(r'codex/hp/([0-9a-f-]{36})', branch)
        if workspace:
            try:
                if str(uuid.UUID(workspace[1])) == workspace[1]:
                    return urllib.parse.quote(branch, safe='/')
            except ValueError:
                pass
        if branch in self.config.allowed_branches and re.fullmatch('[A-Za-z0-9][A-Za-z0-9/_-]*', branch) and '..' not in branch:
            return urllib.parse.quote(branch, safe='/')
        raise GitHubError('branch not allowed')

    def _token(self):
        now = self.clock()
        if self._cached_token and self._token_expiry > now + 60:
            return self._cached_token
        claims = {'iat': int(now) - 60, 'exp': int(now) + 480, 'iss': str(self.config.app_id)}
        private_key = self.secret_resolver(self.config.private_key_secret_ref)
        app_token = self.signer(claims, private_key)
        status, result = self.transport('POST', 'https://api.github.com/app/installations/' + str(self.config.installation_id) + '/access_tokens', self._headers(app_token), {'repository_ids': [self.config.repository_id], 'permissions': self.permissions})
        if status != 201 or not isinstance(result, dict):
            raise GitHubError('installation token request failed')
        repositories = result.get('repositories')
        if not isinstance(repositories, list) or len(repositories) != 1 or repositories[0].get('id') != self.config.repository_id or repositories[0].get('full_name', '').casefold() != (self.config.owner + '/' + self.config.repository).casefold():
            raise GitHubError('installation token repository scope mismatch')
        permissions = result.get('permissions', {})
        if not isinstance(permissions, dict):
            raise GitHubError('installation token permission mismatch')
        if {k: v for k, v in permissions.items() if k != 'metadata'} != self.permissions or permissions.get('metadata', 'read') != 'read':
            raise GitHubError('installation token permission mismatch')
        try:
            expiry = dt.datetime.fromisoformat(result['expires_at'].replace('Z', '+00:00')).timestamp()
        except (ValueError, KeyError, AttributeError):
            raise GitHubError('invalid installation token expiry') from None
        if not now + 60 < expiry <= now + 3660 or not isinstance(result.get('token'), str) or not result['token']:
            raise GitHubError('expired or overlong installation token')
        self._cached_token, self._token_expiry = result['token'], expiry
        return self._cached_token

    @staticmethod
    def _headers(token):
        return {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': 'application/json', 'User-Agent': 'simy-hp-control'}

    def _request(self, method, path, body=None, statuses=(200,)):
        # Every credential-bearing request remains on the fixed API origin.
        if not path.startswith(self.prefix + '/'):
            raise GitHubError('cross-repository request rejected')
        status, result = self.transport(method, 'https://api.github.com' + path, self._headers(self._token()), body)
        if status not in statuses or not isinstance(result, dict):
            raise GitHubError('GitHub request failed: ' + str(status))
        return result

    def head(self, branch):
        branch = self._branch(branch)
        result = self._request('GET', self.prefix + '/git/ref/heads/' + branch)
        obj = result.get('object', {})
        if obj.get('type') != 'commit':
            raise GitHubError('branch does not reference a commit')
        return _sha(obj.get('sha'))

    def ensure_workspace_branch(self, workspace_uuid, base_commit):
        """Create one exact workspace ref, or reconcile a prior identical create.

        An existing advanced workspace is intentionally rejected: the caller must
        use its durable ownership record rather than claim an arbitrary branch.
        """
        branch = 'codex/hp/' + workspace_uuid
        branch_path = self._branch(branch)
        base_commit = _sha(base_commit)
        url = 'https://api.github.com' + self.prefix + '/git/ref/heads/' + branch_path
        status, result = self.transport('GET', url, self._headers(self._token()), None)
        if status == 200:
            if result.get('object', {}).get('type') != 'commit' or result.get('object', {}).get('sha') != base_commit:
                raise StaleHead('workspace branch already has a different head')
            return branch
        if status != 404:
            raise GitHubError('workspace reference lookup failed')
        self._commit(base_commit)
        try:
            self._request('POST', self.prefix + '/git/refs', {'ref': 'refs/heads/' + branch, 'sha': base_commit}, (201,))
        except Exception as error:
            try:
                current = self.head(branch)
            except Exception:
                raise AmbiguousWrite('workspace branch creation unknown; retry same workspace') from error
            if current != base_commit:
                raise StaleHead('workspace branch already has a different head') from error
            return branch
        if self.head(branch) != base_commit:
            raise StaleHead('workspace branch changed during creation')
        return branch

    def _commit(self, commit):
        return self._request('GET', self.prefix + '/git/commits/' + _sha(commit))

    def _tree(self, sha):
        result = self._request('GET', self.prefix + '/git/trees/' + _sha(sha) + '?recursive=1')
        if result.get('truncated') is not False or not isinstance(result.get('tree'), list):
            raise GitHubError('incomplete source tree')
        return result['tree']

    def read_site(self, branch):
        commit = self.head(branch)
        return self.read_site_at(commit)

    def read_site_at(self, commit):
        commit = _sha(commit)
        obj = self._commit(commit)
        records = self._tree(obj.get('tree', {}).get('sha'))
        files, seen, total = {}, set(), 0
        for entry in records:
            path = entry.get('path', '')
            if not path.startswith('site/') or entry.get('type') == 'tree':
                continue
            relative = validate_path(path[5:])
            if relative.casefold() in seen or entry.get('type') != 'blob' or entry.get('mode') != '100644':
                raise GitHubError('unsafe source tree entry')
            seen.add(relative.casefold())
            size = entry.get('size')
            if type(size) is not int or not 0 <= size <= MAX_FILE or len(seen) > MAX_FILES:
                raise GitHubError('source limits exceeded')
            total += size
            if total > MAX_TOTAL:
                raise GitHubError('source limits exceeded')
            blob = self._request('GET', self.prefix + '/git/blobs/' + _sha(entry.get('sha')))
            try:
                if blob.get('encoding') != 'base64':
                    raise ValueError()
                content = base64.b64decode(''.join(blob['content'].split()), validate=True)
            except (ValueError, KeyError, TypeError):
                raise GitHubError('invalid blob encoding') from None
            if len(content) != size or _git_hash('blob', content) != entry['sha']:
                raise GitHubError('source blob hash mismatch')
            files[relative] = content
        return SourceSnapshot(commit, validate_files(files))

    def commit_site(self, branch, expected_head, files, message, operation_id, operation_created_at):
        branch_path = self._branch(branch)
        expected_head = _sha(expected_head)
        validate_files(files)
        try:
            if str(uuid.UUID(operation_id)) != operation_id:
                raise ValueError()
        except (ValueError, AttributeError):
            raise GitHubError('invalid operation ID') from None
        if not isinstance(message, str) or not message or len(message) > 300 or any(ord(c) < 32 or ord(c) == 127 for c in message):
            raise GitHubError('commit title must be a bounded single line')
        try:
            created_at = dt.datetime.fromisoformat(operation_created_at.replace('Z', '+00:00'))
            if created_at.tzinfo is None:
                raise ValueError()
            timestamp = created_at.astimezone(dt.timezone.utc).isoformat(timespec='seconds')
        except (ValueError, AttributeError):
            raise GitHubError('persisted operation creation timestamp required') from None
        parent = self._commit(expected_head)
        root_tree = _sha(parent.get('tree', {}).get('sha'))
        original = self.read_site_at(expected_head).files
        entries = []
        for path in sorted(original.keys() | files.keys()):
            if original.get(path) == files.get(path):
                continue
            if path not in files:
                entries.append({'path': 'site/' + path, 'mode': '100644', 'type': 'blob', 'sha': None})
            else:
                content = files[path]
                expected_blob = _git_hash('blob', content)
                result = self._request('POST', self.prefix + '/git/blobs', {'content': base64.b64encode(content).decode(), 'encoding': 'base64'}, (201,))
                if result.get('sha') != expected_blob:
                    raise GitHubError('created blob hash mismatch')
                entries.append({'path': 'site/' + path, 'mode': '100644', 'type': 'blob', 'sha': expected_blob})
        if not entries:
            if self.head(branch) != expected_head:
                raise StaleHead('draft branch has advanced')
            return CommitResult(expected_head, root_tree, False)
        # All Git object writes are content addressed; retries create the same objects.
        tree = self._request('POST', self.prefix + '/git/trees', {'base_tree': root_tree, 'tree': entries}, (201,))
        tree_sha = _sha(tree.get('sha'))
        identity = {'name': self.config.author_name, 'email': self.config.author_email, 'date': timestamp}
        commit_message = message + '\n\nHP-Operation-Id: ' + operation_id
        result = self._request('POST', self.prefix + '/git/commits', {'message': commit_message, 'tree': tree_sha, 'parents': [expected_head], 'author': identity, 'committer': identity}, (201,))
        commit_sha = _sha(result.get('sha'))
        current = self.head(branch)
        if current == commit_sha:
            return CommitResult(commit_sha, tree_sha, True)
        if current != expected_head:
            raise StaleHead('draft branch has advanced')
        try:
            self._request('PATCH', self.prefix + '/git/refs/heads/' + branch_path, {'sha': commit_sha, 'force': False})
        except Exception as error:
            # A connection loss or 409/422 may occur after GitHub accepted the write.
            try:
                current = self.head(branch)
            except Exception:
                raise AmbiguousWrite('branch result unknown; retry same operation') from error
            if current == commit_sha:
                return CommitResult(commit_sha, tree_sha, True)
            if current != expected_head:
                raise StaleHead('draft branch changed during update') from error
            raise AmbiguousWrite('branch did not acknowledge save; retry same operation') from error
        if self.head(branch) != commit_sha:
            raise AmbiguousWrite('branch advanced after save; reconcile same operation')
        return CommitResult(commit_sha, tree_sha, False)

    def reconcile_site_commit(self, branch, expected_head, file_hashes, message, operation_id, operation_created_at):
        """Read-only recovery of a known deterministic commit intent.

        None is unresolved; it never authorizes creating another commit. Hashes
        and trusted metadata are persisted before the original write begins.
        """
        current = self.head(branch)
        obj = self._commit(current)
        source = self.read_site_at(current)
        if {p: hashlib.sha256(v).hexdigest() for p, v in source.files.items()} != file_hashes:
            return None
        if current == expected_head:
            return {'commit': current}  # A no-op save has no external Git effect.
        timestamp = dt.datetime.fromisoformat(operation_created_at.replace('Z', '+00:00')).astimezone(dt.timezone.utc)
        parents = obj.get('parents', [])
        if len(parents) != 1 or parents[0].get('sha') != expected_head or obj.get('message') != message + '\n\nHP-Operation-Id: ' + operation_id:
            return None
        for field in ('author', 'committer'):
            identity = obj.get(field, {})
            try:
                actual = dt.datetime.fromisoformat(identity['date'].replace('Z', '+00:00')).astimezone(dt.timezone.utc)
            except (KeyError, ValueError, AttributeError):
                return None
            if actual != timestamp or identity.get('name') != self.config.author_name or identity.get('email') != self.config.author_email:
                return None
        return {'commit': current}
