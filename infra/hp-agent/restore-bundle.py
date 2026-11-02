#!/usr/bin/env python3
"""Restore a verified, single-writer HP service archive to its dedicated disk."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import sqlite3
import sys
import tarfile

spec = importlib.util.spec_from_file_location('verify_release', Path(__file__).with_name('verify-release.py'))
release_verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_verifier)


def safe_member(member, destination):
    parts = PurePosixPath(member.name).parts
    if not parts or parts[0] not in {'control', 'state', 'work', 'codex-auth'} or '..' in parts:
        raise ValueError('unexpected_archive_path')
    if not (member.isdir() or member.isfile()):
        raise ValueError('archive_links_or_special_files_rejected')
    if member.uid not in {0, 1000} or member.gid not in {0, 1000}:
        raise ValueError('unexpected_archive_owner')
    result = tarfile.data_filter(member, destination)
    # Preserve the original controller/worker boundary, not arbitrary owners.
    result.uid, result.gid = member.uid, member.gid
    result.mode = member.mode & 0o777
    return result


def main():
    archive = Path(sys.argv[1])
    expected_archive, expected_database, manifest_hash, source_sha, image = sys.argv[2:]
    repo_root = Path(__file__).resolve().parents[2]
    release_verifier.verify(repo_root, repo_root/'release-manifest.json', manifest_hash, source_sha, image)
    target = Path('/srv/hp-agent')
    assert os.getuid() == 0 and os.path.ismount(target)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected_archive
    assert not any((target/name).exists() for name in ['control','state','work','codex-auth'])
    with tarfile.open(archive) as source:
        # Validate every header before extracting even the first file.
        for member in source.getmembers():
            safe_member(member, str(target))
        source.extractall(target, filter=safe_member)
    database = target/'state/agent.sqlite3'
    assert hashlib.sha256(database.read_bytes()).hexdigest() == expected_database
    for file in (target/'control').iterdir():
        assert file.is_file() and file.stat().st_uid == 0 and file.stat().st_mode & 0o077 == 0
    auth = target/'codex-auth/auth.json'
    assert auth.is_file() and auth.stat().st_uid == 1000
    assert auth.stat().st_mode & 0o077 == 0
    connection = sqlite3.connect(f'file:{database}?mode=ro', uri=True)
    assert connection.execute('pragma quick_check').fetchone()[0] == 'ok'
    assert connection.execute("select count(*) from agent_jobs where stage not in ('awaiting_approval','stopped','needs_input')").fetchone()[0] == 0
    assert connection.execute("select count(*) from agent_effects where state='admitted'").fetchone()[0] == 0
    assert connection.execute("select count(*) from notifications where state in ('sending','ambiguous')").fetchone()[0] == 0
    proof={'database_sha256':expected_database,'archive_sha256':expected_archive,
           'database_integrity':'ok','pending_effects':0,'active_jobs':0,
           'manifest_sha256':manifest_hash,'source_sha':source_sha,'image':image}
    marker=target/'migration-verified.json'
    marker.write_text(json.dumps(proof)+'\n');marker.chmod(0o600)
    print(json.dumps(proof))


if __name__ == '__main__':
    main()
