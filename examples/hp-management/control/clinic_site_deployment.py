#!/usr/bin/env python3
"""Turn infra/clinic-site outputs into the site binding's deployment block.

Read-only. For each environment it reads the CloudFront distribution and the
origin bucket that Terraform created, checks that they are the fresh, private
clinic-site shape HP Control can publish to, and prints:

- ``deployment``: bucket, distribution_id, origin_id, the complete-config hash
  the publisher pins (``expected_config_sha256``) and the files already served
  from the bucket root (``initial_file_paths``),
- ``dev_url`` / ``prod_url`` for the binding, and
- ``claim_target`` for ``clinic_sites`` in the live hp-control tfvars.

Run it only after the prod domain is attached and the initial copy is uploaded:
any later change to either distribution's config invalidates the pinned hash.

    terraform -chdir=infra/clinic-site output -json > outputs.json
    python clinic_site_deployment.py --terraform-output outputs.json
"""
from __future__ import annotations

import argparse
import json
import re
from urllib.parse import urlsplit

from bundles import BundleError, validate_files
from publisher import config_sha256

ACCOUNT = '209300895845'
REGION = 'ap-northeast-1'
ENVIRONMENTS = ('dev', 'prod')


class NotReady(ValueError):
    pass


def outputs_from_terraform(raw):
    """Accept `terraform output -json` (values wrapped in {"value": ...})."""
    values = {name: (item['value'] if isinstance(item, dict) and 'value' in item else item)
              for name, item in raw.items()}
    for name in ('deployment', 'dev_url', 'prod_url', 'prod_domain_attached'):
        if name not in values:
            raise NotReady('terraform output missing: ' + name)
    if values['prod_domain_attached'] is not True:
        raise NotReady('attach the prod domain (prod_domain_attached = true) before pinning the config')
    if set(values['deployment']) != set(ENVIRONMENTS):
        raise NotReady('both dev and prod deployments are required')
    return values


def served_files(s3, bucket):
    paths = []
    for page in s3.get_paginator('list_objects_v2').paginate(Bucket=bucket, ExpectedBucketOwner=ACCOUNT):
        paths += [item['Key'] for item in page.get('Contents', [])]
    if any(path.startswith('releases/') for path in paths):
        # The publisher stages every release under releases/. Initial content
        # there would be outside the inventory it invalidates and verifies.
        raise NotReady('%s already holds releases/ objects; the initial copy must not use that prefix' % bucket)
    try:
        # version.json is the publisher's own marker, not site content.
        validate_files({path: b'' for path in paths if path != 'version.json'})
    except BundleError as error:
        raise NotReady('initial copy in %s is not publishable: %s' % (bucket, error)) from None
    return sorted(paths)


def environment_target(cloudfront, s3, env, output, served_host):
    result = cloudfront.get_distribution(Id=output['distribution_id'])
    distribution = result['Distribution']
    if distribution.get('ARN') != 'arn:aws:cloudfront::%s:distribution/%s' % (ACCOUNT, output['distribution_id']):
        raise NotReady(env + ': distribution is not in the HP Control account')
    config = distribution['DistributionConfig']
    origins = [o for o in config['Origins']['Items'] if o.get('Id') == output['origin_id']]
    if len(origins) != 1 or config['Origins']['Quantity'] != 1:
        raise NotReady(env + ': expected exactly the clinic-site origin')
    origin = origins[0]
    if (not re.fullmatch(re.escape(output['bucket']) + r'\.s3(?:[.-][a-z0-9-]+)?\.amazonaws\.com', origin['DomainName'])
            or 'S3OriginConfig' not in origin or not origin.get('OriginAccessControlId')):
        raise NotReady(env + ': origin is not the private clinic-site bucket')
    if origin.get('OriginPath', ''):
        # A release prefix means the publisher already owns this site.
        raise NotReady(env + ': origin path is not the bucket root; this site was already published')
    aliases = config.get('Aliases', {}).get('Items', [])
    if served_host not in aliases + [distribution['DomainName']]:
        raise NotReady(env + ': %s is not served by this distribution' % served_host)
    return {'bucket': output['bucket'], 'distribution_id': output['distribution_id'],
            'origin_id': output['origin_id'], 'expected_config_sha256': config_sha256(config, output['origin_id']),
            'initial_file_paths': served_files(s3, output['bucket'])}


def deployment_block(values, cloudfront, s3):
    urls = {'dev': values['dev_url'], 'prod': values['prod_url']}
    deployment = {env: environment_target(cloudfront, s3, env, values['deployment'][env], urlsplit(urls[env]).hostname)
                  for env in ENVIRONMENTS}
    return {'dev_url': urls['dev'], 'prod_url': urls['prod'], 'deployment': deployment,
            'claim_target': {env: {'bucket': t['bucket'], 'distribution': t['distribution_id']}
                             for env, t in deployment.items()}}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--terraform-output', required=True, help='File written by `terraform output -json`.')
    a = p.parse_args()
    try:
        with open(a.terraform_output, encoding='utf-8') as handle:
            values = outputs_from_terraform(json.load(handle))
    except NotReady as error:
        raise SystemExit(str(error)) from None
    import boto3
    session = boto3.Session(region_name=REGION)
    if session.client('sts').get_caller_identity()['Account'] != ACCOUNT:
        raise SystemExit('wrong AWS account')
    try:
        block = deployment_block(values, session.client('cloudfront'), session.client('s3'))
    except NotReady as error:
        raise SystemExit(str(error)) from None
    print(json.dumps(block, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
