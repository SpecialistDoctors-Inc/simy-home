"""Durable stage/effect records beside the existing request and mail ledger.

A local filesystem flock serializes the service. SQLite is not hosted on NFS and
this is not a multi-host queue. Uncertain effects are reconciled, never retried.
"""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import time
from ledger import Ledger, canon, digest, require


class AgentStore(Ledger):
    def __init__(self, path, clock=time.time):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = path
        super().__init__(str(path), clock)
        os.chmod(path, 0o600)
        self.connection.executescript('''
CREATE TABLE IF NOT EXISTS agent_jobs(
 site_id TEXT NOT NULL, request_id TEXT NOT NULL, revision INTEGER NOT NULL,
 stage TEXT NOT NULL, data TEXT NOT NULL, token TEXT, error TEXT,
 PRIMARY KEY(site_id,request_id,revision));
CREATE TABLE IF NOT EXISTS agent_events(
 event_id TEXT PRIMARY KEY, request_id TEXT NOT NULL, revision INTEGER NOT NULL,
 digest TEXT NOT NULL, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agent_rejections(
 event_digest TEXT PRIMARY KEY, code TEXT NOT NULL, observed_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS agent_boots(
 boot_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, pid INTEGER NOT NULL,
 parent_pid INTEGER NOT NULL, command TEXT NOT NULL);
''')

    @contextmanager
    def exclusive(self):
        lock = self.path.with_suffix('.lock')
        fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError('agent_instance_busy') from None
            yield
        finally:
            os.close(fd)

    def observe(self, event):
        with self.transaction():
            old = self.row('SELECT digest FROM agent_events WHERE event_id=?', (event['event_id'],))
            require(old is None or old['digest'] == digest(event), 'sheet_event_mutated')
            self.connection.execute('INSERT OR IGNORE INTO agent_events VALUES(?,?,?,?,?)',
                (event['event_id'], event['request_id'], int(event['revision']), digest(event), canon(event)))

    def reject_event(self, event, code):
        with self.transaction():
            self.connection.execute('INSERT OR IGNORE INTO agent_rejections VALUES(?,?,?)',(digest(event),code,self.clock()))

    def abandon_not_started(self, effect_key):
        with self.transaction():
            row=self.row('SELECT state FROM agent_effects WHERE key=?',(effect_key,))
            require(row is not None and row['state']=='admitted','effect_not_admitted')
            self.connection.execute("UPDATE agent_effects SET state='not_started' WHERE key=?",(effect_key,))

    def notification_not_started(self, key, token):
        with self.transaction():
            row=self.row('SELECT state,token_hash FROM notifications WHERE key=?',(key,))
            require(row is not None and row['state']=='sending' and row['token_hash']==digest(token),'notification_not_admitted')
            self.connection.execute("UPDATE notifications SET state='not_started' WHERE key=?",(key,))

    def add_job(self, request):
        key = self.key(request)
        with self.transaction():
            self.connection.execute('INSERT OR IGNORE INTO agent_jobs VALUES(?,?,?,?,?,?,?)',
                (*key, 'queued', '{}', None, None))

    def job(self, key):
        row = self.row('SELECT * FROM agent_jobs WHERE site_id=? AND request_id=? AND revision=?', key)
        return {**dict(row), 'data': json.loads(row['data'])} if row else None

    def save(self, key, stage, data, token):
        with self.transaction():
            self.connection.execute('UPDATE agent_jobs SET stage=?,data=?,token=?,error=NULL WHERE site_id=? AND request_id=? AND revision=?',
                (stage, canon(data), token, *key))

    def set_error(self, key, code):
        # Exception text may contain provider payloads. Store a fixed/type code.
        with self.transaction():
            self.connection.execute('UPDATE agent_jobs SET error=? WHERE site_id=? AND request_id=? AND revision=?', (code, *key))

    def effect(self, request, name, payload):
        key = self.key(request)
        stable = digest({'request':key, 'stage':name})
        with self.transaction():
            old = self.row('SELECT * FROM agent_effects WHERE key=?', (stable,))
            if old:
                require(old['input_digest'] == digest(payload), 'effect_input_conflict')
                return {'key':stable, 'state':old['state'], 'receipt':json.loads(old['receipt']) if old['receipt'] else None}
            self.leased(request)
            self.no_delivery_in_progress(key[0])
            self.connection.execute('INSERT INTO agent_effects VALUES(?,?,?,?,?,?,?,?,?,?)',
                (stable, *key, name, digest(payload), 'admitted', digest(request['token']), None, self.clock()))
            return {'key':stable, 'state':'new', 'receipt':None}

    def record_effect(self, key, receipt):
        # Reconciliation only. It cannot issue another effect or restore a lease.
        with self.transaction():
            old = self.row('SELECT * FROM agent_effects WHERE key=?', (key,))
            require(old is not None, 'effect_not_admitted')
            require(old['receipt'] is None or json.loads(old['receipt']) == receipt, 'effect_receipt_conflict')
            self.connection.execute("UPDATE agent_effects SET state='observed',receipt=? WHERE key=?", (canon(receipt),key))
