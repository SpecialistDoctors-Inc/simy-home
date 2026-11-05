# Renderer remains dormant unless validation_enabled passes a separately reviewed
# image/launcher gate. There is no ECS service or task application IAM role.
resource "aws_ecs_cluster" "validation" {
  name = "${local.name}-validation"
  tags = local.tags
}
resource "aws_iam_role" "validation_execution" {
  name = "${local.name}-validation-execution"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole"
  }] })
}
resource "aws_ecr_repository" "validator" {
  name                 = "simy-hp-control-validator"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false
  encryption_configuration { encryption_type = "AES256" }
  image_scanning_configuration { scan_on_push = true }
  tags       = local.tags
  depends_on = [terraform_data.guard]
}
resource "aws_iam_role_policy" "validation_execution" {
  name = "renderer-image-pull-and-logs"
  role = aws_iam_role.validation_execution.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    {
      Sid      = "RendererLogsOnly", Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"],
      Resource = "${aws_cloudwatch_log_group.runtime["validator"].arn}:*"
    },
    {
      # ECR authorization tokens do not support resource-level IAM scoping.
      Sid = "EcrPullAuthentication", Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*"
    },
    {
      Sid      = "PullOnlyReviewedRendererRepository", Effect = "Allow",
      Action   = ["ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
      Resource = aws_ecr_repository.validator.arn
    }
  ] })
}
resource "aws_ecs_task_definition" "validation" {
  family                   = "${local.name}-validation"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.validation_execution.arn
  # No task_role_arn: container receives no AWS application credentials.
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  ephemeral_storage { size_in_gib = 21 }
  volume { name = "scratch" }
  container_definitions = jsonencode([{
    name                   = "validator", image = var.validator_image, essential = true,
    readonlyRootFilesystem = true, user = "1000:1000", privileged = false,
    mountPoints            = [{ sourceVolume = "scratch", containerPath = "/tmp", readOnly = false }],
    linuxParameters        = { capabilities = { drop = ["ALL"] } },
    environment            = [{ name = "AWS_EC2_METADATA_DISABLED", value = "true" }],
    logConfiguration = { logDriver = "awslogs", options = {
      awslogs-group  = aws_cloudwatch_log_group.runtime["validator"].name,
      awslogs-region = var.region, awslogs-stream-prefix = "validation"
    } }
  }])
  tags = local.tags
}
# Isolated from the existing agent/default VPC and application private networks.
# Only public IPv4 HTTPS egress is allowed, with no VPC peering or NAT.
resource "aws_vpc" "validation" {
  cidr_block           = "10.233.0.0/24"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = local.tags
}
resource "aws_subnet" "validation" {
  vpc_id     = aws_vpc.validation.id
  cidr_block = "10.233.0.0/25"
  tags       = local.tags
}
resource "aws_internet_gateway" "validation" {
  vpc_id = aws_vpc.validation.id
  tags   = local.tags
}
resource "aws_route_table" "validation" {
  vpc_id = aws_vpc.validation.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.validation.id
  }
}
resource "aws_route_table_association" "validation" {
  subnet_id      = aws_subnet.validation.id
  route_table_id = aws_route_table.validation.id
}
resource "aws_security_group" "validation" {
  name        = "${local.name}-validation"
  description = "No ingress; public HTTPS only. No application/private-network or metadata egress."
  vpc_id      = aws_vpc.validation.id
  tags        = local.tags
}

resource "aws_vpc_security_group_egress_rule" "public_https" {
  for_each          = toset(["1.0.0.0/8", "2.0.0.0/7", "4.0.0.0/6", "8.0.0.0/7", "11.0.0.0/8", "12.0.0.0/6", "16.0.0.0/4", "32.0.0.0/3", "64.0.0.0/3", "96.0.0.0/6", "100.0.0.0/10", "100.128.0.0/9", "101.0.0.0/8", "102.0.0.0/7", "104.0.0.0/5", "112.0.0.0/5", "120.0.0.0/6", "124.0.0.0/7", "126.0.0.0/8", "128.0.0.0/3", "160.0.0.0/5", "168.0.0.0/8", "169.0.0.0/9", "169.128.0.0/10", "169.192.0.0/11", "169.224.0.0/12", "169.240.0.0/13", "169.248.0.0/14", "169.252.0.0/15", "169.255.0.0/16", "170.0.0.0/7", "172.0.0.0/12", "172.32.0.0/11", "172.64.0.0/10", "172.128.0.0/9", "173.0.0.0/8", "174.0.0.0/7", "176.0.0.0/4", "192.0.0.0/9", "192.128.0.0/11", "192.160.0.0/13", "192.169.0.0/16", "192.170.0.0/15", "192.172.0.0/14", "192.176.0.0/12", "192.192.0.0/10", "193.0.0.0/8", "194.0.0.0/7", "196.0.0.0/6", "200.0.0.0/5", "208.0.0.0/4"])
  security_group_id = aws_security_group.validation.id
  cidr_ipv4         = each.value
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

locals {
  validator_config = {
    enabled            = var.validation_enabled
    account_id         = "209300895845"
    region             = var.region
    cluster            = aws_ecs_cluster.validation.arn
    task_definition    = aws_ecs_task_definition.validation.arn
    image_digest       = split("@", var.validator_image)[1]
    container_name     = "validator"
    subnet_ids         = [aws_subnet.validation.id]
    security_group_ids = [aws_security_group.validation.id]
    artifact_bucket    = aws_s3_bucket.artifacts.id
    output_bucket      = aws_s3_bucket.artifacts.id
    deadline_seconds   = 600
  }
}
