# Public-site copy clarity — 18 languages

Purpose: make the contact invitation, input hints and adjacent public-site explanations understandable to first-time visitors in their chosen language. This implements the safe copy/localization portion of the 2026-10-04 audit, using current `main` (`4b121bf`) rather than the audit's older SEO feature branch.

Acceptance conditions:
- Contact headings translate as complete sentences in all 18 supported languages; hints use the same language.
- Demo, footer and adjacent company/careers/how-it-works copy convey the business meaning of “ship”, “standup” and “user focus”. Existing billing text left in English is localized without changing its conditions.
- Language switching preserves entered text. Missing translations restore English hints; failed requests can recover on reload.
- Existing navigation, generated pages and SEO checks pass; screenshots and a separate review support the change.

Decisions: reuse the existing DOM dictionary/React translation bridge. The original React TSX sources are absent, so the compiled contact component receives only a whole-sentence heading and label/input associations; no form state, submit handler or delivery behavior changes. A small generator keeps both file-preview bundles reproducible. The ten simulated editorial perspectives were idiom, first-use understanding, concrete meaning, benefit, next action, factual fidelity, conciseness, accessibility, consistency and cultural fit; this is not human/native certification.

Scope limits / remaining decisions:
- The contact submit handler currently changes the displayed state without delivering the enquiry. This PR does not certify sending, provider E2E or the “received” message. Delivery routing and its truthful completion UX need a separate, confirmed contract before release of a working enquiry flow. Do not interpret the existing completion state as delivery evidence.
- Response deadlines, prices, free offers, security assurances, benchmarks, testimonials and stronger/weaker product promises were not chosen or changed on a customer's behalf. Claim-sensitive audit proposals remain pending evidence and owner decisions.
- No merge, deployment, production mutation or message sending is part of this PR. Roll back the commit if localization breaks; before publishing, recheck localized contact/demo pages and the above delivery limitation. Observe untranslated text, overflow and navigation errors after any separately authorized release.
- This repository is static HTML/JS, not Next.js; it has no DESIGN.md, package manifest or bundled Next.js guides. Existing styles/components are retained.

Verification commands:
```sh
python3 scripts/build-i18n-bundle.py --check
python3 scripts/build-localized-home.py --check
python3 scripts/build-content-pages.py --check
python3 scripts/site_header.py --check
python3 scripts/check-home-seo.py
python3 scripts/check-site-seo.py
python3 scripts/organize-guide-intent.py --check
node --test tests/*.test.cjs
NODE_PATH=<existing Playwright runtime> node tests/copy-browser.cjs
```

Browser evidence contains synthetic inputs only. The runner uses a private loopback server, blocks unrelated external requests, never submits a valid enquiry, and closes its browser/server when finished. Screenshots document key contact and demo states; `browser-results.json` records actual verified locales and widths. HTTP fallback is covered; full authenticated/provider or message delivery E2E is not applicable to this copy change and was not performed.

SQM未実施：SIMY CLIのバグ修正後に別途実施予定

Results (2026-10-06): Node tests 1,295 passed, 0 failed/skipped; generated homepage/content/header checks, home/site SEO, guide regeneration and bundle checks passed. Browser checks passed 54 contact states (18 languages × 1440/390/320px) and 36 demo states (18 languages × 1440/390px), plus JA→FR→EN→AR→JA with synthetic input, keyboard label focus, HTTP 503 fallback/reload recovery and three Japanese adjacent pages. Four screenshots were inspected. No browser page errors were recorded; unrelated external requests are intentionally blocked.

Screen captures: [JA contact, desktop](contact-ja-1440.png), [EN contact, mobile](contact-en-390.png), [Arabic contact, mobile/RTL](contact-ar-390.png), [JA demo, desktop](demo-ja-1440.png). Detailed states: [browser-results.json](browser-results.json).

Independent review, pass 1: a separate `gpt-5.5` / `xhigh` session found two P1 issues (demo runtime cache/raw fallback, remaining standup mistranslations) and a related P3 test-evidence gap. Corrections align the raw English fallback/runtime version, localize the outcome label and scene consistently, and add semantic/cache regressions. The second separate `gpt-5.5` / `xhigh` review confirmed the P1 fixes but its final report found a P3 inconsistency: the static Japanese footer and an app-separation paragraph still used the older recording-app wording. Those dictionary values and both bundles are now aligned and the focused screenshots verified. The final separate `gpt-5.5` / `xhigh` code-review session completed with no actionable findings; its bundle check and changed test passed. Its full-suite attempt could not complete because its read-only sandbox denied temporary directories; the normal-workspace full suite passed 1,295 tests. Delivery, provider behavior, policy claims and native-speaker quality are not certified.

P3 closure verification: [footer-results.json](footer-results.json) confirms the Japanese static footer in Contact and Demo now renders the same recording-app label as the React bridge; both JA screenshots were refreshed. The full suite was rerun after this correction (1,295 passed).


Purpose-focused refinement (2026-10-06): an editorial assessment of 85/100 identified two remaining comprehension gaps: the “purity of decisions” metaphor and the demo's vague ownership sentence. All 18 languages now refer to the original decision's intent/meaning; the remaining “high purity” variants in the user-intent paragraph also use fidelity to that intent, and the demo explicitly introduces a usage example. Four Japanese company-copy paragraphs use the software term “release” instead of physical shipment; their existing promises and numeric claims are retained, and the testimonial is untouched. No layout, endpoint, business condition or dependency was added. Whole-sentence legacy aliases remain for existing pages. Static English fallback and runtime cache versions are aligned.

The target 95/100 is an editorial judgment of this copy/localization scope, not a service-readiness score or native-speaker certification. The remaining five points require native-speaker assessment of idiom and tone. Contact delivery and unsupported business/product claims remain separately unresolved and block treating this PR as evidence of a working enquiry service.


Refinement verification: the final dictionaries/bundles pass all 1,295 Node tests and the bundle check. The browser runner now verifies 126 states: 54 Contact, 36 Demo and 36 About (all 18 languages at desktop/mobile widths), including the three company-copy paragraphs and the complete demo subtitle. It also retains input-preservation, keyboard-focus and HTTP 503/reload recovery checks. No page errors or horizontal overflow were found. The Japanese mobile About screenshot is [about-ja-390.png](about-ja-390.png); the Japanese desktop Demo screenshot was refreshed and visually inspected. Existing generated-page, shared-header and SEO checks pass. These checks demonstrate rendered copy and recovery, not real enquiry delivery.


Heading/body closure: the user-needs heading is now natural in every language, consistent with the adjacent paragraph; Japanese and Chinese headings were already clear. After this final wording change, the focused browser run passed all 36 About states, including the heading and all three paragraphs, and the six copy regression tests plus bundle check passed again. [about-results.json](about-results.json) records this focused run; language-switch and failure recovery evidence remains in the full 126-state run, not in the focused run. No business claim, quote or delivery behavior was changed.


Final refinement independent review: separate `gpt-5.5` / `xhigh` review session `01a1119b-3e65-7451-ae3e-d320586ff5ff` completed with exit 0 after inspecting the final heading/body changes, runtime/cache behavior, archive routing and evidence. Its final response: “No actionable correctness regressions were found in the current staged, unstaged, and untracked changes. The localization bundle check and focused Node tests passed for the changed areas.” No unresolved findings. The earlier refinement attempt was interrupted when the wording changed and is not counted as a completed review. Editorial purpose assessment: 95/100 within the stated copy/localization scope; native-speaker quality and enquiry delivery remain unverified.
