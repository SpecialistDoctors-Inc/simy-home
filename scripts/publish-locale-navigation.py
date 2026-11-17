"""Publish only the reviewed locale menu HTML and its three support objects."""
import hashlib
import json
import os
import re
import subprocess
from locale_navigation_release import ROOT, check
from hp_industry_release import source_path


def aws(args, output=False):
    if output:
        return json.loads(subprocess.check_output(['aws', *args]))
    subprocess.run(['aws', *args], check=True, stdout=subprocess.DEVNULL)


def publish(root=ROOT, runner=aws):
    manifest, digest = check(root, os.environ.get('EXPECTED_RELEASE_SHA256'))
    bucket = os.environ['SITE_S3_BUCKET']
    distribution = os.environ['SITE_CF_DISTRIBUTION_ID']
    if not re.fullmatch('[a-z0-9][a-z0-9.-]+', bucket) or not re.fullmatch('[A-Z0-9]+', distribution):
        raise ValueError('Invalid locale publication target')
    # Validate every source before any AWS operation. A frozen checkout is also
    # checked again immediately before each upload, including alias uploads.
    for item in manifest['objects']:
        body = source_path(root / 'site', item['source']).read_bytes()
        if len(body) != item['bytes'] or hashlib.sha256(body).hexdigest() != item['sha256']:
            raise ValueError('Locale source hash mismatch: ' + item['source'])
    written = []
    for item in manifest['objects']:
        source = source_path(root / 'site', item['source'])
        body = source.read_bytes()
        if len(body) != item['bytes'] or hashlib.sha256(body).hexdigest() != item['sha256']:
            raise ValueError('Locale source changed during publication: ' + item['source'])
        content_type = ('text/html' if item['source'].endswith('.html') else
                        'text/javascript' if item['source'].endswith('.js') else 'application/json')
        runner(['s3api', 'put-object', '--bucket', bucket, '--key', item['key'],
                '--body', str(source), '--content-type', content_type + '; charset=utf-8',
                '--cache-control', 'public, max-age=300'])
        written.append({key: item[key] for key in ('key', 'source', 'bytes', 'sha256')})
    paths = manifest['invalidation_paths']
    result = runner(['cloudfront', 'create-invalidation', '--distribution-id', distribution,
                     '--paths', *paths, '--output', 'json'], output=True)
    invalidation = result['Invalidation']['Id']
    runner(['cloudfront', 'wait', 'invalidation-completed', '--distribution-id', distribution, '--id', invalidation])
    receipt = {'status': 'uploaded_and_invalidated', 'commit': os.environ.get('GITHUB_SHA'),
               'manifest_sha256': digest, 'objects': len(written), 'object_keys': [o['key'] for o in written],
               'object_hashes': written, 'invalidation_paths': paths, 'invalidation_id': invalidation}
    (root / 'locale-navigation-deployment.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    receipt = publish()
    print(json.dumps({key: receipt[key] for key in ('status', 'objects', 'commit', 'manifest_sha256', 'invalidation_id')}))
