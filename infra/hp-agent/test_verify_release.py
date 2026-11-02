import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('verify_release', Path(__file__).with_name('verify-release.py'))
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.files = {}
        for folder, names in {
            'infra/hp-agent': ['verify-release.py', 'install-runtime.sh', 'restore-bundle.py', 'health.py'],
            'examples/hp-management/runner': ['agent.py', 'Dockerfile', 'requirements.txt', 'seccomp-codex.json', 'apparmor-codex.profile'],
        }.items():
            for name in names:
                path = self.root/folder/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(name)
                self.files[folder+'/'+name] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.payload = {'source_sha': 'a'*40, 'image': 'repo@sha256:'+'b'*64, 'files': self.files}
        self.manifest = self.root/'manifest.json'
        self.write_manifest()

    def write_manifest(self):
        self.manifest.write_text(json.dumps(self.payload))
        self.digest = hashlib.sha256(self.manifest.read_bytes()).hexdigest()

    def verify(self, **changes):
        args = dict(root=self.root, manifest=self.manifest, expected_hash=self.digest,
                    source_sha=self.payload['source_sha'], image=self.payload['image'])
        args.update(changes)
        return release.verify(**args)

    def test_release_and_image_match(self):
        value = self.verify()
        actual = {name: self.files['examples/hp-management/runner/'+name]
                  for name in ['agent.py', 'requirements.txt']}
        release.verify_image(value, actual)
        actual['agent.py'] = 'c'*64
        with self.assertRaisesRegex(ValueError, 'image_content_mismatch'):
            release.verify_image(value, actual)

    def test_pinned_identity_and_bytes_required(self):
        for args in [{'expected_hash':'c'*64}, {'source_sha':'c'*40}, {'image':'wrong-image'}]:
            with self.subTest(args=args), self.assertRaises(ValueError): self.verify(**args)
        (self.root/'infra/hp-agent/install-runtime.sh').write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'release_file_mismatch'): self.verify()

    def test_escape_symlink_and_missing_file_rejected(self):
        self.files['../outside'] = 'd'*64
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'unsafe_release_path'): self.verify()
        del self.files['../outside']
        self.write_manifest()
        file = self.root/'infra/hp-agent/health.py'
        file.unlink()
        file.symlink_to(self.root/'infra/hp-agent/verify-release.py')
        with self.assertRaisesRegex(ValueError, 'unsafe_release_file'): self.verify()

    def test_marker_bound_to_same_release(self):
        marker = self.root/'migration.json'
        value = {'manifest_sha256': self.digest, 'source_sha': self.payload['source_sha'],
                 'image': self.payload['image'], 'database_integrity':'ok', 'pending_effects':0,'active_jobs':0}
        marker.write_text(json.dumps(value))
        release.verify_migration(marker, self.digest, value['source_sha'], value['image'])
        value['image'] = 'old-image'
        marker.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'migration_release_mismatch'):
            release.verify_migration(marker, self.digest, value['source_sha'], self.payload['image'])


if __name__ == '__main__': unittest.main()
