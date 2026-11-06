import base64
import datetime as dt
import hashlib
import json
import unittest

from github_app import AmbiguousWrite, AppConfig, GitHubApp, GitHubError, StaleHead, _git_hash

NOW = 1800000000
BASE = 'a' * 40
OPERATION = '23456789-1234-4234-8234-123456789abc'
CREATED_AT = '2026-11-05T00:00:00Z'


class FakeGitHub:
    def __init__(self):
        self.calls = []
        self.current = BASE
        self.files = {'index.html': b'base', 'x.txt': b'x'}
        self.blobs = {_git_hash('blob', value): value for value in self.files.values()}
        self.root = 'b' * 40
        self.commits = {BASE: {'sha': BASE, 'tree': {'sha': self.root}, 'committer': {'date': '2026-01-01T00:00:00Z'}}}
        self.token_scope = [{'id': 3, 'full_name': 'example/site'}]
        self.expiry = NOW + 3600
        self.permission = {'contents': 'write', 'metadata': 'read'}
        self.fail_patch = False
        self.apply_then_fail = False
        self.fail_read_after_patch = False
        self.patched = False
        self.missing_workspace = False
        self.create_then_fail = False

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url, headers, body))
        self.assert_origin(url)
        path = url.removeprefix('https://api.github.com')
        if path == '/app/installations/2/access_tokens':
            assert body == {'repository_ids': [3], 'permissions': {'contents': 'write'}}
            return 201, {'token': 'FAKE-not-a-secret', 'expires_at': dt.datetime.fromtimestamp(self.expiry, dt.timezone.utc).isoformat(), 'permissions': self.permission, 'repositories': self.token_scope}
        assert path.startswith('/repos/example/site/')
        assert headers['Authorization'] == 'Bearer FAKE-not-a-secret'
        if method == 'GET' and '/git/ref/heads/' in path:
            if self.missing_workspace and '/codex/hp/' in path:
                return 404, {'message': 'Not Found'}
            if self.patched and self.fail_read_after_patch:
                raise OSError('connection unavailable')
            return 200, {'object': {'type': 'commit', 'sha': self.current}}
        if method == 'GET' and '/git/commits/' in path:
            return 200, self.commits[path.rsplit('/', 1)[1]]
        if method == 'GET' and '/git/trees/' in path:
            return 200, {'truncated': False, 'tree': [{'path': 'site/' + p, 'mode': '100644', 'type': 'blob', 'sha': _git_hash('blob', value), 'size': len(value)} for p, value in self.files.items()] + [{'path': 'infra/private.tf', 'mode': '100644', 'type': 'blob', 'sha': 'e' * 40, 'size': 12}]}
        if method == 'GET' and '/git/blobs/' in path:
            return 200, {'encoding': 'base64', 'content': base64.b64encode(self.blobs[path.rsplit('/', 1)[1]]).decode()}
        if method == 'POST' and path.endswith('/git/blobs'):
            content = base64.b64decode(body['content'])
            sha = _git_hash('blob', content)
            self.blobs[sha] = content
            return 201, {'sha': sha}
        if method == 'POST' and path.endswith('/git/trees'):
            return 201, {'sha': hashlib.sha1(json.dumps(body, sort_keys=True).encode()).hexdigest()}
        if method == 'POST' and path.endswith('/git/commits'):
            sha = hashlib.sha1(json.dumps(body, sort_keys=True).encode()).hexdigest()
            self.commits[sha] = dict(body, sha=sha)
            return 201, {'sha': sha}
        if method == 'POST' and path.endswith('/git/refs'):
            assert body['ref'].startswith('refs/heads/codex/hp/')
            self.current = body['sha']
            self.missing_workspace = False
            if self.create_then_fail:
                raise OSError('response lost')
            return 201, {'ref': body['ref'], 'object': {'sha': self.current}}
        if method == 'PATCH':
            assert body['force'] is False
            self.patched = True
            if self.apply_then_fail:
                self.current = body['sha']
                raise OSError('response lost')
            if self.fail_patch:
                raise OSError('connection unavailable')
            self.current = body['sha']
            return 200, {'object': {'sha': self.current}}
        raise AssertionError((method, path))

    @staticmethod
    def assert_origin(url):
        assert url.startswith('https://api.github.com/')


class GitHubAppTest(unittest.TestCase):
    def setUp(self):
        self.fake = FakeGitHub()
        self.secrets = []
        self.signed = []
        self.now = NOW
        def resolve(ref):
            self.secrets.append(ref)
            return 'FAKE-KEY'
        def sign(claims, key):
            self.signed.append((claims, key))
            return 'FAKE-JWT'
        self.app = GitHubApp(AppConfig(1, 2, 3, 'example', 'site', 'secret://app-key'), resolve, self.fake, lambda: self.now, sign)

    def save(self):
        return self.app.commit_site('dev', BASE, {'index.html': b'changed', 'x.txt': b'x'}, 'Update home', OPERATION, CREATED_AT)

    def test_exact_runtime_permissions_are_requested_and_unexpected_grants_rejected(self):
        requested = {'contents': 'write', 'pull_requests': 'write', 'checks': 'read', 'actions': 'read'}
        calls = []
        def transport(method, url, headers, body):
            if url.endswith('/access_tokens'):
                calls.append(body)
                return 201, {'token':'TEST-TOKEN', 'expires_at':dt.datetime.fromtimestamp(NOW+3600, dt.timezone.utc).isoformat(),
                    'repositories':[{'id':3,'full_name':'example/site'}], 'permissions':{**requested,'metadata':'read'}}
            return 200, {'object':{'type':'commit','sha':BASE}}
        app = GitHubApp(self.app.config, lambda _: 'KEY', transport, lambda: NOW, lambda *_:'JWT', permissions=requested)
        self.assertEqual(app.head('dev'), BASE)
        self.assertEqual(calls, [{'repository_ids':[3], 'permissions':requested}])
        with self.assertRaises(GitHubError):
            GitHubApp(self.app.config, lambda _: 'KEY', permissions={**requested,'administration':'write'})
        def excessive(method,url,headers,body):
            status,result = transport(method,url,headers,body)
            if url.endswith('/access_tokens'):
                result['permissions']['actions'] = 'write'
            return status,result
        with self.assertRaises(GitHubError):
            GitHubApp(self.app.config, lambda _: 'KEY', excessive, lambda: NOW, lambda *_:'JWT', permissions=requested).head('dev')

    def test_exact_token_scope_cache_and_expiry(self):
        self.assertEqual(self.app.read_site('dev').files, self.fake.files)
        self.app.read_site('dev')
        self.assertEqual(self.secrets, ['secret://app-key'])
        claims, key = self.signed[0]
        self.assertEqual(claims, {'iat': NOW - 60, 'exp': NOW + 480, 'iss': '1'})
        self.now += 3550
        self.fake.expiry = self.now + 3600
        self.app.head('main')
        self.assertEqual(len(self.secrets), 2)

    def test_wrong_repository_permissions_expiry_rejected(self):
        for change in ({'token_scope': [{'id': 4, 'full_name': 'example/other'}]}, {'token_scope': [{'id': 3, 'full_name': 'example/site'}, {'id': 4, 'full_name': 'example/other'}]}, {'expiry': NOW - 1}, {'expiry': NOW + 7200}, {'permission': {'contents': 'write', 'administration': 'write'}}):
            with self.subTest(change=change):
                fake = FakeGitHub()
                for name, value in change.items():
                    setattr(fake, name, value)
                app = GitHubApp(self.app.config, lambda _: 'FAKE', fake, lambda: NOW, lambda *_: 'FAKE')
                with self.assertRaises(GitHubError):
                    app.head('dev')

    def test_branch_allowlist_and_cross_repo(self):
        for branch in ('staging', 'codex/hp/../../main', 'https://other', 'codex/hp/not-uuid'):
            with self.subTest(branch=branch), self.assertRaises(GitHubError):
                self.app.head(branch)
        self.app.head('codex/hp/' + OPERATION)
        with self.assertRaises(GitHubError):
            self.app._request('GET', '/repos/example/other/git/ref/heads/main')

    def test_save_is_deterministic_and_replay_reconciles(self):
        saved = self.save()
        replay = self.save()
        self.assertEqual(saved.commit, replay.commit)
        self.assertTrue(replay.replayed)
        updates = [call for call in self.fake.calls if call[0] == 'PATCH']
        self.assertEqual(len(updates), 1)
        commit = self.fake.commits[saved.commit]
        self.assertIn('HP-Operation-Id: ' + OPERATION, commit['message'])
        self.assertEqual(commit['parents'], [BASE])
        self.assertEqual(commit['committer']['date'], '2026-11-05T00:00:00+00:00')
        trees = [call[3] for call in self.fake.calls if call[0] == 'POST' and call[1].endswith('/git/trees')]
        self.assertEqual([e['path'] for e in trees[0]['tree']], ['site/index.html'])

    def test_stale_head_never_updates_ref(self):
        self.fake.current = 'f' * 40
        with self.assertRaises(StaleHead):
            self.save()
        self.assertFalse(any(c[0] == 'PATCH' for c in self.fake.calls))

    def test_ambiguous_update_readback(self):
        self.fake.apply_then_fail = True
        result = self.save()
        self.assertTrue(result.replayed)
        self.assertEqual(result.commit, self.fake.current)

    def test_unacknowledged_write_retains_operation(self):
        self.fake.fail_patch = True
        with self.assertRaises(AmbiguousWrite):
            self.save()
        self.assertEqual(self.fake.current, BASE)
        self.fake.fail_patch = False
        result = self.save()
        self.assertEqual(result.commit, self.fake.current)

    def test_noop_and_unsafe_candidate(self):
        result = self.app.commit_site('dev', BASE, self.fake.files, 'Nothing', OPERATION, CREATED_AT)
        self.assertEqual(result.commit, BASE)
        self.assertFalse(any(c[0] in ('POST', 'PATCH') and '/repos/' in c[1] for c in self.fake.calls))
        with self.assertRaises(ValueError):
            self.app.commit_site('dev', BASE, {'index.html': b'x', '../infra/config.json': b'x'}, 'Unsafe', OPERATION, CREATED_AT)

    def test_workspace_create_reconcile_and_collision(self):
        self.fake.missing_workspace = True
        self.fake.create_then_fail = True
        self.assertEqual(self.app.ensure_workspace_branch(OPERATION, BASE), 'codex/hp/' + OPERATION)
        self.assertEqual(self.app.ensure_workspace_branch(OPERATION, BASE), 'codex/hp/' + OPERATION)
        self.assertEqual(sum(call[0] == 'POST' and call[1].endswith('/git/refs') for call in self.fake.calls), 1)
        self.fake.current = 'e' * 40
        with self.assertRaises(StaleHead):
            self.app.ensure_workspace_branch(OPERATION, BASE)


if __name__ == '__main__':
    unittest.main()
