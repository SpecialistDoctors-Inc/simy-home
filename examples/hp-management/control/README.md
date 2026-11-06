# HP local editor control

Customer Codex edits ordinary static files locally. This deterministic control
service stores authorized changes in a private GitHub repository, validates the
exact artifact, publishes it on explicit authenticated approval, and reports
results. It never invokes Codex, another model, or customer build scripts.

**State (2026-11-06):** real Google/GitHub connections, customer-local save,
local live preview, native Codex confirmation, exact-artifact dev and production
delivery, recipient inbox arrival and real process-crash recovery have been
verified. The user confirmed the exact production artifact in the native card;
all nine served files matched and Sheet/mail reporting completed once. Old dev
and prod writers are fenced. The old dedicated EC2 runtime is stopped with its
encrypted disks and backups preserved after explicit resource approval. New publication still requires a fresh confirmation;
connection-test cards cannot authorize it.

## Boundaries

- `PROTOCOL.md` defines snapshot, change ZIP and saved receipt formats. Customer
  helpers need Python 3 on macOS/Linux, no Git or GitHub token. The public plugin
  is maintained in `SpecialistDoctors-Inc/simy-hp-skills`.
- Google OIDC identity is mapped to site roles. Administrator-issued exact-email
  invitations bind once to a verified immutable Google subject. Customers cannot
  set repository IDs, Drive roots, recipients or AWS destinations through tools.
- The private GitHub repo is authoritative. Drafts use one workspace branch;
  save retry uses the original operation ID and expected head. File-level B/U/R
  reconciliation keeps independent changes and returns conflicts to local Codex.
- Drive holds transfer ZIPs. A snapshot is accepted locally only with the
  authenticated operation result and matching full ZIP hash/site/workspace/base.
- DynamoDB is authoritative for permissions, leases, operation receipts and
  exact-artifact approvals. SQS FIFO orders a site's work; transactional outbox
  and conditional writes survive duplicate delivery. API enqueue is immediate,
  and a due-time indexed dispatcher recovers lost enqueue responses.
- GitHub Actions runs trusted static checks only; exact workflow/head/run/artifact
  identity and downloaded bytes are verified. An isolated nonroot Fargate
  renderer receives no task role or app secrets. See `validator/README.md` for
  actual browser isolation limits; Chromium OS sandbox is disabled in this image.
- Confirmation cards use official MCP Apps private metadata and app-only tools.
  OAuth identity, live ACLs, one-time nonce and exact artifact are checked again.
  Host metadata visibility is not cryptographic human attestation. Actual host
  behavior must be tested before publication is enabled.

## Delivery and recovery

A commit, accepted command or successful CI job is not publication. Dev preview
pointer is cleared before changing its served content and restored only after
exact readback. Production updates only the approved site tree on main and
promotes the same sealed artifact without rebuilding it. Main source state is
recorded separately from currently published bytes.

Unknown provider effects keep the site blocked until readback reconciles them.
Expected CI/renderer/CloudFront waits use durable scheduled retry, not the FIFO
message visibility timeout. Definite validation failures unblock and return
failure; error budgets/deadlines produce `needs_attention` without false success.
Revocation/cancellation permits readback of prior admitted effects, not new
writes. Publication already completed externally is recorded as a factual
`published_after_cancel_or_revocation` result. If cache cleanup remains after a
revocation, attention and the site block remain; this does not claim cancellation
rolled back publication.

If a confirmation response is lost, `hp_get_confirmation` reads the original
owned approval and any existing operation without returning its nonce. A
`prepared` read does not establish that an in-flight confirmation had no effect.
Approval audits retain their records alongside operations; their original
confirmation deadline still limits new confirmation. Explicit
`hp_cancel_confirmation` atomically withdraws an unaccepted approval. If another
surface already requested the same publication, readback still reports that
existing operation; withdrawal never rolls back an accepted publication.

Requests and Events record each local operation with its own operation UUID and
revision 1. Their `local_*` states never activate the old cloud-editor intake.

Customer-visible operations remain `reporting` until required Sheet/mail
readback completes. Only preview-ready and published outcomes send customer
mail. Workspace/draft saves append audit events without email. Provider acceptance
and recipient inbox arrival are separate evidence. Revoked/cancelled reporting
can be suppressed; deterministic configuration errors require attention.

Static manifests have source/file/transport limits and the publication intent
has a 300 KiB bound before writes. Oversized manifests fail explicitly. CloudFront
edge configuration/cache propagation is not globally atomic; a verified receipt
means the configured public URLs were read back against exact current bytes and
removed paths returned 404.

## Deployment gates

Read `CONNECTIONS.md` and `INFRA.md`. Administrator setup must prepare dedicated
GitHub App, Google web client, operator Google credentials, signing key and
webhook key references; no placeholders count as live credentials.

Before **either dev or prod** switches to `releases/<hash>`, retire the matching
legacy bucket-root writer. The old sample workflow uses `s3 sync --delete` and
could otherwise delete new release prefixes. Verify it is disabled/revoked for
that environment, capture the actual initial file set and CloudFront config
hash, and record cutover evidence. Do not change `simy-home` visibility or unrelated
organization apps as part of this migration.

Provisioning sites and invitations is an operator-only action. The MCP endpoint
cannot create/edit those bindings. Initial acceptance uses the current test
account; tshiwaku onboarding remains deferred.

## Local checks

Install the hash-locked `requirements.lock` and the pinned dependencies in
`requirements-test.txt`, then run Python3.12 unittest discovery in this directory. UI uses
`npm ci --ignore-scripts`, `npm test`, `npm run typecheck`, `npm run build`.
`build_lambda.py --verify-runtime` produces a source-hashed package and imports
it in a pinned official Lambda image with network disabled. The renderer has a
separate image/smoke test. Neither fake AWS/provider tests nor the local MCP Apps
harness prove real Google login, GitHub App permissions, Codex-host confirmation,
CloudFront switching or customer mail delivery.
