#!/usr/bin/env bash
# Replace a stopped, identified controller after a deliberate host reboot.
# This helper never stops, removes, or signals a container or process.
set -euo pipefail

old_id=${1:?exact stopped container ID required}
old_source=${2:?old source SHA required}
old_manifest=${3:?old migration manifest SHA required}
old_image=${4:?old image digest required}
new_image=${5:?new immutable image digest required}
region=${6:?AWS region required}
instance_id=${7:?instance ID required}
new_source=${8:?new source SHA required}
new_manifest=${9:?new manifest SHA required}

image_pattern='^209300895845\.dkr\.ecr\.ap-northeast-1\.amazonaws\.com/simy-hp-agent@sha256:[a-f0-9]{64}$'
[[ $(id -u) == 0 ]]
[[ "$old_id" =~ ^[a-f0-9]{64}$ && "$old_source" =~ ^[a-f0-9]{40}$ && "$new_source" =~ ^[a-f0-9]{40}$ ]]
[[ "$old_manifest" =~ ^[a-f0-9]{64}$ && "$new_manifest" =~ ^[a-f0-9]{64}$ && "$old_image" =~ $image_pattern && "$new_image" =~ $image_pattern ]]
[[ "$old_source" != "$new_source" && "$region" == ap-northeast-1 && "$instance_id" =~ ^i-[a-f0-9]+$ ]]

repo_root=$(cd "$(dirname "$0")/../.." && pwd -P)
state_db=/srv/hp-agent/state/agent.sqlite3
marker=/srv/hp-agent/migration-verified.json
suffix=${new_source:0:8}
receipt=/srv/hp-agent/upgrade-recovery-${suffix}.json
rollback=hp-agent-rollback-${old_source:0:8}
previous_marker=/srv/hp-agent/migration-verified.previous-${old_source:0:8}.json
phase=preflight

write_receipt() {
  local result=${1:?result required}
  local code=${2:-0}
  local temporary=${receipt}.tmp
  umask 077
  printf '{"result":"%s","phase":"%s","exit_code":%s,"old_container_id":"%s","old_source":"%s","new_source":"%s","rollback_container":"%s"}\n' \
    "$result" "$phase" "$code" "$old_id" "$old_source" "$new_source" "$rollback" > "$temporary"
  chmod 600 "$temporary"
  mv "$temporary" "$receipt"
}

trap 'code=$?; write_receipt failed "$code"; exit "$code"' ERR
[[ ! -e "$receipt" ]] || { echo "existing upgrade receipt requires explicit recovery review" >&2; exit 1; }
mountpoint -q /srv/hp-agent
[[ -f "$marker" && ! -L "$marker" && -f "$state_db" && ! -L "$state_db" ]]

# Verify the candidate release before changing the currently recorded release.
python3 "$repo_root/infra/hp-agent/verify-release.py" \
  --root "$repo_root" --manifest "$repo_root/release-manifest.json" \
  --sha256 "$new_manifest" --source "$new_source" --image "$new_image"

# The old restore proof is immutable evidence. Verify its original shape and
# bind it to the exact old release supplied by the operator before preserving it.
python3 - "$repo_root/infra/hp-agent/verify-release.py" "$marker" "$old_manifest" "$old_source" "$old_image" <<'PY'
import importlib.util
import sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('verify_release', Path(sys.argv[1]))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
proof = module.verify_migration_shape(Path(sys.argv[2]))
expected = {'manifest_sha256': sys.argv[3], 'source_sha': sys.argv[4], 'image': sys.argv[5]}
if any(proof[key] != value for key, value in expected.items()):
    raise ValueError('old_migration_release_mismatch')
PY

# No current worker, uncertain provider effect, mail outcome, or operator
# incident may be carried across an in-place runtime upgrade.
python3 - "$state_db" <<'PY'
import sqlite3
import sys
database = sqlite3.connect(f'file:{sys.argv[1]}?mode=ro', uri=True)
try:
    if database.execute('pragma quick_check').fetchone()[0] != 'ok':
        raise RuntimeError('database_integrity_failed')
    tables = {row[0] for row in database.execute(
        "select name from sqlite_master where type='table'"
    )}
    required_legacy_columns = {
        'requests': {'site_id', 'request_id', 'revision', 'state'},
        'agent_jobs': {'site_id', 'request_id', 'revision', 'stage', 'data', 'token', 'error'},
        'agent_effects': {'site_id', 'request_id', 'revision', 'state'},
        'notifications': {'site_id', 'request_id', 'revision', 'state'},
    }
    recovery_tables = {'agent_job_runtime', 'agent_incidents', 'agent_service_runtime'}
    def columns(table):
        return {row[1] for row in database.execute(f'pragma table_info({table})')}
    if 'agent_incidents' not in tables:
        # The b92 controller had none of the recovery tables. Do not mistake a
        # damaged or half-upgraded database for that known, migration-safe shape.
        if (tables & recovery_tables or
                any(not expected <= columns(table)
                    for table, expected in required_legacy_columns.items())):
            raise RuntimeError('unknown_preincident_schema')
        legacy_without_incidents = True
    else:
        required_recovery_columns = {
            'agent_job_runtime': {'site_id', 'request_id', 'revision', 'stage', 'deadline_at'},
            'agent_incidents': {'site_id', 'request_id', 'revision', 'resolved_at'},
            'agent_service_runtime': {'id', 'failures', 'retry_at', 'paused'},
        }
        if (not recovery_tables <= tables or
                any(not expected <= columns(table)
                    for table, expected in required_recovery_columns.items())):
            raise RuntimeError('invalid_recovery_schema')
        legacy_without_incidents = False
    checks = [
        "select count(*) from agent_effects where state='admitted'",
        "select count(*) from notifications where state in ('sending','ambiguous')",
        '''select count(*) from agent_jobs AS job
           where job.stage not in ('awaiting_approval','stopped')
             and not (job.stage='needs_input' and exists (
               select 1 from requests AS request
               where request.site_id=job.site_id and request.request_id=job.request_id
                 and request.revision=job.revision
                 and request.state in ('superseded','cancelled','revoked')
             ) and not exists (
               select 1 from agent_effects AS effect
               where effect.site_id=job.site_id and effect.request_id=job.request_id
                 and effect.revision=job.revision and effect.state='admitted'
             ) and not exists (
               select 1 from notifications AS notification
               where notification.site_id=job.site_id and notification.request_id=job.request_id
                 and notification.revision=job.revision
                 and notification.state in ('sending','ambiguous')
             ))''',
    ]
    if not legacy_without_incidents:
        checks.append('''select count(*) from agent_incidents AS incident
           where incident.resolved_at is null
             and not exists (
               select 1 from requests AS request
               where request.site_id=incident.site_id and request.request_id=incident.request_id
                 and request.revision=incident.revision
                 and request.state in ('superseded','cancelled','revoked')
             )''')
    if any(database.execute(query).fetchone()[0] for query in checks):
        raise RuntimeError('active_or_unresolved_state')
finally:
    database.close()
PY

# Identify the one current service by its full Docker ID, expected name and
# release label. The post-reboot service must be fully stopped and unable to
# automatically restart before any mutation.
[[ $(docker inspect --format '{{.Id}}' hp-agent) == "$old_id" ]]
[[ $(docker inspect --format '{{.Name}}' "$old_id") == /hp-agent ]]
[[ $(docker inspect --format '{{index .Config.Labels "codex.task"}}' "$old_id") == hp-always-on ]]
[[ $(docker inspect --format '{{index .Config.Labels "codex.source"}}' "$old_id") == "$old_source" ]]
[[ $(docker inspect --format '{{.State.Running}}' "$old_id") == false ]]
[[ $(docker inspect --format '{{.State.Pid}}' "$old_id") == 0 ]]
[[ $(docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' "$old_id") == no ]]
[[ ! -e "$previous_marker" ]]
! docker inspect "$rollback" >/dev/null 2>&1

# From here, failure is intentionally left for an operator to reconcile from
# the receipt. The old container is retained under its rollback name.
phase=rename_old_container
docker rename "$old_id" "$rollback"

phase=preserve_old_marker
install -m 600 "$marker" "$previous_marker"

phase=bind_existing_state_to_new_release
python3 - "$marker" "$new_manifest" "$new_source" "$new_image" <<'PY'
import json
import os
import sys
from pathlib import Path
marker = Path(sys.argv[1])
proof = json.loads(marker.read_text())
proof.update({'manifest_sha256': sys.argv[2], 'source_sha': sys.argv[3], 'image': sys.argv[4]})
temporary = marker.with_name(marker.name + '.upgrade-tmp')
temporary.write_text(json.dumps(proof, sort_keys=True) + '\n')
os.chmod(temporary, 0o600)
temporary.replace(marker)
PY

phase=create_new_container
bash "$repo_root/infra/hp-agent/install-runtime.sh" "$new_image" "$region" "$instance_id" "$new_source" "$new_manifest"

phase=complete
write_receipt completed 0
