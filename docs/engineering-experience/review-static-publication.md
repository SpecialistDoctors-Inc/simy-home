**Finding**
- Low: [.github/workflows/deploy-site.yml](/Users/t.shiwaku/.codex/worktrees/engineer-delivery-experience/simy-home/.github/workflows/deploy-site.yml:10) still triggers deploys for `infra/cloudfront-functions/**`, but edge publication now only runs on manual `workflow_dispatch` with `publish_edge_function=true`. A function-only push could produce a green static deploy/invalidation while publishing no edge change, which weakens the new “explicit manual opt-in” operating model. Consider removing that path trigger or adding an explicit workflow notice/check.

No blocking findings on ordering, S3 slash-key publication, delete filters, shell failure propagation, dependency assets, or auth/download preservation.

**Verification**
- Reviewed staged/uncommitted changes only: workflow, README recovery section, new shell script, new test.
- Confirmed historical `309480d` had `continue-on-error: true` on CloudFront function update and the existing `old/` literal-key publish step.
- Passed: `bash -n scripts/publish-occupation-pages.sh`
- Passed: `node --check tests/occupation-publishing.test.cjs`
- Passed: `node --test tests/home-seo-routing.test.cjs`
- Passed: `python3 scripts/check-site-seo.py`
- Passed: `node --test tests/engineering-pages.test.cjs`
- Passed: `git diff --cached --check`

Limitation: `node --test tests/occupation-publishing.test.cjs` could not run in this read-only sandbox because `mkdtemp` under `/var/.../T` is denied with `EPERM`. I did not run live AWS operations or verify live HTTP/run-log claims.
