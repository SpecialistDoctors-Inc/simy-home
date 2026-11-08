resource "aws_iam_role" "runtime" {
  for_each = toset(["api", "consumer", "dispatcher"])
  name     = "${local.name}-${each.key}"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole"
  }] })
  tags = local.tags
}
resource "aws_iam_role_policy" "runtime" {
  for_each = aws_iam_role.runtime
  name     = "bounded-runtime"
  role     = each.value.id
  policy = jsonencode({ Version = "2012-10-17", Statement = concat([
    {
      Sid      = "AuthorityTransactions", Effect = "Allow",
      Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:ConditionCheckItem"],
      Resource = aws_dynamodb_table.authority.arn
    },
    {
      Sid      = "RuntimeLogOnly", Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"],
      Resource = "${aws_cloudwatch_log_group.runtime[each.key].arn}:*"
    },
    {
      Sid      = "CommandQueueOnly", Effect = "Allow",
      Action   = each.key != "consumer" ? ["sqs:SendMessage"] : ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes", "sqs:ChangeMessageVisibility"],
      Resource = aws_sqs_queue.commands.arn
    }
    ], each.key != "dispatcher" ? [
    {
      Sid      = "DedicatedCredentialsOnly", Effect = "Allow", Action = ["secretsmanager:GetSecretValue"],
      Resource = each.key == "api" ? compact([var.google_secret_arn, var.signing_secret_arn, var.github_webhook_secret_arn, var.entitlement_secret_arn, var.preflight_secret_arn]) : compact([var.github_secret_arn, var.google_operator_secret_arn, var.entitlement_secret_arn])
    },
    {
      Sid      = "ArtifactsOnly", Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"],
      Resource = ["${aws_s3_bucket.artifacts.arn}/artifacts/*"]
    }
    ] : [], each.key == "dispatcher" ? [{
      Sid      = "QueryPendingOutboxOnly", Effect = "Allow", Action = ["dynamodb:Query"],
      Resource = ["${aws_dynamodb_table.authority.arn}/index/queue-state", "${aws_dynamodb_table.authority.arn}/index/attention-state"]
      }] : [], each.key == "consumer" && length(local.publisher_sites) > 0 ? [{
      Sid      = "SeparatePublisherOnly", Effect = "Allow", Action = ["sts:AssumeRole"],
      Resource = [for role in aws_iam_role.publisher : role.arn]
  }] : []) })
}
# These are NEW roles. Existing GitHub deploy roles, policies, buckets and
# distributions remain under infra/sample-clinic and are never modified here.
resource "aws_iam_role" "publisher" {
  for_each = local.publisher_sites
  name     = "${local.name}-publisher-${each.key}"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { AWS = aws_iam_role.runtime["consumer"].arn }, Action = "sts:AssumeRole"
  }] })
  max_session_duration = 3600
  tags                 = local.tags
}
resource "aws_iam_role_policy" "publisher" {
  for_each = aws_iam_role.publisher
  name     = "sample-clinic-${each.key}-release-only"
  role     = each.value.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    {
      Sid      = "ListOrigin", Effect = "Allow", Action = ["s3:ListBucket"],
      Resource = "arn:aws:s3:::${local.sites[each.key].bucket}"
    },
    {
      Sid      = "ImmutableReleaseContent", Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"],
      Resource = "arn:aws:s3:::${local.sites[each.key].bucket}/releases/*"
    },
    {
      Sid      = "SwitchOnlyVerifiedDistribution", Effect = "Allow",
      Action   = ["cloudfront:GetDistribution", "cloudfront:GetDistributionConfig", "cloudfront:UpdateDistribution", "cloudfront:CreateInvalidation", "cloudfront:ListInvalidations", "cloudfront:GetInvalidation"],
      Resource = "arn:aws:cloudfront::209300895845:distribution/${local.sites[each.key].distribution}"
    }
  ] })
}
