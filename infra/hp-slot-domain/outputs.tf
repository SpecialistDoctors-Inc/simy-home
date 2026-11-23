output "slot_certificate_arn" {
  description = "Pass to infra/clinic-site as slot_certificate_arn."
  value       = aws_acm_certificate_validation.slots.certificate_arn
}

output "slot_zone_id" {
  description = "Pass to infra/clinic-site as slot_zone_id."
  value       = data.aws_route53_zone.simy.zone_id
}
