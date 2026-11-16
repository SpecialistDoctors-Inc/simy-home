import base64
import hashlib
import unittest
from unittest.mock import Mock

import test_clinic_onboarding as clinic
from licensing import LicenseUnavailable
from plugin_distribution import PluginDistribution


class PluginDistributionTest(unittest.TestCase):
    def test_package_checksum_and_version_are_pinned_in_private_download(self):
        digest = hashlib.sha256(b'package').hexdigest()
        client = Mock()
        client.head_object.return_value = {'VersionId': 'fixed-version', 'ContentLength': 7,
            'ChecksumSHA256': base64.b64encode(bytes.fromhex(digest)).decode()}
        client.generate_presigned_url.return_value = 'https://download.example.test/private-package'
        package = PluginDistribution(client, 'private-artifacts', {'object_key':
            'plugins/hp-local-editor/0.3.13/hp-local-editor-darwin-arm64.zip', 'sha256': digest})
        self.assertTrue(package.download().startswith('https://'))
        self.assertEqual(client.generate_presigned_url.call_args.kwargs['Params']['VersionId'], 'fixed-version')
        client.head_object.return_value['ChecksumSHA256'] = 'wrong'
        with self.assertRaises(LicenseUnavailable): package.download()

    def test_paid_google_session_is_required_before_the_package_is_signed(self):
        h = clinic.ClinicOnboardingTest(); h.setUp(); h.sign_in()
        callback = Mock(return_value='https://download.example.test/private-package')
        h.onboarding.plugin_download = callback
        result = h.call('GET', '/start/plugin', {'session_id': clinic.SESSION}, cookie='')
        self.assertEqual(result['statusCode'], 403)
        callback.assert_not_called()
        result = h.call('GET', '/start/plugin', {'session_id': clinic.SESSION})
        self.assertEqual(result['statusCode'], 303)
        callback.assert_called_once()


if __name__ == '__main__': unittest.main()
