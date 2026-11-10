"""Owned, immutable file transport using the existing artifact bucket.

URLs stay in private MCP metadata. No customer Drive credentials are required.
Preparation transfers files only; it does not admit a save, preview or publication.
"""
import base64
import re
from bundles import MAX_TRANSPORT
from service import Rejected, digest, exact, uuid
from store import Write, Check


PREFIX = 'hp-upload-'


def upload_binding(service, claims, body):
    record = service.store.get('transfer:' + uuid(body['operation_id']))
    expected = {name: body[name] for name in
        ('operation_id', 'site_id', 'workspace_id', 'base_commit', 'bundle_sha256')}
    if (not record or any(record.get(k) != v for k, v in expected.items()) or
            record.get('subject') != claims['sub'] or
            body['bundle_file_id'] != PREFIX + body['operation_id']):
        raise Rejected('transfer_access_denied')
    member, site = service.authorized(claims, body['site_id'], 'edit')
    if (record['member_version'] != member['_version'] or
            record['site_config_version'] != site['config_version'] or
            not site.get('direct_transfer_enabled')):
        raise Rejected('transfer_binding_changed')
    return record


class Transfers:
    def __init__(self, service, bucket, s3):
        self.service, self.bucket, self.s3 = service, bucket, s3

    def download(self, claims, site_id, workspace_id):
        _, site = self.service.authorized(claims, site_id, 'edit')
        workspace = self.service.workspace(claims, site_id, workspace_id)
        key = workspace.get('snapshot_artifact_key')
        expected = 'artifacts/' + site_id + '/' + digest(workspace.get('snapshot_sha256')) + '/site.zip'
        if not site.get('direct_transfer_enabled') or key != expected:
            raise Rejected('direct_transfer_unavailable')
        # Recheck the principal and workspace at the credential issuance boundary.
        self.service.workspace(claims, site_id, workspace_id)
        url = self.s3.generate_presigned_url('get_object', Params={
            'Bucket': self.bucket, 'Key': key}, ExpiresIn=300)
        return ({'site_id': site_id, 'workspace_id': workspace_id,
                 'snapshot_sha256': workspace['snapshot_sha256'], 'expires_in': 300},
                {'method': 'GET', 'url': url, 'headers': {}})

    def prepare_upload(self, claims, body):
        exact(body, ('operation_id', 'site_id', 'workspace_id', 'base_commit', 'bundle_sha256', 'size'))
        operation = uuid(body['operation_id'])
        member, site = self.service.authorized(claims, body['site_id'], 'edit')
        workspace = self.service.workspace(claims, body['site_id'], body['workspace_id'])
        if not site.get('direct_transfer_enabled'):
            raise Rejected('direct_transfer_unavailable')
        if workspace.get('head_commit') != body['base_commit']:
            raise Rejected('workspace_changed')
        digest(body['bundle_sha256'])
        if not isinstance(body['size'], str) or not re.fullmatch('[1-9][0-9]{0,8}', body['size']):
            raise Rejected('invalid_transfer_size')
        size = int(body['size'])
        if size > MAX_TRANSPORT:
            raise Rejected('invalid_transfer_size')
        key = 'artifacts/' + body['site_id'] + '/' + body['bundle_sha256'] + '/site.zip'
        record = {**body, 'subject': claims['sub'], 'key': key,
                  'member_version': member['_version'], 'site_config_version': site['config_version']}
        old = self.service.store.get('transfer:' + operation)
        version_fields = {'member_version', 'site_config_version', '_version'}
        if old:
            if ({k: v for k, v in old.items() if k not in version_fields} !=
                    {k: v for k, v in record.items() if k not in version_fields}):
                raise Rejected('transfer_id_conflict')
        changed = old and any(old[k] != record[k] for k in ('member_version', 'site_config_version'))
        if not old or changed:
            # Before save admission, a still-authorized editor can refresh this
            # same immutable transfer after an ordinary membership/config update.
            # Never change the binding of work that has already been admitted.
            if self.service.store.get('operation:' + operation):
                raise Rejected('transfer_binding_changed')
            self.service.store.transact([
                Write('transfer:' + operation, record, old['_version'] if old else None),
                Check('operation:' + operation, None),
                Check('principal:' + claims['sub'], member['_version']),
                Check('site:' + body['site_id'], site['_version']),
                Check('workspace:' + body['workspace_id'], workspace['_version']),
            ])
        binding = {**body, 'bundle_file_id': PREFIX + operation}
        upload_binding(self.service, claims, binding)
        checksum = base64.b64encode(bytes.fromhex(body['bundle_sha256'])).decode('ascii')
        headers = {'Content-Type': 'application/zip', 'Content-Length': str(size),
                   'x-amz-checksum-sha256': checksum, 'If-None-Match': '*',
                   'x-amz-server-side-encryption': 'AES256'}
        url = self.s3.generate_presigned_url('put_object', Params={
            'Bucket': self.bucket, 'Key': key, 'ContentType': 'application/zip',
            'ContentLength': size, 'ChecksumSHA256': checksum,
            'IfNoneMatch': '*', 'ServerSideEncryption': 'AES256'}, ExpiresIn=300)
        return ({'operation_id': operation, 'bundle_file_id': PREFIX + operation,
                 'bundle_sha256': body['bundle_sha256'], 'size': size, 'expires_in': 300},
                {'method': 'PUT', 'url': url, 'headers': headers})
