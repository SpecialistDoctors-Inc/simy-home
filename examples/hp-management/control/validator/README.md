# Secretless static browser validator

This image renders the exact checked static artifact in a disposable task. It has
no task IAM role, OAuth credentials, model SDK, Codex, npm, dependency installation
or source build at runtime. Customer JavaScript executes only inside Chromium.
The consumer validates an immutable reviewed task-definition revision and final
image digest before any candidate effects, seals a durable operation/artifact
intent, and launches that exact task/network configuration. Deployment gates stay
disabled until the actual image/network/approval boundary has been reviewed and
exercised in AWS. Local smoke is not AWS isolation or production proof.

`image-manifest.json` records the observed official base manifest. Dockerfile pins
the Linux/amd64 Playwright Python 1.56.0 base by digest; requirements pin the actual
observed Python package versions. A built image has its own final manifest digest:
review and configure **that final digest**, never substitute the base-image digest
or a local Docker configuration/image ID. No registry push is performed here.

## Actual isolation and limitations

The image runs user 1000, has a read-only root, drops all Linux capabilities, has
no privileged mode, secrets, task role, host mounts or execute-command access, and
uses a task-local writable `/tmp` scratch volume. Its only network capabilities
are four short-lived S3 URLs: one exact artifact GET and three exact conditional
PUTs (`desktop.png`, `mobile.png`, `report.json`). The launcher supplies expected
bucket-owner headers, and PUTs use `If-None-Match: *`. Capability URLs are never
injected into the page or logged. The worker self-exits at the sealed deadline;
there is no StopTask permission and no shared service or process is stopped.

The local hardened Docker smoke could not start Chromium's OS namespace sandbox
(`No usable sandbox`). The implemented Fargate-compatible launch is explicitly
`headless=True, chromium_sandbox=False`; reports and receipts record
`chromium_os_sandbox: false`. The isolation claim is the dedicated secretless
container/task, the reviewed network and request routing, **not** Chromium's OS
sandbox. A Chromium exploit could compromise this task and its scoped transfer
capabilities; this is not proof of hostile-browser exploit containment. A stronger
browser sandbox requires a separately supported runtime and independent approval.
Do not weaken the task's privileges or shared host configuration to make it start.

The trusted Python process downloads and safely validates the artifact ZIP, checks
its exact SHA-256 and generated source/version metadata, and serves extracted
regular static files on an ephemeral **127.0.0.1-only** HTTP server. Browser routes
permit only that exact host and port, abort every external/private request, block
websockets and service workers, and apply a restrictive network CSP. The task's
reviewed security group separately denies private/link-local egress and allows
public HTTPS only for scoped input/output transfers. Presigned transfer redirects
are rejected. No website-supplied program runs outside the browser.

At desktop 1440x1000 and mobile 390x844, the renderer requires a 200 index response,
visible nonempty body, no page/console/HTTP errors, no blocked resource attempts,
and no horizontal overflow. It captures both full-page PNGs and a JSON report.
These deterministic checks do not judge design quality, accessibility, every
interactive path or every page. Human screenshot review remains necessary.

## Consumer interface

`BrowserValidation(store, ecs, s3, config)` exposes:

- `preflight(site, guard)`: read-only task/image/isolation/bucket admission checks.
- `validate(site, preview, artifact_key, operation_id, guard)`: seals intent and
  launches or safely resumes the exact operation, then verifies complete output.
- `reconcile(site, preview, artifact_key, operation_id, fence_guard)`: reads only;
  returns verified evidence or an explicit `safe_to_resume` control signal. A
  revoked operation never re-enters launch under a fence-only guard.

The preview carries `site_id`, full `source_commit`, `artifact_sha256` and
`package_operation_id`. The input key must be exactly
`artifacts/{site_id}/{artifact_sha256}/site.zip`. Output keys are exactly
`browser-validation/{site_id}/{operation_id}/{artifact_sha256}/desktop.png`,
`mobile.png` and `report.json`. Input and output digests, source metadata, task
identity, image digest, both viewport results and each screenshot hash are checked.
The receipt contains the report key/hash and a list of screenshot keys.

Config fields are `enabled` (explicit true), `account_id` (209300895845), `region`,
`cluster` (exact ARN), `task_definition` (exact revision ARN), `image_digest`
(`sha256:...` final image), `container_name`, reviewed `subnet_ids` and
`security_group_ids`, `artifact_bucket`, `output_bucket`, and `deadline_seconds`
(60-600). No customer chooses URLs, AWS targets, IAM roles or task overrides.
The task definition must have only a task-local writable `/tmp` volume, nonroot
user, read-only root and no task application role/secrets/environment files.

RunTask `clientToken` is the full deterministic operation/site/source/artifact
fingerprint, with its first 32 hex characters as `startedBy`. The entire request,
including scoped URLs and deadline, is persisted **before** RunTask and reused
unchanged after an ambiguous acknowledgement. A returned task ARN is persisted
for readback, including STOPPED tasks. Lost acknowledgements can be discovered by
startedBy while running; a stopped task not discoverable by ListTasks requires an
actively authorized replay of the identical idempotent RunTask request. Read-only
reconciliation never launches one. Deadline or definite task/render failure raises
a rejection; running/missing-yet-bounded output raises a durable waiting exception.

## Local or CI smoke

From the repository root, with Docker available:

```sh
docker build --platform linux/amd64 -t hp-browser-validator:local-test examples/hp-management/control/validator
mkdir -p examples/hp-management/control/validator/smoke-output
docker run --rm --platform linux/amd64 --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges --user 1000:1000 \
  --tmpfs /tmp:rw,mode=1777,size=512m \
  --mount "type=bind,source=$PWD/examples/hp-management/control/validator/smoke-output,target=/output" \
  --entrypoint python3 hp-browser-validator:local-test /opt/validator/smoke.py
python3 -m unittest discover -s examples/hp-management/control -p test_browser_validation.py -v
```

Smoke has no cloud credentials, URLs or external network. It verifies a valid
render, JavaScript error detection, overflow detection, and rejection of both
169.254.169.254 and an external script request. Results and screenshots stay under
ignored `smoke-output/`. The valid desktop/mobile screenshots were visually
inspected locally. Negative cases must produce `verified:false`; the smoke command
succeeds only when every expected positive/negative outcome matches.
