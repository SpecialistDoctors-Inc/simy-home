"""Paid-session download of an immutable, checksum-verified native package."""
import base64
import re
from licensing import LicenseUnavailable
from publisher import ACCOUNT


class PluginDistribution:
    def __init__(self, client, bucket, config):
        self.client, self.bucket, self.config = client, bucket, config

    def download(self):
        key, checksum = self.config.get('object_key'), self.config.get('sha256')
        if (not isinstance(key, str) or not re.fullmatch(
                r'plugins/hp-local-editor/[0-9]+\.[0-9]+\.[0-9]+/hp-local-editor-darwin-arm64\.zip', key)
                or not isinstance(checksum, str) or not re.fullmatch('[0-9a-f]{64}', checksum)):
            raise LicenseUnavailable('plugin_distribution_unavailable')
        head = self.client.head_object(Bucket=self.bucket, Key=key, ExpectedBucketOwner=ACCOUNT, ChecksumMode='ENABLED')
        if (head.get('ChecksumSHA256') != base64.b64encode(bytes.fromhex(checksum)).decode()
                or not head.get('VersionId') or not 0 < head.get('ContentLength', 0) <= 100 * 1024 * 1024):
            raise LicenseUnavailable('plugin_distribution_unverified')
        return self.client.generate_presigned_url('get_object', Params={'Bucket': self.bucket, 'Key': key,
            'VersionId': head['VersionId'], 'ResponseContentDisposition': 'attachment; filename="hp-local-editor-mac.zip"',
            'ResponseContentType': 'application/zip'}, ExpiresIn=300)
