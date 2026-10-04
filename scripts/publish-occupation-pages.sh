#!/usr/bin/env bash
# S3 REST origins serve literal keys; a trailing slash does not imply index.html.
# Keep both forms so publication works with current and future CloudFront routing.
set -euo pipefail
bucket="${1:?Usage: publish-occupation-pages.sh BUCKET}"
find site/for -type f -name index.html -print0 |
  while IFS= read -r -d '' html; do
    key="${html#site/}"
    key="${key%index.html}"
    aws s3api put-object \
      --bucket "$bucket" \
      --key "$key" \
      --body "$html" \
      --content-type "text/html; charset=utf-8" \
      --cache-control "public, max-age=300" \
      --query ETag --output text
  done
