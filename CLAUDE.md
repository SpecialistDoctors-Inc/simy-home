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
│           └── prod.tfvars
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

```bash
cd infra/terraform
terraform init
terraform plan -var-file="environments/prod.tfvars"
```

## Deployment

Push changes to `site/` on `main` branch triggers automatic deployment via GitHub Actions.
