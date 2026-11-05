# HP confirmation card

Build with `npm ci --ignore-scripts && npm run build`. The lockfile fixes the
official `@modelcontextprotocol/ext-apps` SDK (2.0.4) and esbuild (0.28.2).
`dist/publish.html` is self-contained; it loads no external scripts at runtime.
Run `npm test` and `npm run typecheck` for focused state and type checks.

The card consumes `hp_prepare_publish` results through the official App SDK.
With publication disabled, preparation creates an immutable `connection_test`
card for the authenticated user's current verified preview. The card says that
it does not publish and its button is 「接続を確認する」. The same app-only confirm
tool validates the private nonce, identity, publish role, expiry, membership/site
versions and exact preview, then atomically audits `connection_tested` on the
approval record. It creates no operation, queue entry or site publication side effect.
Replaying a valid test returns the same result; expired, revoked or stale cards
are rejected. Enabling publication later cannot turn that card into publication
authority. A new card prepared with publication enabled is required to publish.
The card does not send the test result to model context; the receipt has no
publication operation ID. Actual app-only result visibility remains a host boundary.
The nonce is read only from private result `_meta`; only the operation ID is
written to model context. A trusted click, valid TTL, and complete card are
required. Confirmation is attempted once: ambiguous failures require operation
reconciliation rather than a blind resend. Queued/running, retry/reconciliation, and completed are separate states.
A verified publication can complete while result reporting or email needs
attention; the card states those outcomes separately and never resends a publish
request to repair a notification problem. The status button performs a read and never resends confirmation.

The host must enforce `ui.visibility: ["app"]` and keep tool-result `_meta` out
of model context. These MCP Apps presentation boundaries and `event.isTrusted`
are not signed proof of a human action. An authorized user crafting a raw request
is still that same identity. The server validates the OAuth identity, private
nonce, current membership and exact preview/artifact. Keep publication disabled
until the actual Codex host has been exercised with private metadata delivery,
app-only tool exposure and a real button click. Local fake-host tests do not prove
Codex host behavior or deployed OAuth.
