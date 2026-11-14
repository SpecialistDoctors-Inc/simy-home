# Registrar work is isolated from publication and DNS mutation. It is disabled
# until verified customer details/DNS continuity/price acceptance are connected.
locals {
  clinic_transfer = var.clinic_transfer_enabled ? toset(["registrar"]) : toset([])
}
resource "aws_iam_role" "clinic_transfer" {
  for_each = local.clinic_transfer
  name     = "${local.name}-clinic-transfer"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole"
  }] })
  tags = local.tags
}
resource "aws_cloudwatch_log_group" "clinic_transfer" {
  for_each          = local.clinic_transfer
  name              = "${local.log_prefix}/clinic-transfer"
  retention_in_days = 30
  tags              = local.tags
}
resource "aws_iam_role_policy" "clinic_transfer" {
  for_each = aws_iam_role.clinic_transfer
  name     = "clinic-transfer-only"
  role     = each.value.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    {
      Sid      = "TransferLedger", Effect = "Allow",
      Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:ConditionCheckItem"],
      Resource = aws_dynamodb_table.authority.arn,
      Condition = { "ForAllValues:StringLike" = { "dynamodb:LeadingKeys" = [
        "clinic-transfer-pending", "clinic-transfer:*", "clinic-intake:*", "stripe-subscription:*"
      ] } }
    },
    {
      Sid      = "IntakeKeyOnly", Effect = "Allow", Action = ["secretsmanager:GetSecretValue"],
      Resource = var.clinic_transfer_key_secret_arn
    },
    {
      # Route 53 Domains does not support resource-level ARNs for these actions.
      Sid = "RegistrarOnly", Effect = "Allow",
      Action = ["route53domains:CheckDomainTransferability", "route53domains:TransferDomain",
      "route53domains:GetOperationDetail", "route53domains:ListOperations"],
      Resource = "*"
    },
    {
      Sid      = "LogOnly", Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"],
      Resource = "${aws_cloudwatch_log_group.clinic_transfer[each.key].arn}:*"
    }
  ] })
}
resource "aws_lambda_function" "clinic_transfer" {
  for_each                       = local.clinic_transfer
  function_name                  = "${local.name}-clinic-transfer"
  filename                       = var.lambda_zip
  source_code_hash               = filebase64sha256(var.lambda_zip)
  role                           = aws_iam_role.clinic_transfer[each.key].arn
  runtime                        = "python3.12"
  handler                        = "hp_control.transfer_clinic_domains"
  timeout                        = 120
  memory_size                    = 256
  reserved_concurrent_executions = 1
  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.clinic_transfer[each.key].name
  }
  environment {
    variables = {
      HP_TABLE_NAME                 = aws_dynamodb_table.authority.name
      HP_DOMAIN_TRANSFER_SECRET_ARN = var.clinic_transfer_key_secret_arn
    }
  }
  lifecycle {
    precondition {
      condition     = can(regex(":secret:hp-control/", var.clinic_transfer_key_secret_arn))
      error_message = "A dedicated hp-control/ intake-key secret is required before registrar writes are enabled."
    }
  }
  depends_on = [aws_cloudwatch_log_group.clinic_transfer, aws_iam_role_policy.clinic_transfer]
  tags       = local.tags
}
resource "aws_cloudwatch_event_rule" "clinic_transfer" {
  for_each            = local.clinic_transfer
  name                = "${local.name}-clinic-transfer"
  schedule_expression = "rate(1 minute)"
  tags                = local.tags
}
resource "aws_cloudwatch_event_target" "clinic_transfer" {
  for_each = local.clinic_transfer
  rule     = aws_cloudwatch_event_rule.clinic_transfer[each.key].name
  arn      = aws_lambda_function.clinic_transfer[each.key].arn
  retry_policy {
    maximum_event_age_in_seconds = 60
    maximum_retry_attempts       = 0
  }
}
resource "aws_lambda_permission" "clinic_transfer" {
  for_each      = local.clinic_transfer
  statement_id  = "ClinicTransferScheduleOnly"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.clinic_transfer[each.key].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.clinic_transfer[each.key].arn
}
