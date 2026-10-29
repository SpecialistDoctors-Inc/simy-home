#!/usr/bin/env bash
set -euo pipefail

CLINIC_DIRECTORY=$1
CLINIC_ENVIRONMENT=$2
case "$CLINIC_ENVIRONMENT" in
  dev) CLINIC_BRANCH=dev; CLINIC_URL=https://sample-clinic-dev.simy.one ;;
  prod) CLINIC_BRANCH=main; CLINIC_URL=https://sample-clinic.simy.one ;;
  *) exit 2 ;;
esac
test -n "$SITE_CF_DISTRIBUTION_ID"
test "$SITE_S3_BUCKET" = "simy-sample-clinic-$CLINIC_ENVIRONMENT-209300895845"
test "$(aws sts get-caller-identity --query Account --output text)" = '209300895845'
test "$(git ls-remote origin "refs/heads/$CLINIC_BRANCH" | cut -f1)" = "$GITHUB_SHA"
export CLINIC_DIRECTORY CLINIC_ENVIRONMENT
# JavaScript template strings below must stay literal to the shell.
# shellcheck disable=SC2016
node --input-type=module -e '
  import fs from "node:fs/promises";
  import { artifactHash } from "./examples/sample-clinic/build.mjs";
  const v=JSON.parse(await fs.readFile(`${process.env.CLINIC_DIRECTORY}/version.json`,"utf8"));
  if(v.siteId!=="sample-clinic" || v.environment!==process.env.CLINIC_ENVIRONMENT || v.artifactHash!==await artifactHash(process.env.CLINIC_DIRECTORY)) throw new Error("Artifact validation failed");
  if((v.environment==="dev"?v.sourceRevision:v.releaseRevision)!==process.env.GITHUB_SHA) throw new Error("Release revision differs");
'

# Each origin is exclusive to this sample site. Upload its version marker last.
aws s3 sync "$CLINIC_DIRECTORY/" "s3://$SITE_S3_BUCKET/" --delete --exclude version.json --only-show-errors --cache-control 'public, max-age=300'
aws s3 cp "$CLINIC_DIRECTORY/version.json" "s3://$SITE_S3_BUCKET/version.json" --only-show-errors --cache-control 'no-store'
INVALIDATION_ID=$(aws cloudfront create-invalidation --distribution-id "$SITE_CF_DISTRIBUTION_ID" --paths '/*' --query 'Invalidation.Id' --output text)
aws cloudfront wait invalidation-completed --distribution-id "$SITE_CF_DISTRIBUTION_ID" --id "$INVALIDATION_ID"
curl --fail --silent --show-error --retry 3 --max-time 30 "$CLINIC_URL/version.json" -o "$RUNNER_TEMP/clinic-live-version.json"
export CLINIC_LIVE_VERSION="$RUNNER_TEMP/clinic-live-version.json"
# shellcheck disable=SC2016
node --input-type=module -e '
  import fs from "node:fs/promises";
  const expected=JSON.parse(await fs.readFile(`${process.env.CLINIC_DIRECTORY}/version.json`,"utf8"));
  const actual=JSON.parse(await fs.readFile(process.env.CLINIC_LIVE_VERSION,"utf8"));
  for(const key of Object.keys(expected)) if(actual[key]!==expected[key]) throw new Error(`Live ${key} differs`);
'
printf 'Verified %s at %s\n\nCloudFront invalidation: %s\n' "$CLINIC_ENVIRONMENT" "$CLINIC_URL" "$INVALIDATION_ID" >> "$GITHUB_STEP_SUMMARY"
cat "$CLINIC_DIRECTORY/version.json" >> "$GITHUB_STEP_SUMMARY"
