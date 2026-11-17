# SIMY CLI bilingual publication — 2026-11-17

Scope: Japanese `/for/engineers/`, English `/for/en/engineers/`, and their affiliate-information pages. User explicitly requested production publication. The isolated checkout starts at main `579e3c41`; no unrelated working-copy changes are included.

## Readable comic

The earlier artwork included raster lettering that shrank with the image. New lettering-free artwork was generated with the built-in image_gen tool. Each panel is a single frame containing live HTML speech balloons and the illustration. Dialogue is 20 CSS px at every checked viewport, including 320px. Frame height grows with text. No zoom, horizontal swiping, or captions below the image are required to read the conversation. Speaker names are 14px. All eight panels are available in both languages.

Image: `site/assets/cli-ui/comic-art.png`. Source reference, SHA-256, generation prompt and framing are in `art-provenance.json`. The image has no printed text or UI labels; HTML lettering is translated independently. The prompt requests the same cast and eight scenes: duplicate registration, warning, investigation, retry cause, human input-preservation decision, test/review, release decision, next work.

Checked native image and rendered Japanese/English dialogue visually. `lettering-qa.json` contains 14 cases: each language at 320/360/390/720/768/1024/1440px. All have 20px dialogue, zero text overflow, zero text rectangles outside their bubble, eight frames, and page width equal to viewport width. Balloon tails intentionally extend outside their speech boxes; overflow measurements target the text, not the decorative tails.

## Language and product accuracy

English includes every main section, controls, alternative text, pricing notes, private-network assessment and affiliate terms. Each version has explicit reciprocal language links and hreflang. Japanese app screenshots are labelled as Japanese sample UI in English.

The product feed was rechecked before publication: version 1.2.11, publishedAt `2026-11-17T02:17:50.987Z`. README and native-copy changes from v1.2.8 to tag v1.2.11 (`9146fe2ced9f79571210f087665d7e94795dfdb9`) were inspected. README adds headless SSH sign-in documentation; native copy refines the repeated-identical-SQM-findings stop message. These do not contradict the described workflows. The five existing native captures remain explicitly labelled v1.2.8; they are not represented as newly captured v1.2.11 screens. Their provenance is in `../verification.md` and the asset manifest.

## Pricing and affiliate boundaries

General prices and feature allocation remain clearly marked as a proposal, not a new purchasable product. Figures derive from the existing pricing catalog, including tax and annual-payment examples. AI-provider fees are separate. Private-network configurations require assessment and an individual quote; a standard installer is not claimed to work fully offline.

Affiliate terms remain a proposal: 10%, 14-day attribution, 50-day review, minimum JPY10,000 request. No signup, bank transfer, webhook or database change is published. Since the affiliate application routes are still local-only work, public information pages show coming-soon language and a sales enquiry link instead of sending visitors to an unavailable app portal.

## Verification before publication

- Full `node --test tests/*.test.cjs`: 1,587 passed, zero failed.
- Localized-home and pharmaceutical generators: check passed.
- Engineering/affiliate generation: deterministic `--check` passed.
- Home SEO check passed.
- Sitewide SEO check: 196 HTML pages, 156 indexable, 40 noindex; metadata, reciprocal hreflang, sitemap and internal links passed.
- Browser samples: `ja-mobile.jpg`, `en-mobile.jpg`, desktop and other mobile states checked in-app. Physical-device and other-browser acceptance are not claimed.

Pre-publication review, SQM proof and deployment outcome are recorded separately once complete. Earlier local-only notes describe their earlier stage; this record is the release scope.
