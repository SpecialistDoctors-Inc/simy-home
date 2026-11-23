# Plan-only. The AWS provider is mocked; nothing is read or changed in AWS.
# Run: TF_WORKSPACE=hp-slot-domain terraform -chdir=infra/hp-slot-domain test
mock_provider "aws" {
  override_data {
    target          = data.aws_caller_identity.current
    override_during = plan
    values          = { account_id = "209300895845" }
  }
  override_data {
    target          = data.aws_route53_zone.simy
    override_during = plan
    values          = { zone_id = "Z0008232OGBGLDBHC41G" }
  }
  override_resource {
    target          = aws_acm_certificate.slots
    override_during = plan
    values = {
      arn                       = "arn:aws:acm:us-east-1:209300895845:certificate/00000000-0000-0000-0000-000000000000"
      domain_validation_options = [{ domain_name = "*.hp.simy.one", resource_record_name = "_x.hp.simy.one.", resource_record_type = "CNAME", resource_record_value = "_y.acm-validations.aws." }]
    }
  }
}

run "wildcard_certificate_is_validated_in_the_simy_zone" {
  command = plan
  assert {
    condition     = aws_acm_certificate.slots.domain_name == "*.hp.simy.one" && aws_acm_certificate.slots.validation_method == "DNS"
    error_message = "slots share one *.hp.simy.one certificate"
  }
  assert {
    condition     = alltrue([for r in aws_route53_record.validation : r.zone_id == "Z0008232OGBGLDBHC41G" && r.name == "_x.hp.simy.one."])
    error_message = "validation records belong in the simy.one zone"
  }
}
