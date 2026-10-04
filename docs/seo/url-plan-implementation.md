# Occupation and workflow URL delivery — 2026-10-04

Purpose: help prospective SIMY users find a relevant work outcome and then reach a practical setup or workflow guide. Sales users need reviewable meeting preparation/follow-up examples; engineers need the steps for development and quality checks. Success means each published page answers its own intent, is reachable from an existing entry point, and has correct language and indexing signals. Beyond basic correctness, the shared content source must prevent stale translations, broken reciprocal links and misleading quality claims.

## This delivery

| Intent | Japanese | English |
| --- | --- | --- |
| Occupation directory | `/for/` | `/for/en/` |
| Sales preparation and follow-up | `/for/sales/` | `/for/en/sales/` |
| First SIMY task | `/guides/simy-getting-started.html` | `/guides/en/simy-getting-started.html` |
| CLI development workflow | `/guides/simy-delivery-loop.html` | `/guides/en/simy-delivery-loop.html` |
| Applicable safeguards and proof | `/guides/simy-sqm.html` | `/guides/en/simy-sqm.html` |
| Parallel development with Conductor | `/guides/conductor.html` | `/guides/en/conductor.html` |
| Claude Code setup and first change | `/guides/claude-code.html` | `/guides/en/claude-code.html` |

The existing engineering pages remain at `/for/engineers/` and `/for/en/engineers/`. Their new guide links explain the practical steps. All six homes link to the occupation hub; Japanese uses JA, other languages use EN, with the fallback identified in translated link text. JA/EN guide indexes and the existing Claude/Cowork/Codex guides link into the new content.

## Decisions and boundaries

- `/for/` answers who benefits, what inputs to share and what result to review. `/guides/` answers a specific tool/workflow question. Keep existing `.html` guide addresses and clean occupation directory addresses; do not migrate unrelated URLs.
- New pages are authored in JA/EN only. Their manifest declares both translations; hreflang includes those two and English x-default. Existing 15 guide topics and their indexes retain all six languages. Language URLs are not claims of country-specific keyword validation.
- Conductor means the development product at **https://www.conductor.build/** in the accepted implementation plan. No dedicated SIMY integration or automatic evidence handoff is claimed.
- No additional Ahrefs results were obtained for this implementation. The prior research quota limitation remains. Do not present these new topics as validated search volume/KD opportunities, or infer a ranking lift from technical checks.
- Remaining planned occupations (product managers, business owners, financial advisors, dentists, pharma sales), meeting follow-up and dedicated integration pages remain later deliveries. Do not create placeholder translations, speculative feature availability, Pro entitlements or job-title-swapped pages.
- User authorization covers publishing this delivery. This work does not change product permissions, billing, data storage or infrastructure access policies.

## Content sources and maintenance

Edit `scripts/content-pages.json` and `site/content-pages.css`, then run `python3 scripts/build-content-pages.py`. CSS is embedded in generated HTML, consistent with existing guide delivery. The existing guide-intent organizer is reused by the generator, so its independent check still covers the new guides. `finalize-guides.py` leaves these generator-owned pages alone.

SIMY product facts were checked against installed `@awak-app/simy-cli` **0.5.64**: `README.md`, `src/console/commands.js`, `src/console/app.js`, `src/orchestrator/delivery/WORKFLOW.md`, `src/orchestrator/delivery/references/delivery-levels.md`, and `src/sqm/command.js` / `proof.js`. The guide describes the CLI Agentic Loop, not the removed provider hook-based Delivery Loop skill. This implementation uses the SIMY CLI SQM commands; it does not claim the CLI orchestrator authored the website.

External facts were checked against:

- https://www.conductor.build/
- https://code.claude.com/docs/en/overview
- https://code.claude.com/docs/en/quickstart

Workflow examples are original illustrative requests, not customer case studies, tested integrations or measured savings. Prices and detailed entitlements are linked to the current product pages rather than copied into URLs or invented.

## Verification and review

Required checks: content/home/engineering regeneration checks; home and whole-site SEO audits; guide-intent check; all Node tests; `git diff --check`.

Whole-site audit target: **166 HTML files, 138 indexable URLs, 28 noindex pages**. New browser coverage: all 14 pages at 390 and 1440 CSS pixels, inspecting overflow, image loading and shared card geometry. Cards on the same row must align within 1 pixel. Screenshots and DOM measurements are stored outside the repository under `/tmp/simy-url-plan-proof/` so recording evidence cannot change the SQM candidate digest. Entry flows include home → hub → sales → language alternate → getting started → download, and engineering → Delivery Loop → contents anchor.

Independent review uses a separate `gpt-5.5` session with `xhigh` reasoning. The first review identified a missing anchor write-back in homepage locale switching. It also identified root-hub normalization in the optional edge function, the default SQM cloud evidence upload, and the required guidance argument for /continue. The routing code and both CLI guide translations were corrected, with --no-upload in the example and explicit explanation of the default. It was repaired and a repeated-locale regression was added; Chrome also verified JA → EN → JA. Browser tests do not establish that the product examples themselves were executed or that Google has indexed the new pages.

Final SQM must run on the committed candidate: `simy sqm min-check --base origin/main` followed by `simy sqm check` using that min result and external proof paths. Match repository/base/HEAD/working-tree identity and verify the signature with installed SQM tooling. A passed result with no applicable rules is recorded as zero applicable SQM coverage, not complete SEO or product verification. PR evidence records the final result and review verdict after the gates finish.

## Release, rollback and measurement

The integrated main branch includes PR #106's literal S3 slash-key publication. The new root hub also needs `for/` excluded from the later deleting asset sync; the pre-existing `for/*/` exclusion does not cover the root hub. Publisher tests now cover both JA/EN hub keys as well as occupation keys and upload failure. No CloudFront Function permissions are required for the normal publish. The optional checked-in Function/Terraform handlers now normalize the root hub too, so a future edge publication cannot redirect /for/ to /for.html. Live pre-release GET /for/ returned an S3-backed 404, not that redirect; normal publication therefore follows the literal-key path, and final live HTTP checks must confirm it.

Release through the repository CI and main deploy workflow. After deployment, GET every new URL and changed HTML/asset; check status, HTML content type, canonical and the expected content against the deployed revision. Check live entry links and language alternates. A green workflow alone is insufficient.

Rollback: revert this feature's changes through a reviewed commit and redeploy the prior site. If retiring the literal slash keys, remove the newly added hub/sales objects only after the prior homepage links and sitemap are restored; the publisher does not automatically delete obsolete slash objects. Preserve the existing engineering pages and the prior routing publication fix.

After release, inspect sitemap processing/indexing and compare Search Console impressions, clicks and destination queries by country and page family after sufficient crawl/observation time. Track visits reaching the download/pricing entry points with the existing consent-aware analytics. Technical publication is confirmed separately from search performance; no ranking guarantee or new recurring automation is introduced.
