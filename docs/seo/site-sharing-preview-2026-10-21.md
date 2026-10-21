# Site sharing-preview review — 2026-10-21

All 187 HTML files were inventoried. Of the 156 indexable pages, 150 now have dedicated, localized 1200×630 PNG cards; the six pharmaceutical pages retain their recently reviewed illustrated cards. Previously, 125 pages referenced the same English `ogp.png`, and another 14 shared a generic home image. Some role pages used dense UI screenshots or nonstandard image dimensions.

Cards use each page’s existing headline and language. They do not introduce or independently verify pricing, model capabilities, product claims, or article facts. This review covers sharing previews; it is not a complete editorial or functional audit of every page.

## Sources and regeneration

- `scripts/social-preview-pages.json`: page, language, topic, headline, image and accessible description. Keep this in step with future headline changes.
- `scripts/capture-site-social.cjs`: native HTML/CSS card renderer, using Playwright/Chrome. It checks text bounds and font readiness before saving each PNG. Hindi uses the bundled Devanagari font.
- `scripts/social_preview.py`: shared metadata normalization invoked by `site_header.apply`, which all current page generators already call. It also updates article schema references to legacy sharing covers.
- `node --test tests/social-preview.test.cjs`: indexable-page coverage, unique OG/Twitter tags, matching URLs/alts/language, and real PNG signatures/dimensions.

Run the capture script with a Playwright-capable `NODE_PATH`, then `python3 scripts/site_header.py`. Check all page generators with `--check`, SEO checks, and the full Node test suite. Card geometry and small-preview contact sheets were reviewed locally. Existing Messages/social platform caches may keep a previously fetched preview; origin publication alone does not prove those caches refreshed.

## Pages intentionally excluded from marketing cards

The following 31 noindex documents are archived content, redirect aliases, error/authentication/verification pages, or the service status page. Their current behavior and metadata are retained.

- `404.html`
- `auth-callback.html`
- `compare/index.html`
- `engineers-en.html`
- `engineers.html`
- `error.html`
- `google-site-verification-TODO.html`
- `news/ai-mentor-20261005-en.html`
- `news/ai-mentor-20261005.html`
- `old/404.html`
- `old/about.html`
- `old/careers.html`
- `old/compare/index.html`
- `old/compare.html`
- `old/contact.html`
- `old/demo.html`
- `old/error.html`
- `old/how-it-works.html`
- `old/index.html`
- `old/integrations.html`
- `old/press-release.html`
- `old/press.html`
- `old/pricing.html`
- `old/privacy.html`
- `old/security.html`
- `old/status.html`
- `old/terms.html`
- `old.html`
- `press.html`
- `pricing.html`
- `status.html`
