"""Server-side validation of untrusted HP archives (stdlib only)."""
from __future__ import annotations

import hashlib
import io
import json
import re
import stat
import unicodedata
import uuid
import zipfile
import zlib
from dataclasses import dataclass

MAX_TRANSPORT = 60 * 1024 * 1024
MAX_TOTAL = 50 * 1024 * 1024
MAX_FILE = 10 * 1024 * 1024
MAX_FILES = 1000
SUFFIXES = {'.html', '.css', '.js', '.json', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.ico', '.txt', '.xml', '.woff', '.woff2', '.ttf', '.pdf', '.webmanifest'}
DENIED = {'.hp', '.git', '.github', 'node_modules', 'package.json', 'package-lock.json', 'pnpm-lock.yaml', 'yarn.lock', 'credentials.json', 'service-account.json', 'config.json', 'tsconfig.json', 'jsconfig.json', 'next.config.js', 'vite.config.js', 'vercel.json', 'version.json'}


class BundleError(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_path(path: str) -> str:
    if not isinstance(path, str) or not path or len(path) > 1024 or any(c in path for c in ('\\', ':', '\x00')) or unicodedata.normalize('NFC', path) != path:
        raise BundleError('unsafe path')
    parts = path.split('/')
    if any(not p or p in ('.', '..') or (p.startswith('.') and p != '.well-known') or p.casefold() in DENIED for p in parts):
        raise BundleError('forbidden path')
    basename = parts[-1].casefold()
    if '.config.' in basename or basename.startswith(('credentials.', 'service-account.', 'service_account.')) or basename in {'server.js', 'build.js', 'deploy.js', 'gulpfile.js', 'gruntfile.js'}:
        raise BundleError('configuration or server script is not site content')
    if '.' not in parts[-1] or '.' + parts[-1].rsplit('.', 1)[-1].lower() not in SUFFIXES:
        raise BundleError('unsupported file suffix')
    if any(ord(c) < 32 or ord(c) == 127 for c in path):
        raise BundleError('control character in path')
    return path


def validate_files(files: dict[str, bytes]) -> dict[str, bytes]:
    if not isinstance(files, dict) or not 0 < len(files) <= MAX_FILES or 'index.html' not in files:
        raise BundleError('candidate requires index.html and bounded file count')
    folded = set()
    directories = set()
    components = {}
    total = 0
    for path, data in files.items():
        validate_path(path)
        if path.casefold() in folded or not isinstance(data, bytes) or len(data) > MAX_FILE:
            raise BundleError('collision or invalid file')
        folded.add(path.casefold())
        originals = path.split('/')
        for i in range(1, len(originals) + 1):
            original = '/'.join(originals[:i])
            if original.casefold() in components and components[original.casefold()] != original:
                raise BundleError('case-folding directory collision')
            components[original.casefold()] = original
        parts = path.casefold().split('/')
        for i in range(1, len(parts)):
            directories.add('/'.join(parts[:i]))
        total += len(data)
    if folded & directories:
        raise BundleError('file and directory collision')
    if total > MAX_TOTAL:
        raise BundleError('candidate too large')
    return dict(files)


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise BundleError('duplicate JSON key')
        value[key] = item
    return value


def _archive(data):
    if not isinstance(data, bytes) or len(data) > MAX_TRANSPORT:
        raise BundleError('transport too large')
    result = {}
    folded = set()
    components = {}
    total = 0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if len(archive.infolist()) > MAX_FILES * 2 + 10:
                raise BundleError('too many archive entries')
            for info in archive.infolist():
                name = info.filename
                if name in result or name.casefold() in folded:
                    raise BundleError('duplicate archive entry')
                folded.add(name.casefold())
                prefix = []
                for component in name.rstrip('/').split('/'):
                    prefix.append(component)
                    canonical = '/'.join(prefix)
                    folded_path = canonical.casefold()
                    if folded_path in components and components[folded_path] != canonical:
                        raise BundleError('case-folding directory collision')
                    components[folded_path] = canonical
                mode = info.external_attr >> 16
                kind = stat.S_IFMT(mode)
                if info.flag_bits & 1 or kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise BundleError('encrypted or special archive entry')
                if info.is_dir():
                    directory = name[:-1]
                    if directory != 'files':
                        if not directory.startswith('files/'):
                            raise BundleError('unexpected directory')
                        # Validate directory components using an allowed dummy leaf.
                        validate_path(directory[6:] + '/placeholder.txt')
                    if kind not in (0, stat.S_IFDIR) or info.file_size:
                        raise BundleError('invalid directory')
                    result[name] = None
                    continue
                if kind == stat.S_IFDIR:
                    raise BundleError('invalid regular entry')
                if name != 'manifest.json':
                    if not name.startswith('files/'):
                        raise BundleError('unexpected payload')
                    validate_path(name[6:])
                limit = 1024 * 1024 if name == 'manifest.json' else MAX_FILE
                if info.file_size > limit:
                    raise BundleError('file too large')
                content = archive.read(info)
                total += len(content)
                if total > MAX_TOTAL + 1024 * 1024:
                    raise BundleError('archive too large')
                result[name] = content
        manifest = json.loads(result.pop('manifest.json').decode('utf-8'), object_pairs_hook=_object)
        return manifest, {k: v for k, v in result.items() if v is not None}
    except (zipfile.BadZipFile, KeyError, UnicodeError, json.JSONDecodeError, RuntimeError, NotImplementedError, zlib.error, RecursionError) as error:
        raise BundleError('invalid archive') from error


def _keys(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise BundleError('invalid fields')


def _uuid(value):
    try:
        if not isinstance(value, str) or str(uuid.UUID(value)) != value:
            raise ValueError()
    except (ValueError, AttributeError):
        raise BundleError('invalid UUID') from None


def _header(manifest, kind, site_id):
    _keys(manifest, ('schema_version', 'kind', 'site_id', 'workspace_id', 'base_commit', 'files') if kind == 'snapshot' else ('schema_version', 'kind', 'site_id', 'workspace_id', 'base_commit', 'operation_id', 'changes'), () if kind == 'snapshot' else ('change_summary',))
    if type(manifest['schema_version']) is not int or manifest['schema_version'] != 1 or manifest['kind'] != kind:
        raise BundleError('unsupported manifest')
    if not isinstance(manifest['site_id'], str) or not manifest['site_id'] or len(manifest['site_id']) > 200 or (site_id is not None and manifest['site_id'] != site_id):
        raise BundleError('wrong site')
    _uuid(manifest['workspace_id'])
    if not isinstance(manifest['base_commit'], str) or not re.fullmatch('[0-9a-f]{40}', manifest['base_commit']):
        raise BundleError('invalid commit')


def _records(records):
    if not isinstance(records, list) or len(records) > MAX_FILES:
        raise BundleError('invalid records')
    paths = []
    for record in records:
        if not isinstance(record, dict):
            raise BundleError('invalid record')
        paths.append(validate_path(record.get('path')))
    if paths != sorted(paths) or len(set(p.casefold() for p in paths)) != len(paths):
        raise BundleError('unsorted or colliding paths')


def _hash(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


@dataclass(frozen=True)
class ValidatedSnapshot:
    manifest: dict
    files: dict[str, bytes]
    bundle_sha256: str


@dataclass(frozen=True)
class ValidatedChanges:
    manifest: dict
    candidate_files: dict[str, bytes]
    bundle_sha256: str


@dataclass(frozen=True)
class Reconciliation:
    files: dict[str, bytes]
    conflicts: tuple[str, ...]


def validate_snapshot(data: bytes, expected_site_id=None, expected_workspace_id=None, expected_base_commit=None) -> ValidatedSnapshot:
    manifest, payload = _archive(data)
    _header(manifest, 'snapshot', expected_site_id)
    if expected_workspace_id is not None and manifest['workspace_id'] != expected_workspace_id:
        raise BundleError('wrong workspace')
    if expected_base_commit is not None and manifest['base_commit'] != expected_base_commit:
        raise BundleError('wrong base commit')
    _records(manifest['files'])
    files = {}
    for item in manifest['files']:
        _keys(item, ('path', 'sha256', 'size'))
        content = payload.pop('files/' + item['path'], None)
        if content is None or not _hash(item['sha256']) or type(item['size']) is not int or item['size'] != len(content) or item['sha256'] != sha256(content):
            raise BundleError('payload hash or size mismatch')
        files[item['path']] = content
    if payload:
        raise BundleError('extra payload')
    return ValidatedSnapshot(manifest, validate_files(files), sha256(data))


def validate_changes(data: bytes, base_snapshot: ValidatedSnapshot, expected_operation_id=None) -> ValidatedChanges:
    manifest, payload = _archive(data)
    base = base_snapshot.manifest
    _header(manifest, 'changes', base['site_id'])
    if any(manifest[key] != base[key] for key in ('workspace_id', 'base_commit')):
        raise BundleError('wrong authoritative base')
    _uuid(manifest['operation_id'])
    if expected_operation_id is not None and manifest['operation_id'] != expected_operation_id:
        raise BundleError('wrong operation')
    summary = manifest.get('change_summary', '')
    if not isinstance(summary, str) or len(summary) > 200 or any(ord(c) < 32 or ord(c) == 127 for c in summary):
        raise BundleError('invalid summary')
    _records(manifest['changes'])
    files = dict(base_snapshot.files)
    for item in manifest['changes']:
        _keys(item, ('path', 'action', 'base_sha256', 'sha256', 'size'))
        path, action = item['path'], item['action']
        original = files.get(path)
        if action not in ('add', 'modify', 'delete') or type(item['size']) is not int:
            raise BundleError('invalid action or size')
        if action == 'add':
            if original is not None or item['base_sha256'] is not None:
                raise BundleError('add conflicts with base')
        elif original is None or item['base_sha256'] != sha256(original):
            raise BundleError('base hash mismatch')
        if action == 'delete':
            if item['sha256'] is not None or item['size'] != 0:
                raise BundleError('invalid deletion')
            del files[path]
        else:
            content = payload.pop('files/' + path, None)
            if content is None or not _hash(item['sha256']) or item['size'] != len(content) or item['sha256'] != sha256(content) or content == original:
                raise BundleError('payload mismatch or unchanged content')
            files[path] = content
    if payload:
        raise BundleError('extra payload')
    return ValidatedChanges(manifest, validate_files(files), sha256(data))


def build_snapshot(site_id, workspace_id, base_commit, files) -> bytes:
    validate_files(files)
    manifest = {'schema_version': 1, 'kind': 'snapshot', 'site_id': site_id, 'workspace_id': workspace_id, 'base_commit': base_commit, 'files': [{'path': p, 'sha256': sha256(files[p]), 'size': len(files[p])} for p in sorted(files)]}
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in [('manifest.json', json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode())] + [('files/' + p, files[p]) for p in sorted(files)]:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
    result = out.getvalue()
    validate_snapshot(result, site_id)
    return result


def reconcile(base_files, candidate_files, current_files) -> Reconciliation:
    for files in (base_files, candidate_files, current_files):
        validate_files(files)
    result, conflicts = {}, []
    for path in sorted(base_files.keys() | candidate_files.keys() | current_files.keys()):
        base, user, remote = base_files.get(path), candidate_files.get(path), current_files.get(path)
        if user == base:
            value = remote
        elif remote == base or user == remote:
            value = user
        else:
            conflicts.append(path)
            continue
        if value is not None:
            result[path] = value
    if not conflicts:
        validate_files(result)
    return Reconciliation(result, tuple(conflicts))
