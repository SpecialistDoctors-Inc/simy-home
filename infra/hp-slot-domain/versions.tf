terraform {
  required_version = ">= 1.10.0"

  # The bucket and lockfile settings come from a private backend config, not
  # embedded in this repository. See backend.hcl.example.
  backend "s3" {}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# CloudFront certificates must be issued in us-east-1. Route53 is global.
provider "aws" {
  region              = "us-east-1"
  allowed_account_ids = [var.expected_aws_account_id]
}
