data "aws_caller_identity" "current" {}

data "aws_vpc" "selected" {
  id = var.vpc_id
}

data "aws_subnet" "selected" {
  id = var.subnet_id
}

locals {
  name               = "simy-hp-agent"
  aws_cli_version    = "2.39.3"
  aws_cli_zip_sha256 = "f6eb845fbacb11bee87de3f5fbe8043773cbe89d0414607b44b71e216eb9226b"
  tags = merge({
    Name      = local.name
    Project   = "hp-agent"
    ManagedBy = "terraform"
  }, var.tags)
  operational_alarm_actions = var.operational_alert_email == "" ? [] : [aws_sns_topic.operational[0].arn]
}

resource "terraform_data" "guard" {
  lifecycle {
    precondition {
      condition     = data.aws_caller_identity.current.account_id == var.expected_aws_account_id
      error_message = "Refusing to create the HP agent outside account ${var.expected_aws_account_id}."
    }
    precondition {
      condition     = data.aws_subnet.selected.vpc_id == var.vpc_id
      error_message = "subnet_id must belong to vpc_id."
    }
    precondition {
      condition     = var.region == "ap-northeast-1"
      error_message = "This dedicated HP agent is intentionally pinned to ap-northeast-1."
    }
    precondition {
      condition     = data.aws_vpc.selected.cidr_block == "172.31.0.0/16"
      error_message = "This runtime is approved only for the selected default VPC CIDR 172.31.0.0/16."
    }
    precondition {
      condition     = startswith(var.artifact_prefix, "sealed/") && endswith(var.artifact_prefix, "/")
      error_message = "artifact_prefix must be a sealed/ prefix ending in '/'."
    }
  }
}

resource "aws_s3_bucket" "artifact" {
  bucket     = var.artifact_bucket_name
  depends_on = [terraform_data.guard]
  tags       = local.tags
}

resource "aws_s3_bucket_public_access_block" "artifact" {
  bucket                  = aws_s3_bucket.artifact.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifact" {
  bucket = aws_s3_bucket.artifact.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_versioning" "artifact" {
  bucket = aws_s3_bucket.artifact.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_lifecycle_configuration" "artifact" {
  bucket = aws_s3_bucket.artifact.id
  rule {
    id     = "remove-migration-staging-within-one-day"
    status = "Enabled"
    filter { prefix = "" }
    expiration { days = 1 }
    noncurrent_version_expiration { noncurrent_days = 1 }
    abort_incomplete_multipart_upload { days_after_initiation = 1 }
  }
}

data "aws_iam_policy_document" "artifact_bucket" {
  statement {
    sid    = "DenyUnencryptedTransport"
    effect = "Deny"
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.artifact.arn, "${aws_s3_bucket.artifact.arn}/*"]
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "artifact" {
  bucket = aws_s3_bucket.artifact.id
  policy = data.aws_iam_policy_document.artifact_bucket.json
}

resource "aws_ecr_repository" "agent" {
  name                 = local.name
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
  tags = local.tags
}

resource "aws_ecr_lifecycle_policy" "agent" {
  repository = aws_ecr_repository.agent.name
  policy = jsonencode({ rules = [{
    rulePriority = 1
    description  = "Retain the most recent ten immutable deployment images."
    selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 10 }
    action       = { type = "expire" }
  }] })
}

resource "aws_cloudwatch_log_group" "agent" {
  name              = "/simy/hp-agent"
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_sns_topic" "operational" {
  count = var.operational_alert_email == "" ? 0 : 1
  name  = "${local.name}-operational-alerts"
  tags  = local.tags
}

data "aws_iam_policy_document" "operational_sns" {
  count = var.operational_alert_email == "" ? 0 : 1
  statement {
    sid    = "CloudWatchMayPublishOnlyForTheseAgentAlarms"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com"]
    }
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.operational[0].arn]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
    condition {
      test     = "ArnEquals"
      variable = "AWS:SourceArn"
      values = [
        "arn:aws:cloudwatch:${var.region}:${data.aws_caller_identity.current.account_id}:alarm:${local.name}-system-status-recovery",
        "arn:aws:cloudwatch:${var.region}:${data.aws_caller_identity.current.account_id}:alarm:${local.name}-heartbeat-missing",
      ]
    }
  }
}

resource "aws_sns_topic_policy" "operational" {
  count  = var.operational_alert_email == "" ? 0 : 1
  arn    = aws_sns_topic.operational[0].arn
  policy = data.aws_iam_policy_document.operational_sns[0].json
}

resource "aws_sns_topic_subscription" "operational_email" {
  count     = var.operational_alert_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.operational[0].arn
  protocol  = "email"
  endpoint  = var.operational_alert_email
}

resource "aws_security_group" "agent" {
  name_prefix = "${local.name}-"
  description = "No inbound access. Agent egress for provider APIs, GitHub, ECR and DNS only."
  vpc_id      = var.vpc_id
  tags        = local.tags

  egress {
    description = "HTTPS to Google, GitHub, OpenAI, AWS and package registries"
    protocol    = "tcp"
    from_port   = 443
    to_port     = 443
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    description = "DNS UDP resolver queries"
    protocol    = "udp"
    from_port   = 53
    to_port     = 53
    cidr_blocks = ["${cidrhost(data.aws_vpc.selected.cidr_block, 2)}/32"]
  }
  egress {
    description = "DNS TCP resolver fallback"
    protocol    = "tcp"
    from_port   = 53
    to_port     = 53
    cidr_blocks = ["${cidrhost(data.aws_vpc.selected.cidr_block, 2)}/32"]
  }
}

data "aws_iam_policy_document" "instance_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "instance" {
  name               = "${local.name}-instance"
  assume_role_policy = data.aws_iam_policy_document.instance_assume.json
  tags               = local.tags
}

data "aws_iam_policy_document" "instance" {
  # Session Manager requires only these control/data channels. No Parameter
  # Store, inventory, patching, or Run Command document permissions are given.
  statement {
    sid    = "SessionManagerMessagingOnly"
    effect = "Allow"
    actions = [
      "ec2messages:AcknowledgeMessage",
      "ec2messages:DeleteMessage",
      "ec2messages:FailMessage",
      "ec2messages:GetEndpoint",
      "ec2messages:GetMessages",
      "ec2messages:SendReply",
      "ssm:UpdateInstanceInformation",
      "ssmmessages:CreateControlChannel",
      "ssmmessages:CreateDataChannel",
      "ssmmessages:OpenControlChannel",
      "ssmmessages:OpenDataChannel",
    ]
    # SSM messaging actions do not support resource-level scoping.
    resources = ["*"]
  }
  statement {
    sid       = "ReadOnlySealedMigrationBundle"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.artifact.arn}/${var.artifact_prefix}*"]
  }
  statement {
    sid       = "ListOnlySealedMigrationPrefix"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.artifact.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["${var.artifact_prefix}*"]
    }
  }
  statement {
    sid       = "PullOnlyThisAgentImage"
    effect    = "Allow"
    actions   = ["ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
    resources = [aws_ecr_repository.agent.arn]
  }
  statement {
    sid       = "EcrAuthenticationToken"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }
  statement {
    sid       = "WriteOnlyThisLogGroup"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:DescribeLogStreams", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.agent.arn}:*"]
  }
  statement {
    sid       = "AgentHealthMetricOnly"
    effect    = "Allow"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["SIMY/HPAgent"]
    }
  }
}

resource "aws_iam_role_policy" "instance" {
  name   = "${local.name}-runtime"
  role   = aws_iam_role.instance.id
  policy = data.aws_iam_policy_document.instance.json
}

resource "aws_iam_instance_profile" "agent" {
  name = local.name
  role = aws_iam_role.instance.name
}

resource "aws_ebs_volume" "data" {
  availability_zone = data.aws_subnet.selected.availability_zone
  size              = var.data_volume_size_gib
  type              = "gp3"
  encrypted         = true
  tags              = merge(local.tags, { Backup = "daily-7d", Purpose = "hp-agent-state" })
  lifecycle { prevent_destroy = true }
}

resource "aws_instance" "agent" {
  ami                         = var.ubuntu_ami_id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [aws_security_group.agent.id]
  iam_instance_profile        = aws_iam_instance_profile.agent.name
  associate_public_ip_address = true
  monitoring                  = true
  ebs_optimized               = true
  # Bootstrap is immutable after first launch; replacement needs a separately
  # reviewed migration rather than an incidental user-data change.
  user_data_replace_on_change = false
  credit_specification {
    cpu_credits = "standard"
  }
  user_data = <<-USERDATA
    #!/bin/bash
    set -euo pipefail
    export DEBIAN_FRONTEND=noninteractive
    # The pinned arm64 Noble image uses Ubuntu's ports archive. Replace fresh
    # image defaults explicitly, rather than blindly rewriting mirror names.
    rm -f /etc/apt/sources.list
    rm -f /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources
    cat >/etc/apt/sources.list.d/ubuntu.sources <<'SOURCES'
    Types: deb
    URIs: https://ports.ubuntu.com/ubuntu-ports
    Suites: noble noble-updates noble-backports
    Components: main restricted universe multiverse
    Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

    Types: deb
    URIs: https://ports.ubuntu.com/ubuntu-ports
    Suites: noble-security
    Components: main restricted universe multiverse
    Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
    SOURCES
    apt-get update
    apt-get install -y --no-install-recommends docker.io ca-certificates gnupg curl jq apparmor unzip
    aws_cli_zip="/var/tmp/awscli-${local.aws_cli_version}-aarch64.zip"
    curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
      "https://awscli.amazonaws.com/awscli-exe-linux-aarch64-${local.aws_cli_version}.zip" \
      --output "$aws_cli_zip"
    printf '%s  %s\n' '${local.aws_cli_zip_sha256}' "$aws_cli_zip" | sha256sum --check --status
    install_dir="$(mktemp -d)"
    unzip -q "$aws_cli_zip" -d "$install_dir"
    "$install_dir/aws/install" --install-dir /usr/local/aws-cli --bin-dir /usr/local/bin
    rm -rf "$install_dir" "$aws_cli_zip"
    systemctl enable --now docker
    # The state bundle and service unit are intentionally installed later by a
    # separate verified encrypted migration step after the data disk is
    # attached. The operator verifies the encrypted archive and pinned SHA-256
    # through SSM before any service is started.
  USERDATA

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "disabled"
  }

  root_block_device {
    encrypted             = true
    volume_type           = "gp3"
    volume_size           = var.root_volume_size_gib
    delete_on_termination = true
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      ami,
      user_data,
      user_data_replace_on_change,
      # Normal stop releases ephemeral IPv4; that must not replace this protected host.
      associate_public_ip_address,
    ]
    precondition {
      condition     = startswith(var.instance_type, "t4g.")
      error_message = "The pinned Ubuntu AMI and the Codex image are arm64; use a t4g instance type."
    }
  }
  tags       = local.tags
  depends_on = [terraform_data.guard]
}

resource "aws_volume_attachment" "data" {
  # Prevent an unattended Terraform change from detaching the live SQLite/auth
  # disk. Planned maintenance must explicitly remove this safeguard first.
  device_name  = "/dev/sdf"
  volume_id    = aws_ebs_volume.data.id
  instance_id  = aws_instance.agent.id
  force_detach = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_cloudwatch_metric_alarm" "system_recovery" {
  actions_enabled     = !var.retired
  alarm_name          = "${local.name}-system-status-recovery"
  alarm_description   = "Recover the dedicated agent instance on AWS system status failure."
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed_System"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  dimensions          = { InstanceId = aws_instance.agent.id }
  alarm_actions       = concat(["arn:aws:automate:${var.region}:ec2:recover"], local.operational_alarm_actions)
  ok_actions          = local.operational_alarm_actions
  tags                = local.tags
}

data "aws_iam_policy_document" "dlm_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["dlm.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "dlm" {
  name               = "${local.name}-dlm"
  assume_role_policy = data.aws_iam_policy_document.dlm_assume.json
  tags               = local.tags
}

data "aws_iam_policy_document" "dlm" {
  statement {
    sid       = "DescribeForLifecycleSelection"
    effect    = "Allow"
    actions   = ["ec2:DescribeSnapshots", "ec2:DescribeVolumes", "ec2:DescribeTags"]
    resources = ["*"]
  }
  statement {
    sid     = "CreateSnapshotOnlyForAgentDataVolume"
    effect  = "Allow"
    actions = ["ec2:CreateSnapshot"]
    resources = [
      "arn:aws:ec2:${var.region}:${var.expected_aws_account_id}:volume/${aws_ebs_volume.data.id}",
      # EC2 snapshot ARNs have an empty account field; volume ARNs do not.
      "arn:aws:ec2:${var.region}::snapshot/*"
    ]
  }
  statement {
    sid       = "DeleteOnlyTaggedAgentDataSnapshots"
    effect    = "Allow"
    actions   = ["ec2:DeleteSnapshot"]
    resources = ["arn:aws:ec2:${var.region}::snapshot/*"]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Project"
      values   = ["hp-agent"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Purpose"
      values   = ["hp-agent-state"]
    }
  }
  statement {
    sid       = "TagOnlyDuringSnapshotCreation"
    effect    = "Allow"
    actions   = ["ec2:CreateTags"]
    resources = ["arn:aws:ec2:${var.region}::snapshot/*"]
    condition {
      test     = "StringEquals"
      variable = "ec2:CreateAction"
      values   = ["CreateSnapshot"]
    }
  }
}

resource "aws_iam_role_policy" "dlm" {
  name   = "${local.name}-snapshot"
  role   = aws_iam_role.dlm.id
  policy = data.aws_iam_policy_document.dlm.json
}

resource "aws_dlm_lifecycle_policy" "data" {
  description        = "Daily seven day snapshots for the persistent HP agent SQLite volume"
  execution_role_arn = aws_iam_role.dlm.arn
  state              = "ENABLED"
  policy_details {
    resource_types = ["VOLUME"]
    target_tags    = { Name = local.name, Purpose = "hp-agent-state" }
    schedule {
      name      = "daily-seven-day"
      copy_tags = true
      create_rule {
        interval      = 24
        interval_unit = "HOURS"
        times         = [var.backup_time_utc]
      }
      retain_rule { count = var.snapshot_retention_days }
      tags_to_add = merge(local.tags, { Source = "hp-agent-data-volume" })
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "agent_heartbeat_missing" {
  actions_enabled     = !var.retired
  alarm_name          = "${local.name}-heartbeat-missing"
  alarm_description   = "HP update service requires attention: missing heartbeat, unresolved request incident, or overdue work."
  namespace           = "SIMY/HPAgent"
  metric_name         = "Healthy"
  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 2
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  dimensions          = { InstanceId = aws_instance.agent.id }
  alarm_actions       = local.operational_alarm_actions
  ok_actions          = local.operational_alarm_actions
  tags                = local.tags
}

# Resource-level retirement: preserve the host and disks, with no process signals.
# Disable the dedicated alarms before requesting the normal EC2 stop.
resource "aws_ec2_instance_state" "retired" {
  count       = var.retired ? 1 : 0
  instance_id = aws_instance.agent.id
  state       = "stopped"
  force       = false

  lifecycle {
    precondition {
      condition     = aws_instance.agent.id == "i-0249d60873ec01d17" && data.aws_caller_identity.current.account_id == "209300895845"
      error_message = "Retirement is approved only for the existing dedicated HP agent i-0249d60873ec01d17."
    }
  }
  depends_on = [aws_cloudwatch_metric_alarm.system_recovery, aws_cloudwatch_metric_alarm.agent_heartbeat_missing]
}
