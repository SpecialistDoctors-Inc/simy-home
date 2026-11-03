#!/usr/bin/env python3
"""Send only service health, never request content or credentials, to CloudWatch."""
from datetime import datetime, timezone
import json
import sqlite3
import subprocess
import sys


UNRESOLVED_STAGES = (
    'needs_input',
    'worker_interrupted',
    'provider_reconciliation_required',
    'retry_exhausted',
)


def unresolved_work(path, now):
    """Return whether durable state requires an operator, without exposing it.

    The controller can keep polling unrelated work after an interrupted request.
    A recent ``idle`` poll therefore cannot be the only health signal. The
    agent owns the schema; an unreadable state database is fail-closed.
    """
    try:
        connection = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        try:
            incident = connection.execute(
                'SELECT 1 FROM agent_incidents WHERE resolved_at IS NULL LIMIT 1'
            ).fetchone()
            stage = connection.execute(
                'SELECT 1 FROM agent_jobs WHERE stage IN (?,?,?,?) LIMIT 1',
                UNRESOLVED_STAGES,
            ).fetchone()
            overdue = connection.execute(
                """SELECT 1 FROM agent_job_runtime
                   WHERE deadline_at <= ?
                     AND stage NOT IN ('queued', 'awaiting_approval', 'stopped')
                   LIMIT 1""",
                (now.timestamp(),),
            ).fetchone()
            return bool(incident or stage or overdue)
        finally:
            connection.close()
    except (OSError, sqlite3.Error):
        return True


def healthy(running, log, now, state_path=None):
    if not running:
        return False
    latest = None
    for line in log.splitlines():
        try:
            stamp, payload = line.split(' ', 1)
            event = json.loads(payload)
            if not isinstance(event, dict):
                continue
            if event.get('event') != 'poll_completed':
                continue
            observed = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
            if observed.tzinfo is None:
                continue
            if latest is None or observed >= latest[0]:
                latest = observed, event
        except (ValueError, TypeError):
            continue
    if latest is None:
        return False
    stamp, event = latest
    # A coding/review call may legitimately occupy one tick for several minutes.
    heartbeat_ok = (0 <= (now - stamp).total_seconds() <= 1800
                    and not event.get('error')
                    and event.get('stage') in {
                        'idle', 'coding', 'candidate', 'ci', 'merge', 'deploy',
                        'results', 'notification', 'verifying', 'reviewing',
                        'awaiting_approval', 'stopped'})
    if not heartbeat_ok:
        return False
    return state_path is None or not unresolved_work(state_path, now)


def main():
    region, instance_id = sys.argv[1:]
    status = subprocess.run(['docker', 'inspect', '--format', '{{.State.Running}}', 'hp-agent'],
                            capture_output=True, text=True)
    logs = subprocess.run(['docker', 'logs', '--since', '31m', '--tail', '200', '--timestamps', 'hp-agent'],
                          capture_output=True, text=True)
    ok = healthy(status.returncode == 0 and status.stdout.strip() == 'true',
                 logs.stdout if logs.returncode == 0 else '', datetime.now(timezone.utc),
                 '/srv/hp-agent/state/agent.sqlite3')
    metric = [{'MetricName': 'Healthy', 'Dimensions': [{'Name': 'InstanceId', 'Value': instance_id}],
               'Value': int(ok), 'Unit': 'Count'}]
    # AWS CLI applies its own request timeouts; this script never kills a process.
    subprocess.run(['aws', 'cloudwatch', 'put-metric-data', '--region', region,
                    '--namespace', 'SIMY/HPAgent', '--metric-data', json.dumps(metric),
                    '--cli-connect-timeout', '5', '--cli-read-timeout', '10'], check=True)
    print(json.dumps({'healthy': ok}))


if __name__ == '__main__':
    main()
