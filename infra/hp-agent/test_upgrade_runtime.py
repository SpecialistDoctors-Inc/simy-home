from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest


class UpgradeRuntimeTest(unittest.TestCase):
    script = Path(__file__).with_name('upgrade-runtime.sh')

    def test_shell_syntax_and_fail_closed_preflight_are_present(self):
        subprocess.run(['bash', '-n', self.script], check=True)
        text = self.script.read_text()
        for expected in [
            'verify-release.py', 'verify_migration_shape', 'active_or_unresolved_state',
            "stage not in ('awaiting_approval','stopped')", 'docker rename',
            'RestartPolicy.Name', 'migration-verified.previous-', 'upgrade-recovery-',
            'install-runtime.sh', 'existing upgrade receipt requires explicit recovery review',
            "request.state in ('superseded','cancelled','revoked')",
            'mountpoint -q /srv/hp-agent',
        ]:
            self.assertIn(expected, text)
        for forbidden in ['docker stop', 'docker kill', 'docker rm', ' kill ', 'pkill', 'killall']:
            self.assertNotIn(forbidden, text)

    def test_exact_container_identity_is_checked_before_rename(self):
        text = self.script.read_text()
        self.assertLess(text.index("docker inspect --format '{{.Id}}' hp-agent"),
                        text.index('docker rename "$old_id" "$rollback"'))
        self.assertIn("[[ $(docker inspect --format '{{.State.Running}}' \"$old_id\") == false ]]", text)
        self.assertIn("[[ $(docker inspect --format '{{.State.Pid}}' \"$old_id\") == 0 ]]", text)

    def test_only_terminal_legacy_needs_input_is_exempted_from_quiesce_check(self):
        text = self.script.read_text()
        active_check = text.index("select count(*) from agent_jobs AS job")
        allowed_legacy = text.index("job.stage='needs_input'", active_check)
        self.assertLess(active_check, allowed_legacy)
        self.assertIn("effect.state='admitted'", text[active_check:])
        self.assertIn("notification.state in ('sending','ambiguous')", text[active_check:])

    def write_legacy_database(self, path, *, partial_recovery=False):
        connection = sqlite3.connect(path)
        connection.executescript('''
CREATE TABLE requests(site_id TEXT, request_id TEXT, revision INTEGER, state TEXT);
CREATE TABLE agent_jobs(site_id TEXT, request_id TEXT, revision INTEGER, stage TEXT, data TEXT, token TEXT, error TEXT);
CREATE TABLE agent_effects(site_id TEXT, request_id TEXT, revision INTEGER, state TEXT);
CREATE TABLE notifications(site_id TEXT, request_id TEXT, revision INTEGER, state TEXT);
''')
        if partial_recovery:
            connection.execute('CREATE TABLE agent_job_runtime(stage TEXT, deadline_at REAL)')
        connection.commit()
        connection.close()

    def run_quiesce_preflight(self, database):
        text = self.script.read_text()
        python = text.split("python3 - \"$state_db\" <<'PY'\n", 1)[1].split('\nPY\n', 1)[0]
        with tempfile.TemporaryDirectory() as directory:
            check = Path(directory) / 'quiesce.py'
            check.write_text(python)
            return subprocess.run(['python3', check, database], capture_output=True, text=True)

    def test_complete_legacy_database_without_recovery_tables_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'agent.sqlite3'
            self.write_legacy_database(database)
            result = self.run_quiesce_preflight(database)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_incidents_table_is_rejected_for_partial_recovery_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'agent.sqlite3'
            self.write_legacy_database(database, partial_recovery=True)
            result = self.run_quiesce_preflight(database)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unknown_preincident_schema', result.stderr)

    def test_legacy_schema_still_rejects_an_admitted_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'agent.sqlite3'
            self.write_legacy_database(database)
            connection = sqlite3.connect(database)
            connection.execute("INSERT INTO agent_effects VALUES ('site', 'request', 1, 'admitted')")
            connection.commit()
            connection.close()
            result = self.run_quiesce_preflight(database)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('active_or_unresolved_state', result.stderr)


if __name__ == '__main__':
    unittest.main()
