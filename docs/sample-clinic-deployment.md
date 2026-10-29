# Sample clinic deployment

The sample is isolated from the existing SIMY homepage. Dev is
`sample-clinic-dev.simy.one`; production is `sample-clinic.simy.one`. Both send
`X-Robots-Tag: noindex, nofollow, noarchive`. Source is under
`examples/sample-clinic/`; the build produces `dist/` without dependencies.

## Infrastructure and state

`infra/sample-clinic/` creates separate private, versioned, encrypted S3 origins,
CloudFront OAC/distributions, ACM certificates, Route53 aliases and scoped GitHub
OIDC roles in AWS account `209300895845`, hosted zone `Z0008232OGBGLDBHC41G`.
Terraform >= 1.10 is required. Use the backend example with an existing versioned
state bucket and distinct workspaces `sample-clinic-dev` / `sample-clinic-prod`.
The configuration refuses the wrong account or workspace. Never apply an old
saved plan after changing configuration or state.

```sh
terraform -chdir=infra/sample-clinic init -backend-config=/secure/path/backend.hcl
terraform -chdir=infra/sample-clinic workspace select sample-clinic-dev
terraform -chdir=infra/sample-clinic plan -var-file=environments/dev.tfvars
```

Use `workspace new` only on first setup. Repeat with `sample-clinic-prod` and
`environments/prod.tfvars` for production. Apply only an inspected plan for the
explicitly authorized target. This setup never syncs the existing homepage buckets.

## GitHub setup

Environments `sample-clinic-dev` and `sample-clinic-prod` must allow only branch
`dev` and `main`, respectively. Production must require a reviewer who checks
the customer approval evidence. Keep the production enable variable false until
these protections and all production secrets have been read back successfully.
The reviewer must not approve a production job merely because CI passed.

Set environment-scoped secrets from the matching Terraform outputs:

| Secret | Output |
| --- | --- |
| `AWS_SAMPLE_CLINIC_DEPLOY_ROLE_ARN` | `site_deploy_role_arn` |
| `SAMPLE_CLINIC_S3_BUCKET` | `s3_bucket_name` |
| `SAMPLE_CLINIC_CF_DISTRIBUTION_ID` | `cloudfront_distribution_id` |

## Development delivery

A sample-only PR into `dev` runs the Node build/tests. After merge, the workflow
builds the exact dev SHA, deploys it, waits for CloudFront invalidation, and reads
back `version.json`. It then uploads an immutable GitHub artifact named
`sample-clinic-dev-<SHA>-<attempt>` and records its artifact ID. The manifest
includes the SHA, static-byte hash and request ID/revision when present.
Inspect the actual page after deployment and append the URL, exact identity,
artifact ID and browser results to the request's Sheet events.

An old workflow rerun cannot overwrite a newer branch head. If an unrelated
path-filtered commit advances dev while the job is waiting, manually dispatch
from the latest dev branch. PR validation uses its own concurrency group.

## Production promotion

Production runs **only** through `workflow_dispatch` from `main`, with repository
variable `SAMPLE_CLINIC_PRODUCTION_ENABLED=true`, after the protected Environment
review. A main push never publishes the sample. This is a manually reviewed
promotion path, not an automatic customer-approval service.

Provide these frozen inputs from the reviewed preview and recorded human decision:

- `environment`: `prod`
- `source_artifact_id`: immutable artifact ID from the successful dev run
- `approved_source_sha`: full dev source SHA
- `approved_artifact_hash`: its `artifactHash`
- `request_id` and `request_revision`: the approved Sheet request version
- `approval_record_ref`: an opaque reference to the customer's actual decision
  (never a token or private approval text)

The environment reviewer verifies that the customer authorized exactly that
request and artifact. A Sheet status or a typed reference alone grants no
publication authority. The workflow checks GitHub's artifact/run metadata:
expected repository, source workflow, dev branch, successful latest attempt,
source SHA and artifact name. It then checks downloaded static bytes against the
approved hash and the manifest's request ID/revision. Missing evidence, a fork,
a PR artifact, expired artifact, failed deployment or modified bytes fails closed.

The static files are copied unchanged from dev. Only `version.json` is updated:
`sourceRevision` remains the approved dev SHA; `releaseRevision` identifies the
main workflow SHA; `sourceArtifactId` identifies the immutable artifact. The
approval reference is not exposed in the public site manifest. This avoids
promoting unrelated changes between the existing dev and main branches. Install
sample-only workflow/source updates on main using a separately reviewed PR;
do not merge the repository's unrelated branch divergence as part of this sample.
Artifacts expire after 90 days; an expired review requires a fresh dev deployment
and customer review. Do not rebuild and silently substitute new bytes.

After publication, verify the manifest and the changed page, then record a
`published` event. GitHub acceptance or a successful upload alone is not completion.

## Manual acceptance test and future automation

The initial Sheet test explicitly invokes the customer and developer Codex roles
in the current engineering chat. Both use the same connected management Google
account, marked as a test. It proves real Sheet writes/readback, source changes,
GitHub CI and dev rendering; it does not prove distinct-customer OAuth isolation,
Sheet-triggered unattended execution or email delivery.

A future automated business service must use a persisted SIMY WorkFlow with
frozen input, authoritative site/customer bindings, durable claims, cancellation,
idempotent effects and a 202 run receipt. Execution handlers belong in simy-crew;
SQL/migrations belong in simy-backend. The existing agent_task worker is read/draft
only and must not be repurposed to bypass external-write policy. An engineering
chat or GitHub job is not evidence that this business-run integration exists.
