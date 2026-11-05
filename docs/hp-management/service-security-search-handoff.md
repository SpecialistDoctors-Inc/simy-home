# Service disclosure frontend handoff

Base main: 0191a229cff8e2c328b8a39031eb59e11a3cb7e9. Local branch: codex/service-security-search.

Consumes the Sites `report.serviceSecurity` contract from `/tmp/simy-sites-service-security`. Merge the API commit first or together; the frontend tolerates older reports. Changes are limited to the service-security adapter, existing result renderer, their two existing page cache versions, and regression tests. No manga, registration gate, pricing, layout or routing changes.

Live and reviewed component notices have `subjectId`, `published`, nullable `occurred`, `checkedAt`, `kind`, `relationship`, nullable `affectedVersions`, `verification`, `url`, `summary`, `scope`, and `impact`. Same-provider sibling cases remain explicitly distinguished. Empty/unresearched services do not become visible rows. Component cases appear only for components already observed by the diagnosis, with no vulnerable-version verdict. Existing provider notices remain in the provider section.

The existing footer now distinguishes completed/partial/unavailable runtime research from dated catalog examples, without claiming complete coverage. The renderer adds affected-version text within existing rows. No extra explanation section was introduced.

Verified locally: all 1,522 Node tests, localized-home check, international SEO check, pharmaceutical page check. API tests/build are documented in the API checkout. Deployment and real paid web search were not run; the OpenAI key is owned by the shared-resource AI task. Integration must verify the normal clinic flow, saved/reloaded results, actual search provenance and PDF export on the deployed version.
