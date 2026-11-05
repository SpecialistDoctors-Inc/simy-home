import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from package_site import package
from validate_site import ValidationError, validate

OPERATION = '23456789-1234-4234-8234-123456789abc'
COMMIT = 'a' * 40
HTML = '<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="A page"><title>Example</title></head><body><h1 id="top">Example</h1>{}</body></html>'


class StaticSiteTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.site = self.root / 'site'
        self.site.mkdir()
        self.put('index.html', HTML.format('<a href="/about/">About</a><img src="/images/photo.png"><link rel="stylesheet" href="style.css">'))
        self.put('about/index.html', HTML.format('<a href="/index.html#top">Home</a>'))
        self.put('images/photo.png', b'image bytes')
        self.put('style.css', 'body { background-image: url("images/photo.png"); }')

    def tearDown(self):
        self.temporary.cleanup()

    def put(self, name, data):
        path = self.site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode() if isinstance(data, str) else data)

    def test_pages_and_assets_are_valid(self):
        self.assertEqual(len(validate(self.site)), 4)

    def test_missing_asset_link_and_anchor_are_rejected(self):
        for reference in ('missing.html', '/images/missing.png', 'index.html#missing', '../../outside.html'):
            with self.subTest(reference=reference):
                self.put('index.html', HTML.format('<a href="' + reference + '">Broken</a>'))
                with self.assertRaises(ValidationError):
                    validate(self.site)

    def test_missing_css_asset_is_rejected(self):
        self.put('style.css', 'body { background-image: url("missing.png"); }')
        with self.assertRaises(ValidationError):
            validate(self.site)

    def test_paths_limits_and_reserved_metadata(self):
        for name in ('vercel.json', 'version.json', '.git/config.txt', 'node_modules/x.js', 'server.js', 'webpack.config.js'):
            with self.subTest(name=name):
                self.put(name, '{}')
                with self.assertRaises(ValidationError):
                    validate(self.site)
                (self.site / name).unlink()
                parent = (self.site / name).parent
                if parent != self.site:
                    parent.rmdir()
        # Exercise collision handling even on a case-insensitive developer disk.
        with mock.patch('validate_site.os.walk', return_value=[(str(self.site), [], ['index.html']), (str(self.site / 'images'), [], ['photo.png', 'Photo.png'])]):
            with self.assertRaises(ValidationError):
                validate(self.site)
        (self.site / 'images/link.png').symlink_to(self.site / 'images/photo.png')
        with self.assertRaises(ValidationError):
            validate(self.site)

    def test_metadata_and_index_required(self):
        self.put('index.html', '<html><title>Missing metadata</title></html>')
        with self.assertRaises(ValidationError):
            validate(self.site)
        (self.site / 'index.html').unlink()
        with self.assertRaises(ValidationError):
            validate(self.site)

    def test_minimal_error_page_keeps_main_page_metadata_requirements(self):
        self.put('error.html', '<!doctype html><html lang="ja"><meta charset="utf-8"><title>Not found</title><a href="/">Home</a></html>')
        validate(self.site)
        self.put('error.html', '<!doctype html><html lang="ja"><title>Missing charset</title></html>')
        with self.assertRaises(ValidationError):
            validate(self.site)
        (self.site / 'error.html').unlink()
        self.put('index.html', '<!doctype html><html lang="ja"><meta charset="utf-8"><title>Main page needs SEO metadata</title></html>')
        with self.assertRaises(ValidationError):
            validate(self.site)

    @unittest.skipUnless(shutil.which('node'), 'Node required for real syntax-only check')
    def test_javascript_is_checked_never_executed(self):
        marker = self.root / 'executed'
        self.put('script.js', 'import fs from "node:fs"; fs.writeFileSync(' + json.dumps(str(marker)) + ', "unsafe"); export const ok = true;')
        validate(self.site)
        self.assertFalse(marker.exists())
        self.put('script.js', 'function invalid( {')
        with self.assertRaises(ValidationError):
            validate(self.site)
        self.put('script.js', '')
        self.put('index.html', HTML.format('<script>function invalid( {</script>'))
        with self.assertRaises(ValidationError):
            validate(self.site)

    def test_deterministic_artifact_and_readback_binding(self):
        manifest = package(self.site, self.root / 'first', OPERATION, COMMIT)
        package(self.site, self.root / 'second', OPERATION, COMMIT)
        artifact = (self.root / 'first/site.zip').read_bytes()
        self.assertEqual(artifact, (self.root / 'second/site.zip').read_bytes())
        self.assertEqual(manifest['artifact_sha256'], hashlib.sha256(artifact).hexdigest())
        with zipfile.ZipFile(io.BytesIO(artifact)) as archive:
            version = json.loads(archive.read('version.json'))
            self.assertEqual(version['source_commit'], COMMIT)
            self.assertEqual(version['source_sha256'], manifest['source_sha256'])
            self.assertEqual(version['operation_id'], OPERATION)
            for record in manifest['files']:
                content = archive.read(record['path'])
                self.assertEqual(record['sha256'], hashlib.sha256(content).hexdigest())
                self.assertEqual(record['size'], len(content))
        self.put('index.html', HTML.format('Changed'))
        changed = package(self.site, self.root / 'third', OPERATION, COMMIT)
        self.assertNotEqual(manifest['artifact_sha256'], changed['artifact_sha256'])
        self.assertNotEqual(manifest['source_sha256'], changed['source_sha256'])

    def test_packaging_requires_real_commit_and_external_output(self):
        with self.assertRaises(ValidationError):
            package(self.site, self.root / 'output', OPERATION, 'local')
        with self.assertRaises(ValidationError):
            package(self.site, self.site / 'output', OPERATION, COMMIT)


if __name__ == '__main__':
    unittest.main()
