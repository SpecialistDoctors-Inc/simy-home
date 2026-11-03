variable "region" {
  type    = string
  default = "ap-northeast-1"
}

variable "expected_aws_account_id" {
  type    = string
  default = "209300895845"
}

variable "vpc_id" {
  description = "Dedicated agent VPC boundary. The default VPC is used only until a private network is provisioned."
  type        = string
}

variable "subnet_id" {
  description = "One subnet with public IPv4 egress. No inbound security-group rule is created."
  type        = string
}

variable "ubuntu_ami_id" {
  description = "Pinned Canonical Ubuntu 24.04 arm64 AMI ID, verified before apply."
  type        = string

  validation {
    condition     = var.ubuntu_ami_id == "ami-07d7d1bf631243bb0"
    error_message = "Use the verified Canonical Ubuntu 24.04 arm64 AMI ami-07d7d1bf631243bb0."
  }
}

variable "instance_type" {
  type    = string
  default = "t4g.medium"
}

variable "artifact_bucket_name" {
  description = "Globally unique name for the agent's encrypted one-day staging bucket."
  type        = string
}

variable "artifact_prefix" {
  description = "Only object prefix the instance may read after an operator uploads a sealed migration bundle."
  type        = string
  default     = "sealed/"
}

variable "root_volume_size_gib" {
  type    = number
  default = 16
}

variable "data_volume_size_gib" {
  type    = number
  default = 20
}

variable "snapshot_retention_days" {
  type    = number
  default = 7
}

variable "backup_time_utc" {
  description = "UTC time for the daily DLM state-volume snapshot, in 24-hour HH:MM form."
  type        = string
  default     = "03:00"

  validation {
    condition     = can(regex("^([01][0-9]|2[0-3]):[0-5][0-9]$", var.backup_time_utc))
    error_message = "backup_time_utc must use 24-hour UTC HH:MM form."
  }
}

variable "operational_alert_email" {
  description = "Optional dedicated operations mailbox for only this agent's CloudWatch alarm and recovery notifications. Leave blank to create no notification target."
  type        = string
  default     = ""

  validation {
    condition     = var.operational_alert_email == "" || can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.operational_alert_email))
    error_message = "operational_alert_email must be blank or a single email address."
  }
}

variable "tags" {
  type    = map(string)
  default = {}
}
