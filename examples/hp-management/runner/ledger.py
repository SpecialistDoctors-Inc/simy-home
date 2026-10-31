#!/usr/bin/env python3
"""Standalone, operator-owned control ledger. No provider calls or SIMY login.

A human_confirmation_ref records an operator's check of a real decision; it is
not cryptographic customer authentication. GitHub's protected production
Environment remains a separate gate. Provider evidence must be read back by the
calling Codex before recording it here.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import PurePosixPath
import re
import secrets
import sqlite3
import sys
import time
from urllib.parse import urlparse
from uuid import UUID

FIELDS = (
    'request_id', 'revision', 'site_id', 'outcome', 'target', 'effective_at',
    'expires_at', 'timezone', 'assets_rights', 'dependencies', 'acceptance',
    'requester_ref', 'notification_recipient_ref', 'proposal_state',
)
CONFIG_FIELDS = {'site_id', 'sheet_id', 'repo', 'content_path', 'dev_url', 'prod_url',
                 'recipient', 'requester_ref', 'notification_recipient_ref'}
IDENTITY = ('source_sha', 'artifact_id', 'artifact_hash')
TERMINAL = {'cancelled', 'revoked', 'superseded', 'failed'}


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canon(value).encode()).hexdigest()


def require(condition, code):
    if not condition:
        raise ValueError(code)


def positive(value):
    if isinstance(value, str) and re.fullmatch(r'[1-9][0-9]{0,15}', value):
        value = int(value)
    require(type(value) is int and 0 < value < 2**53, 'invalid_positive_integer')
    return value


def text(value, limit=6000):
    require(isinstance(value, str) and 0 < len(value.strip()) <= limit and '\x00' not in value, 'invalid_text')
    return value


def url(value):
    parsed = urlparse(text(value, 2000))
    require(parsed.scheme == 'https' and parsed.hostname and not parsed.username
            and not parsed.password and not parsed.query and not parsed.fragment
            and parsed.port in (None, 443), 'invalid_url')
    return value.rstrip('/')


def identity(value):
    result = {key: value.get(key) for key in IDENTITY}
    require(isinstance(result['source_sha'], str) and re.fullmatch(r'[a-f0-9]{40}', result['source_sha']), 'invalid_source_sha')
    require(isinstance(result['artifact_hash'], str) and re.fullmatch(r'[a-f0-9]{64}', result['artifact_hash']), 'invalid_artifact_hash')
    require(isinstance(result['artifact_id'], str) and re.fullmatch(r'[1-9][0-9]*', result['artifact_id']), 'invalid_artifact_id')
    return result


class Ledger:
    def __init__(self, path, clock=time.time):
        self.clock = clock
        self.connection = sqlite3.connect(path, timeout=10, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript('''
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS site_config(
  site_id TEXT PRIMARY KEY, body TEXT NOT NULL, digest TEXT NOT NULL, revision INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS requests(
  site_id TEXT NOT NULL, request_id TEXT NOT NULL, revision INTEGER NOT NULL,
  body TEXT NOT NULL, digest TEXT NOT NULL, config_digest TEXT NOT NULL, state TEXT NOT NULL,
  preview TEXT, approval TEXT, publication TEXT, reason TEXT,
  PRIMARY KEY(site_id,request_id,revision), FOREIGN KEY(site_id) REFERENCES site_config(site_id));
CREATE TABLE IF NOT EXISTS leases(
  site_id TEXT NOT NULL, request_id TEXT NOT NULL, revision INTEGER NOT NULL,
  owner TEXT NOT NULL, token TEXT NOT NULL UNIQUE, expires REAL NOT NULL,
  PRIMARY KEY(site_id,request_id,revision),
  FOREIGN KEY(site_id,request_id,revision) REFERENCES requests(site_id,request_id,revision));
CREATE TABLE IF NOT EXISTS notifications(
  key TEXT PRIMARY KEY, site_id TEXT NOT NULL, request_id TEXT NOT NULL, revision INTEGER NOT NULL,
  kind TEXT NOT NULL, envelope TEXT NOT NULL, state TEXT NOT NULL,
  provider_message_id TEXT, receipt TEXT, created REAL NOT NULL, token_hash TEXT,
  FOREIGN KEY(site_id,request_id,revision) REFERENCES requests(site_id,request_id,revision));
''')

    def close(self):
        self.connection.close()

    @contextmanager
    def transaction(self):
        # All eligibility reads and mutations share this lock, including replays.
        self.connection.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.connection.commit()
        except BaseException:
            self.connection.rollback()
            raise

    def row(self, sql, args=()):
        return self.connection.execute(sql, args).fetchone()

    def key(self, data):
        return (text(data['site_id'], 63), str(UUID(data['request_id'])), positive(data['revision']))

    def current(self, data):
        key = self.key(data)
        request = self.row('SELECT * FROM requests WHERE site_id=? AND request_id=? AND revision=?', key)
        require(request is not None, 'request_not_found')
        config = self.row('SELECT * FROM site_config WHERE site_id=?', key[:1])
        require(config is not None and config['digest'] == request['config_digest'], 'config_drift')
        latest = self.row('SELECT MAX(revision) AS revision FROM requests WHERE site_id=? AND request_id=?', key[:2])
        require(latest['revision'] == key[2], 'request_superseded')
        require(request['state'] not in TERMINAL, 'request_inactive')
        return request, json.loads(config['body']), key

    def leased(self, data):
        request, config, key = self.current(data)
        lease = self.row('SELECT * FROM leases WHERE site_id=? AND request_id=? AND revision=?', key)
        require(lease is not None and lease['token'] == data.get('token')
                and lease['expires'] > self.clock(), 'lease_unavailable')
        return request, config, key

    def execute(self, operation, data):
        require(isinstance(data, dict), 'invalid_input')
        with self.transaction():
            method = getattr(self, 'op_' + operation.replace('-', '_'), None)
            require(method is not None and operation in OPERATIONS, 'unknown_operation')
            return method(data)

    def no_delivery_in_progress(self, site_id):
        # Admission is the local send linearization point. A later cancellation
        # stays pending until the already-admitted provider effect is reconciled.
        pending = self.row("SELECT key FROM notifications WHERE site_id=? AND state IN ('sending','ambiguous') LIMIT 1", (site_id,))
        require(pending is None, 'delivery_reconciliation_required')

    def op_config(self, data):
        config = data['config']
        require(isinstance(config, dict) and set(config) == CONFIG_FIELDS, 'invalid_config')
        require(all(isinstance(v, str) for v in config.values()), 'invalid_config')
        require(re.fullmatch(r'[a-z][a-z0-9-]{1,62}', config['site_id']), 'invalid_site_id')
        require(re.fullmatch(r'[A-Za-z0-9_-]{10,256}', config['sheet_id']), 'invalid_sheet_id')
        require(re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+', config['repo']), 'invalid_repository')
        path = PurePosixPath(config['content_path'])
        require(bool(path.parts) and not path.is_absolute() and str(path) == config['content_path']
                and not set(path.parts) & {'..', '.git', '.github'} and '\\' not in str(path), 'invalid_content_path')
        require(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', config['recipient']), 'invalid_recipient')
        text(config['requester_ref'], 200)
        text(config['notification_recipient_ref'], 200)
        config = {**config, 'dev_url': url(config['dev_url']), 'prod_url': url(config['prod_url'])}
        require(config['dev_url'] != config['prod_url'], 'environments_must_differ')
        config_digest = digest(config)
        old = self.row('SELECT * FROM site_config WHERE site_id=?', (config['site_id'],))
        if old is not None and old['digest'] != config_digest:
            self.no_delivery_in_progress(config['site_id'])
        revision = 1 if old is None else old['revision'] + (old['digest'] != config_digest)
        self.connection.execute('INSERT INTO site_config VALUES(?,?,?,?) ON CONFLICT(site_id) DO UPDATE SET body=excluded.body,digest=excluded.digest,revision=excluded.revision',
                                (config['site_id'], canon(config), config_digest, revision))
        return {'site_id': config['site_id'], 'config_digest': config_digest, 'config_revision': revision}

    def op_ingest(self, data):
        row = data['request']
        require(isinstance(row, dict) and set(row) == set(FIELDS), 'invalid_request_shape')
        key = self.key(row)
        require(all(isinstance(v, str) for k, v in row.items() if k != 'revision'), 'invalid_cell')
        normalized = {**row, 'request_id': key[1], 'revision': str(key[2])}
        require(all(not v.startswith('=') and '\x00' not in v and len(v) <= 6000 for v in normalized.values()), 'invalid_cell')
        require(all(normalized[k].strip() for k in ('outcome', 'acceptance', 'requester_ref', 'notification_recipient_ref')), 'incomplete_request')
        config = self.row('SELECT * FROM site_config WHERE site_id=?', key[:1])
        require(config is not None, 'config_missing')
        binding = json.loads(config['body'])
        require(all(row[k] == binding[k] for k in ('requester_ref', 'notification_recipient_ref')),
                'request_binding_mismatch')
        require(row['target'] == binding['dev_url'] + '/#news' and row['proposal_state'] == 'ready_for_dev', 'invalid_target_or_state')
        require(row['timezone'] == 'Asia/Tokyo', 'timezone_required')
        value_digest = digest(normalized)
        existing = self.row('SELECT * FROM requests WHERE site_id=? AND request_id=? AND revision=?', key)
        if existing:
            require(existing['digest'] == value_digest and existing['config_digest'] == config['digest'], 'request_conflict')
            return {'digest': value_digest, 'state': existing['state'], 'reused': True}
        latest = self.row('SELECT MAX(revision) AS revision FROM requests WHERE site_id=? AND request_id=?', key[:2])['revision']
        require(key[2] == (latest or 0) + 1, 'revision_not_monotonic')
        self.no_delivery_in_progress(key[0])
        self.connection.execute("UPDATE requests SET state='superseded' WHERE site_id=? AND request_id=? AND state NOT IN ('cancelled','revoked','failed','superseded')", key[:2])
        self.connection.execute('DELETE FROM leases WHERE site_id=? AND request_id=?', key[:2])
        self.connection.execute('INSERT INTO requests(site_id,request_id,revision,body,digest,config_digest,state) VALUES(?,?,?,?,?,?,?)',
                                (*key, canon(normalized), value_digest, config['digest'], 'queued'))
        return {'digest': value_digest, 'state': 'queued', 'reused': False}

    def op_claim(self, data):
        request, _, key = self.current(data)
        self.no_delivery_in_progress(key[0])
        ttl = positive(data.get('ttl', 900))
        require(ttl <= 3600, 'lease_ttl_exceeded')
        owner = text(data.get('owner'), 200)
        old = self.row('SELECT * FROM leases WHERE site_id=? AND request_id=? AND revision=?', key)
        require(old is None or old['expires'] <= self.clock(), 'lease_busy')
        token = secrets.token_urlsafe(32)
        expiry = self.clock() + ttl
        self.connection.execute('INSERT INTO leases VALUES(?,?,?,?,?,?) ON CONFLICT(site_id,request_id,revision) DO UPDATE SET owner=excluded.owner,token=excluded.token,expires=excluded.expires', (*key, owner, token, expiry))
        if request['state'] == 'queued':
            self.connection.execute("UPDATE requests SET state='working' WHERE site_id=? AND request_id=? AND revision=?", key)
        return {'token': token, 'expires': expiry, 'state': 'working' if request['state'] == 'queued' else request['state']}

    def op_renew(self, data):
        self.leased(data)
        ttl = positive(data.get('ttl', 900))
        require(ttl <= 3600, 'lease_ttl_exceeded')
        expiry = self.clock() + ttl
        self.connection.execute('UPDATE leases SET expires=? WHERE token=?', (expiry, data['token']))
        return {'expires': expiry}

    def op_release(self, data):
        key = self.key(data)
        result = self.connection.execute('DELETE FROM leases WHERE site_id=? AND request_id=? AND revision=? AND token=?', (*key, data.get('token')))
        return {'released': result.rowcount == 1}

    def op_status(self, data):
        key = self.key(data)
        value = self.row('SELECT * FROM requests WHERE site_id=? AND request_id=? AND revision=?', key)
        require(value is not None, 'request_not_found')
        return {k: json.loads(value[k]) if value[k] and k in {'body', 'preview', 'approval', 'publication'} else value[k] for k in value.keys()}

    def stop(self, data, state):
        key = self.key(data)
        self.no_delivery_in_progress(key[0])
        reason = text(data.get('reason'), 1000)
        result = self.connection.execute('UPDATE requests SET state=?,reason=? WHERE site_id=? AND request_id=? AND revision=?', (state, reason, *key))
        require(result.rowcount == 1, 'request_not_found')
        self.connection.execute('DELETE FROM leases WHERE site_id=? AND request_id=? AND revision=?', key)
        return {'state': state}

    def op_cancel(self, data):
        return self.stop(data, 'cancelled')

    def op_revoke(self, data):
        return self.stop(data, 'revoked')

    def op_preview(self, data):
        request, config, key = self.leased(data)
        proof = {**identity(data), 'run_id': positive(data.get('run_id')), 'run_attempt': positive(data.get('run_attempt')),
                 'url': data.get('url'), 'tests_passed': data.get('tests_passed')}
        require(proof['url'] == config['dev_url'] and proof['tests_passed'] is True, 'preview_evidence_invalid')
        if request['preview']:
            require(json.loads(request['preview']) == proof, 'preview_conflict')
            return {'state': request['state'], 'reused': True}
        require(request['state'] == 'working', 'preview_invalid_state')
        self.connection.execute("UPDATE requests SET state='preview_ready',preview=? WHERE site_id=? AND request_id=? AND revision=?", (canon(proof), *key))
        return {'state': 'preview_ready', 'reused': False}

    def op_approve(self, data):
        request, _, key = self.current(data)
        approved = identity(data)
        preview = json.loads(request['preview'] or '{}')
        require(all(approved[k] == preview.get(k) for k in IDENTITY), 'approval_artifact_mismatch')
        ref = text(data.get('human_confirmation_ref'), 1000)
        proof = {**approved, 'human_confirmation_ref': ref}
        if request['approval']:
            require(json.loads(request['approval']) == proof, 'approval_conflict')
            return {'state': request['state'], 'reused': True}
        require(request['state'] == 'preview_ready', 'approval_invalid_state')
        self.connection.execute("UPDATE requests SET state='approved',approval=? WHERE site_id=? AND request_id=? AND revision=?", (canon(proof), *key))
        return {'state': 'approved', 'reused': False}

    def op_publish(self, data):
        request, config, key = self.leased(data)
        self.no_delivery_in_progress(key[0])
        proof = identity(data)
        approved = json.loads(request['approval'] or '{}')
        require(all(proof[k] == approved.get(k) for k in IDENTITY), 'publication_artifact_mismatch')
        release = data.get('release_sha')
        require(isinstance(release, str) and re.fullmatch(r'[a-f0-9]{40}', release), 'invalid_release_sha')
        require(data.get('url') == config['prod_url'] and data.get('readback_verified') is True, 'publication_not_verified')
        proof.update(release_sha=release, url=data['url'], run_id=positive(data.get('run_id')), readback_verified=True)
        if request['publication']:
            require(json.loads(request['publication']) == proof, 'publication_conflict')
            return {'state': request['state'], 'reused': True}
        require(request['state'] == 'approved', 'publication_invalid_state')
        self.connection.execute("UPDATE requests SET state='published',publication=? WHERE site_id=? AND request_id=? AND revision=?", (canon(proof), *key))
        return {'state': 'published', 'reused': False}

    def envelope(self, data):
        request, config, key = self.leased(data)
        kind = data.get('kind')
        require(kind in {'preview_ready', 'published'}, 'invalid_notification_kind')
        require(request['state'] in ({'preview_ready', 'approved', 'published'} if kind == 'preview_ready' else {'published'}), 'notification_not_ready')
        proof = json.loads(request['preview'] if kind == 'preview_ready' else request['publication'])
        notification_key = digest({'site': key[0], 'request': key[1], 'revision': key[2], 'kind': kind,
                                   'config': request['config_digest'], 'proof': proof, 'recipient': config['recipient']})
        title = '確認用ページの準備ができました' if kind == 'preview_ready' else 'ホームページを公開しました'
        body = f"{title}。\n{proof['url']}\n\n依頼: {key[1]} / revision {key[2]}\nsource SHA: {proof['source_sha']}\nartifact: {proof['artifact_id']} / {proof['artifact_hash']}\n\nHP-NOTICE-{notification_key}"
        return key, notification_key, {'to': config['recipient'], 'subject': '【サンプルクリニック】' + title, 'body': body}

    def op_outbox_reserve(self, data):
        key, notification_key, envelope = self.envelope(data)
        existing = self.row('SELECT * FROM notifications WHERE key=?', (notification_key,))
        if existing:
            return {'key': notification_key, 'state': existing['state'], 'created': False, 'may_send': False}
        self.connection.execute('INSERT INTO notifications VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                                (notification_key, *key, data['kind'], canon(envelope), 'reserved', None, None, self.clock(), None))
        return {'key': notification_key, 'state': 'reserved', 'created': True, 'may_send': False}

    def op_outbox_admit(self, data):
        key, notification_key, envelope = self.envelope(data)
        require(data.get('key') == notification_key, 'notification_key_mismatch')
        existing = self.row('SELECT * FROM notifications WHERE key=?', (notification_key,))
        require(existing is not None, 'notification_not_reserved')
        if existing['state'] != 'reserved':
            return {'key': notification_key, 'state': existing['state'], 'may_send': False}
        self.no_delivery_in_progress(key[0])
        self.connection.execute("UPDATE notifications SET state='sending',token_hash=? WHERE key=?", (digest(data['token']), notification_key))
        return {'key': notification_key, 'state': 'sending', 'may_send': True, 'envelope': envelope}

    def op_outbox_record(self, data):
        notification_key = text(data.get('key'), 64)
        existing = self.row('SELECT * FROM notifications WHERE key=?', (notification_key,))
        require(existing is not None, 'notification_not_reserved')
        require(existing['token_hash'] == digest(data.get('token'))
                and existing['state'] != 'reserved', 'notification_not_admitted')
        # Readback may arrive after lease expiry. This only records the admitted
        # effect; it cannot authorize another send or change the envelope.
        state = data.get('state')
        require(state in {'ambiguous', 'provider_accepted', 'inbox_verified'}, 'invalid_notification_state')
        provider_id = data.get('provider_message_id')
        if state != 'ambiguous':
            text(provider_id, 500)
            require(data.get('readback_verified') is True, 'notification_readback_required')
        require(existing['provider_message_id'] in (None, provider_id), 'notification_provider_conflict')
        require(existing['state'] != 'inbox_verified' or state == 'inbox_verified', 'notification_state_regression')
        require(existing['state'] != 'provider_accepted' or state != 'ambiguous', 'notification_state_regression')
        if state == 'inbox_verified':
            text(data.get('inbox_evidence_ref'), 1000)
            require(existing['state'] in {'provider_accepted', 'inbox_verified'}, 'provider_readback_required')
        self.connection.execute('UPDATE notifications SET state=?,provider_message_id=?,receipt=? WHERE key=?', (state, provider_id, canon(data), notification_key))
        return {'key': notification_key, 'state': state}

    def op_outbox_query(self, data):
        key = self.key(data)
        rows = self.connection.execute('SELECT key,kind,state,envelope,provider_message_id FROM notifications WHERE site_id=? AND request_id=? AND revision=?', key)
        return {'notifications': [{**dict(r), 'envelope': json.loads(r['envelope'])} for r in rows]}


OPERATIONS = {'config', 'ingest', 'claim', 'renew', 'release', 'status', 'cancel', 'revoke',
              'preview', 'approve', 'publish', 'outbox-reserve', 'outbox-admit', 'outbox-record', 'outbox-query'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('operation', choices=sorted(OPERATIONS))
    args = parser.parse_args()
    ledger = None
    try:
        data = json.load(sys.stdin)
        ledger = Ledger(args.db)
        print(canon(ledger.execute(args.operation, data)))
    except (ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        print(canon({'error': str(exc)}))
        return 2
    finally:
        if ledger:
            ledger.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
