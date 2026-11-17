# Clinic sites for Payment Link purchases

How a clinic that bought HP management through a simy.one Payment Link and
registered "その他のホームページ" (a general URL) gets its site in live HP
Control, and what the operator does between the purchase and the clinic's first
edit.

## Problem (live, 2026-11-18)

- `/start` hands the URL to `Service.register_by_owner_email`. It claims the site
  only when the operator registered `registration-site:<host>` with the same
  owner email **and** `_check_claim_targets` finds the site's dev/prod bucket and
  CloudFront distribution in `HP_SITE_CLAIM_TARGETS`.
- Live `HP_SITE_CLAIM_TARGETS` is `{}`: Terraform derived claim targets for at
  most one site (`self_service_site_id`), always pointing at the sample-clinic
  destinations, and live leaves that ID empty. Every owner-email claim therefore
  raised `hp_license_unavailable` and the intake stayed `received`.
- The live publisher roles could write only the sample-clinic buckets and
  distributions, so even a claimed clinic site could not be previewed or
  published.
- `/start` promises "準備ができましたら … あてにご連絡します", but nothing sent
  that mail. The clinic had to reopen `/start` by chance.

Acceptance proved the claim itself on 2026-11-18 with placeholder targets
(simy-home#469); this change gives live the equivalent for real sites.

## Design

### Per-site claim targets (`clinic_sites`)

`infra/hp-control` takes a live-only map:

```hcl
clinic_sites = {
  "<site_id>" = {
    dev  = { bucket = "<dev origin bucket>",  distribution = "<dev CloudFront ID>" }
    prod = { bucket = "<prod origin bucket>", distribution = "<prod CloudFront ID>" }
  }
}
```

- `HP_SITE_CLAIM_TARGETS` becomes the sample self-service entry (unchanged
  behavior) merged with `clinic_sites`. `_check_claim_targets` already looks a
  site up by its own `site_id` and compares both environments exactly, so the
  application needs no change to support many sites.
- The existing per-environment publisher roles are extended to exactly the
  listed buckets (`ListBucket`, `releases/*` get/put) and distributions. The
  policy name is kept so live updates in place. The publisher still validates
  each site's full CloudFront config, ETag and readback before switching.
- Guards: live only (acceptance keeps its placeholders); requires preview,
  publication and the license bridge; every site has its own dev and prod
  bucket and distribution, never shared with another clinic site or the sample
  clinic; sample-clinic and acceptance placeholder buckets are rejected.
- `terraform test` (mocked AWS, plan only) checks the env JSON, both publisher
  policies, and each guard. CI runs it in `check-hp-control.yml`.

Trade-off: one publisher role per environment can reach every clinic site of
that environment; the consumer chooses the destination from the DynamoDB site
binding it already validates. Per-site roles would narrow that blast radius
but need a site-aware `HP_PUBLISHER_ROLES`; left as a follow-up once the number
of clinic sites justifies it.

### Claim and "ready" mail (`clinic_ready.py`)

The operator runs `notify_clinic_ready.py --subscription-id sub_...`. Without
`--apply` it is read-only: it reads the subscription, intake, registration and
the API Lambda's deployed `HP_SITE_CLAIM_TARGETS` and reports what is missing.
With `--apply` it invokes the API Lambda directly with
`{"hp_operator_task": "clinic_ready", "subscription_id": ...}`. The handler takes
this path only for events without `requestContext`, i.e. IAM-authorized direct
invocations; API Gateway events never reach it.

`ClinicReady.notify`:

1. requires an active subscription whose bound Google subject matches the
   intake;
2. for an open intake (`received` / `needs_review`), calls
   `register_by_owner_email` with the subject and verified sign-in email the
   intake recorded — the same check as reopening `/start` — and marks the intake
   `claimed`;
3. reserves `ready_notified_at` on the intake, then sends one SES mail from the
   existing sign-in sender (`HP_EMAIL_LOGIN_FROM`, already allowed by IAM) to that
   verified mailbox with the clinic's own `/start?session_id=…` link. A failed
   send releases the reservation so a rerun retries; a successful one is never
   repeated.

Results are explicit (`site_not_registered`, `owner_mismatch`,
`site_unavailable` = claim targets not deployed, `subscription_inactive`,
`mail_failed`, `notified`, `already_notified`, …) so the operator can fix and
rerun. A clinic that already claimed by reopening `/start` still gets the mail
once. With no SES sender configured the site is claimed and the result says
`mail: not_configured`.

No new IAM, routes, schedules or tables are added for this.

## Operator runbook (live)

Do each step for one clinic. Steps 3 and 5 change live; get explicit approval
for the Terraform apply and for the claim/mail.

1. **Find the intake.** The clinic's `clinic-intake:<sub_id>` row holds the URL,
   verified email and copy state; the public homepage copy is at
   `artifacts bucket/intake/…/site.zip` when `copy_state` is `done`.
2. **Provision the site.** Create the site repository from the site template,
   its dev and prod origin buckets and CloudFront distributions (same shape as
   `infra/sample-clinic`: private versioned bucket behind CloudFront OAC; the
   publisher later switches the origin path to a `releases/` prefix), Drive
   folders and Sheet. Write the verified binding JSON (fields per
   `provision_site.validate`, with no `license_policy`) and dry-run it:

   ```bash
   python provision_site.py --site site.json --enable-domain-registration --owner-email <clinic email>
   ```

   `prod_url` must be the clinic's URL as entered (same host). `--owner-email`
   is the clinic's verified sign-in mailbox from the intake.
3. **Deploy claim targets.** Add the site to `clinic_sites` in the live tfvars
   (`hp-control` workspace) with the exact buckets and distribution IDs from the
   binding. Review the plan: only `HP_SITE_CLAIM_TARGETS` on the API Lambda and
   the two publisher policies may change. Apply after approval.
4. **Register the site.** Repeat step 2's command with
   `--table simy-hp-control --apply`. This writes only
   `registration-site:<host>`; nothing is granted yet.
5. **Claim and notify.**

   ```bash
   python notify_clinic_ready.py --subscription-id sub_...
   ```

   Expect `registration: present`, `owner_matches: true`,
   `claim_targets: deployed`, `subscription: active`. Then add `--apply`. Expect
   `{"status": "notified", …}`. The clinic opens the link, signs in, downloads
   the HP plugin and starts editing.

If the clinic signed in with a different mailbox (`needs_review` /
`owner_mismatch`), confirm the owner out of band, then re-register with the
mailbox they actually use and rerun step 5.

## Not covered

- Creating per-clinic buckets/distributions has no generic Terraform root yet
  (`infra/sample-clinic` is hard-wired to the sample clinic). Generalizing it is
  the natural next step.
- Nothing here was applied to live or acceptance.
