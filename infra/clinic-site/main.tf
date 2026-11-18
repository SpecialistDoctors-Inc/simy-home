# Dev and prod origins for one clinic site that HP Control previews and
# publishes. Each environment is a private, versioned S3 bucket behind its own
# CloudFront distribution (OAC). HP Control's publisher later switches the
# origin path to an immutable releases/<sha256> prefix; nothing else here
# deploys content. One Terraform workspace (clinic-site-<site_id>) per site.

data "aws_caller_identity" "current" {}

locals {
  environments = toset(["dev", "prod"])
  origin_id    = "clinic-site-s3"
  bucket_name  = { for env in local.environments : env => "simy-hp-site-${var.site_id}-${env}-${data.aws_caller_identity.current.account_id}" }
  # Only an attached prod domain is served under its own name. Dev always uses
  # its cloudfront.net name, which the publisher accepts as the served host.
  aliases = { dev = [], prod = var.prod_domain_attached ? [var.prod_domain] : [] }
}

resource "terraform_data" "guard" {
  lifecycle {
    precondition {
      condition     = data.aws_caller_identity.current.account_id == var.expected_aws_account_id
      error_message = "Refusing to manage a clinic site outside AWS account ${var.expected_aws_account_id}."
    }

    precondition {
      condition     = terraform.workspace == "clinic-site-${var.site_id}"
      error_message = "Select Terraform workspace clinic-site-${var.site_id} before planning or applying."
    }
  }
}

resource "aws_s3_bucket" "site" {
  for_each   = local.environments
  bucket     = local.bucket_name[each.key]
  depends_on = [terraform_data.guard]
}

resource "aws_s3_bucket_versioning" "site" {
  for_each = local.environments
  bucket   = aws_s3_bucket.site[each.key].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "site" {
  for_each = local.environments
  bucket   = aws_s3_bucket.site[each.key].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "site" {
  for_each = local.environments
  bucket   = aws_s3_bucket.site[each.key].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudfront_origin_access_control" "site" {
  for_each                          = local.environments
  name                              = "simy-hp-site-${var.site_id}-${each.key}-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# Requested at once so the clinic can add the validation record before the
# homepage moves. Validated by the clinic's DNS, never by a SIMY zone.
resource "aws_acm_certificate" "prod" {
  provider          = aws.us_east_1
  domain_name       = var.prod_domain
  validation_method = "DNS"
  depends_on        = [terraform_data.guard]

  lifecycle {
    create_before_destroy = true
  }
}

# Waits until ACM issued the certificate. Only applied once attached.
resource "aws_acm_certificate_validation" "prod" {
  count           = var.prod_domain_attached ? 1 : 0
  provider        = aws.us_east_1
  certificate_arn = aws_acm_certificate.prod.arn

  timeouts {
    create = "10m"
  }
}

resource "aws_cloudfront_response_headers_policy" "site" {
  for_each = local.environments
  name     = "simy-hp-site-${var.site_id}-${each.key}-headers"

  # Previews must never be indexed. Production is the clinic's real homepage.
  dynamic "custom_headers_config" {
    for_each = each.key == "dev" ? [1] : []
    content {
      items {
        header   = "X-Robots-Tag"
        override = true
        value    = "noindex, nofollow, noarchive"
      }
    }
  }

  security_headers_config {
    content_type_options { override = true }
    frame_options {
      frame_option = "SAMEORIGIN"
      override     = true
    }
    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }
    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = false
      preload                    = false
      override                   = true
    }
  }
}

resource "aws_cloudfront_distribution" "site" {
  for_each            = local.environments
  comment             = "SIMY HP clinic site ${var.site_id} ${each.key}"
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  aliases             = local.aliases[each.key]
  price_class         = "PriceClass_200"
  http_version        = "http2and3"

  origin {
    domain_name              = aws_s3_bucket.site[each.key].bucket_regional_domain_name
    origin_id                = local.origin_id
    origin_access_control_id = aws_cloudfront_origin_access_control.site[each.key].id
  }

  default_cache_behavior {
    target_origin_id           = local.origin_id
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    response_headers_policy_id = aws_cloudfront_response_headers_policy.site[each.key].id

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }

    min_ttl     = 0
    default_ttl = 300
    max_ttl     = 86400
  }

  custom_error_response {
    error_code            = 403
    response_code         = 404
    response_page_path    = "/error.html"
    error_caching_min_ttl = 60
  }

  custom_error_response {
    error_code            = 404
    response_code         = 404
    response_page_path    = "/error.html"
    error_caching_min_ttl = 60
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    cloudfront_default_certificate = length(local.aliases[each.key]) == 0
    acm_certificate_arn            = length(local.aliases[each.key]) > 0 ? aws_acm_certificate_validation.prod[0].certificate_arn : null
    ssl_support_method             = length(local.aliases[each.key]) > 0 ? "sni-only" : null
    minimum_protocol_version       = length(local.aliases[each.key]) > 0 ? "TLSv1.2_2021" : "TLSv1"
  }

  # The publisher owns the origin path after the first release; Terraform must
  # not move the live site back to the bucket root on a later apply.
  lifecycle {
    ignore_changes = [origin]
  }
}

resource "aws_s3_bucket_policy" "site" {
  for_each = local.environments
  bucket   = aws_s3_bucket.site[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowCloudFrontReadOnly"
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.site[each.key].arn}/*"
      Condition = { StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.site[each.key].arn } }
    }]
  })
}
