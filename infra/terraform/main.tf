data "aws_caller_identity" "current" {}

locals {
  bucket_name              = "simy-site-${var.environment}"
  github_oidc_provider_arn = var.github_oidc_provider_arn != "" ? var.github_oidc_provider_arn : "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
}

# -----------------------------------------------------------------------------
# S3 Bucket (private, OAC access only)
# -----------------------------------------------------------------------------

resource "aws_s3_bucket" "site" {
  bucket = local.bucket_name
}

resource "aws_s3_bucket_versioning" "site" {
  bucket = aws_s3_bucket.site.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "site" {
  bucket = aws_s3_bucket.site.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "site" {
  bucket = aws_s3_bucket.site.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontOAC"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.site.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.site.arn
          }
        }
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# CloudFront Origin Access Control
# -----------------------------------------------------------------------------

resource "aws_cloudfront_origin_access_control" "site" {
  name                              = "${local.bucket_name}-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# -----------------------------------------------------------------------------
# ACM Certificate (us-east-1)
# -----------------------------------------------------------------------------

resource "aws_acm_certificate" "site" {
  provider = aws.us_east_1

  domain_name               = var.domain_name
  subject_alternative_names = var.subject_alternative_names
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "cert_validation" {
  for_each = var.route53_zone_id != "" ? {
    for dvo in aws_acm_certificate.site.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  } : {}

  zone_id = var.route53_zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 300
}

resource "aws_acm_certificate_validation" "site" {
  provider = aws.us_east_1

  certificate_arn         = aws_acm_certificate.site.arn
  validation_record_fqdns = var.route53_zone_id != "" ? [for r in aws_route53_record.cert_validation : r.fqdn] : []
}

# -----------------------------------------------------------------------------
# CloudFront Distribution
# -----------------------------------------------------------------------------

resource "aws_cloudfront_distribution" "site" {
  enabled             = true
  default_root_object = "index.html"
  aliases             = concat([var.domain_name], var.subject_alternative_names)
  price_class         = "PriceClass_200"
  http_version        = "http2and3"

  origin {
    domain_name              = aws_s3_bucket.site.bucket_regional_domain_name
    origin_id                = "s3-site"
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }

  default_cache_behavior {
    target_origin_id       = "s3-site"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 300   # 5 minutes for HTML
    max_ttl     = 86400 # 1 day

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.redirect.arn
    }
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
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.site.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  depends_on = [aws_acm_certificate_validation.site]
}

# -----------------------------------------------------------------------------
# CloudFront Function (viewer-request: optional basic auth + /test/* redirect)
# -----------------------------------------------------------------------------

locals {
  basic_auth_enabled = var.basic_auth_username != "" && var.basic_auth_password != ""
  basic_auth_token   = local.basic_auth_enabled ? base64encode("${var.basic_auth_username}:${var.basic_auth_password}") : ""
}

resource "aws_cloudfront_function" "redirect" {
  name    = "simy-site-${var.environment}-redirect"
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = <<-EOF
    var BASIC_AUTH_ENABLED = ${local.basic_auth_enabled ? "true" : "false"};
    var EXPECTED_AUTH = 'Basic ${local.basic_auth_token}';
    var OLD_BASIC_AUTH_ENABLED = true;
    var OLD_EXPECTED_AUTH = 'Basic dGV0c3VvQHNpbXkub25lOm1qNHgzM2Rk';

    function queryHas(request, key) {
      return request.querystring && request.querystring[key];
    }

    function queryToString(request, additions) {
      var querystring = request.querystring || {};
      var parts = [];
      for (var key in querystring) {
        if (!querystring.hasOwnProperty(key)) continue;
        var item = querystring[key];
        if (item.multiValue) {
          for (var i = 0; i < item.multiValue.length; i++) {
            parts.push(encodeURIComponent(key) + '=' + encodeURIComponent(item.multiValue[i].value || ''));
          }
        } else if (item.value === '') {
          parts.push(encodeURIComponent(key));
        } else {
          parts.push(encodeURIComponent(key) + '=' + encodeURIComponent(item.value || ''));
        }
      }
      for (var addKey in additions) {
        if (!additions.hasOwnProperty(addKey)) continue;
        parts.push(encodeURIComponent(addKey) + '=' + encodeURIComponent(additions[addKey]));
      }
      return parts.length ? '?' + parts.join('&') : '';
    }

    function regionFromCountry(country) {
      var c = (country || '').toUpperCase();
      var map = {
        US: 'us',
        JP: 'jp',
        GB: 'gb',
        DE: 'de',
        FR: 'fr',
        CA: 'ca',
        IN: 'in',
        KR: 'kr',
        BR: 'br',
        MX: 'mx',
        ID: 'id',
        VN: 'vn',
        ES: 'es',
        IT: 'it',
        SA: 'sa',
        TW: 'tw',
        TH: 'th',
        MY: 'my',
        PH: 'ph'
      };
      return map[c] || '';
    }

    function regionFromAcceptLanguage(acceptLanguage) {
      var raw = (acceptLanguage || '').toLowerCase();
      if (!raw) return '';
      var first = raw.split(',')[0].split(';')[0].trim();
      if (first.indexOf('ja') === 0) return 'jp';
      if (first.indexOf('en-us') === 0 || first.indexOf('en') === 0) return 'us';
      if (first.indexOf('en-gb') === 0) return 'gb';
      if (first.indexOf('en-ca') === 0) return 'ca';
      if (first.indexOf('en-in') === 0) return 'in';
      if (first.indexOf('fr') === 0) return 'fr';
      if (first.indexOf('de') === 0) return 'de';
      if (first.indexOf('es-es') === 0) return 'es';
      if (first.indexOf('es') === 0) return 'mx';
      if (first.indexOf('it') === 0) return 'it';
      if (first.indexOf('ko') === 0) return 'kr';
      if (first.indexOf('pt') === 0) return 'br';
      if (first.indexOf('zh') === 0) return 'tw';
      if (first.indexOf('hi') === 0) return 'in';
      if (first.indexOf('ar') === 0) return 'sa';
      if (first.indexOf('vi') === 0) return 'vn';
      if (first.indexOf('th') === 0) return 'th';
      if (first.indexOf('id') === 0) return 'id';
      return '';
    }

    function maybeRedirectWithViewerRegion(request, host, uri) {
      if (queryHas(request, 'region') || queryHas(request, 'lang')) return null;
      if (!(uri === '/' || uri === '/index.html' || uri === '/compare.html' || uri === '/press-release.html' || uri === '/privacy.html' || uri === '/terms.html')) return null;

      var countryHeader = request.headers['cloudfront-viewer-country'];
      var languageHeader = request.headers['accept-language'];
      var region = countryHeader ? regionFromCountry(countryHeader.value) : '';
      if (!region && languageHeader) region = regionFromAcceptLanguage(languageHeader.value);
      if (!region) return null;

      var normalizedUri = uri === '/index.html' ? '/' : uri;
      return {
        statusCode: 302,
        statusDescription: 'Found',
        headers: { location: { value: 'https://' + host + normalizedUri + queryToString(request, { region: region }) } }
      };
    }

    function handler(event) {
      var request = event.request;
      var uri = request.uri;

      if (BASIC_AUTH_ENABLED) {
        var headers = request.headers;
        if (!headers.authorization || headers.authorization.value !== EXPECTED_AUTH) {
          return {
            statusCode: 401,
            statusDescription: 'Unauthorized',
            headers: {
              'www-authenticate': { value: 'Basic realm="dev"' }
            }
          };
        }
      }

      if (OLD_BASIC_AUTH_ENABLED && (uri === '/old' || uri === '/old/' || uri.startsWith('/old/'))) {
        var oldHeaders = request.headers;
        if (!oldHeaders.authorization || oldHeaders.authorization.value !== OLD_EXPECTED_AUTH) {
          return {
            statusCode: 401,
            statusDescription: 'Unauthorized',
            headers: {
              'www-authenticate': { value: 'Basic realm="SIMY old"' }
            }
          };
        }
      }

      var host = request.headers.host ? request.headers.host.value : '';
      var viewerRegionRedirect = maybeRedirectWithViewerRegion(request, host, uri);
      if (viewerRegionRedirect) return viewerRegionRedirect;

      if (uri === '/test' || uri === '/test/' || uri.startsWith('/test/')) {
        return {
          statusCode: 301,
          statusDescription: 'Moved Permanently',
          headers: { location: { value: 'https://' + host + '/' } }
        };
      }

      // /index.html -> / redirect
      if (uri === '/index.html') {
        return {
          statusCode: 301,
          statusDescription: 'Moved Permanently',
          headers: { location: { value: 'https://' + host + '/' } }
        };
      }

      if (uri === '/old') {
        return {
          statusCode: 301,
          statusDescription: 'Moved Permanently',
          headers: { location: { value: 'https://' + host + '/old/' } }
        };
      }

      if (uri === '/old/') {
        request.uri = '/old/index.html';
        return request;
      }

      // The alternate homepage preview is now the production homepage.
      if (uri === '/newpage') {
        return {
          statusCode: 301,
          statusDescription: 'Moved Permanently',
          headers: { location: { value: 'https://' + host + '/' } }
        };
      }

      if (uri === '/newpage/' || uri === '/newpage/index.html') {
        return {
          statusCode: 301,
          statusDescription: 'Moved Permanently',
          headers: { location: { value: 'https://' + host + '/' } }
        };
      }

      // Remove trailing slash (except root /)
      // e.g. /about/ -> /about.html
      if (uri !== '/' && uri.endsWith('/')) {
        var trimmed = uri.slice(0, -1);
        return {
          statusCode: 301,
          statusDescription: 'Moved Permanently',
          headers: { location: { value: 'https://' + host + trimmed + '.html' } }
        };
      }

      // /pricing, /compare, /about etc. -> redirect to .html
      if (uri !== '/' && !uri.includes('.')) {
        return {
          statusCode: 301,
          statusDescription: 'Moved Permanently',
          headers: { location: { value: 'https://' + host + uri + '.html' } }
        };
      }

      return request;
    }
  EOF
}

# -----------------------------------------------------------------------------
# Route53 Records (only when zone_id is provided)
# -----------------------------------------------------------------------------

resource "aws_route53_record" "site_a" {
  count = var.route53_zone_id != "" ? 1 : 0

  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = aws_cloudfront_distribution.site.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "site_aaaa" {
  count = var.route53_zone_id != "" ? 1 : 0

  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = aws_cloudfront_distribution.site.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "www_a" {
  count = var.route53_zone_id != "" && contains(var.subject_alternative_names, "www.${var.domain_name}") ? 1 : 0

  zone_id = var.route53_zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = aws_cloudfront_distribution.site.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "www_aaaa" {
  count = var.route53_zone_id != "" && contains(var.subject_alternative_names, "www.${var.domain_name}") ? 1 : 0

  zone_id = var.route53_zone_id
  name    = "www.${var.domain_name}"
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = aws_cloudfront_distribution.site.hosted_zone_id
    evaluate_target_health = false
  }
}

# -----------------------------------------------------------------------------
# GitHub Actions OIDC Deploy Role (S3 sync + CF invalidation)
# -----------------------------------------------------------------------------

resource "aws_iam_role" "github_actions_site_deploy" {
  name = "simy-site-${var.environment}-gha-deploy"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.github_oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:environment:${var.environment}"
          }
        }
      }
    ]
  })
}

resource "aws_iam_policy" "github_actions_site_deploy" {
  name = "simy-site-${var.environment}-gha-deploy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3Sync"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.site.arn,
          "${aws_s3_bucket.site.arn}/*"
        ]
      },
      {
        Sid    = "CloudFrontInvalidation"
        Effect = "Allow"
        Action = [
          "cloudfront:CreateInvalidation",
          "cloudfront:GetInvalidation",
          "cloudfront:ListInvalidations"
        ]
        Resource = aws_cloudfront_distribution.site.arn
      },
      {
        Sid    = "CloudFrontFunctionManagement"
        Effect = "Allow"
        Action = [
          "cloudfront:DescribeFunction",
          "cloudfront:GetFunction",
          "cloudfront:UpdateFunction",
          "cloudfront:PublishFunction"
        ]
        Resource = "arn:aws:cloudfront::${data.aws_caller_identity.current.account_id}:function/simy-site-${var.environment}-redirect"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "github_actions_site_deploy" {
  role       = aws_iam_role.github_actions_site_deploy.name
  policy_arn = aws_iam_policy.github_actions_site_deploy.arn
}
