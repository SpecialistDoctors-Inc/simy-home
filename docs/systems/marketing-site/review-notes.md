# Public review notes — international SEO repair

This is a public-safe index, not a replacement acceptance checklist or a release
receipt. The [complete specification](preimplementation-spec.md),
[refinements](README.md), [results](acceptance-results.md),
[40-row ledger](market-route-ledger.csv), [market supplement](existing-market-ledger.csv)
and [security audit](security-claims.md) retain the acceptance source and gaps.
The [original design rereview](design-ledger-rereview.md) is conditional design
approval, not implementation or production proof.

The PR repairs occupation discovery, illustrative sales drafts, setup/installer
recovery and truthfulness; it preserves the approved Guide versus for URL plan.
The latest source changes stack mobile numbered TOCs across 14 generated pages,
normalize Chinese Windows recovery to `zh-Hans` in both locale parameters, and
remove unsupported security assertions from the current page, all 18 dictionaries,
the bundle and security SEO entries. Security/configuration and legal policy are
unchanged. The market supplement's CRLF repair was already committed; validation
must use `git diff --check origin/main...HEAD`, not only a clean worktree check.

Screenshot provenance: `extension-*` artifacts collected through connected Chrome
Extension/cua_repl are browser observations. Earlier shell Playwright captures are
diagnostics only. Neither source constitutes a fresh-human comprehension study,
an observed installed-product result or a production deployment. Raw screenshots,
logs, signed proofs and machine results stay in ignored local storage; no private
account screenshot is published. The PR body identifies the final revision and
which observations were recollected for it.

Independent final review must inspect the exact committed candidate, source diff,
acceptance gaps, current checks and raw browser observations. For this
2026-10-06 continuation, the user explicitly excluded SQM execution and removed
it as a commit/push/Draft-PR gate. SQM未実施：SIMY CLIのバグ修正後に別途実施予定。
Older zero-rule SQM receipts are historical evidence, not acceptance of this
candidate. CI must
match the PR head and disclose skips. These are required gates, not assertions
that this document itself proves them.

PR #108 remains Draft. Fresh-reader evidence (AC-1–4), authorized setup/product
results (AC-5/7), page-specific Ahrefs research and security/product owner evidence
(AC-8), and reviewed production/live identity (AC-6/9) are unresolved. Ahrefs
allowance reset is reported as 19 October; no upgrade or scheduled retry exists.
No Ready transition, merge or deploy is authorized while those frozen holds remain.
