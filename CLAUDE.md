# CLAUDE.md

## Repository Overview

Static website for [simy.one](https://simy.one), hosted on AWS CloudFront + S3.

## Repository Structure

```
simy-home/
├── site/                          ← Static site (deployed to S3)
│   ├── index.html
│   ├── error.html
│   └── *.png                      ← Images
├── infra/
│   └── terraform/                 ← CloudFront + S3 infrastructure
│       ├── versions.tf
│       ├── variables.tf
│       ├── main.tf
│       ├── outputs.tf
│       └── environments/
│           ├── prod.tfvars
│           └── dev.tfvars
├── .github/workflows/
│   └── deploy-site.yml            ← Static site deploy (S3 sync + CF invalidation)
└── CLAUDE.md
```

## Infrastructure

- **S3**: Private bucket with versioning, accessed via CloudFront OAC
- **CloudFront**: PriceClass_200 (Asia included), HTTP/2+3, redirect to HTTPS
- **ACM**: Certificate for simy.one + www.simy.one (us-east-1)
- **Route53**: A/AAAA records pointing to CloudFront
- **GitHub Actions**: OIDC-authenticated deploy (S3 sync + CF invalidation)

## Commands

No build commands. The site is static HTML/CSS/images.

### Terraform

Each environment uses a separate Terraform workspace / state.

```bash
cd infra/terraform

# prod (simy.one)
terraform init
terraform plan -var-file="environments/prod.tfvars"

# dev (dev.simy.one)
terraform init
terraform plan -var-file="environments/dev.tfvars"
```

## Environments

| Env  | Domain        | Branch | S3 bucket         |
| ---- | ------------- | ------ | ----------------- |
| prod | simy.one      | main   | simy-site-prod    |
| dev  | dev.simy.one  | dev    | simy-site-dev     |

## Deployment

- Push to `site/` on `main` → deploys to **prod** (simy.one)
- Push to `site/` on `dev` → deploys to **dev** (dev.simy.one)
- Manual: `gh workflow run deploy-site.yml -r <branch> -f environment=<prod|dev>`

GitHub Actions uses environment-scoped secrets (`AWS_SITE_DEPLOY_ROLE_ARN`, `AWS_REGION`, `SITE_S3_BUCKET`, `SITE_CF_DISTRIBUTION_ID`) configured per GitHub Environment (`prod`, `dev`).
