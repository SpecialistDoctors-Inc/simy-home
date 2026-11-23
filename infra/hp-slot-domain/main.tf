# One shared certificate for clinic site slots: each slot's prod distribution
# serves <site_id>.hp.simy.one (infra/clinic-site, slot mode) until the clinic's
# own domain is moved. Apply once, in workspace hp-slot-domain.

data "aws_caller_identity" "current" {}

data "aws_route53_zone" "simy" {
  name         = "simy.one."
  private_zone = false
}

resource "terraform_data" "guard" {
  lifecycle {
    precondition {
      condition     = data.aws_caller_identity.current.account_id == var.expected_aws_account_id && terraform.workspace == "hp-slot-domain"
      error_message = "Use the HP Control account and the hp-slot-domain workspace."
    }
  }
}

resource "aws_acm_certificate" "slots" {
  domain_name       = "*.hp.simy.one"
  validation_method = "DNS"
  depends_on        = [terraform_data.guard]

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "validation" {
  for_each = { for dvo in aws_acm_certificate.slots.domain_validation_options : dvo.domain_name => dvo }
  zone_id  = data.aws_route53_zone.simy.zone_id
  name     = each.value.resource_record_name
  type     = each.value.resource_record_type
  records  = [each.value.resource_record_value]
  ttl      = 300
}

resource "aws_acm_certificate_validation" "slots" {
  certificate_arn         = aws_acm_certificate.slots.arn
  validation_record_fqdns = [for record in aws_route53_record.validation : record.fqdn]
}
