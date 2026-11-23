# Clinic sites for Payment Link purchases

How a clinic that bought HP management through a simy.one Payment Link and
registered "一般的なサイト" (a general URL, formerly "その他のホームページ") gets its site in live HP
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

## Slot pool: no operator step after payment (`clinic_slots.py`)

The runbook above needs the operator for every clinic, and until then the
clinic waits on "準備ができましたら…ご連絡します" with no mail (seen live on
2026-11-23). Creating repositories and AWS destinations at payment time would
need the GitHub App's Administration permission (not allowed, see
CONNECTIONS.md) and CloudFront/S3 create rights in the API. Instead the operator
prepares empty sites in advance and the copier hands them out.

### What a slot is

A slot is an ordinary clinic site (repository, Drive folders, Sheet, dev/prod
origins, binding) that is not assigned yet. Its prod distribution serves
`<site_id>.hp.simy.one` at once with the shared `*.hp.simy.one` certificate,
so no clinic DNS is needed before editing and publishing. Its bucket roots hold
only a placeholder `index.html`. Its claim target is deployed in `clinic_sites`
and its id is listed in `clinic_slot_ids`.

### What happens after payment

1. `/start` keeps the URL as an intake and queues the homepage copy (unchanged).
2. The copier stores the copy (now up to 1,000 files / 50 MB, the publisher's
   own limits) and queues the subscription for a slot (`clinic-slot-pending`).
3. In the same scheduled run `SlotAssigner.run_one`:
   - skips WordPress.com intakes and domains the operator registered by hand;
   - reserves the first free slot in `site-slot-pool` (one transaction over the
     pool row, the slot row and the intake, so two clinics never share a slot);
   - uploads the publishable files of the copy to both slot buckets, refusing a
     bucket that holds anything but the placeholder (or a `releases/` prefix);
   - writes `registration-site:<clinic host>` with the intake's verified
     sign-in email as owner and the uploaded files as `initial_file_paths`;
   - invokes the API Lambda's `clinic_ready` task, which claims the site under
     the clinic's subscription and sends the "ready" mail once.
4. The clinic's `/start` page shows the editing guide and the slot's address
   (`https://<site_id>.hp.simy.one`). Partial copies and "no free slot" are
   shown on the page; files the editor cannot publish (query-string pages,
   unsupported types) are counted in `copy_skipped`.

Each step is recorded on the intake (`slot_site_id`, `slot_state` =
`assigned` / `registered` / `ready` / `waiting` / `failed`, `slot_error`) and is
safe to repeat after a Lambda timeout. `no_free_slot` and a pending claim stay
queued and are retried every minute; adding a slot resumes them.

The copier role gains only: read `artifacts/intake/*`, list and put objects in
the buckets of `clinic_slot_ids`, and invoke the API function. It creates no
AWS resources and grants nothing itself; the API's existing claim path checks
the license and the deployed claim targets.

### Operator: prepare slots (live)

Each step changes live AWS or HP Control data; get explicit approval for each.

1. Once: `infra/hp-slot-domain` (workspace `hp-slot-domain`) issues
   `*.hp.simy.one` in us-east-1, validated in the simy.one zone. Note its
   `slot_certificate_arn` and `slot_zone_id` outputs.
2. Per slot (`site_id` such as `slot-001`):
   1. Repository, Drive folders and Sheet as for any site.
   2. `infra/clinic-site` in workspace `clinic-site-<site_id>` with
      `-var site_id=<site_id> -var slot_certificate_arn=… -var slot_zone_id=…`
      (no `prod_domain`). Prod serves `<site_id>.hp.simy.one` immediately.
   3. Upload a placeholder `index.html` to the root of both buckets.
   4. `clinic_site_deployment.py --terraform-output outputs.json` prints the
      deployment block (initial files: `["index.html"]`) and the claim target.
   5. Write the binding JSON (no `license_policy`) and dry-run
      `python provision_slot.py --site slot.json`.
3. Add every new slot to `clinic_sites` and `clinic_slot_ids` in the live
   tfvars (`hp-control` workspace) and apply. The plan may change only
   `HP_SITE_CLAIM_TARGETS`, the publisher policies and the copier policy/env.
4. `python provision_slot.py --site slot.json --table simy-hp-control --apply`
   for each slot. The pool now lists it as free.
5. Intakes copied before slots existed (or after `slot_error`) are queued with
   `python provision_slot.py --enqueue sub_… --table simy-hp-control --apply`.

Keep a few slots free. When the pool is empty, clinics see
「編集用の環境を準備中です」 and are served as soon as a slot is added.

## Not covered

- Moving the clinic's DNS to `prod_dns_target` (cutover) is arranged with the
  clinic; until then a production publication's served readback reaches the
  old homepage and stays pending. A slot keeps publishing on
  `<site_id>.hp.simy.one` until its own cutover, which is not automated.
- Alerting when the slot pool runs low (the `hp_clinic_slot` log event with
  `no_free_slot` is the signal today).
- Per-site publisher roles (see the trade-off above).
- Nothing here was applied to live or acceptance.
