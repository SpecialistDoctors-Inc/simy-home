# SEO-01 / AC-8 — whole-site and security-claim audit

2026-10-04. The raw HTML inventory was remeasured by scripts/check-site-seo.py:
166 HTML, 138 indexable, 28 noindex. Metadata, reciprocal hreflang, sitemap,
static anchors and internal links passed. This is artifact integrity, not search
indexing, user comprehension or demand validation.

Prior Ahrefs evidence remains in docs/seo/ahrefs-observations-2026-10-03.json:
eight country observations, first-page Also talk about sample only, country SV
not co-occurrence frequency, dated SERP warning preserved. The shared frozen 40-row
market-route-ledger.csv and existing-market-ledger.csv retain the route-market sources. All page-specific demand
is unvalidated due the 2026-10-04 credit limit (reset 19 October). No new report
was requested and no credit/plan upgrade performed. No route was added.

## Security page claims (copy repair; configuration untouched)

Source surfaces: site/security.html, site/lang/*.json, site/privacy.html,
infra/terraform/main.tf. Translation dictionaries reproduce the same claims;
translation consistency does not substantiate them.

- Historical "All data ... TLS 1.3 ... third-party integrations" is contradicted by the current read-only TLS1.2 handshake. Corrected fallback, 18 locale dictionaries and generated bundle now scope HTTPS to this website; backend and third-party transport remain unverified. The
  marketing CloudFront configuration specifies minimum TLSv1.2_2021 (line 168),
  which cannot prove TLS 1.3 for every client, backend or third party. No claim of
  a live vulnerability or live configuration change follows from this source.
- AES-256 for servers and backups: no product database/backup configuration or
  operational evidence in this static-site repository. Unknown, owner evidence
  needed; S3 marketing-site protection is not product-data coverage.
- AWS/GCP hosting: privacy policy names those providers; network isolation,
  patching, MFA and RBAC operation remain unverified here.
- Plan training summary: privacy.html 158–160 documents Standard/Pro versus
  Enterprise/Business, and a Google-data exception. security.html's short summary
  omits Business and the Google exception. Policy itself was not changed.
- Enterprise SSO/SAML, audit logs, retention and isolation check marks: plan and
  implementation evidence unavailable in this scope; unknown, not verified.
- GDPR/CCPA "Active", SOC2 2026, HIPAA/ISO 2027: these are existing published
  statements, not certification or legal evidence. No certification/audit report
  or owner-confirmed roadmap was found in this repository. No compliance verdict.
- Disclosure 24h/72h targets: published targets, not observed service performance.

Owner action: site/security/product owner must supply current architecture,
operational/plan evidence and approved policy wording before these claims can be
certified. An SEO metadata pass does not make them true. The owner attestations remain pending; changing security policy/configuration is
outside level 4 authority. No security configuration, authentication, IAM or
legal policy was edited.

## Source checks for first-phase content

SIMY installed package console/commands.js confirms /new, /repos, /branch,
/executor, /continue with required guidance, /pause, /resume and /stop. SQM help
confirms min/check, --base, --min-result, --proof, --signed-evidence and --no-upload.
The actual CLI --version attempt returned the existing-daemon warning (it is not
a version command); no daemon was stopped or replaced.

https://www.conductor.build/ (2026-10-04): isolated cloud microVMs and first-party
Claude Code/Codex/Cursor/OpenCode. No SIMY integration evidence claimed.
https://code.claude.com/docs/en/overview and /quickstart (2026-10-04): code reading,
editing/commands, terminal and other surfaces; official setup remains linked.
These checks support the existing bounded content, not customer outcomes.

## Scope and implementation mapping

AC-1/UX-01: six generated homes expose the existing occupation hub before the
long hero copy, retaining direct engineering navigation. AC-2/3/4: JA/EN sales
pages add an illustrative source→draft→unknowns→human-review example. AC-5: six
download pages retain a dated 0.5.65 fallback with explicit reload/account recovery;
shared script selects matching platform/architecture only and validates URL and
version before replacing the fallback. AC-7: getting-started pages explicitly
separate an illustrative request from a verified product result. AC-6: all 14
routes and 16 entries remain under the unchanged URL plan. REL-01: production
held pending required acceptance and release gates.

Canonical interaction specification: immutable preimplementation-spec.md supplied
with this run, hash 19abec2955fdfaa150d167348e2835cfffb1e38655ae996b91a7e418405e8fe9.
No acceptance obligation is replaced by this compact audit. Required first-read
observations remain pending; automation does not establish comprehension.

## Current source disposition after independent boundary review

The historical claims above are an audit inventory, not retained public assurances.
The current `security.html` removes unsubstantiated at-rest/backups, AWS/GCP
controls, RBAC/MFA, plan training/feature checkmarks, GDPR/CCPA active status,
SOC2/HIPAA/ISO target years and 24h/72h disclosure promises. The blanket hero
assurance is removed. All 18 current locale dictionaries and their generated
bundle remove corresponding keys. Their old home FAQ security summary now uses
the same existing website-only HTTPS description. All 18 security SEO entries in
`site/i18n.js` also use that scope (the current page's `data-reviewed-seo` guard
already prevents runtime metadata replacement, but stale source promises are removed).
Localized policy/terms links and a directly usable security email link remain.
Removal does not establish product security, plan entitlement, compliance or
mailbox delivery. Those owner attestations still block release.

Independent gpt-5.5/xhigh boundary review conditionally approved source removal
and identified stale SEO/FAQ sources and untranslated added prose. Those findings
were addressed before freezing the candidate. An earlier delegated reviewer
edited prematurely; its result is not used as independent approval. A fresh
read-only review supplied the boundary findings; final candidate review is a
separate gate. No infrastructure, authentication or legal policy changed.

Whole-site term inventory also identifies security references in third-party
PLAUD/Notta/ChatGPT guides and Qwen deployment examples, plus legacy `/old/`
content. A sample TLS configuration is not a claim that SIMY enforces TLS1.3.
Third-party claims and legacy content are not certified by this source repair;
the whole-site claims gate remains pending for source/owner validation. Legal
policy text remains authoritative policy text, not observed operational proof.

The publicly reachable `/old/security.html` also contained the contradicted
TLS 1.3 assertion and other unverified claims. Its proposed source now forwards
visitors to the reviewed `/security.html`, preserving the query and fragment when
JavaScript runs; a visible link and HTML refresh provide fallback navigation.
This does not correct the currently deployed URL until a reviewed release is
made and its live response is checked. Other legacy pages remain outside this
specific redirect repair and the whole-site claims gate remains pending.

The legacy React home bundle and its archived copy also embedded assertions
about physical database isolation, end-to-end encryption and zero training.
Those direct assertions have been replaced with neutral pointers in the shipped
assets, and the corresponding stale translation entries have been removed from
both active and `/old/` home dictionaries and the generated bundle. This is
source containment, not proof of the product's security architecture. Other
legacy pricing, press and policy assertions still require owner-backed review
before the whole-site claims gate can pass.

Latest observed public installer metadata on 2026-10-04 at 06:24 UTC was 0.5.67.
Mac and Windows artifact HEAD responses were 200 and lengths matched their
manifests (50,730,192 / 28,843,766 bytes). Mac manifest declared signed/notarized;
Windows declared unsigned. These are publisher metadata, not locally verified
signatures. The dated 0.5.65 fallback remained available (50,726,752 / 28,840,453
bytes); it is intentionally not labelled latest. Recheck at the release gate.

2026-10-07 follow-up: removed the orphaned `pricing.secP` and `pr.p15` entries
from all 18 active and 18 archived locale dictionaries, then regenerated the
active i18n bundle. Their physical database isolation, end-to-end encryption and
zero-training promises lacked supporting evidence. No references to either key
were found in site HTML or site/scripts JavaScript and Python; inspection of the
active and archived dictionary lookup paths found no dynamic construction of
these keys. A regression checks their absence from dictionaries and consumers.
This removes unused source claims only. Other compiled legacy pricing/press
strings and the comparison's zero-training row remain pending rendered-surface
and owner review; other product and third-party semantic claims also remain
unverified. This does not close the whole-site claims gate.
