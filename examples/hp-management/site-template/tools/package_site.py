#!/usr/bin/env python3
"""Create a deterministic static artifact from validated bytes; no git required."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import uuid
import zipfile

from validate_site import ValidationError, validate


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def records(files):
    return [{'path': path, 'sha256': digest(data), 'size': len(data)} for path, data in sorted(files.items())]


def package(site, output, operation_id, source_commit):
    if str(uuid.UUID(operation_id)) != operation_id:
        raise ValidationError('operation ID must be a canonical UUID')
    if not isinstance(source_commit, str) or not re.fullmatch('[0-9a-f]{40}', source_commit):
        raise ValidationError('source commit must be 40 lowercase hex characters')
    if Path(site).is_symlink():
        raise ValidationError('site must not be a symlink')
    root, output = Path(site).resolve(), Path(output).resolve()
    if output == root or root in output.parents:
        raise ValidationError('artifact output must be outside site/')
    files = validate(root)
    source_sha256 = digest(canonical(records(files)))
    metadata = {'schema_version': 1, 'source_commit': source_commit, 'operation_id': operation_id, 'source_sha256': source_sha256, 'version': source_sha256}
    files['version.json'] = canonical(metadata) + b'\n'
    stream = io.BytesIO()
    # Stored bytes avoid zlib-version-dependent output while remaining below the
    # transport budget (source is capped at 50 MiB; transport allows 60 MiB).
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
        for path, data in sorted(files.items()):
            entry = zipfile.ZipInfo(path, (1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            entry.compress_type = zipfile.ZIP_STORED
            archive.writestr(entry, data)
    artifact = stream.getvalue()
    manifest = dict(metadata, kind='static-site-artifact', artifact_sha256=digest(artifact), files=records(files))
    output.mkdir(parents=True, exist_ok=True)
    (output / 'site.zip').write_bytes(artifact)
    (output / 'manifest.json').write_bytes(canonical(manifest) + b'\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', default='site')
    parser.add_argument('--output', default='output')
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--operation-id', required=True)
    args = parser.parse_args()
    try:
        manifest = package(args.site, args.output, args.operation_id, args.source_commit)
    except (ValidationError, ValueError, OSError) as error:
        parser.exit(1, str(error) + '\n')
    print(json.dumps(manifest, sort_keys=True))


if __name__ == '__main__':
    main()
