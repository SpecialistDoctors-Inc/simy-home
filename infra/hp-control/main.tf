data "aws_caller_identity" "current" {}
locals {
  acceptance = var.environment == "acceptance"
  name       = local.acceptance ? "simy-hp-control-acceptance" : "simy-hp-control"
  workspace  = local.acceptance ? "hp-control-acceptance" : "hp-control"
  hostname   = local.acceptance ? "hp-control-acceptance.simy.one" : "hp-control.simy.one"
  log_prefix = local.acceptance ? "/simy/hp-control-acceptance" : "/simy/hp-control"
  tags       = { Project = local.workspace, ManagedBy = "terraform" }
  common_environment = {
    HP_TABLE_NAME          = aws_dynamodb_table.authority.name
    HP_COMMAND_QUEUE_URL   = aws_sqs_queue.commands.url
    HP_ARTIFACT_BUCKET     = aws_s3_bucket.artifacts.id
    HP_PUBLIC_BASE_URL     = "https://${local.hostname}"
    HP_PUBLICATION_ENABLED = tostring(var.publication_enabled)
  }
  sites = {
    dev  = { bucket = "simy-sample-clinic-dev-209300895845", distribution = "E2BEBS6CE71LYO" }
    prod = { bucket = "simy-sample-clinic-prod-209300895845", distribution = "E294F04MBS65GK" }
  }
  publisher_sites = { for env, site in local.sites : env => site if !local.acceptance && (env == "dev" ? var.preview_enabled : var.publication_enabled) }
  claim_targets   = { for site_id in [var.self_service_site_id] : site_id => local.publisher_sites if site_id != "" }
}
resource "terraform_data" "guard" {
  lifecycle {
    precondition {
      condition     = data.aws_caller_identity.current.account_id == "209300895845" && terraform.workspace == local.workspace
      error_message = "Use the verified AWS account and dedicated hp-control workspace/state."
    }
    precondition {
      condition = !local.acceptance || (
        !var.preview_enabled && !var.validation_enabled && var.self_service_site_id == "" &&
        (var.wordpress_test_origin != "" && var.publication_enabled) && var.alarm_topic_arn == ""
      )
      error_message = "Acceptance permits publication only to its dedicated WordPress.com test site."
    }
    precondition {
      condition = !local.acceptance || alltrue([for arn in compact([
        var.google_secret_arn, var.signing_secret_arn, var.github_secret_arn,
        var.google_operator_secret_arn, var.github_webhook_secret_arn,
        var.entitlement_secret_arn, var.preflight_secret_arn, var.wordpress_secret_arn,
        var.clinic_billing_secret_arn,
      ]) : startswith(arn, "arn:aws:secretsmanager:ap-northeast-1:209300895845:secret:hp-control/acceptance/")])
      error_message = "Acceptance must use its own HP Control credentials."
    }
    precondition {
      condition     = !var.validation_enabled || length(trimspace(var.validation_gate_reference)) > 0
      error_message = "Renderer launches require reviewed pinned image and isolation evidence."
    }
    precondition {
      condition     = !var.publication_enabled || length(trimspace(var.publication_gate_reference)) > 0
      error_message = "Publication requires a reviewed gate/cutover evidence reference."
    }
    precondition {
      condition     = !var.preview_enabled || length(trimspace(var.preview_gate_reference)) > 0
      error_message = "Preview switching requires legacy-writer retirement and target verification evidence."
    }
    precondition {
      condition     = length(distinct([var.entitlement_endpoint == "", var.entitlement_secret_arn == "", var.preflight_secret_arn == ""])) == 1
      error_message = "Configure both directions of the HP license bridge together."
    }
    precondition {
      condition     = var.self_service_site_id == "" || (var.preview_enabled && var.publication_enabled && var.preflight_secret_arn != "")
      error_message = "Self-service registration requires verified preview, publication and license bridge configuration."
    }
    precondition {
      condition     = var.wordpress_test_origin == "" || (var.wordpress_secret_arn != "" && var.preflight_secret_arn != "" && var.publication_enabled)
      error_message = "The isolated WordPress test requires OAuth, the license bridge and publication authorization."
    }
    precondition {
      condition     = !var.wordpress_paid_sites || (var.wordpress_secret_arn != "" && var.clinic_billing_secret_arn != "" && var.publication_enabled)
      error_message = "Paid WordPress sites need the WordPress credential secret, clinic billing and publication authorization."
    }
    precondition {
      condition     = !var.clinic_copy_enabled || var.clinic_billing_secret_arn != ""
      error_message = "The clinic homepage copier only serves clinic Payment Link intake."
    }
    precondition {
      condition     = var.clinic_billing_secret_arn == "" || startswith(var.clinic_billing_secret_arn, "arn:aws:secretsmanager:ap-northeast-1:209300895845:secret:hp-control/")
      error_message = "Clinic billing must use a dedicated hp-control/ secret."
    }
  }
}
resource "aws_dynamodb_table" "authority" {
  name                        = local.name
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "pk"
  deletion_protection_enabled = true
  attribute {
    name = "pk"
    type = "S"
  }
  attribute {
    name = "queue_state"
    type = "S"
  }
  attribute {
    name = "queue_ready_at"
    type = "N"
  }
  attribute {
    name = "attention_state"
    type = "S"
  }
  global_secondary_index {
    name            = "attention-state"
    hash_key        = "attention_state"
    projection_type = "KEYS_ONLY"
  }
  global_secondary_index {
    name            = "queue-state"
    hash_key        = "queue_state"
    range_key       = "queue_ready_at"
    projection_type = "ALL"
  }
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
  point_in_time_recovery { enabled = true }
  server_side_encryption { enabled = true }
  tags       = local.tags
  depends_on = [terraform_data.guard]
  lifecycle { prevent_destroy = true }
}
resource "aws_sqs_queue" "dead_letters" {
  name                      = "${local.name}-dead.fifo"
  fifo_queue                = true
  sqs_managed_sse_enabled   = true
  message_retention_seconds = 1209600
  tags                      = local.tags
}
resource "aws_sqs_queue" "commands" {
  name                        = "${local.name}-commands.fifo"
  fifo_queue                  = true
  content_based_deduplication = false
  sqs_managed_sse_enabled     = true
  visibility_timeout_seconds  = 5400
  message_retention_seconds   = 345600
  redrive_policy              = jsonencode({ deadLetterTargetArn = aws_sqs_queue.dead_letters.arn, maxReceiveCount = 5 })
  tags                        = local.tags
}
resource "aws_sqs_queue_redrive_allow_policy" "dead_letters" {
  queue_url            = aws_sqs_queue.dead_letters.id
  redrive_allow_policy = jsonencode({ redrivePermission = "byQueue", sourceQueueArns = [aws_sqs_queue.commands.arn] })
}
resource "aws_s3_bucket" "artifacts" {
  bucket     = "${local.name}-artifacts-209300895845"
  tags       = local.tags
  depends_on = [terraform_data.guard]
  lifecycle { prevent_destroy = true }
}
resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_policy" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Sid       = "DenyInsecureTransport", Effect = "Deny", Principal = "*", Action = "s3:*",
    Resource  = [aws_s3_bucket.artifacts.arn, "${aws_s3_bucket.artifacts.arn}/*"],
    Condition = { Bool = { "aws:SecureTransport" = "false" } }
  }] })
}
resource "aws_cloudwatch_log_group" "runtime" {
  for_each          = toset(["api", "consumer", "dispatcher", "validator"])
  name              = "${local.log_prefix}/${each.key}"
  retention_in_days = 30
  tags              = local.tags
}
resource "aws_lambda_function" "runtime" {
  for_each                       = toset(["api", "consumer", "dispatcher"])
  function_name                  = "${local.name}-${each.key}"
  filename                       = var.lambda_zip
  source_code_hash               = filebase64sha256(var.lambda_zip)
  role                           = aws_iam_role.runtime[each.key].arn
  runtime                        = "python3.12"
  handler                        = each.key == "api" ? "hp_control.handler" : each.key == "consumer" ? "hp_control.consume_commands" : "hp_control.dispatch_pending"
  timeout                        = each.key == "consumer" ? 900 : 29
  memory_size                    = each.key == "consumer" ? 2048 : 512
  reserved_concurrent_executions = each.key == "api" ? 10 : each.key == "consumer" ? 2 : 1
  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.runtime[each.key].name
  }
  environment {
    variables = merge(local.common_environment, each.key != "dispatcher" ? {
      HP_CONTROL_ENTITLEMENT_ENDPOINT   = var.entitlement_endpoint
      HP_CONTROL_ENTITLEMENT_SECRET_ARN = var.entitlement_secret_arn
      HP_WORDPRESS_SECRET_ARN           = var.wordpress_secret_arn
      HP_WORDPRESS_TEST_ORIGIN          = var.wordpress_test_origin
      HP_WORDPRESS_PAID_SITES           = tostring(var.wordpress_paid_sites)
      } : {}, each.key == "api" ? {
      HP_GOOGLE_SECRET_ARN            = var.google_secret_arn
      HP_SIGNING_SECRET_ARN           = var.signing_secret_arn
      HP_GITHUB_WEBHOOK_SECRET_ARN    = var.github_webhook_secret_arn
      HP_CONTROL_PREFLIGHT_SECRET_ARN = var.preflight_secret_arn
      HP_SITE_CLAIM_TARGETS           = jsonencode(local.claim_targets)
      HP_CLINIC_BILLING_SECRET_ARN    = var.clinic_billing_secret_arn
      } : each.key == "consumer" ? {
      HP_GITHUB_SECRET_ARN          = var.github_secret_arn
      HP_GOOGLE_OPERATOR_SECRET_ARN = var.google_operator_secret_arn
      HP_VALIDATOR_CONFIG           = jsonencode(local.validator_config)
      HP_PUBLISHER_ROLES            = jsonencode({ for env, role in aws_iam_role.publisher : env => role.arn })
    } : {})
  }
  depends_on = [aws_cloudwatch_log_group.runtime, aws_iam_role_policy.runtime]
  tags       = local.tags
}
resource "aws_lambda_event_source_mapping" "commands" {
  event_source_arn        = aws_sqs_queue.commands.arn
  function_name           = aws_lambda_function.runtime["consumer"].arn
  batch_size              = 1
  function_response_types = ["ReportBatchItemFailures"]
  enabled                 = true
}
resource "aws_apigatewayv2_api" "control" {
  name                         = local.name
  protocol_type                = "HTTP"
  disable_execute_api_endpoint = true
  tags                         = local.tags
}
resource "aws_apigatewayv2_integration" "api" {
  api_id                 = aws_apigatewayv2_api.control.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.runtime["api"].invoke_arn
  payload_format_version = "2.0"
}
resource "aws_apigatewayv2_route" "api" {
  for_each  = toset(concat(["GET /health", "POST /mcp", "POST /github/webhook", "GET /oauth/{proxy+}", "POST /oauth/{proxy+}", "GET /.well-known/{proxy+}"], var.preflight_secret_arn != "" ? ["POST /internal/license/preflight", "POST /internal/site/claim"] : [], var.clinic_billing_secret_arn != "" ? ["GET /start", "GET /start/google", "POST /start/site", "POST /start/wordpress", "GET /start/wordpress/callback", "POST /stripe/webhook"] : []))
  api_id    = aws_apigatewayv2_api.control.id
  route_key = each.value
  target    = "integrations/${aws_apigatewayv2_integration.api.id}"
}
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.control.id
  name        = "$default"
  auto_deploy = true
  default_route_settings {
    throttling_burst_limit = 20
    throttling_rate_limit  = 10
  }
}
resource "aws_lambda_permission" "api" {
  statement_id  = "HttpApiOnly"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.runtime["api"].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.control.execution_arn}/*/*"
}
resource "aws_acm_certificate" "control" {
  domain_name       = local.hostname
  validation_method = "DNS"
  tags              = local.tags
}
resource "aws_route53_record" "validation" {
  for_each = { for option in aws_acm_certificate.control.domain_validation_options : option.domain_name => option }
  zone_id  = var.route53_zone_id
  name     = each.value.resource_record_name
  type     = each.value.resource_record_type
  records  = [each.value.resource_record_value]
  ttl      = 300
}
resource "aws_acm_certificate_validation" "control" {
  certificate_arn         = aws_acm_certificate.control.arn
  validation_record_fqdns = [for record in aws_route53_record.validation : record.fqdn]
}
resource "aws_apigatewayv2_domain_name" "control" {
  domain_name = local.hostname
  domain_name_configuration {
    certificate_arn = aws_acm_certificate_validation.control.certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}
resource "aws_apigatewayv2_api_mapping" "control" {
  api_id      = aws_apigatewayv2_api.control.id
  domain_name = aws_apigatewayv2_domain_name.control.id
  stage       = aws_apigatewayv2_stage.default.id
}
resource "aws_route53_record" "control" {
  zone_id = var.route53_zone_id
  name    = local.hostname
  type    = "A"
  alias {
    name                   = aws_apigatewayv2_domain_name.control.domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.control.domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_cloudwatch_event_rule" "dispatch_pending" {
  name                = "${local.name}-dispatch-pending"
  schedule_expression = "rate(1 minute)"
  tags                = local.tags
}
resource "aws_cloudwatch_event_target" "dispatch_pending" {
  rule = aws_cloudwatch_event_rule.dispatch_pending.name
  arn  = aws_lambda_function.runtime["dispatcher"].arn
  retry_policy {
    maximum_event_age_in_seconds = 300
    maximum_retry_attempts       = 2
  }
}
resource "aws_lambda_permission" "dispatch_pending" {
  statement_id  = "PendingOutboxScheduleOnly"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.runtime["dispatcher"].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.dispatch_pending.arn
}
