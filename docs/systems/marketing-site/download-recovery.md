# Download manifest failure and recovery — 7 October 2026

Latest user revision resumes the task with **gpt-6.1-sol / medium**, including the
independent reviewer, and requests actual CLI Agentic Delivery Loop level3 and
SQM. This supersedes the earlier direct-only / revoked-process revision; all
AC-1..9 and the Draft-only commit/push endpoint remain. No Ready, merge,
deployment, installation, purchase or new provider connection is authorized.
The 28/28 design checklist is design evidence, not implementation acceptance.

## AC-5 cause removal

`site/download-release.js` previously made one unbounded manifest GET per OS.
A temporary network/5xx failure left the dated fallback until manual reload;
a stalled response/body never settled. This is a source-level and injected
failure observation, not a claim about an observed production outage.

Each read now has a five-second deadline covering response headers and body.
A network error (including a body-read TypeError), deadline or server5xx without Retry-After receives one retry
following250ms. Permanent HTTP failure,429, a server-directed Retry-After,
invalid JSON and invalid artifact metadata are not automatically retried.
Existing platform, architecture, origin, version and file-extension validation
remains before any link replacement. No automatic installer request is added.
Six authored pages receive a new script query revision for cache identity.

## Independent continuation under the same fault

Mac and Windows remain independent: successful reads are not repeated when the
other OS fails. After two failed/timed-out attempts, the visible dated fallback,
uncertain-latest explanation, reload and account/web recovery remain available.
A late timed-out response cannot overwrite a newer validated result. This is
bounded same-origin read recovery, not a new daemon or evidence infrastructure.
It does not claim the retained installer is current, signed or installed.

The paired regression exercises the original implementation and fixed code with
the same input. It checks transient recovery without reload, persistent outage,
hung body, another OS completing, stale late response, later-page recovery,
no duplicate successful-OS requests, request bounds, permanent failures and
untrusted artifacts. The original implementation fails the new recovery cases;
fixed focused checks pass. Browser fixtures use explicitly synthetic0.6.7
metadata and never download an installer or submit an account action.

## CLI and acceptance boundary

Read-only doctor found installed CLI0.6.10 and running shared daemon0.6.9,
signed-in session, provider model access unknown. The ordinary CLI startup with
updates/workflow prompt disabled exited2 because an existing service owns the
same origin. The two original SEO run recovery endpoints returned404. Existing
snapshots retain their attempts/budgets and actor binding; no identity edits,
new duplicate run, budget reset, shared-daemon stop or manual challenge forgery
is used to bypass this. The standard delivery-start request also exited2 because
this session already has a loop. That record has never proved Agentic worker
execution. Actual level3/Sol-medium Agentic execution remains unverified, rather
than being replaced by a registration receipt or local tests.

Independent product work proceeds despite this CLI dependency. This increment
repairs one AC-5 failure mechanism; human first-read AC-1–4, actual OS/product
AC-5/7, forty page-demand observations and owner claims AC-8, and deployed/live
AC-6/9 remain pending. The earlier separate PR131 header ownership is unchanged.
Current-head SQM must retain its actual counts, signature and identity; zero
applicable rules or unavailable Cloud never establish feature coverage. Old
proofs remain historical. The final PR evidence records current commands and
separate Sol-medium review without changing frozen product outcomes.

Release remains held. If a later authorized deployment reveals excess requests,
wrong download selection or misleading confirmation, revert this bounded script
and its cache-query references through the normal reviewed workflow. No rollout,
production fault injection or scheduled monitoring occurs in this task.

## Collected bounded observations

Eight local Chrome fault-injection views at390/1440 compare old transient failure,
fixed transient recovery, persistent5xx and a hung Mac read with successful Windows
read. Old code made one request per OS and retained uncertainty; fixed transient
code made two and selected validated synthetic metadata; persistent failure stayed
at two per OS with dated fallback. The hung-Mac case recovered with two Mac reads
and only one Windows read. No page errors or horizontal overflow were recorded.
Representative recovery/fallback screenshots were inspected. This verifies the
bounded script path only, not the full OS/account or human acceptance oracle.
Focused8 tests pass. The broad1,308-test run passed before the final Retry-After
restriction; final focused tests cover that restriction and final CI must bind the
committed candidate. Generation, headers, guide-intent and SEO checks passed
(181 HTML pages,150 indexable URLs,31 noindex).

A separate CLI review requested exactly `gpt-6.1-sol / medium`, session
`01a116b4-1e8b-7df0-8fb6-28198ee47bf7`, but exited1 before review with HTTP400:
“The 'gpt-6.1-sol' model is not supported when using Codex with a ChatGPT account.”
No other model was substituted. Independent review is **not completed** and
remains a final gate; code self-inspection and local tests do not replace it.


## App review correction

The formal app review in a separate `gpt-6.1-sol / medium` context found a body
transport gap in candidate6d18151: a200 response followed by a failed body stream
was not retried. The correction classifies body TypeError as retryable, preserving
terminal JSON SyntaxError and the two-request bound. A standard Response and
erroring ReadableStream regression verifies recovery, persistent failure and
invalid JSON. Focused9 checks pass. The historical CLI HTTP400 remains recorded;
repeat app review, current-candidate CI and SQM receipts belong in the PR evidence.

Read-only recovery comparison covers six isolated cases: the same actor resolves
both primary checkout and dedicated worktree, including a stale local path with
valid cwd; missing repository is rejected and a different actor is rejected
before repository resolution. Both original saved runs differ from the current
session's device binding. Changing cwd alone cannot repair that mismatch. This
comparison dispatches no workers and changes no identities. The common CLI/auth
owner must provide legitimate original-device recovery or a server-backed same-run
transfer with old-writer fencing and preserved attempts/budgets; the static site
cannot supply that authority. Installed-source behavior was compared, while the
running daemon is an older version, so its exact loaded implementation is unknown.
