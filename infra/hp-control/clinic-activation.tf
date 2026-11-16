locals {
  clinic_activation = var.clinic_activation_enabled ? toset(["activation"]) : toset([])
  clinic_buckets    = "arn:aws:s3:::hp-clinic-*-209300895845-*"
}
resource "aws_iam_policy" "clinic_publisher_boundary" {
  for_each = local.clinic_activation
  name     = "${local.name}-clinic-publisher-boundary"
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["s3:ListBucket"], Resource = local.clinic_buckets },
    { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], Resource = "${local.clinic_buckets}/*" },
    { Effect = "Allow", Action = ["cloudfront:GetDistribution", "cloudfront:GetDistributionConfig", "cloudfront:UpdateDistribution", "cloudfront:CreateInvalidation", "cloudfront:ListInvalidations", "cloudfront:GetInvalidation"], Resource = "arn:aws:cloudfront::209300895845:distribution/*" },
    { Effect = "Allow", Action = ["route53:ListResourceRecordSets"], Resource = "arn:aws:route53:::hostedzone/*" },
    { Effect = "Allow", Action = ["route53:ChangeResourceRecordSets"], Resource = "arn:aws:route53:::hostedzone/*",
    Condition = { "ForAllValues:StringEquals" = { "route53:ChangeResourceRecordSetsRecordTypes" = ["A", "AAAA", "CNAME"], "route53:ChangeResourceRecordSetsActions" = ["DELETE", "CREATE"] } } }
  ] })
  tags = local.tags
}
resource "aws_iam_role" "clinic_stack" {
  for_each = local.clinic_activation
  name     = "${local.name}-clinic-stack"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow",
  Principal = { Service = "cloudformation.amazonaws.com" }, Action = "sts:AssumeRole" }] })
  tags = local.tags
}
resource "aws_iam_role_policy" "clinic_stack" {
  for_each = aws_iam_role.clinic_stack
  name     = "isolated-clinic-stack"
  role     = each.value.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Sid = "NewClinicBuckets", Effect = "Allow", Action = ["s3:CreateBucket", "s3:DeleteBucket", "s3:GetBucketLocation", "s3:ListBucket", "s3:PutBucketPolicy", "s3:GetBucketPolicy", "s3:DeleteBucketPolicy", "s3:PutBucketPublicAccessBlock", "s3:GetBucketPublicAccessBlock", "s3:PutEncryptionConfiguration", "s3:GetEncryptionConfiguration", "s3:PutBucketVersioning", "s3:GetBucketVersioning", "s3:PutBucketOwnershipControls", "s3:GetBucketOwnershipControls", "s3:PutBucketTagging", "s3:GetBucketTagging"], Resource = local.clinic_buckets },
    { Sid = "NewCloudFrontResources", Effect = "Allow", Action = ["cloudfront:CreateDistribution"], Resource = "*",
    Condition = { StringEquals = { "aws:RequestTag/hp-control-managed" = "true" } } },
    { Sid = "ManagedDistributions", Effect = "Allow", Action = ["cloudfront:GetDistribution", "cloudfront:GetDistributionConfig", "cloudfront:UpdateDistribution", "cloudfront:DeleteDistribution", "cloudfront:TagResource", "cloudfront:UntagResource", "cloudfront:ListTagsForResource"], Resource = "arn:aws:cloudfront::209300895845:distribution/*",
    Condition = { StringEquals = { "aws:ResourceTag/hp-control-managed" = "true" } } },
    { Sid = "NewOriginAndFunction", Effect = "Allow", Action = ["cloudfront:CreateOriginAccessControl", "cloudfront:CreateFunction"], Resource = "*" },
    { Sid = "OriginAccessControls", Effect = "Allow", Action = ["cloudfront:GetOriginAccessControl", "cloudfront:GetOriginAccessControlConfig", "cloudfront:UpdateOriginAccessControl", "cloudfront:DeleteOriginAccessControl"], Resource = "arn:aws:cloudfront::209300895845:origin-access-control/*" },
    { Sid = "ClinicDirectoryFunctions", Effect = "Allow", Action = ["cloudfront:DescribeFunction", "cloudfront:GetFunction", "cloudfront:UpdateFunction", "cloudfront:PublishFunction", "cloudfront:DeleteFunction"], Resource = "arn:aws:cloudfront::209300895845:function/hp-clinic-*-index" },
    { Sid = "NewCertificates", Effect = "Allow", Action = ["acm:RequestCertificate"], Resource = "*",
    Condition = { StringEquals = { "aws:RequestTag/hp-control-managed" = "true" } } },
    { Sid = "ManagedCertificates", Effect = "Allow", Action = ["acm:DescribeCertificate", "acm:DeleteCertificate", "acm:AddTagsToCertificate", "acm:RemoveTagsFromCertificate", "acm:ListTagsForCertificate"], Resource = "arn:aws:acm:us-east-1:209300895845:certificate/*",
    Condition = { StringEquals = { "aws:ResourceTag/hp-control-managed" = "true" } } },
    { Sid = "CertificateDnsOnly", Effect = "Allow", Action = ["route53:ChangeResourceRecordSets"], Resource = "arn:aws:route53:::hostedzone/*",
    Condition = { "ForAllValues:StringEquals" = { "route53:ChangeResourceRecordSetsRecordTypes" = ["CNAME"] } } },
    { Effect = "Allow", Action = ["route53:GetHostedZone", "route53:ListResourceRecordSets"], Resource = "arn:aws:route53:::hostedzone/*" },
    { Effect = "Allow", Action = ["route53:GetChange"], Resource = "arn:aws:route53:::change/*" },
    { Sid = "BoundPublisherRoles", Effect = "Allow", Action = ["iam:CreateRole"], Resource = "arn:aws:iam::209300895845:role/hp-clinic-*-publisher-*",
    Condition = { StringEquals = { "iam:PermissionsBoundary" = aws_iam_policy.clinic_publisher_boundary[each.key].arn } } },
    { Effect = "Allow", Action = ["iam:GetRole", "iam:GetRolePolicy", "iam:PutRolePolicy", "iam:DeleteRolePolicy", "iam:DeleteRole", "iam:TagRole", "iam:UntagRole", "iam:ListRolePolicies"], Resource = "arn:aws:iam::209300895845:role/hp-clinic-*-publisher-*" }
  ] })
}
resource "aws_iam_role" "clinic_activation" {
  for_each = local.clinic_activation
  name     = "${local.name}-clinic-activation"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow",
  Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }] })
  tags = local.tags
}
resource "aws_cloudwatch_log_group" "clinic_activation" {
  for_each          = local.clinic_activation
  name              = "${local.log_prefix}/clinic-activation"
  retention_in_days = 30
  tags              = local.tags
}
resource "aws_iam_role_policy" "clinic_activation" {
  for_each = aws_iam_role.clinic_activation
  name     = "clinic-activation-only"
  role     = each.value.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:ConditionCheckItem"], Resource = aws_dynamodb_table.authority.arn },
    { Effect = "Allow", Action = ["dynamodb:Query"], Resource = "${aws_dynamodb_table.authority.arn}/index/queue-state",
    Condition = { "ForAllValues:StringEquals" = { "dynamodb:LeadingKeys" = ["clinic_activation"] } } },
    { Effect = "Allow", Action = ["s3:GetObject"], Resource = "${aws_s3_bucket.artifacts.arn}/intake/*" },
    { Effect = "Allow", Action = ["s3:ListBucket"], Resource = local.clinic_buckets },
    { Effect = "Allow", Action = ["s3:PutObject", "s3:GetObject"], Resource = "${local.clinic_buckets}/index.html" },
    { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = compact([var.clinic_activation_secret_arn, var.clinic_bootstrap_token_secret_arn, var.github_secret_arn]) },
    { Effect = "Allow", Action = ["cloudformation:CreateStack", "cloudformation:DescribeStacks", "cloudformation:UpdateStack"], Resource = "arn:aws:cloudformation:us-east-1:209300895845:stack/hp-clinic-*/*" },
    { Effect = "Allow", Action = ["iam:PassRole"], Resource = aws_iam_role.clinic_stack[each.key].arn,
    Condition = { StringEquals = { "iam:PassedToService" = "cloudformation.amazonaws.com" } } },
    { Effect = "Allow", Action = ["cloudfront:GetDistribution"], Resource = "arn:aws:cloudfront::209300895845:distribution/*" },
    { Effect = "Allow", Action = ["route53:GetHostedZone", "route53:ListResourceRecordSets"], Resource = "arn:aws:route53:::hostedzone/*" },
    { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.clinic_activation[each.key].arn}:*" }
  ] })
}
resource "aws_lambda_function" "clinic_activation" {
  for_each                       = local.clinic_activation
  function_name                  = "${local.name}-clinic-activation"
  filename                       = var.lambda_zip
  source_code_hash               = filebase64sha256(var.lambda_zip)
  role                           = aws_iam_role.clinic_activation[each.key].arn
  runtime                        = "python3.12"
  handler                        = "hp_control.activate_clinic_sites"
  timeout                        = 180
  memory_size                    = 512
  reserved_concurrent_executions = 1
  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.clinic_activation[each.key].name
  }
  environment {
    variables = {
      HP_TABLE_NAME                   = aws_dynamodb_table.authority.name
      HP_ARTIFACT_BUCKET              = aws_s3_bucket.artifacts.id
      HP_CLINIC_ACTIVATION_SECRET_ARN = var.clinic_activation_secret_arn
    }
  }
  lifecycle {
    precondition {
      condition     = can(regex(":secret:hp-control/", var.clinic_activation_secret_arn)) && can(regex(":secret:hp-control/", var.clinic_bootstrap_token_secret_arn))
      error_message = "Activation requires dedicated hp-control/ configuration and repository-creation credential references."
    }
  }
  depends_on = [aws_cloudwatch_log_group.clinic_activation, aws_iam_role_policy.clinic_activation]
  tags       = local.tags
}
resource "aws_cloudwatch_event_rule" "clinic_activation" {
  for_each            = local.clinic_activation
  name                = "${local.name}-clinic-activation"
  schedule_expression = "rate(1 minute)"
  tags                = local.tags
}
resource "aws_cloudwatch_event_target" "clinic_activation" {
  for_each = local.clinic_activation
  rule     = aws_cloudwatch_event_rule.clinic_activation[each.key].name
  arn      = aws_lambda_function.clinic_activation[each.key].arn
  retry_policy {
    maximum_event_age_in_seconds = 60
    maximum_retry_attempts       = 0
  }
}
resource "aws_lambda_permission" "clinic_activation" {
  for_each      = local.clinic_activation
  statement_id  = "ClinicActivationScheduleOnly"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.clinic_activation[each.key].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.clinic_activation[each.key].arn
}
