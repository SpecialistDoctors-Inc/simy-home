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
    # Older edge routing sends these new language directory URLs to .html.
    # Serve identical content there until the updated canonical routing is live.
    case "$key" in
      for/es/engineers/|for/fr/engineers/|for/hi/engineers/|for/zh-hans/engineers/|for/es/financial-planners/|for/fr/financial-planners/|for/hi/financial-planners/|for/zh-hans/financial-planners/)
        aws s3api put-object \
          --bucket "$bucket" \
          --key "${key%/}.html" \
          --body "$html" \
          --content-type "text/html; charset=utf-8" \
          --cache-control "public, max-age=300" \
          --query ETag --output text
        ;;
    esac
  done
