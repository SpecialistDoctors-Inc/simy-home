"""Narrow GitHub REST adapter for the standalone HP delivery controller.

The controller owns operation admission/reconciliation.  This adapter never
retries an uncertain mutation: a later controller tick must read the branch or
pull request and decide whether it is already represented remotely.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import urllib.error
import urllib.parse
import urllib.request
from uuid import UUID
import zipfile
from provider_errors import classify_effect, note_write_attempt


SHA = re.compile(r"^[a-f0-9]{40}$")
WORKFLOW = "deploy-sample-clinic.yml"
REQUIRED_CHECKS = {"validate"}


class GitHubProviderError(RuntimeError):
    """A safe, status-only GitHub API failure."""

    def __init__(self, code: str, status: int | None = None):
        super().__init__(code)
        self.status = status


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Make redirect handling explicit: API credentials never follow a URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _sha256_files(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name in sorted(files):
        if name == "version.json":
            continue
        data = files[name]
        digest.update(f"{name}\0{len(data)}\0".encode())
        digest.update(data)
    return digest.hexdigest()


class GitHub:
    """REST-only adapter restricted to one configured file on one dev branch."""

    def __init__(self, token: str, repo: str, content_path: str, dev_url: str,
                 transport=None, web_transport=None, timeout: float = 10.0):
        if not isinstance(token, str) or not token or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ValueError("invalid_github_configuration")
        if content_path != "examples/sample-clinic/content/clinic.json" or not self._safe_path(content_path):
            raise ValueError("untrusted_content_path")
        parsed = urllib.parse.urlparse(dev_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError("invalid_dev_url")
        self.token, self.repo, self.content_path = token, repo, content_path
        self.dev_url, self.timeout = dev_url.rstrip("/"), timeout
        self._custom_transport = transport is not None
        self.transport = transport or self._urllib_transport
        self.web_transport = web_transport or self._urllib_web_transport

    @staticmethod
    def _safe_path(value: str) -> bool:
        path = PurePosixPath(value)
        return bool(path.parts) and not path.is_absolute() and "\\" not in value and not any(p in {"", ".", "..", ".git", ".github"} for p in path.parts)

    @staticmethod
    def _read_limited(result, limit: int) -> bytes:
        body = result.read(limit + 1)
        if len(body) > limit:
            raise GitHubProviderError("github_response_too_large")
        return body

    @staticmethod
    def _open_no_redirect(request, timeout: float):
        return urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout)

    def _urllib_transport(self, method: str, path: str, body: bytes | None, timeout: float) -> Response:
        request = urllib.request.Request("https://api.github.com" + path, data=body, method=method,
            headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {self.token}",
                     "X-GitHub-Api-Version": "2022-11-28", **({"Content-Type": "application/json"} if body else {})})
        try:
            with self._open_no_redirect(request, timeout) as result:
                return Response(result.status, self._read_limited(result, 1_000_000))
        except urllib.error.HTTPError as error:
            return Response(error.code, self._read_limited(error, 4096))
        except urllib.error.URLError as error:
            raise GitHubProviderError("github_transport_unavailable") from error

    def _urllib_web_transport(self, url: str, timeout: float) -> Response:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "*/*"}), timeout=timeout) as result:
                return Response(result.status, self._read_limited(result, 10_000_000))
        except urllib.error.HTTPError as error:
            return Response(error.code, self._read_limited(error, 4096))
        except urllib.error.URLError as error:
            raise GitHubProviderError("dev_readback_unavailable") from error

    @staticmethod
    def _response(raw) -> Response:
        if isinstance(raw, Response):
            return raw
        if isinstance(raw, tuple) and len(raw) == 2:
            return Response(raw[0], raw[1])
        raise TypeError("invalid_transport_response")

    def _json(self, method: str, path: str, payload: object | None = None, *, allow=(200,)) -> object:
        response = self._request(method, path, payload)
        if response.status not in allow:
            raise GitHubProviderError("github_api_error", response.status)
        try:
            return json.loads(response.body.decode()) if response.body else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise GitHubProviderError("github_invalid_response", response.status) from error

    def _request(self, method: str, path: str, payload: object | None = None) -> Response:
        body = _canonical(payload) if payload is not None else None
        if method not in {"GET", "HEAD"}:
            note_write_attempt(self)
        return self._response(self.transport(method, path, body, self.timeout))

    def _bytes(self, method: str, path: str, payload: object | None = None, *, allow=(200,)) -> bytes:
        response = self._request(method, path, payload)
        if response.status not in allow:
            raise GitHubProviderError("github_api_error", response.status)
        return response.body

    def _web(self, url: str) -> bytes:
        response = self._response(self.web_transport(url, self.timeout))
        if response.status != 200:
            raise GitHubProviderError("dev_readback_error", response.status)
        return response.body

    def _artifact_zip(self, artifact_id: int) -> bytes:
        """Download an Actions ZIP without forwarding a repo token to its CDN."""
        path = f"/repos/{self.repo}/actions/artifacts/{artifact_id}/zip"
        if self._custom_transport:
            return self._bytes("GET", path)
        url = "https://api.github.com" + path
        headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {self.token}",
                   "X-GitHub-Api-Version": "2022-11-28"}
        for hop in range(3):
            request = urllib.request.Request(url, headers=headers)
            try:
                result = self._open_no_redirect(request, self.timeout)
                with result:
                    if result.status != 200:
                        raise GitHubProviderError("artifact_download_error", result.status)
                    return self._read_limited(result, 50_000_000)
            except urllib.error.HTTPError as error:
                if error.code not in {301, 302, 303, 307, 308}:
                    raise GitHubProviderError("artifact_download_error", error.code) from None
                location = error.headers.get("Location")
                parsed = urllib.parse.urlparse(location) if isinstance(location, str) else None
                allowed = {"github.com", "api.github.com", "objects.githubusercontent.com"}
                # GitHub Actions serves artifacts from Azure Blob Storage as
                # documented in its hosted-runner communication requirements.
                # Only follow the HTTPS URL returned by GitHub; no repo token
                # is forwarded to any redirect destination.
                if (not parsed or parsed.scheme != "https" or not parsed.hostname
                        or parsed.username or parsed.password or parsed.port not in (None, 443)
                        or (parsed.hostname not in allowed
                            and not parsed.hostname.endswith(".githubusercontent.com")
                            and not parsed.hostname.endswith(".blob.core.windows.net"))):
                    raise GitHubProviderError("artifact_redirect_untrusted")
                url, headers = location, {"Accept": "application/octet-stream"}
        raise GitHubProviderError("artifact_redirect_limit")

    def _ref(self, branch: str) -> str | None:
        response = self._request("GET", f"/repos/{self.repo}/git/ref/heads/{urllib.parse.quote(branch, safe='')}")
        if response.status == 404:
            return None
        if response.status != 200:
            raise GitHubProviderError("github_api_error", response.status)
        try:
            value = json.loads(response.body.decode())
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise GitHubProviderError("github_invalid_response", response.status) from error
        sha = value.get("object", {}).get("sha") if isinstance(value, dict) else None
        if not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise GitHubProviderError("invalid_branch_ref")
        return sha

    def _content(self, ref: str) -> tuple[dict, str]:
        query = urllib.parse.urlencode({"ref": ref})
        value = self._json("GET", f"/repos/{self.repo}/contents/{urllib.parse.quote(self.content_path, safe='/')}?{query}")
        if not isinstance(value, dict) or value.get("type") != "file" or value.get("encoding") != "base64":
            raise GitHubProviderError("invalid_content_response")
        blob = value.get("sha")
        encoded = value.get("content")
        if not isinstance(blob, str) or not re.fullmatch(r"[a-f0-9]{40,64}", blob) or not isinstance(encoded, str):
            raise GitHubProviderError("invalid_content_response")
        try:
            # GitHub's Contents response commonly line-wraps base64 text.
            parsed = json.loads(base64.b64decode("".join(encoded.split()).encode(), validate=True).decode())
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise GitHubProviderError("invalid_content_json") from error
        if not isinstance(parsed, dict):
            raise GitHubProviderError("invalid_content_json")
        return parsed, blob

    def base(self) -> dict:
        sha = self._ref("dev")
        if sha is None:
            raise GitHubProviderError("dev_branch_missing")
        content, blob_sha = self._content(sha)
        return {"sha": sha, "content": content, "blob_sha": blob_sha}

    @staticmethod
    def _branch(request_id: str, revision: int) -> str:
        return f"codex/hp-agent-{UUID(request_id)}-r{revision}"

    def _pulls(self, branch: str) -> list[dict]:
        owner = self.repo.split("/", 1)[0]
        query = urllib.parse.urlencode({"state": "all", "head": f"{owner}:{branch}", "base": "dev", "per_page": "10"})
        value = self._json("GET", f"/repos/{self.repo}/pulls?{query}")
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise GitHubProviderError("invalid_pull_response")
        return value

    def _candidate_pr(self, branch: str, head_sha: str) -> dict | None:
        pulls = self._pulls(branch)
        if len(pulls) > 1:
            raise GitHubProviderError("ambiguous_candidate_pr")
        if not pulls:
            return None
        pr = pulls[0]
        if pr.get("state") != "open" or pr.get("base", {}).get("ref") != "dev" or pr.get("head", {}).get("ref") != branch or pr.get("head", {}).get("sha") != head_sha:
            raise GitHubProviderError("candidate_pr_mismatch")
        return pr

    def reconcile_candidate(self, request_id, revision, base_sha, original_blob_sha, content) -> dict | None:
        """Read-only recovery for a possibly completed candidate mutation.

        ``None`` means absent or only partially created.  A different existing
        branch is unsafe, not partial, and therefore fails closed.
        """
        request_id, revision = str(UUID(str(request_id))), int(revision)
        if revision < 1 or not SHA.fullmatch(str(base_sha)) or not re.fullmatch(r"[a-f0-9]{40,64}", str(original_blob_sha)) or not isinstance(content, dict):
            raise ValueError("invalid_candidate_input")
        branch = self._branch(request_id, revision)
        head_sha = self._ref(branch)
        if head_sha is None:
            return None
        existing, blob_sha = self._content(branch)
        if existing != content:
            # A just-created branch still equals the original base and is safe
            # to classify as partial; anything else is a foreign mutation.
            if head_sha == base_sha and blob_sha == original_blob_sha:
                return None
            raise GitHubProviderError("candidate_payload_conflict")
        pr = self._candidate_pr(branch, head_sha)
        if pr is None:
            return None
        expected_body = f"Standalone HP candidate. base={base_sha} path={self.content_path}"
        if pr.get("body") != expected_body:
            raise GitHubProviderError("candidate_pr_mismatch")
        return {"branch": branch, "head_sha": head_sha, "pr_number": pr["number"], "pr_url": pr["html_url"]}

    @classify_effect
    def ensure_candidate(self, request_id, revision, base_sha, original_blob_sha, content) -> dict:
        request_id, revision = str(UUID(str(request_id))), int(revision)
        if revision < 1 or not SHA.fullmatch(str(base_sha)) or not re.fullmatch(r"[a-f0-9]{40,64}", str(original_blob_sha)) or not isinstance(content, dict):
            raise ValueError("invalid_candidate_input")
        branch = self._branch(request_id, revision)
        branch_sha = self._ref(branch)
        if branch_sha is None:
            # A 422 is deliberately not retried: the next controller tick reads
            # the branch and reconciles a possible successful creation.
            self._json("POST", f"/repos/{self.repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": base_sha}, allow=(201,))
            branch_sha = self._ref(branch)
            if branch_sha != base_sha:
                raise GitHubProviderError("candidate_base_drift")
        existing, blob_sha = self._content(branch)
        if existing != content:
            if blob_sha != original_blob_sha or branch_sha != base_sha:
                raise GitHubProviderError("candidate_payload_conflict")
            payload = {"message": f"HP notice {request_id} revision {revision}", "content": base64.b64encode(_canonical(content)).decode(),
                       "sha": original_blob_sha, "branch": branch}
            result = self._json("PUT", f"/repos/{self.repo}/contents/{urllib.parse.quote(self.content_path, safe='/')}", payload, allow=(200, 201))
            branch_sha = result.get("commit", {}).get("sha") if isinstance(result, dict) else None
            if not isinstance(branch_sha, str) or not SHA.fullmatch(branch_sha):
                raise GitHubProviderError("candidate_commit_missing")
        branch_sha = self._ref(branch)
        if branch_sha is None:
            raise GitHubProviderError("candidate_branch_missing")
        pr = self._candidate_pr(branch, branch_sha)
        if pr is None:
            title = f"HP notice {request_id} revision {revision}"
            body = f"Standalone HP candidate. base={base_sha} path={self.content_path}"
            pr = self._json("POST", f"/repos/{self.repo}/pulls", {"title": title, "head": branch, "base": "dev", "body": body}, allow=(201,))
        if not isinstance(pr, dict):
            raise GitHubProviderError("candidate_pr_missing")
        number, url = pr.get("number"), pr.get("html_url")
        if not isinstance(number, int) or number < 1 or not isinstance(url, str):
            raise GitHubProviderError("candidate_pr_missing")
        return {"branch": branch, "head_sha": branch_sha, "pr_number": number, "pr_url": url}

    def readiness(self, pr: int, head_sha: str):
        if not isinstance(pr, int) or pr < 1 or not SHA.fullmatch(head_sha):
            raise ValueError("invalid_readiness_input")
        pull = self._json("GET", f"/repos/{self.repo}/pulls/{pr}")
        current_base = self._ref("dev")
        if not isinstance(pull, dict) or pull.get("state") != "open" or pull.get("base", {}).get("ref") != "dev" or pull.get("head", {}).get("sha") != head_sha:
            raise GitHubProviderError("candidate_pr_mismatch")
        if current_base != pull.get("base", {}).get("sha"):
            raise GitHubProviderError("candidate_base_drift")
        checks = self._json("GET", f"/repos/{self.repo}/commits/{head_sha}/check-runs?filter=latest&per_page=100")
        statuses = self._json("GET", f"/repos/{self.repo}/commits/{head_sha}/status")
        runs = checks.get("check_runs", []) if isinstance(checks, dict) else []
        states = statuses.get("statuses", []) if isinstance(statuses, dict) else []
        if not isinstance(runs, list) or not isinstance(states, list):
            raise GitHubProviderError("invalid_check_response")
        validates = [item for item in runs if isinstance(item, dict) and item.get("name") == "validate"]
        if not validates:
            return None
        # A check named validate is not authority by itself.  GitHub Actions is
        # required, and, when GitHub supplies a details URL, it must be a run
        # URL rather than an arbitrary external check page.
        if len(validates) != 1:
            raise GitHubProviderError("candidate_validate_untrusted")
        validate = validates[0]
        app = validate.get("app")
        details = validate.get("details_url")
        if not isinstance(app, dict) or app.get("slug") != "github-actions":
            raise GitHubProviderError("candidate_validate_untrusted")
        if details is not None:
            parsed = urllib.parse.urlparse(details) if isinstance(details, str) else None
            if not parsed or parsed.scheme != "https" or parsed.netloc != "github.com" or "/actions/runs/" not in parsed.path:
                raise GitHubProviderError("candidate_validate_untrusted")
        if validate.get("status") != "completed":
            return None
        if validate.get("conclusion") != "success":
            raise GitHubProviderError("candidate_check_failed")
        for item in runs:
            if not isinstance(item, dict):
                raise GitHubProviderError("invalid_check_response")
            if item is validate:
                continue
            if item.get("status") != "completed":
                return None
            if item.get("conclusion") not in {"success", "neutral", "skipped"}:
                raise GitHubProviderError("candidate_check_failed")
        for item in states:
            if item.get("state") in {"failure", "error"}:
                raise GitHubProviderError("candidate_status_failed")
            if item.get("state") not in {"success"}:
                return None
        return {"pr": pr, "head_sha": head_sha, "base_sha": current_base}

    def reconcile_merge(self, pr: int, head_sha: str) -> dict | None:
        """Read only: identify an already-completed squash merge after timeout."""
        if not isinstance(pr, int) or pr < 1 or not SHA.fullmatch(head_sha):
            raise ValueError("invalid_merge_input")
        pull = self._json("GET", f"/repos/{self.repo}/pulls/{pr}")
        if not isinstance(pull, dict) or pull.get("head", {}).get("sha") != head_sha:
            raise GitHubProviderError("merge_head_mismatch")
        base, head = pull.get("base"), pull.get("head")
        if (not isinstance(base, dict) or not isinstance(head, dict) or base.get("ref") != "dev"
                or not isinstance(head.get("ref"), str) or not head["ref"].startswith("codex/hp-agent-")):
            raise GitHubProviderError("merge_receipt_invalid")
        for repo in (base.get("repo"), head.get("repo")):
            if not isinstance(repo, dict) or repo.get("full_name") != self.repo:
                raise GitHubProviderError("merge_receipt_invalid")
        if pull.get("merged") is not True:
            return None
        merge_sha = pull.get("merge_commit_sha")
        if not isinstance(merge_sha, str) or not SHA.fullmatch(merge_sha):
            raise GitHubProviderError("merge_receipt_invalid")
        return {"merge_sha": merge_sha}

    @classify_effect
    def merge_dev(self, pr: int, head_sha: str, expected_base_sha: str) -> dict:
        if not isinstance(pr, int) or pr < 1 or not SHA.fullmatch(head_sha) or not SHA.fullmatch(expected_base_sha):
            raise ValueError("invalid_merge_input")
        # Read checks at the merge linearization point, not on a previous
        # controller poll.  A pending check is deliberately not merged.
        ready = self.readiness(pr, head_sha)
        if ready is None or ready.get("base_sha") != expected_base_sha:
            raise GitHubProviderError("merge_not_ready")
        pull = self._json("GET", f"/repos/{self.repo}/pulls/{pr}")
        current_base = self._ref("dev")
        if (not isinstance(pull, dict) or pull.get("state") != "open" or pull.get("base", {}).get("ref") != "dev"
                or not str(pull.get("head", {}).get("ref", "")).startswith("codex/hp-agent-")
                or pull.get("head", {}).get("sha") != head_sha or current_base != expected_base_sha
                or pull.get("base", {}).get("sha") != expected_base_sha):
            raise GitHubProviderError("merge_base_or_head_drift")
        files = self._json("GET", f"/repos/{self.repo}/pulls/{pr}/files?per_page=100")
        _, head_blob = self._content(head_sha)
        if (not isinstance(files, list) or len(files) != 1 or files[0].get("filename") != self.content_path
                or files[0].get("status") != "modified" or files[0].get("sha") != head_blob):
            raise GitHubProviderError("merge_path_mismatch")
        try:
            result = self._json("PUT", f"/repos/{self.repo}/pulls/{pr}/merge", {"sha": head_sha, "merge_method": "squash"}, allow=(200,))
        except GitHubProviderError as error:
            if error.status is None or error.status < 500:
                raise
            observed = self._json("GET", f"/repos/{self.repo}/pulls/{pr}")
            recovered = self.reconcile_merge(pr, head_sha)
            if recovered is not None:
                return recovered
            raise GitHubProviderError("ambiguous_merge_reconcile_required") from None
        if not isinstance(result, dict) or result.get("merged") is not True or not isinstance(result.get("sha"), str) or not SHA.fullmatch(result["sha"]):
            raise GitHubProviderError("merge_rejected")
        return {"merge_sha": result["sha"]}

    @staticmethod
    def _safe_zip(data: bytes) -> dict[str, bytes]:
        try:
            archive = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as error:
            raise GitHubProviderError("artifact_zip_invalid") from error
        files: dict[str, bytes] = {}
        total = 0
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            mode = (info.external_attr >> 16) & 0o170000
            if info.is_dir():
                if (not path.parts or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts)
                        or mode not in {0, 0o040000}):
                    raise GitHubProviderError("artifact_zip_unsafe")
                continue
            if (not path.parts or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts)
                    or info.file_size > 10_000_000 or str(path) in files or mode not in {0, 0o100000}):
                raise GitHubProviderError("artifact_zip_unsafe")
            total += info.file_size
            if total > 50_000_000:
                raise GitHubProviderError("artifact_zip_unsafe")
            files[str(path)] = archive.read(info)
        if not files or "version.json" not in files:
            raise GitHubProviderError("artifact_zip_invalid")
        return files

    @staticmethod
    def _extract(files: dict[str, bytes], artifact_dir) -> None:
        if artifact_dir is None:
            return
        destination = Path(artifact_dir)
        if destination.exists() and (destination.is_symlink() or not destination.is_dir()):
            raise GitHubProviderError("artifact_directory_unsafe")
        expected = {str(PurePosixPath(name)) for name in files}
        if destination.exists() and any(destination.iterdir()):
            actual: set[str] = set()
            actual_dirs: set[str] = set()
            for root, dirs, names in os.walk(destination, followlinks=False):
                root_path = Path(root)
                for entry in dirs + names:
                    candidate = root_path / entry
                    info = candidate.lstat()
                    if stat.S_ISLNK(info.st_mode) or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                        raise GitHubProviderError("artifact_directory_unsafe")
                for name in names:
                    candidate = root_path / name
                    if not candidate.is_file():
                        raise GitHubProviderError("artifact_directory_unsafe")
                    actual.add(candidate.relative_to(destination).as_posix())
                for name in dirs:
                    actual_dirs.add((root_path / name).relative_to(destination).as_posix())
            expected_dirs = set()
            for name in expected:
                parent = PurePosixPath(name).parent
                while str(parent) != ".":
                    expected_dirs.add(str(parent))
                    parent = parent.parent
            if (actual != expected or actual_dirs != expected_dirs
                    or any((destination / name).read_bytes() != files[name] for name in expected)):
                raise GitHubProviderError("artifact_directory_mismatch")
            return
        destination.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            target = destination.joinpath(*PurePosixPath(name).parts)
            if target.exists() and target.is_symlink():
                raise GitHubProviderError("artifact_directory_unsafe")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    def read_deployment(self, merge_sha: str, request_id: str, revision: int, artifact_dir=None):
        if not SHA.fullmatch(merge_sha) or int(revision) < 1:
            raise ValueError("invalid_deployment_input")
        request_id, revision = str(UUID(str(request_id))), int(revision)
        query = urllib.parse.urlencode({"branch": "dev", "event": "push", "status": "completed", "head_sha": merge_sha, "per_page": "20"})
        runs = self._json("GET", f"/repos/{self.repo}/actions/workflows/{WORKFLOW}/runs?{query}")
        rows = runs.get("workflow_runs", []) if isinstance(runs, dict) else []
        if not rows:
            return None
        if not isinstance(rows, list):
            raise GitHubProviderError("invalid_deployment_response")
        matches = [row for row in rows if isinstance(row, dict) and row.get("head_sha") == merge_sha and row.get("head_branch") == "dev" and row.get("event") == "push"]
        if len(matches) != 1:
            raise GitHubProviderError("deployment_provenance_invalid")
        run = matches[0]
        if run.get("conclusion") != "success" or not isinstance(run.get("id"), int) or not isinstance(run.get("run_attempt"), int):
            raise GitHubProviderError("deployment_failed")
        if run.get("repository", {}).get("full_name") != self.repo or run.get("path") != ".github/workflows/deploy-sample-clinic.yml":
            raise GitHubProviderError("deployment_provenance_invalid")
        artifacts = self._json("GET", f"/repos/{self.repo}/actions/runs/{run['id']}/artifacts?per_page=100")
        values = artifacts.get("artifacts", []) if isinstance(artifacts, dict) else []
        expected = f"sample-clinic-dev-{merge_sha}-{run['run_attempt']}"
        matches = [item for item in values if isinstance(item, dict) and item.get("name") == expected]
        if len(matches) != 1:
            raise GitHubProviderError("artifact_provenance_invalid")
        artifact = matches[0]
        workflow_run = artifact.get("workflow_run")
        if (artifact.get("expired") is not False or not isinstance(artifact.get("id"), int)
                or not isinstance(workflow_run, dict) or workflow_run.get("id") != run["id"]
                or workflow_run.get("head_sha") != merge_sha or workflow_run.get("head_branch") != "dev"):
            raise GitHubProviderError("artifact_provenance_invalid")
        files = self._safe_zip(self._artifact_zip(artifact["id"]))
        try:
            version = json.loads(files["version.json"].decode())
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise GitHubProviderError("artifact_manifest_invalid") from error
        artifact_hash = _sha256_files(files)
        if (not isinstance(version, dict) or version.get("schemaVersion") != 1 or version.get("siteId") != "sample-clinic"
                or version.get("environment") != "dev" or version.get("sourceRevision") != merge_sha
                or version.get("artifactHash") != artifact_hash or version.get("requestId") != request_id
                or version.get("requestRevision") != revision):
            raise GitHubProviderError("artifact_manifest_mismatch")
        for name, data in files.items():
            remote = self._web(f"{self.dev_url}/{urllib.parse.quote(name, safe='/')}")
            if remote != data:
                raise GitHubProviderError("dev_static_readback_mismatch")
        self._extract(files, artifact_dir)
        return {"source_sha": merge_sha, "artifact_id": str(artifact["id"]), "artifact_hash": artifact_hash,
                "run_id": run["id"], "run_attempt": run["run_attempt"], "url": self.dev_url,
                "tests_passed": True, "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}}
