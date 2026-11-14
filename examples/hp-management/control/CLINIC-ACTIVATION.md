# Paid clinic activation

Draft implementation; both registrar and activation schedules remain disabled by
default. UI approval and real-provider acceptance are still outstanding.

## Implemented path

The authenticated Google purchaser registers the HP/AuthCode in the existing
signup flow. A short-lived server quote binds the code, buyer, domain and DNS
connection version. Contact confirmation and explicit fee acceptance prepare the
durable registrar job. Unknown transfer outcomes are reconciled, never resubmitted.
The fee is the registrar's quote, separate from the monthly subscription; this
does not implement an additional Stripe collection of transfer fees.

After registrar completion, the activation worker validates the complete private
copy and rewrites static asset paths/encodings. It creates a deterministic private
GitHub repository from a pinned template and isolated CloudFormation resources.
Resource readback precedes the atomic site, scoped `hp_management` / `Pro`
entitlement and owner grant. Global SIMY Pro/organization membership is not granted
or required. Only four recognized paid HP plans qualify.

Hosting starts empty. Original web DNS is unchanged until an authenticated,
exact-artifact production publication is approved. The publisher verifies stored
bytes before its frozen web-only DNS cutover and checks public HTTPS bytes after
propagation. Reconciliation never authorizes a DNS write. Mail/TXT records are
preserved, and dependencies on the old web addresses must also be verified.

## Platform configuration (once, not per customer)

`clinic_activation_enabled` enables a separate scheduled worker. Its
`clinic_activation_secret_arn` holds the following configuration (example names;
replace with actual reviewed resources, never copy credentials into a PR):

```json
{
  "github": {
    "owner": "platform-owner",
    "template_owner": "platform-owner",
    "template_repository": "reviewed-hp-template",
    "template_tree": "REVIEWED_40_CHARACTER_GIT_TREE_SHA",
    "app_id": 123,
    "installation_id": 456,
    "private_key_secret_ref": "ARN_OF_EXISTING_APP_SECRET",
    "bootstrap_token_secret_ref": "ARN_OF_REPOSITORY_CREATION_SECRET"
  },
  "cloudformation_role_arn": "ARN_FROM_TERRAFORM_OUTPUT",
  "consumer_role_arn": "ARN_FROM_TERRAFORM_OUTPUT",
  "publisher_permissions_boundary_arn": "ARN_FROM_TERRAFORM_OUTPUT",
  "site": {
    "drive_workspace_folder_id": "EXISTING_PLATFORM_FOLDER",
    "drive_changes_folder_id": "EXISTING_PLATFORM_FOLDER",
    "sheet_id": "EXISTING_PLATFORM_SHEET",
    "operator_subject": "EXISTING_PLATFORM_OPERATOR",
    "operator_email": "EXISTING_PLATFORM_OPERATOR_EMAIL"
  }
}
```

The reviewed template must contain the trusted `check-site.yml` workflow and
existing HP site tooling; `examples/hp-management/site-template` is the source
reference. Repository creation uses a separate secret; runtime access remains
bound to the exact GitHub App installation/repository. New publisher roles have
a mandatory permissions boundary and exact tenant bucket/distribution/hostname.
Review the Terraform plan/IAM capabilities before applying. Failed owned stacks
retry in place; no automatic destructive recreation occurs.

For native distribution, billing configuration may contain `plugin_package` with
`object_key` and lowercase `sha256`. Upload the approved Mac 0.3.13 ZIP once to
`plugins/hp-local-editor/0.3.13/hp-local-editor-darwin-arm64.zip` in the private
versioned artifact bucket with a full-object SHA256 checksum. The download route
requires the active authenticated buyer and signs only the verified VersionId.
No package was uploaded or live download accepted by the local tests.

## DNS connector: still required

There is currently **no deployed provider login/export connector** writing the
following proof. Choosing/implementing that actual provider API is required;
manually inserting a row for each customer does not satisfy self-service.

The server-only `dns-connection:<subscription_id>` contract binds `subject`,
`subscription_id`, `host`, `domain`, `status=verified`, `checked_at`, `nameservers`,
`continuity`, `hosted_zone_id`, `web_cutover_safe`, and optional
`registrant_contact`. Verification must come from authenticated provider access,
complete-zone/delegation preservation and mail/application dependency checks.
Public DNS queries and a browser boolean are insufficient. Transfer quotes
require proof checked within an hour; activation/publication preserve its exact
version. No connection button is configured until its real route exists.

WordPress.com is a separate optional connector. Server forms, logins, commerce,
reservations and module applications require their actual source systems;
copying public HTML does not migrate these functions.

## Release and acceptance boundary

Local fixtures and SDK schemas cover signup binding, cancellation, lost responses,
strict imports, deterministic provisioning, exact IAM binding, safe DNS cutover,
download checks and retries. They do not prove a real transfer, real IAM resource
creation or customer publication.

Before enabling: approve the proposed UI; finish the real DNS connector; configure
the reviewed repository/roles/package; provide the separate Stripe test flow and
an authorized test domain. Then verify a new buyer from payment/AuthCode through
automatic grant, Mac edit/save, preview and customer-approved exact-artifact
publication, followed by real public-page readback. Never label queued/saved or
registrar-complete states as published.
