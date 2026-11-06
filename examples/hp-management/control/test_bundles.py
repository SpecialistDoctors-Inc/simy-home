import io
import json
import stat
import unittest
import zipfile

from bundles import BundleError, build_snapshot, reconcile, sha256, validate_changes, validate_snapshot

SITE = 'example'
WORKSPACE = '12345678-1234-4234-8234-123456789abc'
OPERATION = '23456789-1234-4234-8234-123456789abc'
BASE = 'a' * 40


def archive(manifest, payload=(), special=None):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('manifest.json', json.dumps(manifest))
        for name, value in payload:
            entry = zipfile.ZipInfo(name)
            entry.external_attr = ((special or stat.S_IFREG) | 0o644) << 16
            z.writestr(entry, value)
    return out.getvalue()


class BundlesTest(unittest.TestCase):
    def setUp(self):
        self.files = {'index.html': b'base', 'style.css': b'body{}'}
        self.snapshot = validate_snapshot(build_snapshot(SITE, WORKSPACE, BASE, self.files), SITE)

    def changes(self, records, payload=()):
        manifest = {'schema_version': 1, 'kind': 'changes', 'site_id': SITE, 'workspace_id': WORKSPACE, 'base_commit': BASE, 'operation_id': OPERATION, 'changes': records}
        return archive(manifest, payload)

    def test_deterministic_snapshot(self):
        self.assertEqual(build_snapshot(SITE, WORKSPACE, BASE, self.files), build_snapshot(SITE, WORKSPACE, BASE, dict(reversed(list(self.files.items())))))
        self.assertEqual(self.snapshot.files, self.files)

    def test_change_applies_to_authoritative_base(self):
        result = validate_changes(self.changes([{'path': 'index.html', 'action': 'modify', 'base_sha256': sha256(b'base'), 'sha256': sha256(b'new'), 'size': 3}], [('files/index.html', b'new')]), self.snapshot)
        self.assertEqual(result.candidate_files, {'index.html': b'new', 'style.css': b'body{}'})
        self.assertEqual(result.manifest['operation_id'], OPERATION)

    def test_wrong_base_rejected(self):
        data = self.changes([{'path': 'index.html', 'action': 'modify', 'base_sha256': 'f' * 64, 'sha256': sha256(b'new'), 'size': 3}], [('files/index.html', b'new')])
        with self.assertRaises(BundleError):
            validate_changes(data, self.snapshot)

    def test_delete_has_no_payload_and_index_required(self):
        record = {'path': 'style.css', 'action': 'delete', 'base_sha256': sha256(b'body{}'), 'sha256': None, 'size': 0}
        result = validate_changes(self.changes([record]), self.snapshot)
        self.assertEqual(result.candidate_files, {'index.html': b'base'})
        with self.assertRaises(BundleError):
            validate_changes(self.changes([record], [('files/style.css', b'')]), self.snapshot)
        record.update(path='index.html', base_sha256=sha256(b'base'))
        with self.assertRaises(BundleError):
            validate_changes(self.changes([record]), self.snapshot)

    def test_unsafe_paths_and_collision(self):
        for path in ('../a.html', '/a.html', 'a\\b.html', '.hp/a.html', '.github/a.js', 'node_modules/a.js', 'package.json', 'a:b.html', 'e\u0301.html', 'config.json'):
            with self.subTest(path=path), self.assertRaises(BundleError):
                build_snapshot(SITE, WORKSPACE, BASE, {'index.html': b'', path: b''})
        with self.assertRaises(BundleError):
            build_snapshot(SITE, WORKSPACE, BASE, {'index.html': b'', 'A.html': b'', 'a.html': b''})

    def test_hash_extra_fields_payload_symlink(self):
        manifest = dict(self.snapshot.manifest)
        for data in (archive(manifest, [('files/index.html', b'wrong'), ('files/style.css', b'body{}')]), archive(manifest, [('files/index.html', b'base'), ('files/style.css', b'body{}'), ('files/extra.txt', b'extra')]), archive(manifest, [('files/index.html', b'base'), ('files/style.css', b'body{}')], stat.S_IFLNK), archive(dict(manifest, token='no'), [('files/index.html', b'base'), ('files/style.css', b'body{}')])):
            with self.assertRaises(BundleError):
                validate_snapshot(data)

    def test_reconcile_three_way_and_deletion_conflict(self):
        base = {'index.html': b'base', 'a.txt': b'a', 'b.txt': b'b'}
        user = dict(base, **{'a.txt': b'user'})
        remote = dict(base, **{'b.txt': b'remote'})
        result = reconcile(base, user, remote)
        self.assertEqual(result.conflicts, ())
        self.assertEqual(result.files['a.txt'], b'user')
        self.assertEqual(result.files['b.txt'], b'remote')
        del user['b.txt']
        self.assertEqual(reconcile(base, user, remote).conflicts, ('b.txt',))
        self.assertEqual(reconcile(base, remote, remote).files, remote)


if __name__ == '__main__':
    unittest.main()
