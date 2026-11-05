# Financial Planner experience

## Purpose and scope

Help financial planners and team leads understand how SIMY supports meeting follow-up, practice before a consultation, and learning from colleagues. Match the established For Engineers visual structure and provide Japanese and English routes, useful screen examples and a download path.

Success: a reader can identify what to give SIMY, what comes back, and where the advisor must review; all illustrative states are readable on mobile and desktop. The higher quality target is a coherent journey from one meeting to the next, with voice practice understandable without explanation. Improved real consultation outcomes require user research after release and are not established by these tests.

Non-goals: implement the live FP application, record audio, call an AI service, change pricing, make legal/product performance guarantees, deploy, commit or push during the initial design phase. The later request below authorizes production release. All examples are fictional. No source PDF or client information is copied into the repository.

## Sources and decisions

- User-supplied `SIMY_for_FP相談_20260722112447.pdf`: all 16 pages extracted; pages 6 and 11 visually inspected. Meeting follow-up pack, separating facts/hypotheses/open questions, human review, and approved/anonymized colleague experience informed the page.
- The user explicitly confirms iOS role-playing is possible. The PDF does not provide an iOS screen, so the phone is a labeled illustrative recreation, not a verified screenshot of the current app. Exact UI and plan availability remain unverified.
- Document contents were reference material, not instructions or authority to execute workflows, share data or send messages.
- Did not reproduce the PDF's time-savings figures, financial product prices, legal-change claims or security guarantees. None were needed to communicate this experience.
- Native HTML/CSS was chosen for screen images to keep Japanese and English text readable, responsive and accessible. Static PNGs capture the screens for visual evidence and social previews. No raster image-generation service was needed.
- Four sections: meeting follow-up (three views), sales red flags (six evidence checks), iOS practice (three views), and team knowledge. All six views remain visible without JavaScript. There is no automatic motion, recording, network call or account mutation in the demo code.
- Shared navigation uses the existing Python header generator. Existing page diffs add the FP destination and refresh the cached header runtime; the new route must survive locale normalization. Authentication callback is unchanged.
- Sources for both FP pages live in `scripts/build-financial-planner-pages.py`; generate with `python3 scripts/build-financial-planner-pages.py`, verify with `--check`.

## Verification

- `node --test tests/*.test.cjs`: 1,275 passed, none failed.
- `python3 scripts/build-localized-home.py --check`, `python3 scripts/check-home-seo.py`, `python3 scripts/check-site-seo.py`: passed. 173 HTML files, 142 indexable URLs, sitemap/hreflang/internal links valid.
- FP, content and Engineer generator checks passed.
- `tests/financial-planners-browser.cjs`: Chrome, Japanese and English, 320/390/720/768/1440 CSS pixels. All 60 view/state combinations fit; controls and section edges align within 1 CSS pixel. The 720px view approximates a 1440px desktop at 200% zoom through reflow; browser-level zoom was not exercised.
- Verified state switching, keyboard Enter activation, header locale counterparts, home → Solutions → FP navigation, anchor positioning, expandable usage notes and six readable states without JS. No console/page/resource errors on FP pages.
- Saved visual evidence: web summary/draft/pack, iOS scenario/conversation/reflection, complete desktop/mobile pages, Japanese roleplay section and first mobile screen. Inspected hero, web summary, Japanese iOS conversation, English iOS reflection, roleplay section and mobile first screen.
- WebKit/Safari: not run; the browser binary is not installed. No physical iPhone or live app verification.
- Required `gpt-5.5` / `xhigh` independent review cannot run because that model is unavailable in this session. Reported to the user before finalization; a separate available-model agent performs a supplemental review. It does not satisfy the exact model requirement.

## Release and rollback

Uncommitted work in `codex/financial-planner-experience`, based on `origin/main` at `38dadbe`. Not published. Deployment requires the user's separate instruction. Existing `publish-occupation-pages.sh` handles the two new trailing-slash routes. Static assets are included in normal asset synchronization. After an authorized release, verify both routes, menu links, language switch, screen controls and asset HTTP responses. Roll back this coherent change via the normal reviewed release process; no data migration is involved. Useful outcome checks are FP page visits, download intent and qualitative feedback on whether the four use cases are understandable; no new analytics was added.

## Supplemental independent review result

A separate agent reviewed the changes, sources and saved visual evidence and found no required fixes. It independently reran all 1,275 tests, sitewide SEO and whitespace checks; confirmed no auth callback diff; and inspected representative Japanese/English desktop and iOS images. It did not independently repeat browser E2E. Safari, VoiceOver and exact live iOS app parity remain unverified.

Shared-header browser regression check also passed: 147 pages with no mobile overflow, 6 guide destinations, 10 anchor states, 42 responsive layouts, aligned menu centers, Escape behavior, locale navigation and no-JS navigation.

## Tone alignment follow-up

User requested matching the other site pages. Compared rendered Engineer hero/story and its `engineers-experience.css` with FP. Aligned the marketing layer to its 600-weight black headings, paper/white backgrounds, 56px hero / 64px story spacing, large section numbers with a top rule, dark outlines and hard shadows, and flat divided demo controls. Removed the FP-only background grid, large blue/green section fills and glowing phone backdrop. Retained readable product-screen interiors and all six example states. Updated the stylesheet cache version, both language pages, social images and visual evidence.

Rechecked all 60 browser view/state combinations, keyboard/locale/navigation/no-JS behavior, 1px geometry tolerance, four FP tests, sitewide SEO and whitespace. Independently reviewed current hero, iOS section and mobile images with no required fixes. Existing Safari and exact review-model limitations above still apply. Refreshed the user's existing local preview; no publication performed.

## Sales red flags follow-up

The user requested important elements from a Salesforce-based model for spotting sales warning signs. No named scoring model or internal criteria were supplied; an optional clarification was requested. This implementation uses publicly documented Salesforce opportunity-management and qualification concepts, adapted for FP consultations, without asserting a proprietary Salesforce model, certification, integration, or live scoring implementation.

Sources checked 2026-10-06:

- [Salesforce Trailhead: opportunity management](https://trailhead.salesforce.com/ja/content/learn/modules/opportunity-management/manage-opportunities-to-close-deals): stage guidance, questions and warning signs, stakeholder/decision-maker confirmation before progression.
- [Salesforce Trailhead: lead qualification](https://trailhead.salesforce.com/content/learn/modules/lead-qualification-quick-look/get-to-know-lead-qualification): BANT dimensions (budget, authority, need, timeline), with limitations. BANT is presented by Salesforce, not claimed as its invention.
- [Salesforce: pipeline management](https://www.salesforce.com/sales/pipeline/management/): progress/exit criteria, stalled deals, next actions, escalation and review.
- [Salesforce Help: sales methodology](https://help.salesforce.com/s/articleView?id=sales.pipeline_inspection_set_up_methodology.htm&language=en_US&type=5): structured criteria, information gaps and coaching. No numeric probability was derived from this.
- Supplied FP PDF, page 11: a colleague's warning about moving to a proposal before agreeing on monthly burden.

The six adapted checks are needs/priorities, budget/monthly commitment, decision-makers/family agreement, timing/decision criteria, engagement/progress, and next action/owner/due date. Two explicit fictional client concerns are red; three missing-information states are amber; one verified preference is green. Missing CRM contact records are explicitly not proof that contact did not happen. Counts derive from the example records. Color is accompanied by status text. No financial product is recommended or rejected and no suitability, eligibility, or closing probability is scored.

Each item exposes source evidence and a question using native keyboard-accessible details. The red items begin expanded. The proposed next action names the assigned FP and a relative target date, pending advisor review and client agreement. The same family-agreement concern is carried into the iOS role-play conversation and reflection. The marketing journey now has four numbered sections and four matching anchors; Engineer tone is preserved.

Validation: both languages, five widths (320/390/720/768/1440), all six original demo states plus all six risk items; native evidence disclosure, keyboard activation, role-play handoff, no-JS content, no overflow and geometry within 1px. Section captures hide unrelated sticky navigation only while capturing components, avoiding false occlusion in long screenshots. Full-page captures return to the top first. Updated unit/generator, SEO and whitespace checks pass. Live Salesforce, native iOS app and Safari remain outside the verified scope. No remote publication.

Supplemental independent review found one precision issue: the green item initially included priorities, although only the client's needs were evidenced. Corrected its label to “相談したいニーズ / Client needs”; priorities remain an additional question. Reviewer rechecked Japanese/English source and generated HTML and confirmed no unresolved findings. Latest browser evidence was regenerated after the correction.

## Typography follow-up

The user questioned text size. The red-flag descriptions were 13px, evidence/questions 12px, and the phone conversation 12px; the mobile stylesheet also reduced marketing body copy to 14px. These were too small for important reading in this presentation. Raised key body, evidence and next-question text to 16px; screen conversations and supporting copy to 14px; small metadata/status labels to at least 12px. Risk-card headings are 18px. Retained the existing black headings, rules, colors and hierarchy; the smallest-screen hero heading is now 28px. Phone width can reach 340px and shrinks to its container, with natural height and wrapping instead of smaller text. The mockup toolbar can wrap its labels. This is a readability judgment for this landing page, not a universal typography or accessibility-conformance claim.

Updated the shared FP stylesheet, its cache version, both generated language pages and visual evidence. Added computed-font checks to the existing browser verification so narrow layouts cannot silently shrink essential reading text again. All four FP generator/content tests pass. Chrome checks pass in Japanese and English at 320/390/720/768/1440px, covering all six demo states and six red-flag disclosures, keyboard use, language/navigation links, no-JS content, no overflow, aligned geometry, and no console/resource errors. The earlier complete repository suite was not repeated for this CSS-only follow-up. Physical iOS, Safari and the exact required review model remain unverified as documented above. No publication, commit or push.

A separate supplemental review of this typography follow-up found no required fixes, confirmed the four tests and generated-page/whitespace checks, and inspected the red-flag, iOS conversation and mobile hero screenshots. The 16/14/12px hierarchy was judged appropriate for the current layout; real-user readability testing remains the way to establish an optimum.

## Six-language production release follow-up — 2026-10-06

The user requested all non-Japanese versions, localized images, and production merge when complete. Added Spanish, French, Hindi and Simplified Chinese alongside Japanese/English, following the site's existing six-language scope. A strict dictionary supplies 180 translated strings per added locale, including every web and iOS screen state, warnings, evidence, drafts and captions. Missing copy stops generation instead of silently falling back to English. The six hero/social PNGs and screen captures are regenerated from those localized native HTML screens. Shared store brand artwork follows the existing site convention. Native iOS screens remain illustrative, not live app captures. Mother-tongue editorial review and physical-device testing have not been performed.

Each language has its own FP route, metadata, reciprocal hreflang, language switch and download/pricing destination. Shared menus include the localized FP destination. The compact-header language menu is raised above the store row to keep all six options clickable.

Independent review identified that the live older CloudFront function redirects the four new locale directory paths to `.html`. Confirmed with a production HTTP request. Main advanced to `62392c6` during this task and was merged, preserving its new six-language Engineer feature and its established compatibility-key publishing. Extended that same publisher to FP: upload each locale's identical HTML to its directory/index and `.html` compatibility keys; exclude compatibility keys from the later deleting HTML sync. Updated canonical function/Terraform sources already accept all locale prefixes; regression checks additionally cover FP aliases, query preservation, asset paths and unchanged dev authentication. The current live older edge still drops query parameters on these four redirects. Edge normalization remains a separate administrator operation; local default AWS credentials are absent and the existing deployment role's recorded GetFunction denial prevents assuming it can be changed. No IAM or credential change is required for static publication.

Release order: local/remote CI and independent follow-up review, then merge this coherent FP feature into main, await the existing production deployment and verify every locale's final HTTP 200, localized title/content, CSS/JS/social assets and language switch. Images and CSS/JS are placed before pages and navigation. Rollback uses a reviewed revert/redeploy, retaining compatibility keys until the old links are removed; no data migration.

Pre-merge browser verification: six languages × five widths (320/390/720/768/1440), 180 demo view/state combinations plus six evidence cards per view, all same-page language counterparts, keyboard actions, home-to-FP links and no-JS content. Zero console/page/resource errors in the successful full run. Screenshots and verification.json are retained here. A first full run hit an intermittent socket error and was repeated with URL-level failure logging; the successful run contains no such failures. The exact required review model remains unavailable; supplemental separate-agent reviews are used and the exact requirement is not claimed as satisfied.

After integrating main, all 1,287 repository tests passed; FP/content/Engineer/home generator freshness, home SEO, 181-page sitewide SEO and whitespace checks passed. Authentication callback has no FP-related changes.

Independent publication follow-up found a missing shell continuation in the HTML sync; fixed it before any publication and added an executable mock-AWS regression. The separate reviewer independently reran the six publication tests and confirmed no remaining finding. Browser verification now starts a private Node HTTP server, matching the established Engineer test pattern, to avoid dependency on an interrupted manual preview server; errors remain failures rather than being suppressed.
