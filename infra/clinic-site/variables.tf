variable "region" {
  description = "AWS region for the private S3 origin buckets."
  type        = string
  default     = "ap-northeast-1"
}

variable "site_id" {
  description = "HP Control site_id of this clinic site. Also names the Terraform workspace clinic-site-<site_id>."
  type        = string

  validation {
    # Short enough that simy-hp-site-<site_id>-prod-<account> stays a valid bucket name.
    condition     = can(regex("^[a-z][a-z0-9-]{1,30}[a-z0-9]$", var.site_id)) && !strcontains(var.site_id, "--")
    error_message = "site_id must be 3-32 lowercase letters, digits or single hyphens, starting with a letter."
  }
}

variable "prod_domain" {
  description = "The clinic's own homepage host exactly as the clinic entered it (no scheme or path), e.g. www.example-clinic.jp. Empty for a slot."
  type        = string
  default     = ""

  validation {
    condition = (var.prod_domain == "" && var.slot_certificate_arn != "") || (
      var.slot_certificate_arn == ""
      && length(var.prod_domain) <= 253
      && can(regex("^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\\.)+[a-z]{2,63}$", var.prod_domain))
      && !endswith(var.prod_domain, ".simy.one") && var.prod_domain != "simy.one"
      && !endswith(var.prod_domain, ".cloudfront.net")
    )
    error_message = "Give the clinic's own lowercase hostname (not simy.one or cloudfront.net), or leave it empty and set slot_certificate_arn for a slot."
  }
}

variable "prod_domain_attached" {
  description = <<-EOT
    false: the prod distribution serves only its cloudfront.net name while ACM
    waits for the clinic's DNS validation record. true: wait for the issued
    certificate and serve prod_domain. Switch to true before registering the
    site, because the publisher pins the complete CloudFront config.
  EOT
  type        = bool
  default     = false
}

variable "expected_aws_account_id" {
  description = "Account that is allowed to own clinic sites (the HP Control account)."
  type        = string
  default     = "209300895845"
}

variable "slot_certificate_arn" {
  description = <<-EOT
    Slot mode: the *.hp.simy.one certificate from infra/hp-slot-domain. The site
    is an empty, unassigned slot whose prod is served on <site_id>.hp.simy.one
    at once (no clinic DNS needed). clinic_slots.py assigns it to the next paid
    clinic with an unregistered domain. Moving the clinic's own domain later is
    a separate cutover.
  EOT
  type        = string
  default     = ""

  validation {
    condition     = var.slot_certificate_arn == "" || can(regex("^arn:aws:acm:us-east-1:209300895845:certificate/[0-9a-f-]{36}$", var.slot_certificate_arn))
    error_message = "Use the us-east-1 *.hp.simy.one certificate in the HP Control account."
  }
}

variable "slot_zone_id" {
  description = "Slot mode: Route53 hosted zone of simy.one, where <site_id>.hp.simy.one points at the prod distribution."
  type        = string
  default     = ""

  validation {
    condition     = (var.slot_zone_id == "") == (var.slot_certificate_arn == "") && (var.slot_zone_id == "" || can(regex("^Z[A-Z0-9]{5,32}$", var.slot_zone_id)))
    error_message = "Set slot_zone_id together with slot_certificate_arn."
  }
}
