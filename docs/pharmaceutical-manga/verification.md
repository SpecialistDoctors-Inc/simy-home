# Verification — 2026-10-21

## Artwork and implementation

- Eight separate built-in image generation calls produced new 1536×1024 PNG masters. Each output was visually inspected in the generation result; all accepted outputs are preserved outside `site/`.
- Eight distinct WebP exports total 2,275,144 bytes. File hashes and paths are in `art-manifest.json`.
- Japanese, English, Spanish, French, Hindi and Simplified Chinese generated pages contain the eight scene images and retain localized HTML dialogue and narration. Repeated cropped portraits are removed.
- The original hero promise is retained. No new provider subscription or API-key substitution was performed.

## Automated source checks

All passed after the artwork was integrated:

- Required-art generation and reproducibility check.
- Localized homepage reproducibility, homepage SEO and site SEO (187 HTML pages).
- Node suite: 1,314 passed, zero failures.
- `git diff --check`.

The fixture test was corrected to render the maintained localized template before injecting test art; released pages now already contain art and cannot serve as pre-injection inputs.

## Browser evidence

Local result: all 24 locale/viewport combinations passed, with zero browser errors. Report: `browser-local-report.json`. Desktop and mobile screenshots for all six locales were visually inspected for scene/text correspondence, clipping, flow and panel alignment.

The repeatable script is `tests/pharmaceutical-manga-browser.cjs`. It checks the real final art in all six locales at 1440/390/320/720 CSS-pixel widths, including image decoding, eight distinct scene URLs, no repeated portrait images, no horizontal overflow, and shared panel boundaries within 1 CSS pixel. 720px represents the effective content width of a 1440px desktop at 200% zoom; it is not a native browser zoom acceptance claim.

Screenshots and detailed reports are saved in `output/pharmaceutical-manga-qa/`. The local run uses a Node HTTP static server with logs redirected to a file. Intermittent request stalls occurred with the initial Python HTTP server; changing its logging alone did not resolve them. Each viewport uses a fresh browser page and waits for image completion and network idle before closing it, so teardown cancellations are not classified as page failures. These are desktop Chrome viewport simulations; no physical iPhone/Android testing or human acceptance is claimed.

## Release

PR #147 and production deployment are checked separately from local tests. Final commit, CI, merge/deploy results and public readback are reported in the delivery message and PR record.
