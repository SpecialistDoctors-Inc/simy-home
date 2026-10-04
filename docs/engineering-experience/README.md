# Engineer experience: clarity redesign

## Purpose and revised acceptance

The first implementation passed technical checks but failed the user's purpose:
the user could not quickly tell what SIMY does. The user explicitly requested a
short, concrete promise and a design grounded in leading UI/UX practitioners.
Technical pass counts are not evidence of comprehension.

The revised promise is **AIに、開発と品質チェックを任せる。**
The English equivalent is **Let AI build, test, and check your code.**

For an engineer seeing SIMY for the first time:
- C1: The first screen names the work AI handles, without requiring knowledge of
  Delivery Loop, SQM, assurance levels or internal workflow vocabulary.
- C2: A visible request maps to concrete deliverables. Three single-click examples
  cover feature implementation, bug repair and quality checks. No five-step tour
  is required to understand the product.
- C3: Delivery orchestration and incident-derived checks remain distinguishable.
  SQM's opt-in and applicable-rule scope stay explicit beside the explanation.
- C4: Detailed limits, authority and all five assurance levels remain available
  through native disclosures, closed by default. Level 5 is the highest assurance.
- C5: Installation is the primary action; pricing and language links work. Mobile,
  desktop, keyboard, reduced-motion and no-JS users can access the core message.
- C6: No fake executions, measured-effectiveness claims or automatic-release
  promises. Illustrations are labeled examples.

The user remains the authority on whether this redesign communicates well. We have
not run a human comprehension study and do not claim universal clarity.

## Designers and concrete application

These are influential practitioners selected for relevant published work, not an
objective global ranking. They did not participate in or endorse this design.
The application column is our interpretation of their principles for this task.

| Practitioner | Primary source | Application |
| --- | --- | --- |
| Steve Krug | [Don't Make Me Think](https://sensible.com/dont-make-me-think/) | Say exactly what the tool does in one sentence; remove slogans requiring interpretation. |
| Luke Wroblewski | [Obvious Always Wins](https://origin.lukew.com/presos/38/obvious-always-wins) | Keep the primary action visible; expose familiar requests and outputs. |
| Don Norman | [How Might People Interact with Agents](https://jnd.org/how-might-people-interact-with-agents/) | Show the request/result relationship and keep release control explicit. |
| Jakob Nielsen | [Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/) | Move verification depth and specialized details behind clearly labeled disclosures. |
| Bret Victor | [Learnable Programming](https://worrydream.com/LearnableProgramming/) | Connect each example selection immediately to a different visible request and result. |

## Verified product sources — fetched 2026-10-03

- simy-cli origin/dev `67c5992` (v0.5.63)
- simy-web origin/dev `65dd17703`
- simy-backend origin/dev `d0f1dfd27`

These are development snapshots, not proof of deployment for every customer.
Availability remains dependent on version, plan and organization configuration.

| Claim | Source |
| --- | --- |
| Implementation, independent review, repair, bounded retries and human blockers | CLI `src/orchestrator/loop.js`, `src/orchestrator/contract.js`, `src/orchestrator/delivery/WORKFLOW.md` |
| Level 5 highest; required gates and risk floors | CLI `src/orchestrator/delivery-level.js`, `src/orchestrator/delivery/references/delivery-levels.md` |
| Explicit SQM opt-in and separate actual-path verification | CLI `src/orchestrator/delivery/WORKFLOW.md`, `src/sqm/report.js` |
| Deterministic preflight/full checks with pinned code identity | CLI `src/sqm/command.js`, `src/sqm/index.js` |
| Signed, revision-bound results; pending human/post-deployment states | CLI `src/sqm/proof.js` |
| No applicable rules does not establish feature coverage | CLI `src/sqm/report.js` |
| Incident sources, causes, fixes and safeguard lifecycle | Web `src/lib/sqm-knowledge.ts`, `src/services/sqm-knowledge.ts`; backend `supabase/functions/_shared/sqm_knowledge.ts` |
| Local analysis consent and organization scope | CLI `docs/desktop-sqm-controls.md`, `src/sqm/history-store.js` |

## Boundaries and decisions

Use the existing dedicated worktree and static architecture; no new dependencies,
tracking, authentication, billing or infrastructure changes. The six home locales
link to Japanese or English detail as before. Copy lives in
`scripts/engineering-copy.json`; `scripts/build-engineering-pages.py` emits both
crawlable static pages. JavaScript only switches illustrative examples. It does not
execute development, SQM or network requests.

Implementation remains local and uncommitted. No permission to push, create PRs,
merge, deploy or run real Delivery Loop/SQM was inferred from the research request.
If publishing is later authorized, use the existing static deployment. Rollback is
redeployment of the prior site revision. Observe broken links and visitor feedback;
no analytics added here.

## Current verification

- Repository tests: 1,118 passed, zero failed/skipped.
- Both static generators, SEO/resource/locale checks and `git diff --check` passed.
- Chrome browser verification: 6 request/output examples (3 in each language),
  22 viewport/locale combinations, keyboard and no-JS behavior, language switch,
  local links, first-screen content bounds and peer geometry.
- Dedicated pages at 360, 390, 768, 1440 and 720 CSS px; all six home locales at
  390 and 1440. 720px checks desktop 200% reflow equivalence, not native browser zoom.
- Screenshots and measurements are in `screenshots/`. PC and phone first-screen
  captures make the primary promise and example independently inspectable.
- No Safari/Firefox/physical-device testing or real repository execution is claimed.

Reproduce: `node --test tests/*.test.cjs`,
`python3 scripts/build-engineering-pages.py --check`,
`python3 scripts/build-localized-home.py --check`,
`python3 scripts/check-home-seo.py`.
With Playwright available, run `node tests/engineering-browser.cjs`; it starts a
private loopback server and uses installed Chrome. Override `PLAYWRIGHT_CHANNEL`
and `ENGINEERING_EVIDENCE_DIR` as needed.

The two `review-v1-*` records are historical reviews of the rejected first design.
They are not review approval for this redesign.

Current redesign: separate read-only review recorded in `review-clarity.md`, with
no findings. A subsequent color-only audit in `review-contrast.md` verified the
affected secondary text at a minimum 5.09:1 contrast. Both sessions were launched
with `codex exec -m gpt-5.5` and `model_reasoning_effort="xhigh"`. Browser evidence
was regenerated after the color adjustments. These checks are not a substitute
for a comprehension study with actual engineers.

## Theme alignment — 2026-10-04

User requested consistency with the rest of simy.one. The homepage and download
page are the visual references: warm paper, black rules, bold black/blue headings,
blue buttons, mint accents, and offset solid shadows. The copy and example
interactions remain intact, including the positive SQM FAQ wording.

`site/site-theme.css` is the shared source for the existing homepage tokens and
button styles. Both engineering languages and all six home locales load it before
page CSS. The homepage token and button declarations were moved without changing
their values; engineers.css now uses them. The engineering entry on the homepage
also uses the common button and palette. Page-specific layout remains separate to
avoid importing unrelated homepage selectors. Existing download pages are visual
references and were not modified.

Verification: 1,118 repository tests passed; generator freshness and SEO/resource
checks passed. Browser checks cover both detail languages, six home locales,
360/390/720/768/1440 CSS px, keyboard, no-JS and example switches. Added computed
style parity for homepage/detail background, ink, font and primary-button styling,
and <=1px alignment checks for header/main/footer rails alongside existing peer
cards. Screenshots regenerated and reviewed for desktop and mobile. 720 CSS px
remains a reflow proxy, not native browser zoom. No physical-device or Safari/
Firefox test. Implementation remains uncommitted and unpublished; deploy the shared
CSS together with regenerated HTML if release is subsequently authorized.

Independent theme review: separate read-only gpt-5.5 / xhigh CLI session
found a skip-link stacking defect under the sticky header. Raised the skip link
above the header and added a real first-Tab hit-test regression check. See
`review-theme.md` for the initial review and verification limits.

Focused separate re-review confirmed the skip-link correction with no findings
(`review-theme-followup.md`). The root session reran browser verification after
the fix: all 22 viewport/locale checks and first-Tab visibility passed.

## Publication and occupation URL policy — 2026-10-04

The user approved production publication and plans to expand occupation-specific
license use cases. `/for/engineers/` (Japanese) and `/for/en/engineers/` (English)
are canonical. Reserve `/guides/` for task/how-to content and `/for/<occupation>/`
for benefits, examples, relevant licensed capabilities and links to those guides.
Keep plan names out of paths so plan changes do not break incoming links. Do not
create empty pages for future professions or claim unverified license entitlements.
Current homepage pricing uses Starter / SIMY by Industry; the user's term Pro does
not by itself establish a new pricing contract, and this release leaves the
approved page's version/plan/organization availability language intact.

Legacy `/engineers.html` and `/engineers-en.html` return 301 at CloudFront, retaining
query parameters. Local static HTML fallbacks are noindex redirects. Edge routing
maps canonical occupation directories to index.html, with matching Terraform
source; no Terraform apply is needed. Homepage navigation, language switch,
canonical/hreflang, social tags, page schema, sitemap and SEO inventory use the
canonical URLs. Both generators and static browser server support this layout.

Latest main (096623e) was merged before release to preserve new guide/SEO work.
Release through the existing GitHub Actions main deployment, with CI checks first.
Rollback: revert this feature's merge commit and redeploy through the same workflow,
including the prior CloudFront function. Verify production 200s, alias 301s,
canonical metadata, CSS/JS, homepage navigation and language switch after deployment.

Release review found an edge/HTML ordering risk. The workflow now uploads new
occupation pages and their CSS/JS first, publishes the edge function second,
then publishes homepage HTML and invalidates the distribution. Thus the new
routes have origin objects before they are exposed; failure to publish the
function stops before homepage links change. The review's untracked-file warning
is addressed by including both generated canonical pages in the release commit.

Focused independent release follow-up (gpt-5.5 / xhigh) found no actionable
issues. See `review-release-followup.md`. Final pre-publication checks: 1,143 Node
tests passed; both generators, homepage/sitewide SEO, Terraform formatting, YAML
parsing and diff whitespace checks passed. Browser evidence covers 22 views and
six example interactions; real-device/Safari/Firefox coverage remains unverified.
