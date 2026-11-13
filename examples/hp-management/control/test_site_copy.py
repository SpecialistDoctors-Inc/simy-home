import io
import json
import socket
import unittest
import zipfile

import site_copy
from site_copy import CopyFailed, copy_public_site, enqueue, public_address, run_one
from store import MemoryStore

HOST = 'clinic.example.jp'


def site(pages):
    """fetch() serving a dict {url: (status, headers, body)}."""
    calls = []

    def fetch(url):
        calls.append(url)
        if url not in pages:
            return 404, {}, b''
        return pages[url]
    fetch.calls = calls
    return fetch


HTML = 'text/html; charset=utf-8'


class SiteCopyTest(unittest.TestCase):
    def test_copies_same_site_pages_and_assets_only(self):
        fetch = site({
            'https://clinic.example.jp/': (301, {'Location': 'https://www.clinic.example.jp/'}, b''),
            'https://www.clinic.example.jp/': (200, {'Content-Type': HTML}, (
                b'<a href="/access.html">a</a><a href="https://evil.example/x">x</a>'
                b'<a href="http://www.clinic.example.jp/plain">p</a><img src="img/a.png" srcset="img/b.png 2x">'
                b'<link rel="stylesheet" href="/s.css"><a href="/access.html#map">dup</a>'
                b'<a href="mailto:x@example.jp">m</a><style>.h{background:url(\'/bg.jpg\')}</style>')),
            'https://www.clinic.example.jp/access.html': (200, {'Content-Type': HTML}, b'<a href="/">top</a>'),
            'https://www.clinic.example.jp/img/a.png': (200, {'Content-Type': 'image/png'}, b'A'),
            'https://www.clinic.example.jp/img/b.png': (200, {'Content-Type': 'image/png'}, b'B'),
            'https://www.clinic.example.jp/s.css': (200, {'Content-Type': 'text/css'}, b'.x{background:url(f.woff)}'),
            'https://www.clinic.example.jp/f.woff': (200, {'Content-Type': 'font/woff'}, b'F'),
            'https://www.clinic.example.jp/bg.jpg': (200, {'Content-Type': 'image/jpeg'}, b'J'),
        })
        data, manifest = copy_public_site(HOST, fetch=fetch, now=lambda: 1000)
        self.assertFalse(manifest['truncated'])
        self.assertTrue(all('evil.example' not in url and url.startswith('https://') for url in fetch.calls))
        names = set(zipfile.ZipFile(io.BytesIO(data)).namelist())
        self.assertEqual(names, {'manifest.json', 'site/index.html', 'site/access.html', 'site/img/a.png',
                                 'site/img/b.png', 'site/s.css', 'site/f.woff', 'site/bg.jpg'})
        stored = json.loads(zipfile.ZipFile(io.BytesIO(data)).read('manifest.json'))
        self.assertEqual(stored['host'], HOST)
        self.assertEqual(len(stored['files']), 7)

    def test_redirects_off_site_are_not_followed(self):
        fetch = site({'https://clinic.example.jp/': (302, {'Location': 'https://evil.example/'}, b'')})
        with self.assertRaisesRegex(CopyFailed, 'nothing_fetched'):
            copy_public_site(HOST, fetch=fetch)
        self.assertEqual(fetch.calls, ['https://clinic.example.jp/'])

    def test_limits_truncate_the_copy(self):
        links = ''.join(f'<a href="/p{i}.html">p</a>' for i in range(300)).encode()
        pages = {'https://clinic.example.jp/': (200, {'Content-Type': HTML}, links)}
        pages.update({f'https://clinic.example.jp/p{i}.html': (200, {'Content-Type': HTML}, b'x') for i in range(300)})
        data, manifest = copy_public_site(HOST, fetch=site(pages))
        self.assertTrue(manifest['truncated'])
        self.assertEqual(len(manifest['files']), site_copy.MAX_FILES)
        big = {'https://clinic.example.jp/': (200, {'Content-Type': HTML}, b'<img src="/big.bin">'),
               'https://clinic.example.jp/big.bin': (200, {}, b'0' * (site_copy.MAX_FILE + 1))}
        _, manifest = copy_public_site(HOST, fetch=site(big))
        self.assertTrue(manifest['truncated'])
        self.assertEqual([f['path'] for f in manifest['files']], ['site/index.html'])
        ticks = iter(range(0, 1000, 60))
        _, manifest = copy_public_site(HOST, fetch=site(pages), clock=lambda: next(ticks))
        self.assertTrue(manifest['truncated'])
        self.assertLess(len(manifest['files']), 5)

    def test_non_public_addresses_are_refused(self):
        def resolve(*addresses):
            return lambda host, port, type=None: [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (a, port))
                                                  for a in addresses]
        self.assertTrue(public_address(HOST, resolve('93.184.216.34')))
        for address in ('127.0.0.1', '10.0.0.5', '169.254.169.254', '192.168.1.1', '::1', 'fd00::1', '100.64.0.1'):
            self.assertFalse(public_address(HOST, resolve(address)), address)
        self.assertFalse(public_address(HOST, resolve('93.184.216.34', '10.0.0.5')))
        with self.assertRaisesRegex(CopyFailed, 'non_public_host'):
            site_copy.default_fetch('https://' + HOST + '/', resolve=resolve('169.254.169.254'))
        with self.assertRaisesRegex(CopyFailed, 'non_public_host'):
            copy_public_site(HOST, fetch=lambda url: site_copy.default_fetch(url, resolve=resolve('127.0.0.1')))

    def test_archive_paths_stay_inside_the_site_root(self):
        self.assertEqual(site_copy.archive_path('https://h/a/../../etc/passwd'), 'site/a/etc/passwd')
        self.assertEqual(site_copy.archive_path('https://h/dir/'), 'site/dir/index.html')
        self.assertTrue(site_copy.archive_path('https://h/p?x=1').startswith('site/p__'))


class CopyQueueTest(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.objects = {}
        self.store.put('clinic-intake:sub_A', {'host': HOST, 'status': 'received', 'copy_state': 'pending',
                                               'copy_attempts': 0, 'copy_generation': 1})
        enqueue(self.store, 'sub_A', 1)
        enqueue(self.store, 'sub_A', 1)

    def put(self, key, data):
        self.objects[key] = data

    def jobs(self):
        return self.store.get('clinic-copy-pending')['subscriptions']

    def test_copy_is_stored_and_recorded(self):
        copier = lambda host: (b'zip', {'files': [1, 2], 'truncated': False})
        self.assertEqual(run_one(self.store, self.put, copier=copier), 'sub_A:1')
        intake = self.store.get('clinic-intake:sub_A')
        self.assertEqual((intake['copy_state'], intake['copy_files']), ('done', 2))
        self.assertEqual(list(self.objects), [intake['copy_key']])
        self.assertRegex(intake['copy_key'], r'^intake/[0-9a-f]{64}/[0-9a-f]{64}/site\.zip$')
        self.assertEqual(self.jobs(), [])
        self.assertIsNone(run_one(self.store, self.put, copier=copier))

    def test_failures_retry_then_stop(self):
        def copier(host):
            raise CopyFailed('nothing_fetched')
        for _ in range(site_copy.MAX_ATTEMPTS):
            run_one(self.store, self.put, copier=copier)
        intake = self.store.get('clinic-intake:sub_A')
        self.assertEqual((intake['copy_state'], intake['copy_error'], intake['copy_attempts']),
                         ('failed', 'nothing_fetched', site_copy.MAX_ATTEMPTS))
        self.assertEqual(self.jobs(), [])
        self.assertEqual(self.objects, {})

    def test_attempt_is_recorded_and_job_rotated_before_fetching(self):
        # A run killed mid-fetch (Lambda timeout) must still count and must not block others.
        self.store.put('clinic-intake:sub_B', {'host': 'b.example.jp', 'status': 'received', 'copy_state': 'pending',
                                               'copy_attempts': 0, 'copy_generation': 1})
        enqueue(self.store, 'sub_B', 1)

        class Killed(BaseException):
            pass

        def hang(host):
            self.assertEqual(self.store.get('clinic-intake:sub_A')['copy_attempts'], 1)
            self.assertEqual(self.jobs(), ['sub_B:1', 'sub_A:1'])
            raise Killed()
        with self.assertRaises(Killed):
            run_one(self.store, self.put, copier=hang)
        copier = lambda host: (host.encode(), {'files': [1], 'truncated': False})
        self.assertEqual(run_one(self.store, self.put, copier=copier), 'sub_B:1')
        for _ in range(site_copy.MAX_ATTEMPTS - 1):
            with self.assertRaises(Killed):
                run_one(self.store, self.put, copier=lambda host: (_ for _ in ()).throw(Killed()))
        # After MAX_ATTEMPTS recorded attempts the job is closed without fetching again.
        run_one(self.store, self.put, copier=hang)
        self.assertEqual(self.store.get('clinic-intake:sub_A')['copy_state'], 'failed')
        self.assertEqual(self.jobs(), [])

    def test_resubmission_during_a_copy_keeps_the_new_job(self):
        def copier(host):
            # The clinic submits another homepage while host A is being copied.
            latest = self.store.get('clinic-intake:sub_A')
            self.store.put('clinic-intake:sub_A', {**latest, 'host': 'new.example.jp', 'copy_generation': 2,
                                                   'copy_attempts': 0}, latest['_version'])
            enqueue(self.store, 'sub_A', 2)
            return b'old', {'files': [1], 'truncated': False}
        run_one(self.store, self.put, copier=copier)
        intake = self.store.get('clinic-intake:sub_A')
        self.assertEqual((intake['host'], intake['copy_state']), ('new.example.jp', 'pending'))
        self.assertIn('sub_A:2', self.jobs())
        run_one(self.store, self.put, copier=lambda host: (_ for _ in ()).throw(AssertionError()))  # stale gen 1
        self.assertEqual(self.jobs(), ['sub_A:2'])
        run_one(self.store, self.put, copier=lambda host: (host.encode(), {'files': [1], 'truncated': False}))
        self.assertEqual(self.store.get('clinic-intake:sub_A')['copy_state'], 'done')
        self.assertEqual(self.jobs(), [])

    def test_slow_response_hits_the_absolute_fetch_deadline(self):
        class Response:
            status, headers = 200, {}
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, n): return b'x'

        class Opener:
            def open(self, request, timeout): return Response()
        ticks = iter(range(0, 10000))
        public = lambda host, port, type=None: [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', port))]
        with self.assertRaisesRegex(CopyFailed, 'fetch_timeout'):
            site_copy.default_fetch('https://' + HOST + '/', resolve=public, opener=Opener(),
                                    clock=lambda: next(ticks))


if __name__ == '__main__':
    unittest.main()
