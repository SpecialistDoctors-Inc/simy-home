# Plan-only checks of how clinic sites become claim targets and publisher
# permissions. The AWS provider is mocked; nothing is read or changed in AWS.
# Run: TF_WORKSPACE=hp-control terraform -chdir=infra/hp-control test
mock_provider "aws" {
  override_data {
    target          = data.aws_caller_identity.current
    override_during = plan
    values          = { account_id = "209300895845" }
  }
  # The certificate's validation options are otherwise unknown at plan time.
  override_resource {
    target          = aws_acm_certificate.control
    override_during = plan
    values = {
      arn                       = "arn:aws:acm:ap-northeast-1:209300895845:certificate/test"
      domain_validation_options = [{ domain_name = "hp-control.simy.one", resource_record_name = "_x.hp-control.simy.one.", resource_record_type = "CNAME", resource_record_value = "_y.acm-validations.aws." }]
    }
  }
}

variables {
  lambda_zip                 = "versions.tf" # only hashed at plan time
  validator_image            = "209300895845.dkr.ecr.ap-northeast-1.amazonaws.com/simy-hp-control-validator@sha256:0000000000000000000000000000000000000000000000000000000000000000"
  google_secret_arn          = "arn:aws:secretsmanager:ap-northeast-1:209300895845:secret:hp-control/google"
  github_secret_arn          = "arn:aws:secretsmanager:ap-northeast-1:209300895845:secret:hp-control/github"
  signing_secret_arn         = "arn:aws:secretsmanager:ap-northeast-1:209300895845:secret:hp-control/signing"
  google_operator_secret_arn = "arn:aws:secretsmanager:ap-northeast-1:209300895845:secret:hp-control/google-operator"
  github_webhook_secret_arn  = "arn:aws:secretsmanager:ap-northeast-1:209300895845:secret:hp-control/github-webhook"
  entitlement_endpoint       = "https://example.supabase.co/functions/v1/hp-control-entitlement"
  entitlement_secret_arn     = "arn:aws:secretsmanager:ap-northeast-1:209300895845:secret:hp-control/entitlement"
  preflight_secret_arn       = "arn:aws:secretsmanager:ap-northeast-1:209300895845:secret:hp-control/preflight"
  preview_enabled            = true
  preview_gate_reference     = "test"
  publication_enabled        = true
  publication_gate_reference = "test"
  clinic_sites = {
    clinic-a = {
      dev  = { bucket = "simy-hp-site-clinic-a-dev", distribution = "EAAAAADEV" }
      prod = { bucket = "simy-hp-site-clinic-a-prod", distribution = "EAAAAAPROD" }
    }
    clinic-b = {
      dev  = { bucket = "simy-hp-site-clinic-b-dev", distribution = "EBBBBBDEV" }
      prod = { bucket = "simy-hp-site-clinic-b-prod", distribution = "EBBBBBPROD" }
    }
  }
}

run "each_clinic_site_claims_its_own_destinations" {
  command = plan
  assert {
    condition = jsondecode(aws_lambda_function.runtime["api"].environment[0].variables.HP_SITE_CLAIM_TARGETS) == {
      clinic-a = {
        dev  = { bucket = "simy-hp-site-clinic-a-dev", distribution = "EAAAAADEV" }
        prod = { bucket = "simy-hp-site-clinic-a-prod", distribution = "EAAAAAPROD" }
      }
      clinic-b = {
        dev  = { bucket = "simy-hp-site-clinic-b-dev", distribution = "EBBBBBDEV" }
        prod = { bucket = "simy-hp-site-clinic-b-prod", distribution = "EBBBBBPROD" }
      }
    }
    error_message = "Claim targets must list every clinic site with its own destinations."
  }
  assert {
    condition = jsondecode(aws_iam_role_policy.publisher["prod"].policy).Statement[2].Resource == [
      "arn:aws:cloudfront::209300895845:distribution/E294F04MBS65GK",
      "arn:aws:cloudfront::209300895845:distribution/EAAAAAPROD",
      "arn:aws:cloudfront::209300895845:distribution/EBBBBBPROD",
    ]
    error_message = "The prod publisher must reach exactly the prod distributions."
  }
  assert {
    condition = jsondecode(aws_iam_role_policy.publisher["dev"].policy).Statement[1].Resource == [
      "arn:aws:s3:::simy-sample-clinic-dev-209300895845/releases/*",
      "arn:aws:s3:::simy-hp-site-clinic-a-dev/releases/*",
      "arn:aws:s3:::simy-hp-site-clinic-b-dev/releases/*",
    ]
    error_message = "The dev publisher must write only dev release prefixes."
  }
}

run "sample_self_service_site_keeps_its_targets" {
  command = plan
  variables {
    self_service_site_id = "sample-clinic"
  }
  assert {
    condition     = keys(jsondecode(aws_lambda_function.runtime["api"].environment[0].variables.HP_SITE_CLAIM_TARGETS)) == ["clinic-a", "clinic-b", "sample-clinic"]
    error_message = "The sample self-service site stays claimable alongside clinic sites."
  }
}

run "clinic_sites_require_separate_buckets" {
  command = plan
  variables {
    clinic_sites = {
      clinic-a = {
        dev  = { bucket = "simy-hp-site-clinic-a", distribution = "EAAAAADEV" }
        prod = { bucket = "simy-hp-site-clinic-a", distribution = "EAAAAAPROD" }
      }
    }
  }
  expect_failures = [var.clinic_sites]
}

run "clinic_sites_reject_sample_clinic_buckets" {
  command = plan
  variables {
    clinic_sites = {
      clinic-a = {
        dev  = { bucket = "simy-sample-clinic-dev-209300895845", distribution = "EAAAAADEV" }
        prod = { bucket = "simy-hp-site-clinic-a-prod", distribution = "EAAAAAPROD" }
      }
    }
  }
  expect_failures = [var.clinic_sites]
}

run "clinic_sites_require_live_publication" {
  command = plan
  variables {
    publication_enabled = false
  }
  expect_failures = [terraform_data.guard]
}

run "clinic_sites_never_share_a_destination" {
  command = plan
  variables {
    clinic_sites = {
      clinic-a = {
        dev  = { bucket = "simy-hp-site-clinic-a-dev", distribution = "EAAAAADEV" }
        prod = { bucket = "simy-hp-site-clinic-a-prod", distribution = "EAAAAAPROD" }
      }
      clinic-b = {
        dev  = { bucket = "simy-hp-site-clinic-a-dev", distribution = "EBBBBBDEV" }
        prod = { bucket = "simy-hp-site-clinic-b-prod", distribution = "EBBBBBPROD" }
      }
    }
  }
  expect_failures = [terraform_data.guard]
}
