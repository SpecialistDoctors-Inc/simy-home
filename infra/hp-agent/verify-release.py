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
        'verify-release.py', 'install-runtime.sh', 'upgrade-runtime.sh', 'restore-bundle.py', 'health.py']}
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
    proof = verify_migration_shape(marker)
    if any(proof.get(key) != value for key, value in {
        'manifest_sha256': expected_hash, 'source_sha': source_sha, 'image': image,
        'database_integrity': 'ok', 'pending_effects': 0, 'active_jobs': 0,
    }.items()):
        raise ValueError('migration_release_mismatch')


def verify_migration_shape(marker):
    """Check an original restore proof before an in-place runtime upgrade."""
    proof = json.loads(marker.read_bytes())
    required = {
        'database_sha256', 'archive_sha256', 'database_integrity', 'pending_effects',
        'active_jobs', 'manifest_sha256', 'source_sha', 'image',
    }
    if not isinstance(proof, dict) or set(proof) != required:
        raise ValueError('migration_marker_schema_invalid')
    if (not all(re.fullmatch(r'[a-f0-9]{64}', proof[name] or '') for name in
                ('database_sha256', 'archive_sha256', 'manifest_sha256'))
            or not re.fullmatch(r'[a-f0-9]{40}', proof['source_sha'] or '')
            or not re.fullmatch(r'209300895845\.dkr\.ecr\.ap-northeast-1\.amazonaws\.com/simy-hp-agent@sha256:[a-f0-9]{64}', proof['image'] or '')
            or proof['database_integrity'] != 'ok'
            or proof['pending_effects'] != 0
            or proof['active_jobs'] != 0):
        raise ValueError('migration_marker_schema_invalid')
    return proof


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--sha256')
    parser.add_argument('--source')
    parser.add_argument('--image')
    parser.add_argument('--image-hashes', type=Path)
    parser.add_argument('--migration-marker', type=Path)
    parser.add_argument('--verify-migration-marker-shape', action='store_true')
    args = parser.parse_args()
    if args.verify_migration_marker_shape:
        if args.migration_marker is None:
            parser.error('--migration-marker is required with --verify-migration-marker-shape')
        verify_migration_shape(args.migration_marker)
        print(json.dumps({'migration_marker_verified': True}))
        return
    if any(value is None for value in (args.root, args.manifest, args.sha256, args.source, args.image)):
        parser.error('--root, --manifest, --sha256, --source, and --image are required')
    release = verify(args.root, args.manifest, args.sha256, args.source, args.image)
    if args.image_hashes:
        verify_image(release, json.loads(args.image_hashes.read_bytes()))
    if args.migration_marker:
        verify_migration(args.migration_marker, args.sha256, args.source, args.image)
    print(json.dumps({'release_verified': True, 'source_sha': args.source,
                      'image': args.image, 'manifest_sha256': args.sha256}))


if __name__ == '__main__':
    main()
