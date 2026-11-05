#!/usr/bin/env python3
"""Build a public release manifest from committed bytes, never local secrets."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--source', required=True)
parser.add_argument('--image', required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if not re.fullmatch(r'[a-f0-9]{40}', args.source):
    raise ValueError('full_commit_required')
if not re.fullmatch(r'209300895845\.dkr\.ecr\.ap-northeast-1\.amazonaws\.com/simy-hp-agent@sha256:[a-f0-9]{64}', args.image):
    raise ValueError('exact_image_digest_required')
names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', args.source,
    'infra/hp-agent', 'examples/hp-management/runner'], text=True).splitlines()
files = {name: hashlib.sha256(subprocess.check_output(['git', 'show', args.source+':'+name])).hexdigest()
         for name in names}
raw = (json.dumps({'schema': 1, 'source_sha': args.source, 'image': args.image,
                   'files': files}, sort_keys=True, indent=2)+'\n').encode()
args.output.write_bytes(raw)
print(json.dumps({'manifest_sha256': hashlib.sha256(raw).hexdigest(), 'files': len(files)}))
