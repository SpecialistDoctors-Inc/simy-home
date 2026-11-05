import base64
import json
import io
import tempfile
import unittest
from pathlib import Path
import sys
import urllib.parse
import urllib.error
import zipfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
from github_provider import GitHub, GitHubProviderError, Response
from provider_errors import EffectNotStarted


SHA = "a" * 40
PATH = "examples/sample-clinic/content/clinic.json"
CONTENT = {"changeRequest": {"id": "11111111-1111-4111-8111-111111111111", "revision": 1}, "notices": []}


class FakeGitHub:
    def __init__(self):
        self.refs = {"dev": SHA}
        self.files = {"dev": (CONTENT, "b" * 40)}
        self.prs = []
        self.calls = []
    def __call__(self, method, path, body, timeout):
        self.calls.append((method, path, body))
        payload = json.loads(body) if body else None
        if path.startswith("/repos/SpecialistDoctors-Inc/simy-home/git/ref/heads/"):
            branch = urllib.parse.unquote(path.rsplit("/", 1)[1])
            return Response(200, json.dumps({"object": {"sha": self.refs[branch]}}).encode()) if branch in self.refs else Response(404, b'{"message":"Not Found"}')
        if path == "/repos/SpecialistDoctors-Inc/simy-home/git/refs" and method == "POST":
            branch = payload["ref"].removeprefix("refs/heads/")
            self.refs[branch] = payload["sha"]; self.files[branch] = self.files["dev"]
            return Response(201, b"{}")
        if path.startswith("/repos/SpecialistDoctors-Inc/simy-home/contents/"):
            if method == "GET":
                branch = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)["ref"][0]
                if branch not in self.files:
                    branch = next((name for name, sha in self.refs.items() if sha == branch), branch)
                content, blob = self.files[branch]
                encoded = base64.b64encode(json.dumps(content, ensure_ascii=False).encode()).decode()
                return Response(200, json.dumps({"type": "file", "encoding": "base64", "sha": blob, "content": encoded[:12] + "\n" + encoded[12:]}).encode())
            branch = payload["branch"]
            decoded = json.loads(base64.b64decode(payload["content"]))
            self.files[branch] = (decoded, "c" * 40); self.refs[branch] = "d" * 40
            return Response(200, json.dumps({"commit": {"sha": "d" * 40}}).encode())
        if path.startswith("/repos/SpecialistDoctors-Inc/simy-home/pulls?"):
            head = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)["head"][0].split(":", 1)[1]
            return Response(200, json.dumps([p for p in self.prs if p["head"]["ref"] == head]).encode())
        if path == "/repos/SpecialistDoctors-Inc/simy-home/pulls" and method == "POST":
            pr = {"number": 7, "html_url": "https://github.test/pr/7", "state": "open", "body": payload["body"], "base": {"ref": "dev", "sha": SHA}, "head": {"ref": payload["head"], "sha": self.refs[payload["head"]]}}
            self.prs.append(pr); return Response(201, json.dumps(pr).encode())
        return Response(500, b"{}")


class ProviderTests(unittest.TestCase):
    def provider(self, fake):
        return GitHub("token", "SpecialistDoctors-Inc/simy-home", PATH, "https://dev.example", transport=fake, web_transport=lambda *_: Response(200, b""))
    def test_base_and_candidate_replay_create_one_branch_commit_and_pr(self):
        fake = FakeGitHub(); provider = self.provider(fake)
        base = provider.base()
        result = provider.ensure_candidate(CONTENT["changeRequest"]["id"], 1, base["sha"], base["blob_sha"], {**CONTENT, "notices": [{"id": "n"}]})
        replay = provider.ensure_candidate(CONTENT["changeRequest"]["id"], 1, base["sha"], base["blob_sha"], {**CONTENT, "notices": [{"id": "n"}]})
        self.assertEqual(result, replay); self.assertEqual(1, len(fake.prs)); self.assertEqual(1, sum(method == "PUT" and "/contents/" in path for method, path, _ in fake.calls))
        self.assertEqual(result, provider.reconcile_candidate(CONTENT["changeRequest"]["id"], 1, base["sha"], base["blob_sha"], {**CONTENT, "notices": [{"id": "n"}]}))
    def test_existing_candidate_with_foreign_content_fails_closed(self):
        fake = FakeGitHub(); provider = self.provider(fake); base = provider.base()
        branch = provider._branch(CONTENT["changeRequest"]["id"], 1)
        fake.refs[branch] = "e" * 40; fake.files[branch] = ({"foreign": True}, "f" * 40)
        with self.assertRaisesRegex(EffectNotStarted, "ensure_candidate_preflight_failed") as error:
            provider.ensure_candidate(CONTENT["changeRequest"]["id"], 1, base["sha"], base["blob_sha"], CONTENT)
        self.assertEqual("candidate_payload_conflict", str(error.exception.__cause__))

    def test_preflight_failure_is_distinct_from_lost_write_response(self):
        fake = FakeGitHub(); provider = self.provider(fake)
        with patch.object(provider, "readiness", side_effect=GitHubProviderError("candidate_check_failed")):
            with self.assertRaises(EffectNotStarted):
                provider.merge_dev(7, "d" * 40, SHA)
        self.assertEqual([], fake.calls)
        def lost_response(method, path, body, timeout):
            result = fake(method, path, body, timeout)
            if method == "POST":
                raise GitHubProviderError("github_transport_unavailable")
            return result
        provider = self.provider(lost_response)
        with self.assertRaises(GitHubProviderError):
            provider.ensure_candidate(CONTENT["changeRequest"]["id"], 1, SHA, "b" * 40, {**CONTENT, "notices": [{"id": "n"}]})
        self.assertEqual(1, sum(method == "POST" for method, _, _ in fake.calls))
    def test_configuration_and_main_are_rejected(self):
        with self.assertRaises(ValueError):
            GitHub("token", "SpecialistDoctors-Inc/simy-home", "README.md", "https://dev.example")
        fake = FakeGitHub(); provider = self.provider(fake)
        with self.assertRaisesRegex(GitHubProviderError, "dev_branch_missing"):
            fake.refs.pop("dev"); provider.base()

    def test_real_github_404_body_means_missing_ref(self):
        provider = self.provider(FakeGitHub())
        self.assertIsNone(provider._ref("codex/hp-agent-00000000-0000-4000-8000-000000000000-r1"))

    def test_readiness_allows_skipped_deploy_but_rejects_spoofed_validate(self):
        def transport(method, path, body, timeout):
            if path.endswith("/pulls/7"):
                return Response(200, json.dumps({"state": "open", "base": {"ref": "dev", "sha": SHA}, "head": {"sha": "d" * 40}}).encode())
            if "/git/ref/heads/dev" in path:
                return Response(200, json.dumps({"object": {"sha": SHA}}).encode())
            if "check-runs" in path:
                runs = [{"name": "validate", "status": "completed", "conclusion": "success", "app": {"slug": "github-actions"}, "details_url": "https://github.com/SpecialistDoctors-Inc/simy-home/actions/runs/1"}, {"name": "deploy_dev", "status": "completed", "conclusion": "skipped"}, {"name": "deploy_prod", "status": "completed", "conclusion": "neutral"}]
                return Response(200, json.dumps({"check_runs": runs}).encode())
            if path.endswith("/status"):
                return Response(200, b'{"statuses":[]}')
            raise AssertionError(path)
        provider = self.provider(transport)
        self.assertEqual(SHA, provider.readiness(7, "d" * 40)["base_sha"])
        def spoof(method, path, body, timeout):
            response = transport(method, path, body, timeout)
            if "check-runs" in path:
                value = json.loads(response.body); value["check_runs"][0]["app"] = {"slug": "evil"}
                return Response(200, json.dumps(value).encode())
            return response
        with self.assertRaisesRegex(GitHubProviderError, "candidate_validate_untrusted"):
            self.provider(spoof).readiness(7, "d" * 40)

    def test_extract_is_idempotent_and_rejects_traversal(self):
        files = {"version.json": b"{}", "assets/x.txt": b"x"}
        with tempfile.TemporaryDirectory() as directory:
            GitHub._extract(files, directory)
            GitHub._extract(files, directory)
            (Path(directory) / "other.txt").write_text("no")
            with self.assertRaisesRegex(GitHubProviderError, "artifact_directory_mismatch"):
                GitHub._extract(files, directory)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("../escape", b"bad")
            archive.writestr("version.json", b"{}")
        with self.assertRaisesRegex(GitHubProviderError, "artifact_zip_unsafe"):
            GitHub._safe_zip(buffer.getvalue())

    def test_artifact_redirect_strips_auth_and_rejects_untrusted_target(self):
        seen = []
        class Result(io.BytesIO):
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
        class Opener:
            calls = 0
            destination = "https://objects.githubusercontent.com/signed"
            def open(self, request, timeout):
                self.calls += 1; seen.append((request.full_url, dict(request.headers)))
                if self.calls == 1:
                    raise urllib.error.HTTPError(request.full_url, 302, "redirect", {"Location": self.destination}, io.BytesIO())
                return Result(b"zip")
        for destination in ("https://objects.githubusercontent.com/signed", "https://productionresultssa19.blob.core.windows.net/signed"):
            with self.subTest(destination=destination):
                seen.clear()
                opener = Opener(); opener.destination = destination
                with patch("github_provider.urllib.request.build_opener", return_value=opener):
                    provider = GitHub("token", "SpecialistDoctors-Inc/simy-home", PATH, "https://dev.example")
                    self.assertEqual(b"zip", provider._artifact_zip(1))
                self.assertIn("Authorization", seen[0][1]); self.assertNotIn("Authorization", seen[1][1])
        class BadOpener:
            def open(self, request, timeout):
                raise urllib.error.HTTPError(request.full_url, 302, "redirect", {"Location": "https://evil.example/x"}, io.BytesIO())
        with patch("github_provider.urllib.request.build_opener", return_value=BadOpener()):
            with self.assertRaisesRegex(GitHubProviderError, "artifact_redirect_untrusted"):
                GitHub("token", "SpecialistDoctors-Inc/simy-home", PATH, "https://dev.example")._artifact_zip(1)

    def test_deployment_rejects_wrong_workflow_and_artifact_binding(self):
        def transport(method, path, body, timeout):
            if "/actions/workflows/" in path:
                run = {"id": 9, "run_attempt": 1, "head_sha": SHA, "head_branch": "dev", "event": "push", "conclusion": "success", "repository": {"full_name": "SpecialistDoctors-Inc/simy-home"}, "path": ".github/workflows/other.yml"}
                return Response(200, json.dumps({"workflow_runs": [run]}).encode())
            raise AssertionError(path)
        with self.assertRaisesRegex(GitHubProviderError, "deployment_provenance_invalid"):
            self.provider(transport).read_deployment(SHA, CONTENT["changeRequest"]["id"], 1)
        def wrong_artifact(method, path, body, timeout):
            if "/actions/workflows/" in path:
                run = {"id": 9, "run_attempt": 1, "head_sha": SHA, "head_branch": "dev", "event": "push", "conclusion": "success", "repository": {"full_name": "SpecialistDoctors-Inc/simy-home"}, "path": ".github/workflows/deploy-sample-clinic.yml"}
                return Response(200, json.dumps({"workflow_runs": [run]}).encode())
            if "/actions/runs/9/artifacts" in path:
                artifact = {"id": 2, "name": f"sample-clinic-dev-{SHA}-1", "expired": False, "workflow_run": {"id": 8, "head_sha": SHA, "head_branch": "dev"}}
                return Response(200, json.dumps({"artifacts": [artifact]}).encode())
            raise AssertionError(path)
        with self.assertRaisesRegex(GitHubProviderError, "artifact_provenance_invalid"):
            self.provider(wrong_artifact).read_deployment(SHA, CONTENT["changeRequest"]["id"], 1)

    def test_reconcile_merge_requires_trusted_repo_and_branch(self):
        def transport(method, path, body, timeout):
            return Response(200, json.dumps({"merged": True, "merge_commit_sha": SHA, "base": {"ref": "dev", "repo": {"full_name": "SpecialistDoctors-Inc/simy-home"}}, "head": {"sha": "d" * 40, "ref": "codex/hp-agent-x-r1", "repo": {"full_name": "attacker/repo"}}}).encode())
        with self.assertRaisesRegex(GitHubProviderError, "merge_receipt_invalid"):
            self.provider(transport).reconcile_merge(7, "d" * 40)


if __name__ == "__main__":
    unittest.main()
