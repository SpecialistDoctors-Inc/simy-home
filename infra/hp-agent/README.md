# Always-on HP update agent

This Terraform root creates a single dedicated ARM Ubuntu 24.04 EC2 instance
for the standalone homepage update controller. It is deliberately separate from
the static-site Terraform state. The instance has no inbound security-group
rules, no SSH key and is administered through SSM only.

It creates an immutable ECR repository, a one-day encrypted sealed-artifact S3
bucket, a 30-day CloudWatch log group, and a separate encrypted 20 GiB EBS data
volume for the SQLite ledger and Codex auth. The data volume and its attachment
have `prevent_destroy`, and the attachment has `force_detach = false`; a
maintenance migration must explicitly remove those safeguards before a live
detach. The instance itself is protected from destroy and ignores AMI/user-data
drift after first launch. Daily DLM snapshots retain seven copies.

`backup_time_utc` controls the daily snapshot schedule. Its default is `04:15`
UTC (13:15 JST), selected so the first scheduled snapshot can be observed during
this acceptance run. EC2 snapshot ARNs omit the account field; the source volume ARN remains pinned
to this account and this data volume. Before applying an IAM change, export the
rendered policy from the Terraform plan and run `check-dlm-policy.py --policy
<policy.json> --account <account-id> --region <region> --volume-id <volume-id>`.
This read-only AWS IAM simulation covers snapshot create/tag/delete matching and
denial for unrelated volumes and untagged deletions. See the [AWS snapshot IAM
examples](https://docs.aws.amazon.com/ebs/latest/userguide/security_iam_id-based-policy-examples.html#security_iam_id-based-policy-examples-snapshots).

A manual snapshot is not evidence that the DLM schedule
ran; record the DLM-created snapshot timestamp and completion separately.

The bootstrap uses the arm64 Noble HTTPS package source
`https://ports.ubuntu.com/ubuntu-ports`, installs Docker, and installs the
official fixed AWS CLI v2.39.3 archive only after checking its pinned SHA-256.
It intentionally does not install credentials, state, or start the agent. Use a separate encrypted migration after
the Terraform apply succeeds; verify its encryption and pinned SHA-256 in an
SSM session before writing the data volume. The agent instance role can read only
`sealed/*` objects in its artifact bucket, pull only its ECR repository, write
only its log group and publish health metrics under `SIMY/HPAgent`.

The instance role includes only SSM session-messaging channels and instance
registration. It does not receive the broad managed SSM policy and cannot read
Parameter Store.

The health alarm is fail-closed. In addition to a recent container poll, the
host reads the state database without writing it. An unresolved recovery
incident, an interrupted worker/review, a provider reconciliation requirement,
an exhausted retry, an overdue active job, or an unreadable state schema makes
the `Healthy` metric zero. A human approval wait is not an incident.

Set `operational_alert_email` only to the dedicated operations mailbox.
Terraform then creates a task-owned SNS topic and subscription and attaches it
to the service-health and EC2 system-recovery alarms. AWS sends a subscription
confirmation to that address; **do not regard notification as configured until
the recipient accepts it and an alarm test is read back**. With the variable
blank, no SNS topic, subscription, or external alarm action is created. Alert
messages contain CloudWatch alarm metadata, not request text or credentials.

## Apply

Keep `backend.hcl`, the sealed migration bundle and every credential outside Git.
Do not place Google OAuth, GitHub, Codex authentication or local SQLite state in
Terraform variables or user data.

```sh
cd infra/hp-agent
cp terraform.tfvars.example /private/location/hp-agent.tfvars
# Set a recorded, pinned Ubuntu 24.04 arm64 AMI ID and unique bucket name.
terraform init -backend-config=/private/location/backend.hcl
terraform plan -var-file=/private/location/hp-agent.tfvars -out=/private/location/hp-agent.tfplan
terraform apply /private/location/hp-agent.tfplan
```

After apply, use the `ssm_start_session_command` output. Confirm the EBS data
volume is mounted and the sealed migration has been verified before starting the
systemd service. An EC2 system-status alarm uses AWS recovery; it does not
restart the controller for application failures.

The host needs normal HTTPS egress to Google, GitHub, OpenAI and AWS. The
service remains fail-closed: an interrupted worker/reviewer is not retried
without operator recovery, and production publishing still needs its own exact
artifact approval.

## Release and migration

1. Commit and review the runtime files. Build the ARM image from that committed
   runner directory, push to the dedicated ECR, and resolve its immutable digest.
2. Run `build-release.py --source <40-character-commit> --image <ECR@sha256>
   --output <private-staging>/release-manifest.json`. This reads committed Git
   objects, not untracked local files. Retain its printed manifest hash.
3. Package those committed paths with `git archive`, add the manifest, and pin
   the archive SHA-256 in the SSM command. On the host, verify that archive hash
   **before extracting or executing any script**. Run `verify-release.py` with
   the expected manifest hash, source SHA and image digest from the operator's
   release record. Never obtain expected hashes from the downloaded bundle.
4. Use `prepare-volume.sh <exact-volume-id>` on the new dedicated data disk.
   Confirm the old controller has no active work or ambiguous external effects.
   Stop only its recorded, immediately reverified owned process; preserve the
   stopped local volumes as rollback evidence. Never start both writers.
5. Archive the four service volumes (`control`, `state`, `work`, `codex-auth`)
   after the writer has stopped. Checkpoint SQLite and record its hash. Encrypt
   the archive to a dedicated server-generated GPG key whose public fingerprint
   is read back through SSM. Upload only ciphertext to `sealed/`; authentication
   must never appear in SSM commands/output, Git, Terraform, or logs.
6. Decrypt on the host in a root-only directory. Run `restore-bundle.py
   <archive> <archive-sha256> <database-sha256> <manifest-sha256> <source-sha>
   <image>`. It rejects unsafe archive entries, verifies database integrity and
   inactive effect state, and binds the restore marker to this release.
7. Run `install-runtime.sh <image> ap-northeast-1 <instance-id> <source-sha>
   <manifest-sha256>`. It verifies the files and marker, and checks the image's
   Python payload without network/credentials before mounting service secrets.
   A partial install can be retried only while no `hp-agent` container exists;
   inspect any existing container before deciding a separate recovery action.
8. Verify live Google identity, polling, isolation, one new dev request, exact
   deployed files, Sheet readback and a single preview notification. Check the
   health metric and snapshot configuration. Confirm production is unchanged.
   Remove only this task's temporary transfer files and temporary key material.

The systemd egress unit requires the data mount before Docker starts. It blocks
the container from instance metadata, private networks and host-local services.
The application receives no instance AWS role; the host uses it only for ECR,
the sealed migration prefix, CloudWatch and SSM messaging. The operational SNS
recipient is independent of Google/Gmail so it can report an expired Google
connection; keep the recipient confirmation and its test receipt with the
release evidence.

The instance and data volume must not be replaced by routine Terraform applies.
For a deliberate host upgrade, prepare a replacement, quiesce and verify the
single writer, checkpoint/snapshot the disk and perform an explicit migration.
Do not remove Terraform destruction protections to force an unattended upgrade.

## In-place controller upgrade after a planned reboot

`upgrade-runtime.sh` is deliberately narrower than an installation. It may run
only after a planned reboot has left the one recorded old controller stopped.
The operator supplies the exact old container ID, old source/manifest/image
identity and the separately recorded new immutable image/source/manifest
identity. Before changing anything, the helper verifies both release records,
the original migration proof and SQLite integrity. It refuses a pending effect,
ambiguous/sending email, unresolved incident or active job. The sole legacy
exception is a `needs_input` job whose matching request is already
`superseded`, `cancelled` or `revoked` and has no pending effect or email; the
new controller reconciles that parked history to `stopped`.

The helper never stops, removes or signals a process or container. It verifies
the old container is the exact named, stopped, non-restarting container, renames
it to `hp-agent-rollback-<old-source-prefix>`, and preserves the old migration
marker as a root-only backup before creating the new `hp-agent`. If any step
fails, it leaves the current state in place and writes one root-only
`upgrade-recovery-<new-source-prefix>.json` receipt. Do not delete that receipt
or retry automatically: reconcile it against the named rollback container and
the preserved marker first.

## Retiring the dedicated legacy instance

After the replacement production path is fully verified, obtain explicit
resource-lifecycle authority for account `209300895845`, region `ap-northeast-1`,
instance `i-0249d60873ec01d17`. Review the drained ledger, writer fences, published
bytes and retained claim/backups immediately before applying a saved plan.
`retired = true` disables actions on this stack's system-recovery and heartbeat
alarms, then manages only that instance's power state as `stopped` with
`force = false`. It does not terminate the instance, detach/delete disks, alter
DLM, remove credentials/claims/backups, or signal processes/containers. Keep
`retired = true` in the applied variable file so future plans enforce retirement.
The root/data disks, volume attachment and existing destruction protections remain.
Normal stop releases the ephemeral public IPv4 address. The instance lifecycle
ignores that observed association change so a subsequent plan cannot replace the
protected host just to restore an address. Initial provisioning still requests
public IPv4; this exception does not start or replace a retired host.

For this retirement, the applied variables are retained privately in
`output/hp-local-editor-20261105/legacy-retirement-preparation-20261106/retired.candidate.tfvars`.
Keep that `retired = true` input for subsequent plans; the older pre-retirement
variable file is not the applied retirement configuration.

The pinned AWS provider's [`aws_ec2_instance_state` resource](https://registry.terraform.io/providers/hashicorp/aws/5.100.0/docs/resources/ec2_instance_state)
uses a normal EC2 stop when `force = false`. Its [delete handler is a no-op](https://github.com/hashicorp/terraform-provider-aws/blob/v5.100.0/internal/service/ec2/ec2_instance_state.go),
so removing this power-state resource does not restart the instance. Setting
`retired = false` would remove the stopped-state enforcement and re-enable these
two alarms; it is not an automatic operational rollback. Leave retirement in
place unless a separate rollback review authorizes reactivation and restores
exact writer fencing safely. Do not restore a legacy root `sync --delete`
writer while production serves `releases/`. Any later host restart is a separate
resource operation and may auto-start its old runtime; never use it as an
unreviewed rollback. A stopped host continues to incur storage/retained-resource
costs; deleting it or its data is outside this retirement plan.
