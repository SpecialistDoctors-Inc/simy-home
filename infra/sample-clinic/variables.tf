variable "region" {
  description = "AWS region for the private S3 origin bucket."
  type        = string
  default     = "ap-northeast-1"
}

variable "environment" {
  description = "Deployment environment. The workflow and GitHub Environment must use the same value."
  type        = string

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment must be dev or prod."
  }
}

variable "domain_name" {
  description = "Fully qualified hostname for this environment."
  type        = string
}

variable "route53_zone_id" {
  description = "Route53 hosted zone that owns domain_name."
  type        = string
}

variable "github_repository" {
  description = "GitHub repository allowed to assume the deployment role."
  type        = string
  default     = "SpecialistDoctors-Inc/simy-home"
}

variable "expected_aws_account_id" {
  description = "Account that is allowed to own this sample site."
  type        = string
  default     = "209300895845"
}

variable "github_oidc_provider_arn" {
  description = "Existing GitHub Actions OIDC provider ARN. Leave blank to derive it in expected_aws_account_id."
  type        = string
  default     = ""
}
