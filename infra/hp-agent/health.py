#!/usr/bin/env python3
"""Send only service health, never request content or credentials, to CloudWatch."""
from datetime import datetime, timezone
import json
import subprocess
import sys


def healthy(running, log, now):
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
    return (0 <= (now - stamp).total_seconds() <= 1800
            and not event.get('error')
            and event.get('stage') in {
                'idle', 'coding', 'candidate', 'ci', 'merge', 'deploy',
                'results', 'notification', 'awaiting_approval', 'stopped'})


def main():
    region, instance_id = sys.argv[1:]
    status = subprocess.run(['docker', 'inspect', '--format', '{{.State.Running}}', 'hp-agent'],
                            capture_output=True, text=True)
    logs = subprocess.run(['docker', 'logs', '--since', '31m', '--tail', '200', '--timestamps', 'hp-agent'],
                          capture_output=True, text=True)
    ok = healthy(status.returncode == 0 and status.stdout.strip() == 'true',
                 logs.stdout if logs.returncode == 0 else '', datetime.now(timezone.utc))
    metric = [{'MetricName': 'Healthy', 'Dimensions': [{'Name': 'InstanceId', 'Value': instance_id}],
               'Value': int(ok), 'Unit': 'Count'}]
    # AWS CLI applies its own request timeouts; this script never kills a process.
    subprocess.run(['aws', 'cloudwatch', 'put-metric-data', '--region', region,
                    '--namespace', 'SIMY/HPAgent', '--metric-data', json.dumps(metric),
                    '--cli-connect-timeout', '5', '--cli-read-timeout', '10'], check=True)
    print(json.dumps({'healthy': ok}))


if __name__ == '__main__':
    main()
