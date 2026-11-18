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

### Clinic site origins (`infra/clinic-site`)

One Terraform root, one workspace per site (`clinic-site-<site_id>`), creates
the dev and prod destinations in the HP Control account: a private, versioned,
encrypted bucket `simy-hp-site-<site_id>-<env>-<account>` behind its own
CloudFront distribution with OAC and the single origin `clinic-site-s3`.
Compared with `infra/sample-clinic` it has no GitHub deploy role (HP Control's
publisher roles publish) and no SIMY Route53 records:

- Dev previews are served on the distribution's `cloudfront.net` name, which
  the publisher accepts as the served host, with `X-Robots-Tag: noindex`.
- Prod serves the clinic's own host. Its ACM certificate is validated through
  the clinic's DNS, so the root is applied twice: first without the alias
  (outputs the validation record), then with `prod_domain_attached = true`
  once ACM issued it. The prod response has no `noindex`.
- `ignore_changes = [origin]` keeps a later apply from moving a published site
  back to the bucket root, since the publisher owns the origin path.

The publisher pins each distribution's complete config hash in the site
binding. `clinic_site_deployment.py` reads both distributions and buckets
(read-only) after the alias is attached and prints the binding's `deployment`
block, URLs and the `clinic_sites` entry, refusing anything that is not the
fresh clinic-site shape. `terraform test` covers the root with mocked AWS; CI
runs it in `check-hp-control.yml`.

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
3. marks the intake `ready_mail: sending`, sends one SES mail from the existing
   sign-in sender (`HP_EMAIL_LOGIN_FROM`, already allowed by IAM) to that
   verified mailbox with the clinic's own `/start?session_id=…` link, and
   records `ready_mail: sent` (or `failed`, which a rerun retries). Mail state is
   merged into the latest intake version, so the background copier updating the
   same row cannot lose it. A `sending` mark older than five minutes (the API
   Lambda times out at 29 s) was interrupted and is retried; at worst the clinic
   receives the same mail twice. If the clinic submitted another URL while the
   claim ran, the intake is left unclaimed (`intake_changed`) and a rerun
   evaluates the new URL.

Results are explicit (`site_not_registered`, `owner_mismatch`,
`site_unavailable` = claim targets not deployed, `subscription_inactive`,
`intake_changed`, `mail_failed`, `mail_in_progress`, `notified`,
`already_notified`, …) so the operator can fix and
rerun. A clinic that already claimed by reopening `/start` still gets the mail
once. With no SES sender configured the site is claimed and the result says
`mail: not_configured`.

No new IAM, routes, schedules or tables are added for this.

## Operator runbook (live)

Do each step for one clinic. Steps 2.2, 2.4, 2.5, 3, 4 and 5 change live AWS or
HP Control data; get explicit approval for each Terraform apply, the upload,
the registration and the claim/mail.

1. **Find the intake.** The clinic's `clinic-intake:<sub_id>` row holds the URL,
   verified email and copy state; the public homepage copy is at
   `artifacts bucket/intake/…/site.zip` when `copy_state` is `done`.
2. **Provision the site.**
   1. Create the site repository from the site template, Drive folders and
      Sheet as for any site.
   2. Create the origins with `infra/clinic-site` (one workspace per site,
      `clinic-site-<site_id>`; `site_id` is 3-32 characters):

      ```bash
      terraform -chdir=infra/clinic-site init -backend-config=<private backend.hcl>
      terraform -chdir=infra/clinic-site workspace select -or-create clinic-site-<site_id>
      terraform -chdir=infra/clinic-site apply -var site_id=<site_id> -var prod_domain=<clinic host>
      ```

      `prod_domain` is the host of the URL the clinic entered (e.g.
      `www.example-clinic.jp`). This creates a private, versioned bucket and a
      CloudFront distribution (OAC, single origin `clinic-site-s3`) for dev and
      prod. Dev is a preview on its `cloudfront.net` name with
      `X-Robots-Tag: noindex`; prod is indexable. The prod ACM certificate is
      requested but nothing waits for it yet.
   3. Send the `prod_certificate_validation` record to the clinic's DNS
      administrator. Adding it does not affect their current homepage.
   4. Upload the initial copy to the root of both buckets. From the intake's
      `site.zip` (when `copy_state` is `done`) upload only the contents of its
      `site/` directory, with that prefix removed, so `index.html` sits at the
      bucket root; never upload `manifest.json`. Otherwise upload the rebuilt
      site. The copy must contain `index.html`, only publishable paths, and
      nothing under `releases/` (the publisher's prefix). Step 2.6 checks this.
   5. Once ACM shows the certificate issued, apply again with
      `-var prod_domain_attached=true`. Prod now serves the clinic host as an
      alias (the clinic's DNS still points at the old homepage until cutover).
   6. Pin the reviewed destinations into the binding:

      ```bash
      terraform -chdir=infra/clinic-site output -json > outputs.json
      python clinic_site_deployment.py --terraform-output outputs.json
      ```

      This is read-only. It refuses an unattached prod domain, a distribution
      or bucket that is not the fresh clinic-site shape, an origin already
      switched to a release, and an unpublishable initial copy. It prints
      `dev_url`, `prod_url`, the complete `deployment` block (including the
      config hash the publisher pins and the initial file list) and
      `claim_target`. Do not change either distribution after this step; any
      Terraform change to them invalidates the pinned hash.
   7. Write the binding JSON (fields per `provision_site.validate`, with no
      `license_policy`) using those values and dry-run it:

      ```bash
      python provision_site.py --site site.json --enable-domain-registration --owner-email <clinic email>
      ```

      `--owner-email` is the clinic's verified sign-in mailbox from the intake.
3. **Deploy claim targets.** Add the site to `clinic_sites` in the live tfvars
   (`hp-control` workspace) as the `claim_target` printed in step 2.6. Review
   the plan: only `HP_SITE_CLAIM_TARGETS` on the API Lambda and the two
   publisher policies may change. Apply after approval.
4. **Register the site.** Repeat step 2.7's command with
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

- Moving the clinic's DNS to `prod_dns_target` (cutover) is arranged with the
  clinic; until then a production publication's served readback reaches the
  old homepage and stays pending.
- Per-site publisher roles (see the trade-off above).
- Nothing here was applied to live or acceptance.
