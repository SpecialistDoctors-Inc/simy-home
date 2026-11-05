# Public site audit corrections — 2026-10-05

Purpose: visitors can follow navigation, read guide headings on phones, understand prices, and find seller information. Preserve the requested uniform top-level header and existing content design.

Decisions and assumptions:
- Guides target explicit index.html objects: S3 REST does not infer a directory index. This also protects links when edge routing changes. Both static markup and runtime locale switching use the same destination.
- The sticky-header scroll offset follows its measured height with ResizeObserver. A CSS fallback protects navigation without JavaScript. Long filenames wrap within guide examples; table wrappers retain intentional internal scrolling.
- Seller tax copy follows the homepage and observed signup: headline USD prices exclude applicable tax; Japan also displays 10% inclusive prices; checkout shows the final total before purchase. This does not change billing or the refund policy.
- Representative spelling is 塩飽 哲生, consistent with the founder page and https://www.specialist-doctor.com/home/transaction/ .
- No SIMY Google Play listing was verified in the site, related repositories or public search. Preserve the requested badge, label its destination “Android availability”, and link to localized download information with a browser alternative. A direct store link remains dependent on the correct published listing. Do not substitute another app with the same name.
- Correct Intelligence spelling in source copy and locale dictionaries; regenerate derived homepages. Header/i18n cache versions advance so existing browsers receive changes.

Verification: 1255 Node tests; generated home/content/engineering checks; home and site SEO (170 HTML pages, 140 indexable URLs); guide-intent consistency. Browser regression script covers 145 pages at 320px, six actual Guides menu destinations, 10 anchor states, 42 header layouts, keyboard/Escape, same-page language switching, legal navigation and no-JavaScript menus. Chrome Extension separately verifies rendered pages and production behavior. Account creation, payment and credentials are not part of this static-site change.

Release: existing main-branch S3/CloudFront workflow, followed by production Chrome Extension checks. Rollback: revert this change and redeploy through the same workflow; no data or infrastructure migrations. Post-release checks: Guides destinations, header script/assets, mobile body overflow and anchored heading visibility. Existing user work remains in the primary checkout.
