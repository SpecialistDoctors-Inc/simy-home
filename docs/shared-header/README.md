# Shared visitor navigation

Owner: SIMY website maintainers. System: simy-marketing-navigation.
Baseline: af39dd0d4346b7c5cde291c74f180881141da72a, local source inspected 2026-10-04.
Source of authority: approved five-entry shared-header charter in this delivery run.
The original complaint was ten crowded desktop links and Japanese labels wrapping.
Success is a visitor reaching the intended page/account flow from any rendered page,
with readable navigation across six languages, keyboard and JavaScript-disabled use.
Extra quality means one maintainable source and repeatable regression evidence.

## Required observable contract (intended, not observed verification)

All units below serve an anonymous website visitor. Entry requires only loading a
visitor page, with no account, storage, network API or cookie consent prerequisite.
AC-1 through AC-3 are the frozen parent acceptance IDs. Sub-IDs below decompose
independently falsifiable behavior without replacing these parent outcomes.

| ID | Context, entry and perception | Choice → response and usable postcondition | Continuation, alternatives and recovery | Oracle and mapping |
| --- | --- | --- | --- | --- |
| AC-1.entry | Load any home, guide, download, occupation, company, product, legal, archive navigation or error page. See SIMY and the common controls in initial HTML. | Read or use the header; the same five primary groups are available. Existing content and metadata remain intact. | AC-2.product/work/direct/language/account. Redirect and empty verification utility documents retain their specialized behavior. | Raw inventory against generator; browser family checks. No runtime insertion dependency. |
| AC-2.product | From AC-1.entry on desktop, Product is closed and identifies a disclosure. | Activate summary by pointer, Enter or Space; see product, AI tools, how it works, apps and why SIMY links; follow one to its localized home section. | Close by summary; with JS Escape closes and focuses summary, outside pointer/focus leaving closes. Without JS summary still toggles and links still navigate. | Actual disclosure states, focus, destination sections and no-JS browser tests. |
| AC-2.work | From AC-1.entry, open For your work. | Select real localized occupation hub, engineering, sales or home use cases; correct destination is reachable. | JA uses JA pages; other locales use existing English occupation pages, explicitly labeled English when the selected language lacks a translation. Browser Back returns to source. | All-page href existence plus browser destination checks. Latest baseline includes actual hub and sales pages. |
| AC-2.direct | From entry or mobile menu, see Pricing, Guides and Download. | Follow Pricing to localized home pricing, Guides to localized guide index, Download to localized download. | Back returns; no hidden JavaScript requirement. | Destination existence and runtime navigation, retaining pricing plan controls in body. |
| AC-2.mobile | Viewport narrows before labels collide. Logo, language, signup and menu remain visible. | Open menu; all product/work/direct links and login become available in a readable scrollable panel. | Close same summary; JS Escape/outside click/focus-leave closes. Resize to desktop closes obsolete mobile state. No modal focus trap; keyboard may leave to body. | Widths 360/390/768/1024/1280/1440/1920, open/closed geometry and reachability. |
| AC-2.language | Open language disclosure from any included page; six names identify the choices. | Pick available equivalent topic/download/occupation/home locale and navigate there. Static equivalents have localized header and body. | Absent equivalent: explicitly identify English equivalent if present, otherwise localized home fallback. Do not claim untranslated body is translated. Legacy query-translated pages preserve body translation and query context; region/plan semantics are preserved at account handoff. | All six locales; topic retention, real fallback destination/label, no-JS links and legacy body/runtime isolation. |
| AC-2.account | Entry or mobile menu; visitor sees signup, login. | Follow existing signup/login endpoints with language/locale and applicable region; no new plan chosen by the common header. Five archived pages retain their existing Pro/yearly query as the explicit preservation exception described below. | Existing body plan CTAs retain their plan/interval. App authentication is downstream and outside this site's execution authority. | Raw and runtime URL contract; no live signup write. |
| AC-2.layout | Entry/open dropdown at each required width and long labels. | Read one-line primary labels without overlap or horizontal overflow; focused controls remain visible. | Narrow view uses mobile menu; dropdown contents stay within viewport; reduced-motion preference disables unnecessary motion. | Screenshot inspection and rect measurements; intended homepage rails within 1 CSS px, 200% text/zoom where practical. |
| AC-3.regenerate | Maintainer changes shared source or runs home/content/engineering/guide generators. | All renderers consume shared generator; --check detects drift and exits nonzero. CI runs fresh-output, SEO, Node and diff gates. | Repair stale artifacts with generator then rerun same check; never change expected behavior solely to pass. | Real commands, independent raw coverage and generator idempotence. |
| AC-3.delivery | Maintainer has final committed candidate on latest main. | Boundary and final independent reviews, browser evidence, repository checks, signed SQM identity and current-head CI establish PR readiness. | Failures repaired within authority. Parent owns merge/deploy/live verification; PR is not public delivery. | Revision-bound matrix and outside-repo evidence in /tmp/simy-shared-header-evidence. |

End-to-end acceptance joins AC-1.entry to every AC-2 choice and actual destination,
then AC-3 regeneration/publication safety. Passing individual controls is insufficient.
Required remains separate from observed: evidence records alone report current results.
No production verification or account creation is authorized in this implementation phase.

## Design and boundary decisions

One Python module owns generated raw HTML and page-aware links, with scoped CSS and
progressive enhancement. Existing page renderers call it; a sitewide pass covers
hand-authored pages. Native details/summary supplies the no-JS fallback. Page body
translation is preserved; legacy runtime must neither insert duplicate language
controls nor rewrite header destinations. Actual translated variants take precedence
over preferences. Missing translations remain explicit, not invented content.

Assumption resolved by source inspection: latest base includes JA/EN occupation hub,
sales and engineering pages, plus generated workflow guides. No framework or server
migration, new dependency, auth/payment policy, analytics or persistence is needed.
The highest uncertainty was safely finding the navigation boundary across families;
HTML parser offsets distinguish outer header/nav from nested navigation and body
headings. Only first site navigation is replaced; body TOCs/dialog headers remain.

Views 01/02/03/04/05/07: interaction table above (inventory, transitions, controls,
requirements, states and workflows). View 06: anonymous read navigation; external
account handoff unchanged. Views 08/09/10: generator file contract, locale dictionary,
raw HTML → CSS + optional JS → browser navigation. View 11: no database entities or
ownership changes; static file/locale relationships only. View 12: existing S3 +
CloudFront and GitHub Actions, authoritative AGENTS.md and deploy-site.yml. Publish
assets before referencing HTML/occupation slash keys. Rollback restores previous
HTML/assets together using existing versioned bucket/deployment; parent monitors
live navigation, asset responses and layout after deployment.

Independent reviews and selection receipts are external evidence, never committed
as proof files. The selection is preserved from level-selection.json; this document
does not change it or make any claim about completed verification.

## Preserved account-link exceptions and exclusions

`scripts/header-account-links.json` records original header endpoints/query context
from baseline af39dd0. Home login retains the app landing endpoint; guide signup
retains campaign attribution. The archive headers in old/compare.html, old/index.html,
old/terms.html, old/press-release.html and old/privacy.html retain their already
authored `plan=pro&interval=yearly`; no new plan recommendation is introduced. This
is required by the source charter's account/plan preservation boundary. Active
page signup and body pricing choices retain their original independent semantics.

Excluded documents: engineers.html, engineers-en.html, old.html, pricing.html,
press.html, old/pricing.html and old/press.html are redirects with fallback links;
google-site-verification-TODO.html is an empty noindex setup utility. Error/status
pages and all remaining archive HTML are included. Non-HTML backup assets are not
rendered visitor pages. Guide/download CSS remains inline to preserve their
no-extra-stylesheet-request rendering contract, generated from shared-header.css.
