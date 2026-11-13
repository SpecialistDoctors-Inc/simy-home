# Scheduled copier for clinics that paid through a Payment Link before SIMY
# prepared their site. It reads one pending intake, fetches the clinic's public
# homepage and stores a zip under artifacts-bucket/intake/. Off by default.
locals {
  clinic_copy = var.clinic_copy_enabled ? toset(["copier"]) : toset([])
}
resource "aws_iam_role" "clinic_copy" {
  for_each = local.clinic_copy
  name     = "${local.name}-clinic-copy"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole"
  }] })
  tags = local.tags
}
resource "aws_cloudwatch_log_group" "clinic_copy" {
  for_each          = local.clinic_copy
  name              = "${local.log_prefix}/clinic-copy"
  retention_in_days = 30
  tags              = local.tags
}
resource "aws_iam_role_policy" "clinic_copy" {
  for_each = aws_iam_role.clinic_copy
  name     = "clinic-copy-only"
  role     = each.value.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    {
      Sid      = "IntakeRows", Effect = "Allow",
      Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:ConditionCheckItem"],
      Resource = aws_dynamodb_table.authority.arn
    },
    {
      Sid      = "IntakeCopiesOnly", Effect = "Allow", Action = ["s3:PutObject"],
      Resource = ["${aws_s3_bucket.artifacts.arn}/intake/*"]
    },
    {
      Sid      = "LogOnly", Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"],
      Resource = "${aws_cloudwatch_log_group.clinic_copy[each.key].arn}:*"
    }
  ] })
}
resource "aws_lambda_function" "clinic_copy" {
  for_each                       = local.clinic_copy
  function_name                  = "${local.name}-clinic-copy"
  filename                       = var.lambda_zip
  source_code_hash               = filebase64sha256(var.lambda_zip)
  role                           = aws_iam_role.clinic_copy[each.key].arn
  runtime                        = "python3.12"
  handler                        = "hp_control.copy_clinic_sites"
  timeout                        = 180
  memory_size                    = 512
  reserved_concurrent_executions = 1
  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.clinic_copy[each.key].name
  }
  environment {
    variables = {
      HP_TABLE_NAME      = aws_dynamodb_table.authority.name
      HP_ARTIFACT_BUCKET = aws_s3_bucket.artifacts.id
    }
  }
  depends_on = [aws_cloudwatch_log_group.clinic_copy, aws_iam_role_policy.clinic_copy]
  tags       = local.tags
}
resource "aws_cloudwatch_event_rule" "clinic_copy" {
  for_each            = local.clinic_copy
  name                = "${local.name}-clinic-copy"
  schedule_expression = "rate(1 minute)"
  tags                = local.tags
}
resource "aws_cloudwatch_event_target" "clinic_copy" {
  for_each = local.clinic_copy
  rule     = aws_cloudwatch_event_rule.clinic_copy[each.key].name
  arn      = aws_lambda_function.clinic_copy[each.key].arn
  retry_policy {
    maximum_event_age_in_seconds = 60
    maximum_retry_attempts       = 0
  }
}
resource "aws_lambda_permission" "clinic_copy" {
  for_each      = local.clinic_copy
  statement_id  = "ClinicCopyScheduleOnly"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.clinic_copy[each.key].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.clinic_copy[each.key].arn
}
