"""CI proof regressions: no real GitHub or blob requests."""
from copy import deepcopy
from io import BytesIO
import json
from types import SimpleNamespace
import unittest
import warnings
import urllib.parse
from uuid import uuid5, NAMESPACE_URL
import zipfile
from bundles import sha256
from executor import IntegrationUnavailable
from github_workflow import GitHubWorkflow, ValidationFailed, ValidationPending, download_artifact, unpack_artifact
from service import fingerprint
from test_executor import package

COMMIT = 'a' * 40
OPERATION = '23456789-1234-4234-8234-123456789abc'
REPOSITORY = 'example/site'
BRANCH = 'codex/hp/' + str(uuid5(NAMESPACE_URL, 'hp-candidate:' + OPERATION))
SITE = {'github_app_id':1,'github_installation_id':2,'github_repository_id':3,
    'github_owner':'example','github_repository':'site','validation_workflow_id':4,'dev_branch':'dev'}


def artifact_bytes(files=None):
    files = files or {'index.html':b'checked html'}
    package_id = str(uuid5(NAMESPACE_URL, 'https://github.com/' + REPOSITORY + '/commit/' + COMMIT))
    inner = package(files,COMMIT,package_id)
    with zipfile.ZipFile(BytesIO(inner)) as archive:
        all_files = {name:archive.read(name) for name in archive.namelist()}
    source_hash = fingerprint([{'path':p,'sha256':sha256(v),'size':len(v)} for p,v in sorted(files.items())])
    manifest = {'schema_version':1,'source_commit':COMMIT,'operation_id':package_id,'source_sha256':source_hash,
        'version':source_hash,'kind':'static-site-artifact','artifact_sha256':sha256(inner),
        'files':[{'path':p,'sha256':sha256(v),'size':len(v)} for p,v in sorted(all_files.items())]}
    stream = BytesIO()
    with zipfile.ZipFile(stream,'w') as archive:
        archive.writestr('site.zip',inner)
        archive.writestr('manifest.json',json.dumps(manifest))
    return stream.getvalue(),inner,fingerprint({p:sha256(v) for p,v in files.items()})


class FakeApp:
    def __init__(self, outer):
        self.config = SimpleNamespace(owner='example',repository='site',repository_id=3)
        self.prefix = '/repos/example/site'
        self.permissions = {'contents':'write','pull_requests':'write','checks':'read','actions':'read'}
        self.prs = []
        self.creates = 0
        self.lose_create_response = False
        self.pr = {'number':9,'state':'open','body':'HP-Operation-Id: ' + OPERATION,
            'head':{'ref':BRANCH,'sha':COMMIT,'repo':{'id':3}},'base':{'ref':'dev','repo':{'id':3}}}
        self.run = {'id':8,'run_attempt':1,'head_sha':COMMIT,'head_branch':BRANCH,'repository':{'id':3},
            'head_repository':{'id':3},'workflow_id':4,'event':'pull_request','path':'.github/workflows/check-site.yml',
            'pull_requests':[{'number':9}],'status':'completed','conclusion':'success'}
        self.runs = [self.run]
        self.artifact = {'id':7,'name':'static-site-' + COMMIT + '-1','expired':False,
            'workflow_run':{'id':8,'head_sha':COMMIT},'digest':'sha256:' + sha256(outer),'size_in_bytes':len(outer)}
        self.artifacts = [self.artifact]

    def head(self, branch):
        assert branch == BRANCH
        return COMMIT
    def _token(self):
        return 'TEST-TOKEN'
    @staticmethod
    def _headers(token):
        return {'Authorization':'Bearer ' + token}
    def transport(self, method, url, headers, body):
        parsed = urllib.parse.urlsplit(url)
        assert parsed.netloc == 'api.github.com'
        assert parsed.path.startswith(self.prefix)
        assert headers == {'Authorization':'Bearer TEST-TOKEN'}
        if parsed.path.endswith('/pulls'):
            if method == 'GET':
                return 200,deepcopy(self.prs)
            assert body['head'] == BRANCH and body['base'] == 'dev'
            assert body['body'] == 'HP-Operation-Id: ' + OPERATION
            self.prs = [deepcopy(self.pr)]
            self.creates += 1
            if self.lose_create_response:
                self.lose_create_response = False
                raise OSError('accepted PR response lost')
            return 201,deepcopy(self.pr)
        if parsed.path.endswith('/actions/workflows/4/runs'):
            query = urllib.parse.parse_qs(parsed.query)
            assert query['head_sha'] == [COMMIT] and query['event'] == ['pull_request']
            return 200,{'total_count':len(self.runs),'workflow_runs':deepcopy(self.runs)}
        if parsed.path.endswith('/actions/runs/8/artifacts'):
            return 200,{'total_count':len(self.artifacts),'artifacts':deepcopy(self.artifacts)}
        raise AssertionError((method,url))


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.outer,self.inner,self.tree_hash = artifact_bytes()
        self.app = FakeApp(self.outer)
        self.downloads = []
        def download(url,headers,guard):
            guard(); self.downloads.append((url,headers))
            return self.outer
        self.validator = GitHubWorkflow(lambda site,guard:self.app,download)

    def validate(self):
        return self.validator.validate(SITE,COMMIT,OPERATION,self.tree_hash,lambda:None)

    def test_pr_create_unknown_response_reconciles_without_duplicate(self):
        self.app.lose_create_response = True
        with self.assertRaises(OSError): self.validate()
        proof = self.validate()
        self.assertEqual(self.app.creates,1)
        self.assertEqual(proof['source_commit'],COMMIT)
        self.assertEqual(proof['artifact_sha256'],sha256(self.inner))
        self.assertEqual(self.validator.artifact(proof,lambda:None),self.inner)
        self.assertEqual(proof['site_binding']['github_repository_id'],3)

    def test_new_pr_returns_pending_never_fabricates_ci(self):
        with self.assertRaises(ValidationPending): self.validate()
        self.assertEqual(self.app.creates,1)
        self.assertFalse(self.downloads)

    def test_exact_run_repo_workflow_ref_and_head_required(self):
        self.app.prs = [deepcopy(self.app.pr)]
        for field,value in [('head_sha','b'*40),('head_branch','main'),('repository',{'id':30}),
            ('head_repository',{'id':30}),('workflow_id',40),('event','push'),
            ('path','.github/workflows/untrusted.yml'),('pull_requests',[{'number':90}])]:
            with self.subTest(field=field):
                self.app.runs = [{**self.app.run,field:value}]
                with self.assertRaises(ValidationPending): self.validate()
        self.assertFalse(self.downloads)

    def test_latest_failed_or_running_run_cannot_use_older_success(self):
        self.app.prs = [deepcopy(self.app.pr)]
        self.app.runs = [self.app.run,{**self.app.run,'id':10,'status':'in_progress','conclusion':None}]
        with self.assertRaises(ValidationPending): self.validate()
        self.app.runs[-1].update(status='completed',conclusion='failure')
        with self.assertRaisesRegex(ValidationFailed,'failed'): self.validate()
        self.assertFalse(self.downloads)

    def test_wrong_pr_head_or_fork_is_rejected(self):
        self.app.prs = [{**self.app.pr,'head':{'sha':COMMIT,'ref':BRANCH,'repo':{'id':30}}}]
        with self.assertRaises(ValidationFailed): self.validate()
        self.assertFalse(self.downloads)

    def test_artifact_bound_to_latest_successful_attempt_and_full_digest(self):
        self.app.prs = [deepcopy(self.app.pr)]
        for patch in ({'digest':'sha256:'+'f'*64},{'expired':True},{'workflow_run':{'id':80,'head_sha':COMMIT}},
            {'size_in_bytes':len(self.outer)+1},{'name':'static-site-'+COMMIT+'-2'}):
            with self.subTest(patch=patch):
                self.app.artifacts = [{**self.app.artifact,**patch}]
                with self.assertRaises(ValidationFailed): self.validate()

    def test_readonly_reconciliation_never_creates_missing_pr(self):
        with self.assertRaises(ValidationPending):
            self.validator.reconcile(SITE,COMMIT,OPERATION,self.tree_hash,lambda:None)
        self.assertEqual(self.app.creates,0)
        self.assertFalse(self.downloads)

    def test_missing_preview_readback_remains_explicitly_unavailable(self):
        self.app.prs = [deepcopy(self.app.pr)]
        proof = self.validate()
        with self.assertRaises(IntegrationUnavailable): self.validator.readback(SITE,proof,lambda:None)

    def test_unrelated_source_bytes_fail_requested_tree_binding(self):
        self.app.prs = [deepcopy(self.app.pr)]
        with self.assertRaisesRegex(ValidationFailed,'source_tree'):
            self.validator.validate(SITE,COMMIT,OPERATION,'f'*64,lambda:None)

    def test_outer_archive_extra_paths_and_duplicate_entries_are_rejected(self):
        for name in ('../site.zip','site.zip'):
            stream = BytesIO(self.outer)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                with zipfile.ZipFile(stream,'a') as archive:
                    archive.writestr(name,b'extra')
            with self.assertRaises(ValidationFailed): unpack_artifact(stream.getvalue(),COMMIT,REPOSITORY)

    def test_artifact_manifest_is_bound_to_package_source_and_all_files(self):
        with zipfile.ZipFile(BytesIO(self.outer)) as archive:
            manifest = json.loads(archive.read('manifest.json'))
        for patch in ({'source_commit':'b'*40},{'source_sha256':'f'*64},{'artifact_sha256':'f'*64},
                      {'operation_id':OPERATION},{'files':[]}):
            with self.subTest(patch=patch):
                stream = BytesIO()
                with zipfile.ZipFile(stream,'w') as archive:
                    archive.writestr('site.zip',self.inner)
                    archive.writestr('manifest.json',json.dumps({**manifest,**patch}))
                with self.assertRaises(ValidationFailed): unpack_artifact(stream.getvalue(),COMMIT,REPOSITORY)


class DownloadTests(unittest.TestCase):
    def test_signed_blob_redirect_never_receives_github_credentials(self):
        calls=[]
        def transport(url,headers,limit):
            calls.append((url,headers))
            if len(calls)==1:
                return 302,{'Location':'https://production.blob.core.windows.net/artifact?sig=test'},b''
            return 200,{},b'outer zip'
        result=download_artifact('https://api.github.com/repos/example/site/actions/artifacts/7/zip',
            {'Authorization':'Bearer TEST'},lambda:None,transport)
        self.assertEqual(result,b'outer zip')
        self.assertEqual(calls[1][1],{})

    def test_arbitrary_redirect_and_second_redirect_are_rejected(self):
        for target in ('http://production.blob.core.windows.net/a','https://attacker.invalid/a',
            'https://production.blob.core.windows.net.attacker.invalid/a',
            'https://user:credential@production.blob.core.windows.net/a','https://production.blob.core.windows.net:444/a'):
            calls=[]
            def transport(url,headers,limit):
                calls.append(url)
                return 302,{'Location':target},b''
            with self.assertRaises(ValidationFailed):
                download_artifact('https://api.github.com/repos/example/site/actions/artifacts/7/zip',{},lambda:None,transport)
            self.assertEqual(len(calls),1)
        def again(url,headers,limit):
            return 302,{'Location':'https://production.blob.core.windows.net/a'},b''
        with self.assertRaises(ValidationFailed):
            download_artifact('https://api.github.com/repos/example/site/actions/artifacts/7/zip',{},lambda:None,again)


if __name__=='__main__': unittest.main()
