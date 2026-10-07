# Marketing-site experience contract

Canonical sources: [frozen charter](charter-v2.md), [complete UX specification](preimplementation-spec.md), [40-row route/market ledger](market-route-ledger.csv), and [source provenance](source-provenance.json). The attachments were approved launch inputs; these sanitized shared copies retain their full obligations. Historical run IDs identify their original design, not current execution. Historical charter reference: `coding_loop_2b68a131-41cc-4e40-93c9-4a053018df7c_charter`. Its recorded approval identity is historical, not current authorization.

Read the [initial design findings](design-review-v2.md) together with the [conditional rereview receipt](design-ledger-rereview.md). The latter resolves design readiness, not runtime acceptance. Historical source links with line numbers describe the reviewed historical checkout; no current implementation proof is inferred from them. No review transcript, screenshot, private product thread or machine-local path is required to understand this contract.

The frozen 40 rows cover Japan, US, UK, India and Singapore. [Existing-market supplement](existing-market-ledger.csv) explicitly maps Spain, Mexico and France to their existing home, guide and download paths. It adds no role page, invented research or new translation scope. The [eight-market observation source](../../seo/ahrefs-observations-2026-10-03.json) remains broad historical evidence only. Page-specific demand remains pending after the observed credit limit; allowance reset was reported as 19 October, with no upgrade or scheduled retry.

## Current implementation and observation boundary

The [acceptance results](acceptance-results.md) preserve AC-1..9 and UX-01..07/SEO-01/REL-01. Raw current-head verification, immutable observations, screenshots, signatures and the machine matrix live in ignored `.artifacts/`; they must not be committed. Shared results summarize the known outcome and blockers without claiming that a plan is observed proof.

Source ownership: `scripts/content-pages.json` generates JA/EN occupation and workflow pages via `scripts/build-content-pages.py`; `site/index.html`, `site/home-i18n.js` and `site/home-locales.js` generate homepages. The six download HTML files are authored sources. `site/lang/*.json` generates `site/lang/i18n-bundle.js` with `python3 scripts/build-i18n-bundle.py` (`--check` verifies bytes). Security fallback text lives in `site/security.html`. Do not change security configuration for copy repairs.

## Addendum: source-truthfulness repair (2026-10-04)

These are refinements of existing frozen criteria, not replacements. Intended behavior follows direct accepted human guidance. The installed app's account-dependent result remains unknown on this candidate.

| Unit / predecessor → successor | Actor, context, entry and information | Control, transition and usable outcome | Alternative / recovery and oracle |
| --- | --- | --- | --- |
| UX-02-output / UX-01 → UX-03 | Sales visitor reaches the example output from the page TOC after seeing the synthetic input. The note has no agreed material title, owner, deadline, next date or price. | Reads a full email draft, separate internal questions and ordered next actions; can select/adapt text. Illustration and unsent state remain visible. Human checks source and fills sender/recipient before any send. | Unknowns remain explicit; no invented attachment, date or price. Fresh-reader answers and adapted request are required by frozen UX-02/03; independently compare the rendered JA/EN example to the synthetic note and inspect no write controls. |
| UX-04-pricing / UX-02 → UX-05 | A visitor asks whether trying SIMY is free on the download FAQ, reached from a purpose guide. Home advertises one month free; eligibility is not substantiated here. | FAQ distinguishes promotional period from permanent free plan. Visitor may inspect pricing and signup terms before choosing; no purchase occurs on this site. FAQ structured data must state the same answer. | Exact eligibility, subsequent charge, billing date and cancellation must be checked at signup. Missing account/plan evidence holds setup claims; copy cannot establish entitlement. Compare visible and structured FAQ across six locales; owner supplies product policy evidence. |
| UX-05-windows / UX-05-download → web login or support | A Windows visitor downloads the published installer and sees a Windows protection warning. Page's installation instructions are the reachable reference. | Stop installation; no warning bypass. Verify source/publisher; if not confirmed, choose the explicitly linked web login or contact support. No claim that an unsigned installer is trusted. | OS warning remains intact; account access may still fail independently (UX-07). Verify instructions and web-login link in six locales; actual Windows installation and publisher verification remain pending without an authorized Windows device. Browser text checks do not prove OS installation. |
| SEO-01-transport / security entry → privacy/owner inquiry | Anonymous visitor opens security page or changes its language and reads transport scope. | Sees HTTPS for this website with negotiated TLS depending on client/endpoint, no universal product/third-party promise. May inspect policy links. No configuration is changed. | Product/backups/third-party controls and certification/roadmap claims require owner evidence; do not certify them from site TLS. Oracle: requested read-only TLS1.2 handshake with valid certificate, English fallback and all 18 dictionaries/bundle consistent, existing security controls unchanged. |

Observed repair basis: on 2026-10-04, `openssl s_client -connect simy.one:443 -servername simy.one -tls1_2 -brief` negotiated TLSv1.2 with certificate verification OK. This falsifies universal TLS1.3, not HTTPS. Remaining claims and owner evidence are listed in [security claim audit](security-claims.md). No certification wording is silently converted into a verified assertion.

## Delivery decision and release

Requested/effective level **3**, `assurance-ascending-v2`; current direct selection receipt (7 October): the user's “Sol レベル３でやって”. This supersedes the earlier level-4 selection, retained as history in Git and the frozen charter. Current risk class is bounded, reversible static-site runtime behavior, with safety floor **3**; the authorized commit/push and existing Draft PR are review artifacts, not deployment or a new product side effect. Authentication, payments, persistence, shared API/schema contracts, production security/configuration and CLI recovery mutations are outside this implementation scope. Their higher safety floors remain applicable if that scope changes. One independent final-candidate review must cover the affected design, implementation, views and evidence, including the repository-required gpt-5.5 / xhigh review. Current authorized endpoint is commit/push and Draft PR #108, **not Ready, merge, deployment, production changes or customer messages**. This later instruction supersedes historical publication permission in the frozen charter and earlier prose. REL-01 retains its original production outcome and stays pending; the current endpoint does not satisfy or delete it. All frozen acceptance criteria and minimum-completion evidence requirements remain unchanged.

| Level | Verification/review scope and trade-off | Applicability | Conditional execution hours |
| --- | --- | --- | --- |
| 5 | Adjacent invariants and failure/recovery/rollback; separate design, implementation-boundary and final reviews; more breadth | Available, not selected | 5–9 |
| 4 | Both evidence layers, shared boundaries, recovery, independent design/boundary and final candidate reviews, CI and opted-in SQM | Available; broader assurance than current bounded scope requires | 3–6 |
| 3 | Focused regressions, real principal journey and independent final review; narrower boundary review | Recommended and selected; matches bounded local runtime work and Draft endpoint | 3–5 |
| 2 | Direct regression, actual affected path and scoped review; narrower integration coverage | Unavailable below runtime safety floor 3 | 2.5–4.5 |
| 1 | Artifact/link/diff verification plus repository gates; no runtime assurance by itself | Unavailable below runtime safety floor 3 | 2.5–4 |

Estimates reuse the prior implementation history (14 generated JA/EN pages, six download locales, 18 security dictionaries and whole-site checks). They cover remaining authorized repair/verification to the Draft endpoint, not production or a guaranteed SEO uplift. Review/check overlap is counted once; mandatory repository gates explain overlapping ranges. Confidence is low–medium. CLI recovery, SQM distribution, fresh-reader/product/owner evidence and Ahrefs waiting have no defensible upper bound; total elapsed time is the conditional execution range **plus unknown external/CI/reviewer waiting**. The task remains incomplete if those dependencies prevent its applicable checks. No paid service or expanded authority follows from these estimates.

PR #108 must remain Draft while first-reader, product-plan, Ahrefs or security-owner evidence is missing. No merge/deploy or Ready transition is allowed to force green. Production topology is `main` → `.github/workflows/deploy-site.yml` → S3/CloudFront → `https://simy.one` (AGENTS.md). After gates, verify deploy workflow SHA and live bytes against the exact candidate, then Chrome UX-01/05/06. Rollback is a reviewed revert via the same workflow on broken route, wrong locale or misleading claim. No CloudFront/IAM change. Search Console by page/country at 28 days belongs to site owner; no monitor has been scheduled.

## Latest repair and public evidence index

[Review notes and evidence boundaries](review-notes.md) cover the full PR scope,
including current source removals, canonical Chinese recovery and stacked mobile
TOCs. Raw artifacts remain private and ignored; no screenshots or account records
are committed. The notes distinguish connected Chrome Extension observations from
historical diagnostic Playwright captures. PR #108 remains Draft.

Additional observable refinements, under the same frozen acceptance IDs:

- **UX-05-locale recovery (AC-5):** a Chinese visitor whose Windows installation
  stops at a warning chooses the visible web-login alternative. The destination
  retains `lang=zh-Hans&locale=zh-Hans`; no warning bypass or automatic submission
  occurs. Web account/plan failure remains the separate UX-07 handoff. Oracle:
  inspect and follow the warning link, compare query to the page's authored login
  convention, and test all six locale links. OS installation is still unobserved.
- **UX-06-numbered navigation (AC-6):** a mobile reader reaches any generated
  page's TOC and selects a numbered section. Each choice occupies its own row,
  preserves list order and reaches the matching section by pointer or keyboard.
  Returning to the hub and switching topic language retain their existing links.
  Oracle: at 390px inspect item rectangles for separate rows and common left edge;
  at 1440px verify sidebar layout, valid anchors and no horizontal overflow.
- **SEO-01-claim boundary (AC-8):** an anonymous visitor opens security or changes
  locale. They receive only the website-scoped HTTPS explanation, policy/terms
  links and disclosure contact. Choosing a policy opens the published policy;
  choosing email opens the mail client without sending. Mailbox delivery, product
  controls and compliance are unknown. Oracle: rendered 18-locale content and
  source/bundle/metadata regression checks; owner evidence remains a release hold.


## Twelve-view reconciliation — 7 October 2026

System ID: `marketing-site`; maintainer/acceptance owner: site owner (user). Local source baseline: `a4e088434f18321fa3f96a33515f0171480e33f4`; fetched PR base: `4b121bf146a7331ae31f43c93818de8a73c655af`. This inventory describes the source/proposed journey, not deployed candidate behavior. Existing acceptance remains [AC-1..9](acceptance-results.md); no row is promoted by documentation.

| CLI view | Disposition and canonical source | Consistency boundary / remaining evidence |
| --- | --- | --- |
| art-01-screen-inventory-final | Existing: [route inventory](preimplementation-spec.md#url-market-and-evidence-ledger), `scripts/content-pages.json` | Home → occupation hub → sales/engineering → guide/download; UX-01/05/06. Source inventory is not fresh-reader evidence. |
| art-02-screen-transitions | Existing: [experience contract](preimplementation-spec.md), [observable refinements](#latest-repair-and-public-evidence-index) | UX-01→02→03/04→05→07; UX-06 language/topic and recovery links crosscut the path. Live candidate pending. |
| art-03-wireframes | Existing source layout: `scripts/build-content-pages.py`, `site/index.html`, authored download HTML; proposed behavior in [experience contract](preimplementation-spec.md) | No separate mockup needed for retained layout. [Local JA/EN 390px operation checkpoint](review-notes.md#level-3-local-mobile-checkpoint--7-october-2026) adds technical evidence; independent understanding, actual setup/product and live candidate evidence remain pending. |
| art-04-functional-requirements | Existing unchanged outcomes: [frozen charter](charter-v2.md), [UX/SEO/REL contract](preimplementation-spec.md) | Stable IDs and user/system oracles retained; current authority clarification above overrides historical release permission only. |
| art-05-state-machines | Existing bounded static transitions: [repair table](#addendum-source-truthfulness-repair-2026-10-04) and [acceptance results](acceptance-results.md) | Download warning → stop → web/support; synthetic draft remains unsent. Product setup/task states are unknown; product owner/executor must supply UX-05/07 evidence. |
| art-06-permissions | Updated authority above; existing anonymous-reader and product-account boundaries in [shared boundaries](preimplementation-spec.md#shared-view-and-release-boundaries) | No site auto-send/publish; real product permission is not inferred from copy. No security policy mutation. |
| art-07-user-workflows | Existing: [neutral first-read script](preimplementation-spec.md#neutral-first-read-test-script) and UX rows | Independent first-reader answers and usable real product output remain pending. |
| art-08-data-dictionary | Existing file fields: `scripts/content-pages.json`, [market ledger](market-route-ledger.csv), [market supplement](existing-market-ledger.csv), [provenance](source-provenance.json) | Country ≠ language; observed seed ≠ measured page demand; synthetic examples ≠ customer records. Formal downstream product dictionary unknown/outside this site's implementation. |
| art-09-sequences | Existing: source generators → static HTML → S3/CloudFront → browser; [release boundaries](preimplementation-spec.md#shared-view-and-release-boundaries) | Browser → download/web handoff is not completed installation/task. Combined UX-05/07 and REL-01 evidence pending. |
| art-10-api-design | Existing file/command contracts: repository AGENTS.md, `scripts/build-content-pages.py`, `scripts/build-localized-home.py`, `site/download-release.js` | Source-to-generated checks; manifest validation/fallback behavior. No new backend API. Product API behavior is unverified, not declared N/A. |
| art-11-er-diagram | Database ER is N/A: this change adds no persistence. Logical artifact relationship reused from [route/market ledger](market-route-ledger.csv) | A route has multiple market observations; generator entries produce JA/EN route variants. Do not invent DB tables or equate those relations with product storage. |
| art-12-infrastructure | Existing: AGENTS.md, `.github/workflows/deploy-site.yml`, `infra/terraform/main.tf` | Source-only topology; main deployment is currently unauthorized. No infra changes; deployed candidate identity remains pending. |

Cross-view review must check IDs, route/locale relations, generator ownership, warning recovery, claim boundaries and authority against the sources above. This inventory closes a documentation omission; it is not a controller-owned minimum-completion matrix or a passed independent review.

Current execution distinction: conversation tracking loop `ab60a82b-f450-4d7e-b269-9e9cf4fdd410` has `managed:null`; latest observed state is `recovery_required`. Two historical CLI Agentic Loop records exist: initial `coding_loop_b5cf00d3-1ae3-493e-bc32-799213efce03` and successor `coding_loop_2b68a131-41cc-4e40-93c9-4a053018df7c` linked to this shared charter. The successor contains three completed attempt records on 4 October, but implementation and completion gates are false; its latest saved state is `waiting_human` / `objective_contract_changed`. Both are bound to a different device from the current session. The saved minimum-completion report is `evidence_incomplete` (18 errors) and bound to historical HEAD `31b870236e28320851938bf07fdabfd872c81cd6`, not the current candidate. Completed attempts do not mean accepted delivery. Do not substitute the tracking loop for Agentic execution, rewrite identities, reset history or terminate a shared daemon. Supported original-session restoration is required, followed by reconciliation of the current no-deploy authority.

Historical incident coverage: the SQM UI's `KM-AI-4F1E923C33F04275A801132F` (Home language switching, observing) requires 18 translation assets; all were present on the local baseline. That structural check does not prove runtime translation. The observed SQM proof `SQM-PROOF-de256137-38f5-4cad-9632-2e5c262ab6e6` reported `no_applicable_rules` and zero executions; it does not establish coverage of this safeguard. UX-06's separate aria-current repair has actual regression coverage in `tests/content-pages.test.cjs`; its submitted knowledge-analysis job `602e9300-9f1d-4ee7-9a4f-e7c45dd5a1b8` completed, but publication/reapplication was not proved. Both remain uncovered by the observed zero-case SQM execution. Final-candidate proofs must be recollected after this documentation change and reported on the PR; historical signatures are not current-candidate proof.


## Latest direct execution revision — 7 October 2026

The latest user instruction withdraws Delivery Loop and SQM execution for this task. Use the [direct acceptance frontier](direct-acceptance.md): Loop=direct, SQM=revoked_by_user. This revision supersedes earlier restoration/recheck process requirements above; their receipts remain historical. No Loop/SQM start, resume, reset, check or checkpoint is authorized. All AC-1..9 product outcomes, Sol level3, ordinary checks and separate gpt-5.5/xhigh review remain. Draft PR108 is a partial artifact, with no Ready/merge/deploy permission.


## Later user revision — resumed with CLI Agentic and SQM

The latest explicit instruction supersedes the direct-only/withdrawn-process policy above. Implementation and separate review now use gpt-6.1-sol / medium; requested CLI Agentic level3 and SQM are restored requirements. See [download fault recovery](download-recovery.md) for the bounded AC-5 implementation and actual CLI recovery limits. Historical receipts and all AC-1..9 remain; no new Ready/merge/deploy authority.
