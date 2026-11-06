variable "region" {
  type    = string
  default = "ap-northeast-1"
  validation {
    condition     = var.region == "ap-northeast-1"
    error_message = "HP control is restricted to ap-northeast-1."
  }
}
variable "route53_zone_id" {
  type    = string
  default = "Z0008232OGBGLDBHC41G"
}
variable "lambda_zip" {
  description = "Locally built ZIP containing hp_control.py and pinned dependencies; never a placeholder deployment."
  type        = string
}
variable "google_secret_arn" {
  description = "Existing dedicated Google OAuth client secret reference; no value is stored by Terraform."
  type        = string
  validation {
    condition     = can(regex("^arn:aws:secretsmanager:ap-northeast-1:209300895845:secret:hp-control/", var.google_secret_arn))
    error_message = "Use a dedicated hp-control/ secret in the verified account/region."
  }
}
variable "github_secret_arn" {
  description = "Existing dedicated least-privilege GitHub App credentials reference."
  type        = string
  validation {
    condition     = can(regex("^arn:aws:secretsmanager:ap-northeast-1:209300895845:secret:hp-control/", var.github_secret_arn))
    error_message = "Use a dedicated hp-control/ secret in the verified account/region."
  }
}
variable "validator_image" {
  description = "Reviewed validation image pinned by sha256 digest. No application secrets or task role are injected."
  type        = string
  validation {
    condition     = can(regex("^209300895845[.]dkr[.]ecr[.]ap-northeast-1[.]amazonaws[.]com/simy-hp-control-validator@sha256:[a-f0-9]{64}$", var.validator_image))
    error_message = "Pin the reviewed image digest in the dedicated private HP renderer repository."
  }
}
variable "publication_enabled" {
  type    = bool
  default = false
}
variable "preview_enabled" {
  type    = bool
  default = false
}
variable "preview_gate_reference" {
  description = "Evidence that the legacy dev writer is retired and the target preview configuration is verified."
  type        = string
  default     = ""
}
variable "publication_gate_reference" {
  description = "Reviewed cutover evidence identifier, required before creating publication permissions."
  type        = string
  default     = ""
}
variable "signing_secret_arn" {
  description = "Dedicated RSA PEM OAuth issuer key secret reference; provision key separately."
  type        = string
  validation {
    condition     = can(regex("^arn:aws:secretsmanager:ap-northeast-1:209300895845:secret:hp-control/", var.signing_secret_arn))
    error_message = "Use a dedicated hp-control/ signing key secret."
  }
}
variable "google_operator_secret_arn" {
  description = "Separate dedicated Drive/Sheets/Gmail operator OAuth secret reference."
  type        = string
  validation {
    condition     = can(regex("^arn:aws:secretsmanager:ap-northeast-1:209300895845:secret:hp-control/", var.google_operator_secret_arn))
    error_message = "Use a dedicated hp-control/ operator secret."
  }
}

variable "github_webhook_secret_arn" {
  description = "Dedicated GitHub webhook HMAC signing secret reference, separate from GitHub App private credentials."
  type        = string
  validation {
    condition     = can(regex("^arn:aws:secretsmanager:ap-northeast-1:209300895845:secret:hp-control/", var.github_webhook_secret_arn))
    error_message = "Use a dedicated hp-control/ webhook secret in the verified account/region."
  }
}

variable "validation_enabled" {
  description = "Permit exact reviewed renderer launches; disabled until image, isolation and request guards are verified."
  type        = bool
  default     = false
}
variable "validation_gate_reference" {
  description = "Reviewed image/isolation evidence reference required to enable renderer launches."
  type        = string
  default     = ""
}

variable "alarm_topic_arn" {
  description = "Optional existing reviewed SNS topic for HP operational alarms; no topic or subscription is created."
  type        = string
  default     = ""
  validation {
    condition     = var.alarm_topic_arn == "" || can(regex("^arn:aws:sns:ap-northeast-1:209300895845:[A-Za-z0-9_-]+$", var.alarm_topic_arn))
    error_message = "Use a reviewed existing SNS topic in the verified account/region, or leave blank."
  }
}
