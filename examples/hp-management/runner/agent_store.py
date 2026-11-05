"""Durable stage/effect records beside the existing request and mail ledger.

A local filesystem flock serializes the service. SQLite is not hosted on NFS and
this is not a multi-host queue. Uncertain effects are reconciled, never retried.
"""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import time
from ledger import Ledger, canon, digest, require


PARKED_STAGES = {'needs_input', 'worker_interrupted', 'provider_reconciliation_required'}
SAFE_TERMINAL_STAGES = {'awaiting_approval', 'stopped'}
# A recovery cycle is not complete merely because the controller re-enters its
# target stage.  These are the only transitions that prove the target's work
# actually advanced.  In particular a coding retry remains in the queued
# cycle through worker_starting/coding until it has a validated candidate.
RECOVERY_SUCCESSORS = {
    'queued': {'verifying'},
    'verifying': {'reviewing'},
    'reviewing': {'candidate'},
    'candidate': {'ci'},
    'ci': {'merge'},
    'merge': {'deploy'},
    'deploy': {'results'},
    'results': {'notification', 'awaiting_approval'},
    'notification': {'awaiting_approval'},
}


class AgentStore(Ledger):
    def __init__(self, path, clock=time.time, stage_timeout_seconds=1800):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = path
        require(type(stage_timeout_seconds) is int and 5 <= stage_timeout_seconds <= 86400,
                'invalid_stage_timeout_seconds')
        self.stage_timeout_seconds = stage_timeout_seconds
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
CREATE TABLE IF NOT EXISTS agent_job_runtime(
 site_id TEXT NOT NULL, request_id TEXT NOT NULL, revision INTEGER NOT NULL,
 stage TEXT NOT NULL, started_at REAL NOT NULL, progress_at REAL NOT NULL,
 deadline_at REAL NOT NULL, attempt INTEGER NOT NULL, failures INTEGER NOT NULL,
 retry_at REAL, resume_stage TEXT,
 PRIMARY KEY(site_id,request_id,revision),
 FOREIGN KEY(site_id,request_id,revision) REFERENCES agent_jobs(site_id,request_id,revision));
CREATE TABLE IF NOT EXISTS agent_incidents(
 key TEXT PRIMARY KEY, site_id TEXT NOT NULL, request_id TEXT NOT NULL, revision INTEGER NOT NULL,
 code TEXT NOT NULL, opened_at REAL NOT NULL, updated_at REAL NOT NULL,
 resolved_at REAL, acknowledged_at REAL, acknowledged_by TEXT);
CREATE TABLE IF NOT EXISTS agent_service_runtime(
 id INTEGER PRIMARY KEY CHECK(id=1), failures INTEGER NOT NULL,
 retry_at REAL NOT NULL, paused INTEGER NOT NULL);
INSERT OR IGNORE INTO agent_service_runtime VALUES(1,0,0,0);
''')
        # Older ledgers predate runtime tracking.  They get a new bounded
        # observation window; their old progress time was never recorded.
        with self.transaction():
            now = self.clock()
            self.connection.execute('''
INSERT OR IGNORE INTO agent_job_runtime
 (site_id,request_id,revision,stage,started_at,progress_at,deadline_at,attempt,failures,retry_at,resume_stage)
SELECT site_id,request_id,revision,stage,?,?,?,1,0,NULL,NULL FROM agent_jobs
''', (now, now, now + self.stage_timeout_seconds))

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

    @staticmethod
    def _code(value):
        # Controller callers use a fixed code or an exception type.  Normalize
        # the latter rather than storing a provider exception message.
        require(isinstance(value, str) and 0 < len(value) <= 200 and '\x00' not in value,
                'invalid_incident_code')
        normalized = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', value).lower()
        normalized = re.sub(r'[^a-z0-9]+', '_', normalized).strip('_')[:120]
        require(re.fullmatch(r'[a-z][a-z0-9_]{0,119}', normalized) is not None,
                'invalid_incident_code')
        return normalized

    @staticmethod
    def _stage(value):
        require(isinstance(value, str) and re.fullmatch(r'[a-z][a-z0-9_]{0,119}', value),
                'invalid_agent_stage')
        return value

    def _runtime_row(self, key):
        row = self.row('SELECT * FROM agent_job_runtime WHERE site_id=? AND request_id=? AND revision=?', key)
        require(row is not None, 'runtime_not_found')
        return row

    def runtime(self, key):
        """Return sanitized execution state; durable lease tokens stay in agent_jobs."""
        row = self._runtime_row(key)
        return dict(row)

    def _incident_key(self, key, code, now):
        prefix = digest({'site_id': key[0], 'request_id': key[1], 'revision': key[2],
                         'code': code, 'opened_at': now})
        # A fixed fake clock in a test or a rapid re-open must preserve prior
        # resolved records instead of replacing them.
        n = self.row('SELECT COUNT(*) AS n FROM agent_incidents WHERE key LIKE ?', (prefix + '%',))['n']
        return prefix if not n else prefix + '-' + str(n + 1)

    def _open_incident_locked(self, key, code):
        code = self._code(code)
        now = self.clock()
        if key is None:
            # Store-wide intake incidents are deliberately represented by one
            # sentinel scope.  They cannot accidentally resolve a customer's
            # request-scoped incident.
            key = ('', '', 0)
        require(isinstance(key, tuple) and len(key) == 3, 'invalid_incident_key')
        existing = self.row('''SELECT key FROM agent_incidents
 WHERE site_id=? AND request_id=? AND revision=? AND code=? AND resolved_at IS NULL
 ORDER BY opened_at DESC LIMIT 1''', (*key, code))
        if existing:
            self.connection.execute('UPDATE agent_incidents SET updated_at=? WHERE key=?', (now, existing['key']))
            return existing['key']
        incident_key = self._incident_key(key, code, now)
        self.connection.execute('INSERT INTO agent_incidents VALUES(?,?,?,?,?,?,?,?,?,?)',
                                (incident_key, *key, code, now, now, None, None, None))
        return incident_key

    def open_incident(self, key, code):
        with self.transaction():
            return self._open_incident_locked(key, code)

    def incidents(self):
        rows = self.connection.execute('''SELECT key,site_id,request_id,revision,code,opened_at,updated_at,
 resolved_at,acknowledged_at,acknowledged_by FROM agent_incidents ORDER BY opened_at,key''')
        return [dict(row) for row in rows]

    def service_runtime(self):
        return dict(self.row('SELECT * FROM agent_service_runtime WHERE id=1'))

    def service_failed(self,code,*,retryable,max_retries,base_delay):
        with self.transaction():
            failures=self.service_runtime()['failures']+1
            paused=not retryable or failures>max_retries
            retry_at=self.clock()+base_delay*(2**min(failures-1,10))
            self.connection.execute('UPDATE agent_service_runtime SET failures=?,retry_at=?,paused=? WHERE id=1',
                                    (failures,retry_at,int(paused)))
            self._open_incident_locked(None,code)

    def service_recovered(self):
        with self.transaction():
            self.connection.execute('UPDATE agent_service_runtime SET failures=0,retry_at=0,paused=0 WHERE id=1')
            self._resolve_incidents_locked(None)

    def acknowledge(self, incident_key, actor):
        require(isinstance(incident_key, str) and incident_key, 'invalid_incident_key')
        require(isinstance(actor, str) and 0 < len(actor.strip()) <= 200 and '\x00' not in actor,
                'invalid_incident_actor')
        with self.transaction():
            row = self.row('SELECT * FROM agent_incidents WHERE key=?', (incident_key,))
            require(row is not None and row['resolved_at'] is None, 'incident_not_open')
            now = self.clock()
            self.connection.execute('UPDATE agent_incidents SET acknowledged_at=?,acknowledged_by=?,updated_at=? WHERE key=?',
                                    (now, actor, now, incident_key))
            return {'key': incident_key, 'acknowledged_at': now, 'acknowledged_by': actor}

    def _resolve_incidents_locked(self, key):
        now = self.clock()
        if key is None:
            key = ('', '', 0)
        require(isinstance(key, tuple) and len(key) == 3, 'invalid_incident_key')
        result = self.connection.execute('''UPDATE agent_incidents SET resolved_at=?,updated_at=?
 WHERE site_id=? AND request_id=? AND revision=? AND resolved_at IS NULL''', (now, now, *key))
        return result.rowcount

    def resolve_incidents(self, key):
        with self.transaction():
            return self._resolve_incidents_locked(key)

    def _parking_code(self, stage, data):
        if stage == 'worker_interrupted':
            return 'worker_interrupted'
        if stage == 'provider_reconciliation_required':
            return 'provider_reconciliation_required'
        if stage == 'needs_input':
            for field in ('provider_recovery', 'verification_recovery', 'review_recovery', 'worker_recovery'):
                value = data.get(field)
                if isinstance(value, dict) and isinstance(value.get('code'), str):
                    candidate = value['code'].lower()
                    if re.fullmatch(r'[a-z][a-z0-9_]{0,119}', candidate):
                        return candidate
            return 'needs_input'
        return 'retry_wait'

    def add_job(self, request):
        key = self.key(request)
        with self.transaction():
            self.connection.execute('INSERT OR IGNORE INTO agent_jobs VALUES(?,?,?,?,?,?,?)',
                (*key, 'queued', '{}', None, None))
            now = self.clock()
            self.connection.execute('''INSERT OR IGNORE INTO agent_job_runtime VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                                    (*key, 'queued', now, now, now + self.stage_timeout_seconds, 1, 0, None, None))

    def job(self, key):
        row = self.row('SELECT * FROM agent_jobs WHERE site_id=? AND request_id=? AND revision=?', key)
        return {**dict(row), 'data': json.loads(row['data'])} if row else None

    def save(self, key, stage, data, token):
        stage = self._stage(stage)
        require(isinstance(data, dict), 'invalid_agent_data')
        with self.transaction():
            old = self.row('SELECT stage,error FROM agent_jobs WHERE site_id=? AND request_id=? AND revision=?', key)
            require(old is not None, 'agent_job_not_found')
            runtime = self._runtime_row(key)
            now = self.clock()
            same_stage = old['stage'] == stage
            # Repeated checkpoint writes must not make a stuck stage look new.
            error = old['error'] if same_stage else None
            self.connection.execute('UPDATE agent_jobs SET stage=?,data=?,token=?,error=? WHERE site_id=? AND request_id=? AND revision=?',
                                    (stage, canon(data), token, error, *key))
            if same_stage:
                # A checkpoint in the same stage is not evidence that work
                # progressed.  Keeping this timestamp makes a hung stage
                # observable by its original deadline/progress record.
                return
            target = runtime['resume_stage']
            cycle_advanced = target is not None and stage in RECOVERY_SUCCESSORS.get(target, set())
            # Parking an uncycled job is itself not forward progress.  A
            # pending cycle also retains its original bounded authority until
            # the target reaches its verified successor.
            # A terminal state is verified retirement, irrespective of which
            # recovery target was pending; it must close rather than preserve
            # that cycle's unresolved incident.
            preserve_cycle = stage not in SAFE_TERMINAL_STAGES and (
                (target is not None and not cycle_advanced) or stage in PARKED_STAGES
            )
            if preserve_cycle:
                self.connection.execute('''UPDATE agent_job_runtime
 SET stage=?,retry_at=NULL
 WHERE site_id=? AND request_id=? AND revision=?''', (stage, *key))
                if old['stage'] == 'queued' and stage == 'worker_starting':
                    # Execution time starts when this attempt actually launches.
                    # Queue waiting consumes no worker time; retry count and the
                    # incident remain durable until verified forward progress.
                    self.connection.execute('''UPDATE agent_job_runtime
 SET started_at=?,progress_at=?,deadline_at=?
 WHERE site_id=? AND request_id=? AND revision=?''',
                                            (now, now, now + self.stage_timeout_seconds, *key))
                if stage in PARKED_STAGES:
                    self._open_incident_locked(key, self._parking_code(stage, data))
                return
            self.connection.execute('''UPDATE agent_job_runtime
 SET stage=?,started_at=?,progress_at=?,deadline_at=?,failures=0,retry_at=NULL,resume_stage=NULL
 WHERE site_id=? AND request_id=? AND revision=?''',
                                    (stage, now, now, now + self.stage_timeout_seconds, *key))
            if stage in SAFE_TERMINAL_STAGES:
                self._resolve_incidents_locked(key)
            else:
                # A verified forward transition is the only ordinary automatic
                # resolution path.  Merely resuming an old stage is handled by
                # resume_job and intentionally leaves the incident open.
                self._resolve_incidents_locked(key)

    def set_error(self, key, code):
        # Exception text may contain provider payloads. Store a fixed/type code.
        code = self._code(code)
        with self.transaction():
            result = self.connection.execute('UPDATE agent_jobs SET error=? WHERE site_id=? AND request_id=? AND revision=?', (code, *key))
            require(result.rowcount == 1, 'agent_job_not_found')
            self._open_incident_locked(key, code)

    def fail_job(self, key, code, resume_stage, *, retryable, max_retries=3, base_delay=30):
        """Park a failed local step without granting a provider-side retry."""
        code = self._code(code)
        resume_stage = self._stage(resume_stage)
        require(type(retryable) is bool and type(max_retries) is int and 0 <= max_retries <= 20,
                'invalid_retry_policy')
        require(type(base_delay) is int and 1 <= base_delay <= 86400, 'invalid_retry_delay')
        with self.transaction():
            job = self.row('SELECT * FROM agent_jobs WHERE site_id=? AND request_id=? AND revision=?', key)
            require(job is not None, 'agent_job_not_found')
            runtime = self._runtime_row(key)
            now = self.clock()
            failures = int(runtime['failures']) + 1
            delay = base_delay * (2 ** min(failures - 1, 10))
            retry_at = now + delay
            may_retry = retryable and failures <= max_retries and retry_at < runtime['deadline_at']
            stage = 'retry_wait' if may_retry else 'needs_input'
            self.connection.execute('UPDATE agent_jobs SET stage=?,error=? WHERE site_id=? AND request_id=? AND revision=?',
                                    (stage, code, *key))
            # Preserve the original deadline. A failing stage cannot extend its
            # own authority window merely by retrying.
            self.connection.execute('''UPDATE agent_job_runtime
 SET stage=?,failures=?,retry_at=?,resume_stage=?
 WHERE site_id=? AND request_id=? AND revision=?''',
                                    (stage, failures, retry_at if may_retry else None, resume_stage, *key))
            incident = self._open_incident_locked(key, code)
            return {'stage': stage, 'failures': failures, 'retry_at': retry_at if may_retry else None,
                    'resume_stage': resume_stage, 'incident_key': incident}

    def resume_job(self, key, stage, *, new_attempt=False, reset_budget=False):
        """Typed operator/controller recovery after its own input/effect checks."""
        stage = self._stage(stage)
        require(type(new_attempt) is bool, 'invalid_resume_attempt')
        require(type(reset_budget) is bool, 'invalid_resume_budget')
        with self.transaction():
            job = self.row('SELECT * FROM agent_jobs WHERE site_id=? AND request_id=? AND revision=?', key)
            require(job is not None, 'agent_job_not_found')
            runtime = self._runtime_row(key)
            require(job['stage'] in PARKED_STAGES | {'retry_wait'}, 'job_not_recoverable')
            expected = runtime['resume_stage']
            require(expected is None or expected == stage, 'resume_stage_mismatch')
            if job['stage'] == 'retry_wait':
                require(runtime['retry_at'] is not None and runtime['retry_at'] <= self.clock(), 'retry_not_due')
            now = self.clock()
            attempt = int(runtime['attempt']) + int(new_attempt)
            # Automatic backoff resumes remain within the original authority
            # window and retry budget.  A typed, explicitly requested operator
            # recovery may begin one new bounded cycle; its incident history is
            # still preserved until verified forward progress.
            deadline = now + self.stage_timeout_seconds if reset_budget else runtime['deadline_at']
            failures = 0 if reset_budget else runtime['failures']
            self.connection.execute('UPDATE agent_jobs SET stage=? WHERE site_id=? AND request_id=? AND revision=?',
                                    (stage, *key))
            self.connection.execute('''UPDATE agent_job_runtime
 SET stage=?,started_at=?,progress_at=?,deadline_at=?,attempt=?,failures=?,retry_at=NULL,resume_stage=?
 WHERE site_id=? AND request_id=? AND revision=?''',
                                    (stage, now, now, deadline, attempt, failures, expected or stage, *key))
            # Keep error and incident until a later verified transition records
            # real progress; a resume command itself is not recovery evidence.
            return {'stage': stage, 'attempt': attempt}

    def effect(self, request, name, payload):
        key = self.key(request)
        stable = digest({'request':key, 'stage':name})
        with self.transaction():
            old = self.row('SELECT * FROM agent_effects WHERE key=?', (stable,))
            if old:
                require(old['input_digest'] == digest(payload), 'effect_input_conflict')
                if old['state'] == 'not_started':
                    # A provider preflight proved this effect did not begin. It
                    # still needs a fresh lease and normal delivery exclusion to
                    # become admissible again; an admitted effect is never reset.
                    self.leased(request)
                    self.no_delivery_in_progress(key[0])
                    require(old['receipt'] is None, 'effect_receipt_conflict')
                    self.connection.execute("UPDATE agent_effects SET state='admitted',token_hash=? WHERE key=?",
                                            (digest(request['token']), stable))
                    return {'key': stable, 'state': 'new', 'receipt': None}
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

    def retry_notification(self, key, token):
        """Return a proven-not-started notice to the normal outbox admission gate."""
        require(isinstance(key, str) and key, 'invalid_notification_key')
        with self.transaction():
            row = self.row('SELECT * FROM notifications WHERE key=?', (key,))
            require(row is not None and row['state'] == 'not_started', 'notification_not_retriable')
            request = {'site_id': row['site_id'], 'request_id': row['request_id'],
                       'revision': row['revision'], 'token': token}
            self.leased(request)
            self.no_delivery_in_progress(row['site_id'])
            self.connection.execute("UPDATE notifications SET state='reserved',token_hash=NULL WHERE key=?", (key,))
            return {'key': key, 'state': 'reserved'}
