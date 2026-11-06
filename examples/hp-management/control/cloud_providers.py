"""Bounded provider adapters. Construction performs no network or secret reads."""
from __future__ import annotations
import hashlib
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from bundles import MAX_TRANSPORT, sha256
from executor import IntegrationUnavailable
from github_app import AppConfig, GitHubApp, https_transport


class ProviderError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def google_transport(method, url, headers, data=None, limit=MAX_TRANSPORT):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc not in ('www.googleapis.com', 'oauth2.googleapis.com') or parsed.fragment:
        raise ProviderError('unexpected_google_origin')
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    opener = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    try:
        with opener.open(request, timeout=20) as response:
            status, content = response.status, response.read(limit + 1)
    except urllib.error.HTTPError as error:
        status, content = error.code, error.read(min(limit, 1024 * 1024) + 1)
    if len(content) > limit:
        raise ProviderError('google_response_too_large')
    return status, content


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch('[A-Za-z0-9_-]{10,256}', value):
        raise ProviderError('invalid_drive_identifier')
    return value


class GoogleDrive:
    """Dedicated operator OAuth credentials, distinct from the web login client.

    The secret is a JSON object containing client_id/client_secret/refresh_token.
    The caller supplies an execution guard to every instance, checking the lease
    and membership immediately before each credential-bearing request. for_site
    freezes both expected Google identity fields; every refreshed token is
    verified before any Drive file request, including read-only reconciliation.
    """
    def __init__(self, secret_reference, secret_resolver, guard=None, transport=google_transport,
                 *, expected_subject=None, expected_email=None):
        self.secret_reference, self.secret_resolver = secret_reference, secret_resolver
        self.guard, self.transport = guard, transport
        self.expected_subject, self.expected_email = expected_subject, expected_email

    @staticmethod
    def _identity_binding(subject, email):
        if not isinstance(subject, str) or not subject or len(subject) > 256 or not isinstance(email, str) or not re.fullmatch(r'[^\s@<>,;:]+@[^\s@<>,;:]+\.[^\s@<>,;:]+', email):
            raise ProviderError('operator_identity_not_configured')
        return subject, email.casefold()

    def for_site(self, site, guard):
        if not isinstance(site, dict):
            raise ProviderError('operator_identity_not_configured')
        subject, email = self._identity_binding(site.get('operator_subject'), site.get('operator_email'))
        return GoogleDrive(self.secret_reference, self.secret_resolver, guard, self.transport,
            expected_subject=subject, expected_email=email)

    def for_run(self, guard):
        return GoogleDrive(self.secret_reference, self.secret_resolver, guard, self.transport,
            expected_subject=self.expected_subject, expected_email=self.expected_email)

    def _token(self):
        subject, email = self._identity_binding(self.expected_subject, self.expected_email)
        if not callable(self.guard):
            raise ProviderError('drive_guard_required')
        self.guard()
        secret = self.secret_resolver(self.secret_reference)
        if isinstance(secret, str):
            secret = json.loads(secret)
        if not isinstance(secret, dict) or any(not isinstance(secret.get(k), str) or not secret[k] for k in ('client_id','client_secret','refresh_token')):
            raise ProviderError('invalid_operator_credentials')
        payload = urllib.parse.urlencode({k: secret[k] for k in ('client_id','client_secret','refresh_token')} | {'grant_type': 'refresh_token'}).encode()
        self.guard()
        status, data = self.transport('POST', 'https://oauth2.googleapis.com/token',
            {'Content-Type': 'application/x-www-form-urlencoded'}, payload, 1024 * 1024)
        try:
            result = json.loads(data)
        except ValueError:
            raise ProviderError('oauth_response_invalid') from None
        if status != 200 or not isinstance(result, dict) or not isinstance(result.get('access_token'), str) or not result['access_token'] or any(c in result['access_token'] for c in '\r\n'):
            raise ProviderError('operator_oauth_failed')
        token = result['access_token']
        self.guard()
        status, body = self.transport('GET', 'https://www.googleapis.com/oauth2/v3/userinfo',
            {'Authorization': 'Bearer ' + token}, None, 64 * 1024)
        if status != 200 or len(body) > 64 * 1024:
            raise ProviderError('operator_identity_verification_failed')
        try:
            profile = json.loads(body)
        except ValueError:
            raise ProviderError('operator_identity_verification_failed') from None
        if not isinstance(profile, dict) or profile.get('sub') != subject or not isinstance(profile.get('email'), str) or profile['email'].casefold() != email or profile.get('email_verified') is not True:
            raise ProviderError('operator_google_identity_mismatch')
        return token

    def _request(self, method, path, data=None, content_type=None, missing=False, binary=False):
        if not path.startswith('/drive/v3/') and not path.startswith('/upload/drive/v3/'):
            raise ProviderError('invalid_drive_path')
        self._identity_binding(self.expected_subject, self.expected_email)
        if not callable(self.guard):
            raise ProviderError('drive_guard_required')
        self.guard()
        headers = {'Authorization': 'Bearer ' + self._token()}
        if content_type:
            headers['Content-Type'] = content_type
        self.guard()
        status, body = self.transport(method, 'https://www.googleapis.com' + path, headers, data, MAX_TRANSPORT)
        if status == 404 and missing:
            return None
        if not 200 <= status < 300:
            raise ProviderError('drive_request_failed')
        if binary:
            return body
        try:
            return json.loads(body)
        except ValueError:
            raise ProviderError('drive_response_invalid') from None

    def reserve_id(self):
        result = self._request('GET', '/drive/v3/files/generateIds?count=1&space=drive&type=files')
        ids = result.get('ids')
        if not isinstance(ids, list) or len(ids) != 1:
            raise ProviderError('drive_id_reservation_failed')
        return _identifier(ids[0])

    def _metadata(self, file_id, missing=False):
        return self._request('GET', '/drive/v3/files/' + _identifier(file_id) +
            '?fields=id,parents,trashed,mimeType,size,appProperties&supportsAllDrives=true', missing=missing)

    def read_exact(self, parent_id, file_id):
        parent_id = _identifier(parent_id)
        info = self._metadata(file_id)
        if info.get('id') != file_id or info.get('trashed') is not False or info.get('parents') != [parent_id] or info.get('mimeType') != 'application/zip':
            raise ProviderError('drive_parent_or_type_mismatch')
        try:
            size = int(info['size'])
        except (ValueError, KeyError, TypeError):
            raise ProviderError('drive_size_invalid') from None
        if not 0 <= size <= MAX_TRANSPORT:
            raise ProviderError('drive_size_exceeded')
        body = self._request('GET', '/drive/v3/files/' + _identifier(file_id) + '?alt=media&supportsAllDrives=true', binary=True)
        if len(body) != size:
            raise ProviderError('drive_content_changed')
        # Detect parent/metadata replacement during download, not just before it.
        if self._metadata(file_id) != info:
            raise ProviderError('drive_metadata_changed')
        return body

    def create_exact(self, parent_id, file_id, data, operation_id):
        _identifier(parent_id); _identifier(file_id)
        if not isinstance(data, bytes) or len(data) > MAX_TRANSPORT:
            raise ProviderError('drive_payload_invalid')
        expected = {'operation_id': operation_id, 'sha256': sha256(data)}
        current = self._metadata(file_id, missing=True)
        if current is None:
            metadata = {'id': file_id, 'name': 'workspace-' + operation_id + '.zip',
                'parents': [parent_id], 'mimeType': 'application/zip', 'appProperties': expected}
            boundary = 'hp-' + hashlib.sha256((file_id + operation_id).encode()).hexdigest()
            body = ('--' + boundary + '\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n').encode()
            body += json.dumps(metadata, separators=(',', ':')).encode()
            body += ('\r\n--' + boundary + '\r\nContent-Type: application/zip\r\n\r\n').encode() + data
            body += ('\r\n--' + boundary + '--\r\n').encode()
            # An ambiguous upload is reconciled on retry with the same reserved ID.
            self._request('POST', '/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true',
                body, 'multipart/related; boundary=' + boundary)
            current = self._metadata(file_id)
        if current.get('appProperties') != expected or self.read_exact(parent_id, file_id) != data:
            raise ProviderError('drive_existing_file_mismatch')
        return {'file_id': file_id, 'sha256': sha256(data),
            'download_url': 'https://drive.google.com/file/d/' + file_id + '/view'}


class S3Artifacts:
    def __init__(self, bucket, client, guard=None):
        self.bucket, self.client, self.guard = bucket, client, guard

    def for_run(self, guard):
        return S3Artifacts(self.bucket, self.client, guard)

    @staticmethod
    def _key(key):
        if not isinstance(key, str) or not re.fullmatch(r'artifacts/[a-z][a-z0-9-]{1,62}/[0-9a-f]{64}/site\.zip', key):
            raise ProviderError('invalid_artifact_key')
        return key

    def put_exact(self, key, data):
        self._key(key)
        if not isinstance(data, bytes) or len(data) > MAX_TRANSPORT or key.split('/')[2] != sha256(data):
            raise ProviderError('artifact_digest_mismatch')
        self.guard()
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=data,
                IfNoneMatch='*', ServerSideEncryption='AES256', ContentType='application/zip',
                Metadata={'sha256': sha256(data)})
        except Exception as error:
            code = getattr(error, 'response', {}).get('Error', {}).get('Code')
            if code not in ('PreconditionFailed', '412'):
                raise ProviderError('artifact_write_unknown') from None
        if self.get_exact(key, sha256(data)) != data:
            raise ProviderError('artifact_readback_mismatch')
        return {'key': key, 'sha256': sha256(data)}

    def get_exact(self, key, digest):
        self._key(key); self.guard()
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        if not 0 <= response['ContentLength'] <= MAX_TRANSPORT:
            raise ProviderError('artifact_size_exceeded')
        stream = response['Body']
        try:
            data = stream.read(MAX_TRANSPORT + 1)
        finally:
            stream.close()
        if len(data) != response['ContentLength'] or sha256(data) != digest:
            raise ProviderError('artifact_digest_mismatch')
        return data


def github_factory(secret_reference, secret_resolver):
    """Site binding selects exact app/install/repository; secret contains key only.

    No Actions/PR permissions are silently added to the existing contents token.
    A separate reviewed validator adapter is required for preview admission.
    """
    def create(site, guard):
        def transport(method, url, headers, body):
            guard()
            return https_transport(method, url, headers, body)
        config = AppConfig(app_id=site['github_app_id'], installation_id=site['github_installation_id'],
            repository_id=site['github_repository_id'], owner=site['github_owner'],
            repository=site['github_repository'], private_key_secret_ref=secret_reference,
            allowed_branches=('dev', 'main'))
        def key(reference):
            value = secret_resolver(reference)
            if isinstance(value, str):
                value = json.loads(value)
            if value.get('app_id') != site['github_app_id'] or value.get('installation_id', value.get('install_id')) != site['github_installation_id']:
                raise ProviderError('github_secret_binding_mismatch')
            return value['private_key']
        return GitHubApp(config, key, transport=transport, permissions={
            'contents': 'write', 'pull_requests': 'write', 'checks': 'read', 'actions': 'read'})
    return create


class UnconfiguredValidation:
    def validate(self, *args):
        raise IntegrationUnavailable('reviewed_github_validation_adapter_required')


class DisabledPublisher:
    def publish(self, *args):
        raise IntegrationUnavailable('publication_not_enabled')
