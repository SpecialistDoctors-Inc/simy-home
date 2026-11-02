#!/usr/bin/env python3
"""Verify the operator-pinned public release before exposing migrated credentials."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


def verify(root, manifest, expected_hash, source_sha, image):
    if not re.fullmatch(r'[a-f0-9]{64}', expected_hash):
        raise ValueError('invalid_manifest_hash')
    raw = manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        raise ValueError('manifest_hash_mismatch')
    release = json.loads(raw)
    if release.get('source_sha') != source_sha or release.get('image') != image:
        raise ValueError('release_identity_mismatch')
    files = release.get('files')
    required = {'infra/hp-agent/'+name for name in [
        'verify-release.py', 'install-runtime.sh', 'restore-bundle.py', 'health.py']}
    required |= {'examples/hp-management/runner/'+name for name in [
        'agent.py', 'Dockerfile', 'requirements.txt', 'seccomp-codex.json', 'apparmor-codex.profile']}
    if not isinstance(files, dict) or not required <= files.keys():
        raise ValueError('incomplete_release')
    for name, digest in files.items():
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or str(path) != name:
            raise ValueError('unsafe_release_path')
        file = root/path
        if not file.is_file() or any(parent.is_symlink() for parent in [file, *file.parents]):
            raise ValueError('unsafe_release_file')
        if hashlib.sha256(file.read_bytes()).hexdigest() != digest:
            raise ValueError('release_file_mismatch:'+name)
    return release


def verify_image(release, actual):
    expected = {Path(name).name: value for name, value in release['files'].items()
                if name.startswith('examples/hp-management/runner/') and name.endswith('.py')}
    expected['requirements.txt'] = release['files']['examples/hp-management/runner/requirements.txt']
    if actual != expected:
        raise ValueError('image_content_mismatch')


def verify_migration(marker, expected_hash, source_sha, image):
    proof = json.loads(marker.read_bytes())
    if any(proof.get(key) != value for key, value in {
        'manifest_sha256': expected_hash, 'source_sha': source_sha, 'image': image,
        'database_integrity': 'ok', 'pending_effects': 0, 'active_jobs': 0,
    }.items()):
        raise ValueError('migration_release_mismatch')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--image-hashes', type=Path)
    parser.add_argument('--migration-marker', type=Path)
    args = parser.parse_args()
    release = verify(args.root, args.manifest, args.sha256, args.source, args.image)
    if args.image_hashes:
        verify_image(release, json.loads(args.image_hashes.read_bytes()))
    if args.migration_marker:
        verify_migration(args.migration_marker, args.sha256, args.source, args.image)
    print(json.dumps({'release_verified': True, 'source_sha': args.source,
                      'image': args.image, 'manifest_sha256': args.sha256}))


if __name__ == '__main__':
    main()
