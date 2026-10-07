# For Engineers manga release

Japanese landing page pairs the user-supplied eight-panel manga with a short source-grounded pain-point introduction, a focused hero, and three edited mechanism screens. Existing detailed experiences remain available in native details, including direct/legacy fragment links. Other locales preserve their existing content.

Current public assets:
- assets/engineer-manga/release-crew-ja.webp: unchanged user artwork, lossless WebP.
- assets/engineer-mechanism/delivery-team.webp: SIMY desktop app, original full sidebar restored; illustrative team-local tasks, fictional names, selected task status and remaining work.
- assets/engineer-mechanism/rules-application.webp: SQM Web rule example for duplicate submissions, concurrent retries, separate application acceptance.
- assets/engineer-mechanism/systems-application.webp: SQM Web example of related form/API/storage/test repositories.

The mechanism images use the original screen layouts with explanatory example content, not live execution evidence. This is disclosed in page copy and image notes. Built-in imagegen was used for image edits; retained prompt files document iterations. Earlier screenshots and prompts describe design iterations; only the four current assets are included in publication.

Verification: SEO/localized-generation checks; 1,289 existing tests; browser checks at 1440/390/320px for image loading, aligned edges, overflow, keyboard/no-JS details, and legacy/direct links. Separate fallback reviewers were used because gpt-5.5 is unavailable. Final independent release review found no blockers. Deployment prepares new CSS/images before HTML and invalidates CloudFront. No edge routing changes.

Rollback: revert this feature commit and run the existing production workflow. Post-release: inspect Japanese hero/manga/mechanism, verify four image requests, and test optional details/direct links on the public URL.
