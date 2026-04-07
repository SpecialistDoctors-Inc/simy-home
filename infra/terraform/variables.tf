variable "region" {
  description = "AWS region for S3 bucket"
  type        = string
  default     = "ap-northeast-1"
}

variable "domain_name" {
  description = "Primary domain name (e.g. simy.one)"
  type        = string
}

variable "subject_alternative_names" {
  description = "Additional domain names for the certificate (e.g. www.simy.one)"
  type        = list(string)
  default     = []
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID. If empty, DNS records are not created."
  type        = string
  default     = ""
}

variable "github_repository" {
  description = "GitHub repository in OWNER/REPO format for OIDC trust"
  type        = string
  default     = "SpecialistDoctors-Inc/simy-home"
}

variable "github_oidc_provider_arn" {
  description = "Existing GitHub OIDC provider ARN. If empty, auto-constructed from account ID."
  type        = string
  default     = ""
}

variable "environment" {
  description = "Deployment environment (prod, dev)"
  type        = string
  default     = "prod"
}

variable "basic_auth_username" {
  description = "Basic auth username (empty disables basic auth)"
  type        = string
  default     = ""
}

variable "basic_auth_password" {
  description = "Basic auth password (empty disables basic auth)"
  type        = string
  default     = ""
  sensitive   = true
}
