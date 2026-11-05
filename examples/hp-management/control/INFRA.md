# HP control AWS scaffold

Status: **local scaffold only; nothing applied or published**. This stack owns new
HP-control resources in AWS account `209300895845`, `ap-northeast-1`. It does not
import, modify, remove or replace the existing HP-agent or sample-clinic stack.
Do not apply before the application/security review and verified cutover gate.

## Read-only readiness audit (2026-11-05 JST)

- STS confirmed account `209300895845` (existing local AWS identity).
- Public `simy.one` zone: `Z0008232OGBGLDBHC41G`.
- No `hp-control.simy.one` DNS record or regional ACM certificate was found.
  The scaffold creates its own regional DNS-validated certificate and API alias.
- Existing development site: `sample-clinic-dev.simy.one`, CloudFront
  `E2BEBS6CE71LYO`, origin `simy-sample-clinic-dev-209300895845`.
- Existing production site: `sample-clinic.simy.one`, CloudFront
  `E294F04MBS65GK`, origin `simy-sample-clinic-prod-209300895845`.
  DNS and distributions were inspected only. Their URLs remain intact.
- No dedicated HP/Google secret metadata matched the bounded name inventory.
  No secret values were requested. Existing broader application credentials
  must not be reused or expanded to fill this gap.
- Default VPC metadata was inspected, but this scaffold uses a new isolated
  validation VPC instead. No existing VPC/subnet/security group is changed.

Outstanding deployment inputs: dedicated Google web OAuth client and approved
redirect URI, separate operator Drive/Sheets/Gmail consent/refresh credentials,
least-privilege GitHub App installation for the approved repository, RSA OAuth
issuer signing key, reviewed ZIP and digest-pinned validator image. Metadata
alone cannot verify provider consent, installation permissions or redirect URIs.

## Application interface

`infra/hp-control` defines Python 3.12 Lambda handlers `hp_control.handler` and
`hp_control.consume_commands`, plus a minute-scheduled `hp_control.dispatch_pending`
Lambda. All receive:

| Environment | Meaning |
| --- | --- |
| `HP_TABLE_NAME` | Single authoritative DynamoDB table (`pk` string) |
| `HP_COMMAND_QUEUE_URL` | FIFO command queue |
| `HP_ARTIFACT_BUCKET` | Private encrypted/versioned artifact bucket |
| `HP_PUBLIC_BASE_URL` | `https://hp-control.simy.one` |
| `HP_PUBLICATION_ENABLED` | String `false` until reviewed cutover |

The API additionally receives `HP_GOOGLE_SECRET_ARN` and
`HP_SIGNING_SECRET_ARN`. The consumer receives `HP_GITHUB_SECRET_ARN`,
`HP_GOOGLE_OPERATOR_SECRET_ARN`, and `HP_PUBLISHER_ROLES` (JSON environment-to-role
map, empty while publication is disabled). All references must be existing,
dedicated `hp-control/` Secrets Manager secrets in the target account/region.
Terraform never provisions or reads secret values. If a customer-managed KMS key
is selected for these secrets, separately review exact-key decrypt permissions;
the scaffold does not grant broad KMS access.

HTTP API routes include `GET /health`, `POST /mcp`,
GET/POST `/oauth/{proxy+}`, and GET `/.well-known/{proxy+}`. These cover register,
authorize, token, callback, JWKS, userinfo, OpenID/OAuth discovery and the MCP
protected-resource document. No CORS wildcard or API Gateway default endpoint is
enabled. Authentication, scopes, token audience, PKCE, exact redirect validation,
and MCP notification 202 behavior belong to the application. API Gateway access
logging is deliberately absent so OAuth query parameters do not enter logs;
Lambda application logs must also redact tokens, codes and credentials.

DynamoDB has on-demand capacity, encryption, PITR, deletion protection and TTL
attribute `expires_at` (epoch seconds). Applications must use conditional writes
and transactions for replay keys, leases and state transitions; Terraform cannot
enforce expressions on individual writes. TTL deletion is asynchronous, so the
application must reject expired items even while still present. Site bindings
are admin-provisioned only; clients must never create or mutate them through MCP.
The `queue-state` GSI uses `queue_state` as its partition key and `queue_ready_at` as its range key and projects ALL; only due rows occupy the bounded dispatcher page. The `attention-state` GSI supports a bounded presence check for operations requiring intervention.
The dispatcher queries this index for persisted outbox records and retries SQS
sends at least once. It has no provider secret or artifact access. Successful passes emit only counts/attention state, and Lambda logging is explicitly routed to the scoped log group. The runtime
IAM policy has no table scan or index wildcard permissions.

Commands use `MessageGroupId = site_id` and a durable command identifier as
`MessageDeduplicationId`. Queue deduplication is only an optimization: authority
records must prevent replay beyond SQS's deduplication interval. The consumer's
partial-batch response must stop processing the failed FIFO group. Batch size is
one, timeout 900 seconds, visibility 5,400 seconds, max five receives before the
14-day DLQ. A DLQ arrival is an operational failure requiring reconciliation,
not successful parent completion.

Artifact permissions cover only `artifacts/*`; store immutable manifests,
source bundles and validation evidence there. Presigned URLs must be bounded by
object key, method, expiry and size in application code. No public bucket reads.

## Validation and publication boundary

By default Fargate is dormant. Setting the separately reviewed `validation_enabled`
gate allows only the exact task definition/cluster and execution-role PassRole.
There is no persistent ECS service; each durable operation launches one bounded task.
The container has no task IAM role, AWS application credentials, injected
secrets or privileged capabilities. Its root filesystem is read-only. The
network has no ingress, peering or application private-network route, with
public IPv4 HTTPS egress excluding private, loopback, CGNAT, multicast and
link-local destinations. Fargate does not expose EC2 IMDS; the metadata-disabled
environment variable is defense in depth, not the network boundary. A reviewed
launcher must select the output subnet/security group, enable public IP for
public image pull, enforce a finite deadline, and give validation a sealed input
bundle without application secrets. The execution role can write only validator
logs: private ECR pulls are scoped to the task-owned `simy-hp-control-validator` repository.
Do not treat the task definition as proof that hostile source execution is
fully sandboxed or that the validation application has been exercised.

Production publication defaults to false. Preview has its own disabled-by-default gate and legacy-dev-writer cutover reference; it can be enabled independently. Only enabled environments receive publisher roles/AssumeRole permissions. Enabling requires a nonempty reviewed
`publication_gate_reference`, application policy review and explicit cutover.
This Terraform string guard records evidence; it does not independently approve
that evidence. New per-environment publisher roles can write only immutable
`releases/*` in the exact existing origin and update/invalidate only the exact
verified CloudFront distribution. Existing GitHub deployment IAM roles remain
unchanged. CloudFront IAM cannot constrain an UpdateDistribution call to just
OriginPath: the publisher must validate the full expected configuration and
ETag, change only the intended release prefix, verify readback, and reject drift.
Root objects cannot be overwritten/deleted by the new publisher roles. Do not
switch until existing workflows and rollback paths have been reconciled.

## Local validation and future deployment preparation

```sh
terraform -chdir=infra/hp-control fmt -check
terraform -chdir=infra/hp-control init -backend=false -input=false
terraform -chdir=infra/hp-control validate
```

These checks do not create AWS resources. A real plan requires an approved
isolated backend, `hp-control` workspace, actual artifact paths, all four secret
ARN inputs and validator image digest. No fabricated secrets or deployable
placeholder ZIP is supplied. Check account/region, provider app permissions,
DNS/certificate, current clinic distribution config, state ownership and exact
artifact digest again immediately before any authorized apply. No plan or apply
was run during the scaffold audit.


## Private renderer bootstrap (preparation only)

The renderer registry is task-owned private ECR `simy-hp-control-validator` with
immutable tags, AES256 encryption and image scanning. No image is distributed in
a public registry. The final `validator_image` must be the exact verified account
and region repository URI followed by `@sha256:<reviewed-digest>`. The launcher
remains disabled until a separately reviewed validation gate is enabled.

There is a bootstrap dependency: the private repository must exist before the
reviewed image can be pushed, and the full task definition needs its real digest.
The full root module also requires real Lambda/provider-secret inputs, so do not
pass invented inputs just to target the registry. After explicit infrastructure
authorization and an STS account/region check, create only the dedicated repository
with immutable tags, AES256 encryption and scan-on-push (for example an explicitly
reviewed `aws ecr create-repository` command). This step creates no application
credentials or ECS tasks. Authenticate to that exact private registry without
printing the temporary registry credential, tag/push the locally reviewed Linux
x86_64 image using a new immutable release tag, and read back the image digest.

With the real image digest and the actual application inputs available, initialize
the isolated backend and `hp-control` workspace, import the dedicated repository
into `aws_ecr_repository.validator`, then review the full-stack Terraform plan.
The plan must preserve the imported registry and existing clinic URLs, pin the
image by digest rather than tag, and leave launcher/preview/production gates at
their separately reviewed values. Review scan results and rerun the secretless
renderer smoke before enabling launches. No registry creation, image push, state
import, plan or apply was executed during this local preparation.
