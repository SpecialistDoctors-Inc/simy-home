# Private static site repository template

Copy this directory's contents into a **new private repository**. Import the
verified published human-authored HTML/CSS/JavaScript/assets into `site/`; there is
intentionally no placeholder site or copied repository history here. The first
check requires `site/index.html`. Do not import a prior generated `version.json`:
it is reserved for the trusted packager. Preserve the site's actual public pages,
images, fonts and relative paths. Customers edit **only `site/**`**. Maintainers own
`tools/`, `tests/`, `.github/` and this document.

No package manager, framework, model, generated source build or AWS credentials
are required. Ordinary HTML, CSS, browser JavaScript and image/font files are the
source and the output. Adding `site/about/index.html` adds `/about/`; link to it
from the other pages. New pages require an HTML doctype, `html lang`, UTF-8 charset,
viewport, non-empty title and description. Internal HTML links, anchors, image
sources, stylesheet/script sources, source sets and CSS URLs/imports must resolve
to included static files. Absolute HTTP(S), mailto, tel and data links are allowed;
the validator never fetches them. Root-relative paths refer to the site's root.
Avoid `base href`, which is rejected to keep path resolution unambiguous.
The root `error.html` fallback may omit viewport and description metadata; it still
requires the HTML doctype, language, UTF-8 charset and a non-empty title.

The validator enforces a root index, UTF-8 text, NFC paths, case-folding collision
checks, no symlinks/special files, no hidden directories except `.well-known`, a
1000-file/50 MiB total/10 MiB per-file limit, and the protocol's static suffix list.
Server/build scripts and credentials/config files are rejected. JSON is parsed.
JavaScript (including inline scripts) is passed to `node --check` on stdin without
execution, import resolution or dependencies. This catches syntax mistakes; it is
not a browser compatibility test, full HTML conformance check or accessibility
review. Local/browser preview remains part of reviewing a user-facing change.

## Local validation and packaging

Use Python 3.11+ and Node 22. No local Git checkout is necessary:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 tools/validate_site.py site
python3 tools/package_site.py --site site --output output \
  --source-commit 0123456789abcdef0123456789abcdef01234567 \
  --operation-id 23456789-1234-4234-8234-123456789abc
```

Supply the actual authoritative snapshot commit and persisted operation UUID;
never invent release provenance. Validation alone needs neither value. The
packager reads the validated bytes once and writes `output/site.zip` and
`output/manifest.json`. Output must live outside `site/`. ZIP entries are sorted,
regular mode 0644, use a fixed timestamp, and store bytes without compression, so
retries do not depend on local file mtimes or a compression-library version.
Generated `version.json` lives at the served root inside the ZIP. It does not
modify local source.

For a local browser preview, unpack the ZIP to a temporary directory and serve
that directory using a trusted static HTTP server. A file URL does not reproduce
root-relative routing. Never run executables, build hooks or package scripts from
`site/`.

## CI and immutable artifact interface

The required check is **Check static site / Validate and package static site**.
The workflow validates pull requests and pushes to `dev`, runs trusted tool tests,
checks out and packages the exact PR head SHA (or `github.sha` for a push), then
uploads an immutable Actions artifact. The
server must match the desired revision/event before accepting a check or artifact.
The deterministic CI operation UUID is UUID5 with namespace URL and name
`https://github.com/{owner}/{repo}/commit/{40hex-SHA}`. Reruns keep identical package
bytes; the Actions artifact name includes the attempt only to avoid upload-name
collisions. Official Actions are pinned to full commits, checkout does not persist
credentials, and the job has only `contents: read`. There are no deploy jobs,
OIDC permissions, environment secrets, production credentials, package installs,
or model calls.

The artifact contains these two files:

| File | Contract |
| --- | --- |
| `site.zip` | Exact served root including generated `version.json`; no wrapper directory |
| `manifest.json` | Source/operation identity, source tree digest, ZIP digest and complete entry table |

Manifest fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | Integer `1` |
| `kind` | `static-site-artifact` |
| `source_commit` | Required lowercase 40-hex authoritative source commit |
| `operation_id` | Canonical persisted UUID |
| `source_sha256` | Full SHA-256 of canonical JSON source-only file records |
| `version` | Full `source_sha256`; a display/version identity, never a prefix match |
| `artifact_sha256` | Full SHA-256 of raw `site.zip` bytes |
| `files` | Sorted complete ZIP file records `{path, sha256, size}`, including `version.json` |

Canonical JSON uses UTF-8, `ensure_ascii=False`, sorted object keys and compact
`,`/`:` separators. Source records are sorted by relative POSIX path and contain
`path`, lowercase SHA-256 and byte `size`. `source_sha256` excludes generated
`version.json` to avoid circular hashing. `version.json` contains exactly
`schema_version`, `source_commit`, `operation_id`, `source_sha256` and `version`.
The ZIP digest includes that metadata. These are the new template's snake_case
fields; they differ from the older sample-clinic deployment's camelCase metadata.

The server selects an artifact by immutable Actions artifact ID, records its run
ID, validates repository/workflow/event/source SHA and successful check conclusion,
then verifies the downloaded `site.zip` hash and each manifest record before use.
The workflow summary prints that artifact ID, Actions outer artifact digest,
source commit, full source digest and **inner site.zip digest**. The outer Actions
artifact digest and inner ZIP digest are distinct values. Names are display-only;
never choose a release by a mutable/latest artifact name. An expired artifact
requires a fresh verified run and explicit preparation; do not silently substitute
another package.

No CI result deploys the site. The privileged server's preview/publication worker
owns deployment and separate approval. It must publish these exact bytes and read
back `/version.json` from the actual served origin with cache bypass, comparing
all identity/digest fields to the selected artifact and its persisted operation.
A hosted version document alone does not prove every static byte: the worker must
also verify the deployed artifact/object manifest through its storage/readback
boundary. Approval binds the full resulting artifact digest and source revision.
A package or successful CI check alone is not preview/deployment proof.
