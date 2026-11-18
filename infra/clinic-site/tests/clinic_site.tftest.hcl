# Plan-only checks of the per-clinic site root. The AWS provider is mocked;
# nothing is read or changed in AWS.
# Run: TF_WORKSPACE=clinic-site-clinic-a terraform -chdir=infra/clinic-site test
mock_provider "aws" {
  override_data {
    target          = data.aws_caller_identity.current
    override_during = plan
    values          = { account_id = "209300895845" }
  }
}

mock_provider "aws" {
  alias = "us_east_1"
  override_resource {
    target          = aws_acm_certificate.prod
    override_during = plan
    values = {
      arn                       = "arn:aws:acm:us-east-1:209300895845:certificate/test"
      domain_validation_options = [{ domain_name = "www.clinic-a.example.jp", resource_record_name = "_x.www.clinic-a.example.jp.", resource_record_type = "CNAME", resource_record_value = "_y.acm-validations.aws." }]
    }
  }
  override_resource {
    target          = aws_acm_certificate_validation.prod
    override_during = plan
    values          = { certificate_arn = "arn:aws:acm:us-east-1:209300895845:certificate/test" }
  }
}

variables {
  site_id     = "clinic-a"
  prod_domain = "www.clinic-a.example.jp"
}

run "new_site_serves_both_environments_on_cloudfront_names_first" {
  command = plan
  assert {
    condition = { for env, b in aws_s3_bucket.site : env => b.bucket } == {
      dev  = "simy-hp-site-clinic-a-dev-209300895845"
      prod = "simy-hp-site-clinic-a-prod-209300895845"
    }
    error_message = "each environment needs its own clinic-site bucket"
  }
  assert {
    condition     = alltrue([for d in aws_cloudfront_distribution.site : length(d.aliases) == 0 && d.viewer_certificate[0].cloudfront_default_certificate])
    error_message = "an unattached site must not claim the clinic's domain yet"
  }
  assert {
    condition     = length(aws_acm_certificate_validation.prod) == 0 && aws_acm_certificate.prod.domain_name == "www.clinic-a.example.jp"
    error_message = "the certificate is requested at once without waiting for the clinic's DNS"
  }
  assert {
    condition     = output.prod_certificate_validation == [{ name = "_x.www.clinic-a.example.jp.", type = "CNAME", value = "_y.acm-validations.aws." }]
    error_message = "the clinic's DNS administrator needs the validation record"
  }
  assert {
    condition     = output.prod_url == "https://www.clinic-a.example.jp"
    error_message = "prod_url must be the clinic's own host, as registration looks it up"
  }
}

run "previews_are_noindex_and_production_is_not" {
  command = plan
  assert {
    condition     = length(aws_cloudfront_response_headers_policy.site["dev"].custom_headers_config) == 1 && length(aws_cloudfront_response_headers_policy.site["prod"].custom_headers_config) == 0
    error_message = "only the preview may send X-Robots-Tag noindex"
  }
  assert {
    condition     = alltrue([for env, d in aws_cloudfront_distribution.site : one(d.origin).origin_id == "clinic-site-s3" && d.default_cache_behavior[0].target_origin_id == "clinic-site-s3"])
    error_message = "the publisher binds one exact origin id"
  }
  assert {
    condition     = alltrue([for p in aws_s3_bucket_public_access_block.site : p.block_public_acls && p.block_public_policy && p.ignore_public_acls && p.restrict_public_buckets])
    error_message = "origin buckets stay private"
  }
}

run "attached_prod_domain_is_served_with_the_issued_certificate" {
  command = plan
  variables {
    prod_domain_attached = true
  }
  assert {
    condition = (
      aws_cloudfront_distribution.site["prod"].aliases == toset(["www.clinic-a.example.jp"])
      && aws_cloudfront_distribution.site["prod"].viewer_certificate[0].acm_certificate_arn == "arn:aws:acm:us-east-1:209300895845:certificate/test"
      && aws_cloudfront_distribution.site["prod"].viewer_certificate[0].minimum_protocol_version == "TLSv1.2_2021"
      && length(aws_acm_certificate_validation.prod) == 1
    )
    error_message = "an attached prod domain is served only with the issued certificate"
  }
  assert {
    condition     = length(aws_cloudfront_distribution.site["dev"].aliases) == 0
    error_message = "the preview never serves the clinic's domain"
  }
}

run "simy_hosts_are_not_clinic_domains" {
  command = plan
  variables {
    prod_domain = "clinic-a.simy.one"
  }
  expect_failures = [var.prod_domain]
}

run "long_site_ids_are_rejected_before_bucket_names_break" {
  command = plan
  variables {
    site_id = "a-very-long-clinic-site-identifier-x"
  }
  expect_failures = [var.site_id]
}
