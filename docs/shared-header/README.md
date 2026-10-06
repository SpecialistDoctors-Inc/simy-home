# Shared site header — 2026-10-06

Purpose: visitors receive the same navigation, account links and app badges on every rendered public page, including publicly reachable `/old/` pages. The existing shared visual design and six supported locale destinations remain the source of truth. Content, authentication, pricing, infrastructure and tracking changes are outside this task.

The current 155 pages already used the shared header. The 16 non-redirect legacy pages now use the same generator, CSS and JavaScript. Authentication callbacks, redirect aliases and plain verification tokens are excluded because they do not present ordinary site navigation. Obsolete legacy scroll listeners safely tolerate the removed navigation. The two legacy error pages use a column layout so navigation spans the viewport. The existing verification setup placeholder resets the browser's default body margin; the rendered audit identified an 8px inset on that page.

`python3 scripts/site_header.py --check` validates every eligible page in CI. Missing, duplicated and stale shared headers fail regression checks. Nested legacy i18n scripts retain their same-page language links; an independent review discovered and verified this fix across all six languages.

Run rendered verification with `NODE_PATH=<Playwright installation> node scripts/check-unified-header.cjs`. `SITE_URL` optionally checks production; `HEADER_REPORT_DIR` optionally directs reports outside the repository. The audit compares 171 pages at 320, 390, 960 and 1440 CSS pixels with each locale's homepage header, checking geometry, fonts, colors, dropdown opening, Escape closing and scrolling without JavaScript exceptions. Third-party analytics, fonts and status widgets are blocked to keep this specifically a bundled-header test; the header uses system fonts. This does not claim validation of legacy page content or those external services.

The requested GPT-5.5/xhigh model is unavailable. A separate available-model agent reviewed the implementation and regression script; all findings were corrected and re-reviewed. Physical-device Safari testing is not part of this verification.

Release through the existing main-branch S3/CloudFront workflow. After deployment, verify published header HTML, resources and representative desktop/mobile interactions. Rollback: revert this PR and deploy through the same workflow; no data or infrastructure migration. A published page missing the shared header, broken menu destinations or failed header assets warrants rollback.
