"""Refresh five owned hub/guide aliases during ordinary static publication.

The regular HTML sync publishes the source index files. This bounded step keeps
literal S3 aliases current without depending on a historical release snapshot.
CloudFront invalidation is owned by the surrounding deployment workflow.
"""
import json
import os
import re
import subprocess
from pathlib import Path
from hp_management_industries import HUB_SOURCE, HUB_URL

ROOT = Path(__file__).resolve().parents[1]
ALIASES = ((HUB_SOURCE, HUB_URL.lstrip('/')),
           (HUB_SOURCE, 'hp-management/'),
           (HUB_SOURCE, 'hp-management'),
           ('guides/index.html', 'guides.html'),
           ('guides/index.html', 'guides/'))


def alias_objects(root=ROOT):
    site = root / 'site'
    objects = []
    keys = set()
    for relative, key in ALIASES:
        source = site / relative
        if (not source.is_file() or not source.resolve().is_relative_to(site.resolve())
                or not source.stat().st_size):
            raise ValueError('Missing, empty or escaping alias source: ' + relative)
        if key in keys:
            raise ValueError('Duplicate alias key: ' + key)
        keys.add(key)
        objects.append((source, key))
    return objects


def aws(args):
    subprocess.run(['aws', *args], check=True, stdout=subprocess.DEVNULL)


def publish(root=ROOT, runner=aws):
    # Validate the complete finite source set before the first AWS operation.
    objects = alias_objects(root)
    bucket = os.environ['SITE_S3_BUCKET']
    if not re.fullmatch('[a-z0-9][a-z0-9.-]+', bucket):
        raise ValueError('Invalid alias publication bucket')
    for source, key in objects:
        runner(['s3api', 'put-object', '--bucket', bucket, '--key', key,
                '--body', str(source), '--content-type', 'text/html; charset=utf-8',
                '--cache-control', 'public, max-age=300'])
    return {'status': 'aliases_refreshed', 'objects': len(objects),
            'object_keys': [key for _, key in objects]}


if __name__ == '__main__':
    print(json.dumps(publish()))
