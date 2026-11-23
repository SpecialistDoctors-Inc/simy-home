output "claim_target" {
  description = "Paste as clinic_sites[\"<site_id>\"] in the live hp-control tfvars."
  value = {
    for env in local.environments : env => {
      bucket       = aws_s3_bucket.site[env].bucket
      distribution = aws_cloudfront_distribution.site[env].id
    }
  }
}

output "deployment" {
  description = "Input for clinic_site_deployment.py, which adds the reviewed config hash and initial files."
  value = {
    for env in local.environments : env => {
      bucket          = aws_s3_bucket.site[env].bucket
      distribution_id = aws_cloudfront_distribution.site[env].id
      origin_id       = local.origin_id
      domain_name     = aws_cloudfront_distribution.site[env].domain_name
    }
  }
}

output "dev_url" {
  value = "https://${aws_cloudfront_distribution.site["dev"].domain_name}"
}

output "prod_url" {
  value = "https://${local.prod_host}"
}

output "prod_domain_attached" {
  description = "True once prod serves prod_url (always for a slot)."
  value       = local.slot || var.prod_domain_attached
}

output "prod_certificate_validation" {
  description = "DNS record(s) the clinic's DNS administrator adds so ACM can issue the prod certificate (none for a slot)."
  value = flatten([for cert in aws_acm_certificate.prod : [for dvo in cert.domain_validation_options : {
    name  = dvo.resource_record_name
    type  = dvo.resource_record_type
    value = dvo.resource_record_value
  }]])
}

output "prod_dns_target" {
  description = "Where the clinic's homepage host points (CNAME or ALIAS) once SIMY serves it."
  value       = aws_cloudfront_distribution.site["prod"].domain_name
}
