# Visible alarms only. No new SNS subscription or external notification target.
resource "aws_cloudwatch_log_metric_filter" "dispatcher_heartbeat" {
  name           = "${local.name}-dispatcher-heartbeat"
  log_group_name = aws_cloudwatch_log_group.runtime["dispatcher"].name
  pattern        = "{ $.event = \"hp_dispatch_completed\" }"
  metric_transformation {
    name      = "DispatchHeartbeat"
    namespace = local.metric_namespace
    value     = "1"
    unit      = "Count"
  }
}
resource "aws_cloudwatch_metric_alarm" "dispatcher_heartbeat" {
  alarm_name          = "${local.name}-dispatcher-heartbeat-missing"
  alarm_description   = "No successful HP outbox dispatcher pass for ten minutes; inspect dispatcher logs and pending authority records."
  namespace           = local.metric_namespace
  metric_name         = "DispatchHeartbeat"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 2
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  alarm_actions       = local.operational_alarm_actions
  ok_actions          = local.operational_alarm_actions
  tags                = local.tags
}
resource "aws_cloudwatch_metric_alarm" "command_dead_letters" {
  alarm_name          = "${local.name}-command-dead-letters"
  alarm_description   = "HP command delivery exhausted retries; DLQ arrival is not parent operation completion."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  dimensions          = { QueueName = aws_sqs_queue.dead_letters.name }
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.operational_alarm_actions
  ok_actions          = local.operational_alarm_actions
  tags                = local.tags
}

locals {
  metric_namespace          = local.acceptance ? "SIMY/HPControlAcceptance" : "SIMY/HPControl"
  operational_alarm_actions = var.alarm_topic_arn == "" ? [] : [var.alarm_topic_arn]
}
resource "aws_cloudwatch_log_metric_filter" "attention_required" {
  name           = "${local.name}-attention-required"
  log_group_name = aws_cloudwatch_log_group.runtime["dispatcher"].name
  pattern        = "{ ($.event = \"hp_dispatch_completed\") && ($.has_attention IS TRUE) }"
  metric_transformation {
    name          = "AttentionRequired"
    namespace     = local.metric_namespace
    value         = "1"
    default_value = 0
    unit          = "Count"
  }
}
resource "aws_cloudwatch_metric_alarm" "attention_required" {
  alarm_name          = "${local.name}-operation-needs-attention"
  alarm_description   = "At least one unresolved operation or notification requires attention; ordinary CI/render waits do not trigger this alarm."
  namespace           = local.metric_namespace
  metric_name         = "AttentionRequired"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.operational_alarm_actions
  ok_actions          = local.operational_alarm_actions
  tags                = local.tags
}
