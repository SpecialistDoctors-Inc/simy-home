from datetime import datetime, timezone, timedelta
import unittest
from health import healthy


class HealthTest(unittest.TestCase):
    now = datetime(2026, 11, 3, 3, 0, tzinfo=timezone.utc)

    def event(self, stage='idle', age=0, extra=''):
        return (self.now-timedelta(seconds=age)).isoformat()+' {"event":"poll_completed","stage":"'+stage+'"'+extra+'}'

    def test_completed_poll_and_long_coding_are_healthy(self):
        self.assertTrue(healthy(True, self.event(), self.now))
        self.assertTrue(healthy(True, self.event('coding', 1000), self.now))

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


if __name__ == '__main__':
    unittest.main()
