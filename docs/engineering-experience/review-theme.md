**Findings**

1. **Keyboard skip link is hidden behind the sticky header**  
   [site/engineers.css](/Users/t.shiwaku/.codex/worktrees/engineer-delivery-experience/simy-home/site/engineers.css:61) sets `.skip` to `z-index: 10`, while the sticky header is `z-index: 100` at [site/engineers.css](/Users/t.shiwaku/.codex/worktrees/engineer-delivery-experience/simy-home/site/engineers.css:86). When focused, the skip link moves to `top: 12px`, inside the header area, but remains layered underneath it. Keyboard users may not see the focused “skip to content” control. Raise the skip link above the header, matching the homepage pattern (`z-index: 1000` is fine).

**Verification**

I kept this read-only: no edits, no remote changes.

Passed locally:
- `python3 scripts/build-engineering-pages.py --check`
- `python3 scripts/build-localized-home.py --check`
- `python3 scripts/check-home-seo.py`
- `node --test tests/*.test.cjs` → 1118 passing

Reviewed screenshots:
- `ja-1440-first-screen.png`
- `ja-390-first-screen.png`
- `home-ja.png`

Reviewed existing browser evidence:
- `docs/engineering-experience/screenshots/verification.json` reports zero browser errors, matching computed theme values across `/ja.html`, `/engineers.html`, `/engineers-en.html`, no horizontal overflow in recorded views, and aligned rails.

Limit: I did not rerun `tests/engineering-browser.cjs` because it writes screenshots/verification artifacts and the request was no edits.