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

Results (2026-10-06): Node tests 1,294 passed, 0 failed/skipped; generated homepage/content/header checks, home/site SEO, guide regeneration and bundle checks passed. Browser checks passed 54 contact states (18 languages × 1440/390/320px) and 36 demo states (18 languages × 1440/390px), plus JA→FR→EN→AR→JA with synthetic input, keyboard label focus, HTTP 503 fallback/reload recovery and three Japanese adjacent pages. Four screenshots were inspected. No browser page errors were recorded; unrelated external requests are intentionally blocked.

Screen captures: [JA contact, desktop](contact-ja-1440.png), [EN contact, mobile](contact-en-390.png), [Arabic contact, mobile/RTL](contact-ar-390.png), [JA demo, desktop](demo-ja-1440.png). Detailed states: [browser-results.json](browser-results.json).

Independent review, pass 1: a separate `gpt-5.5` / `xhigh` session found two P1 issues (demo runtime cache/raw fallback, remaining standup mistranslations) and a related P3 test-evidence gap. Corrections align the raw English fallback/runtime version, localize the outcome label and scene consistently, and add semantic/cache regressions. A second separate `gpt-5.5` / `xhigh` review confirmed all findings resolved and found no further actionable issues. It independently ran narrow checks, inspected the refreshed screenshots and read the recorded full-test/browser results. It did not certify delivery, provider behavior, policy claims or native-speaker quality.
