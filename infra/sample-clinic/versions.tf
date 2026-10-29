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

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.expected_aws_account_id]
}

# CloudFront certificates must be issued in us-east-1.
provider "aws" {
  alias               = "us_east_1"
  region              = "us-east-1"
  allowed_account_ids = [var.expected_aws_account_id]
}
