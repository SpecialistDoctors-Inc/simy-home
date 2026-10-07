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
acceptance gaps, current checks and raw browser observations. The 2026-10-06
SQM exclusion is historical: on 2026-10-07 the user explicitly requested the
SIMY CLI Delivery Loop and SQM again. SQM must be reported with its actual
coverage and matching candidate identity; zero applicable rules do not establish
feature acceptance. Final proof identities and signatures belong in the PR body,
not in a self-referential source commit. CI must match the PR head and disclose
skips.

2026-10-07 browser checkpoint against source candidate `60a02e3`:
- Chrome Extension: English getting-started page language menu has only English
  marked current; French fallback retains the same English topic.
- Keyboard Enter on the first-task TOC reaches `#scene`; settled section top
  94.05 px is below the sticky header bottom 77.40 px. No horizontal overflow
  observed at the default desktop viewport. The synthetic note, request and
  reference outline are visible and remain labelled illustrative.
- Japanese 390px navigation timed out during click; do not count this as a pass.
- Ahrefs Japan / 営業 aiエージェント reports Credits limit reached, reset 19 October.
  No new demand/volume/related-term evidence was collected; no plan upgrade.
- CLI loop starts from the observed conversation directory; implementation and
  checks stay in the dedicated seo-cli-redo worktree. A loop being active is not
  acceptance evidence. SQM on the source candidate passed with signature valid,
  zero matching modules and zero executions (`no_applicable_rules`). Recollect
  proof after any committed change; current identities belong in the PR.

## Level-3 local mobile checkpoint — 7 October 2026

The user's “Sol レベル３でやって” changes requested/effective assurance to 3 for
bounded local static-site work, with the unchanged acceptance and Draft endpoint
in [the delivery decision](README.md#delivery-decision-and-release). It does not
restore the historical CLI run or approve its stale completion report.

Connected Chrome Extension operated the actual source site at 390 × 844 through
a localhost HTTP server without manifest interception. Runtime sources are
unchanged from `42b0b3d8e7a9f5e459442b8d1e90a760307ff3bc`; this checkpoint adds
documentation only. The earlier Japanese click timeout remains historical; the
following observations supersede it for the tested local path:

- Japanese home → occupation hub → sales page → output TOC click reached
  `#output`. After smooth scrolling settled, section top was 81.84 px, below the
  sticky header bottom of 65.20 px. Six TOC rows had a common 40 px left edge and
  separate ordered rectangles. The visible note, unsent email draft, questions
  and actions retained their synthetic labels and unknown dates/price.
- Sales → getting-started guide → keyboard Enter on the first-task TOC reached
  `#scene`; settled section top was 82.05 px, below the same header. Same-topic
  language switching reached English and returned to Japanese. Only the actual
  Japanese or English topic link was marked `aria-current="page"` in its menu.
- English mobile first-task TOC click reached the English `#scene`; settled
  section top was 82.18 px, below the same header. All five guide TOC rows in each
  language were separate and aligned. No horizontal page overflow or captured
  console warnings/errors were observed on these guide paths.
- Guide → Japanese download page exposed the warning-stop instruction and web
  alternative, without bypassing a warning or launching an installer. The
  fallback honestly reported that the latest manifest was unverified (the plain
  local server has no release manifest). The web-login destination was inspected;
  account access and actual Windows installation were not exercised.

Raw screenshots and DOM observations remain outside the committed diff. These
are technical operation/result observations, not fresh-human comprehension,
product completion, a current controller minimum-completion pass or deployment
proof. Generator checks, home SEO validation and all 1,302 Node tests passed for
these unchanged runtime sources; independent final review, fresh signed SQM and
CI must bind the resulting documentation commit before any new proof is claimed.

PR #108 remains Draft. Fresh-reader evidence (AC-1–4), authorized setup/product
results (AC-5/7), page-specific Ahrefs research and security/product owner evidence
(AC-8), and reviewed production/live identity (AC-6/9) are unresolved. Ahrefs
allowance reset is reported as 19 October; no upgrade or scheduled retry exists.
No Ready transition, merge or deploy is authorized while those frozen holds remain.
