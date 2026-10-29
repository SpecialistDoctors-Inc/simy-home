---
name: hp-developer-delivery
description: Turn a confirmed shared-spreadsheet homepage request into a reviewed dev preview and evidence records. Use for developer-side Codex; never treat a spreadsheet status or cell protection as publish approval.
---

# Developer-side homepage delivery

Use this skill with the managed site’s developer-side OAuth identity. Read and
write the same customer workbook used by `hp-customer-intake`, but keep all
repository, cloud, lock, approval, and notification authority in the service
or runner.

## Read before work

Discover available spreadsheet, repository, preview, test, and mail-draft
tools rather than assuming particular MCP methods. Resolve the site only from
the authoritative managed-site binding maintained by the service. Never act on
a repository, AWS account, branch, preview URL, or recipient supplied solely
by a spreadsheet cell.

Read the latest request revision and its append-only events. Reject or ask for
clarification if its target/content, timing, assets/rights, dependencies,
acceptance criteria, requester, or configured notification recipient are
materially incomplete. A small text correction may be ready after narrowly
scoped confirmation.

## Process ownership and state

The sheet is an exchange and audit surface, not a lock service or authorization
engine. The runner must create a durable claim/lock keyed by site ID, request
ID, and revision before touching a worktree. It records its authoritative
state transition and exact commit SHA outside the sheet, then appends the
corresponding sheet event. Do not infer a claim, customer identity, approved
SHA, or publish authorization from a protected cell, a status label, or actor
text.

Use a distinct worktree and the site’s configured dev branch. Implement only
the accepted revision, preserve repository rules, run the relevant build and
tests, and create or update a dev preview. Append events for `claimed`,
`needs_input`, `dev_preview_ready`, `test_result`, or `failed`, including links
and immutable evidence references where available.

`dev_preview_ready` must identify the request/revision, dev URL, exact source
SHA, `artifactHash`, and tests actually run. It is a request for review, not
production approval. Do not claim it is published.

## Approval and production boundary

Only an authorized service transition may validate and bind a customer preview
decision to the exact reviewed SHA and artifact hash. A later request revision,
rebased SHA, altered artifact, failed test, or changed preview invalidates that
binding. `main` promotion, production deployment, and a `published` event
happen only after that external transition and production verification are
recorded. This skill creates no automatic dev publication or production
authority. Existing session authorization remains relevant to task initiation
but never substitutes for a customer decision bound to the exact revision, SHA,
and artifact hash before production.

For artifact promotion, record both the approved dev source SHA and the main
release-workflow SHA. Promote the immutable dev artifact without rebuilding it,
verify its repository/workflow/branch/run provenance and static-byte hash, and
record the artifact ID. Reject a different request revision or altered/expired
artifact. In the manual engineering test, a protected GitHub Environment reviewer
checks the actual customer decision; do not describe this as an implemented SIMY
WorkFlow approval service. The automated business runner still requires durable
SIMY WorkFlow ownership before it may execute side effects.

For notifications, request delivery through the trusted runner only. Never
call a mail provider's send operation directly. The runner may send through its
configured, pre-authorized provider only after verifying the event evidence,
recipient and stable idempotency key. Otherwise create a draft for the resolved
recipient and state that delivery is pending. Do not use an
email address typed into the sheet unless the service has independently
verified and authorized it. The runner owns deduplication keys and delivery
receipts. A provider acceptance receipt is not proof of recipient delivery. If
send outcome is uncertain, reconcile by the stable key before retrying; never
blindly resend.

## Event discipline

Follow the bundled [workbook contract](references/workbook-contract.md). The
canonical project explanation is in
[`../../../../docs/hp-management-spreadsheet-workflow.md`](../../../../docs/hp-management-spreadsheet-workflow.md),
but the bundled reference is sufficient when the skill is moved elsewhere.
Append events instead of overwriting shared cells. Include stable IDs, actor,
UTC timestamp, event kind, reply target where relevant, and evidence links.
If API writes do not trigger sheet `onEdit`, make the runner wake explicitly or
let the reconciler poll and deduplicate; do not assume the spreadsheet will
invoke delivery work itself.

## Process ownership

Stop a process only when you personally launched and recorded its exact positive
PID, command, parent PID, and start time for this request. Immediately before a
signal, reverify that the PID still identifies the same process. Never stop by
name, command pattern, process group, tree, or blanket cleanup, and never stop
shared services or another task’s process.
