from datetime import datetime, timezone, timedelta
import sqlite3
import tempfile
import unittest
from pathlib import Path
from health import healthy


class HealthTest(unittest.TestCase):
    now = datetime(2026, 11, 3, 3, 0, tzinfo=timezone.utc)

    def event(self, stage='idle', age=0, extra=''):
        return (self.now-timedelta(seconds=age)).isoformat()+' {"event":"poll_completed","stage":"'+stage+'"'+extra+'}'

    def test_completed_poll_and_long_coding_are_healthy(self):
        self.assertTrue(healthy(True, self.event(), self.now))
        self.assertTrue(healthy(True, self.event('coding', 1000), self.now))
        self.assertTrue(healthy(True, self.event('verifying', 1000), self.now))
        self.assertTrue(healthy(True, self.event('reviewing', 1000), self.now))

    def test_stopped_container_is_not_healthy(self):
        self.assertFalse(healthy(False, self.event(), self.now))

    def test_stale_or_future_heartbeat_is_not_healthy(self):
        for age in [1801, -1]:
            self.assertFalse(healthy(True, self.event(age=age), self.now))

    def test_latest_error_overrides_old_success(self):
        log=self.event(age=30)+'\n'+self.event('ci',extra=',"error":"RuntimeError"')
        self.assertFalse(healthy(True, log, self.now))

    def test_intake_or_reconciliation_failure_is_not_healthy(self):
        for stage in ['intake_blocked','needs_input','worker_interrupted','provider_reconciliation_required']:
            self.assertFalse(healthy(True, self.event(stage), self.now))

    def test_missing_or_malformed_output_is_not_success(self):
        for log in ['', 'not json', '2026-11-03T03:00:00Z {"event":"agent_started"}']:
            self.assertFalse(healthy(True, log, self.now))

    def test_out_of_order_logs_use_newest_poll(self):
        log=self.event()+ '\n'+self.event('intake_blocked',age=60)
        self.assertTrue(healthy(True, log, self.now))

    def state(self, schema=True):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'agent.sqlite3'
        connection = sqlite3.connect(path)
        if schema:
            connection.executescript('''
CREATE TABLE agent_incidents(key TEXT PRIMARY KEY, resolved_at REAL);
CREATE TABLE agent_jobs(stage TEXT NOT NULL);
CREATE TABLE agent_job_runtime(stage TEXT NOT NULL, deadline_at REAL NOT NULL);
''')
        connection.commit()
        connection.close()
        return path

    def test_unresolved_incident_is_unhealthy_even_after_idle_poll(self):
        path = self.state()
        connection = sqlite3.connect(path)
        connection.execute("INSERT INTO agent_incidents VALUES ('incident', NULL)")
        connection.commit(); connection.close()
        self.assertFalse(healthy(True, self.event(), self.now, path))

    def test_recovery_stage_and_overdue_runtime_are_unhealthy(self):
        for query, values in [
            ("INSERT INTO agent_jobs VALUES (?)", ('needs_input',)),
            ("INSERT INTO agent_jobs VALUES (?)", ('worker_interrupted',)),
            ("INSERT INTO agent_jobs VALUES (?)", ('provider_reconciliation_required',)),
            ("INSERT INTO agent_jobs VALUES (?)", ('retry_exhausted',)),
            ("INSERT INTO agent_job_runtime VALUES (?, ?)", ('coding', self.now.timestamp())),
        ]:
            path = self.state()
            connection = sqlite3.connect(path)
            connection.execute(query, values)
            connection.commit(); connection.close()
            self.assertFalse(healthy(True, self.event(), self.now, path))

    def test_retry_wait_requires_its_durable_incident_to_be_resolved(self):
        path = self.state()
        connection = sqlite3.connect(path)
        connection.execute("INSERT INTO agent_jobs VALUES (?)", ('retry_wait',))
        connection.execute("INSERT INTO agent_incidents VALUES ('retry', NULL)")
        connection.commit(); connection.close()
        self.assertFalse(healthy(True, self.event(), self.now, path))

    def test_queued_job_waiting_behind_another_job_is_not_overdue(self):
        path = self.state()
        connection = sqlite3.connect(path)
        connection.execute("INSERT INTO agent_jobs VALUES (?)", ('queued',))
        connection.execute("INSERT INTO agent_job_runtime VALUES (?, ?)",
                           ('queued', self.now.timestamp() - 3600))
        connection.commit(); connection.close()
        self.assertTrue(healthy(True, self.event(), self.now, path))

    def test_approval_wait_is_healthy_and_missing_schema_fails_closed(self):
        path = self.state()
        connection = sqlite3.connect(path)
        connection.execute("INSERT INTO agent_jobs VALUES (?)", ('awaiting_approval',))
        connection.execute("INSERT INTO agent_job_runtime VALUES (?, ?)",
                           ('awaiting_approval', self.now.timestamp() - 1))
        connection.commit(); connection.close()
        self.assertTrue(healthy(True, self.event('awaiting_approval'), self.now, path))
        self.assertFalse(healthy(True, self.event(), self.now, self.state(schema=False)))


if __name__ == '__main__':
    unittest.main()
