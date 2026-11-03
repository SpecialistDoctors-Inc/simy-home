#!/usr/bin/env bash
set -euo pipefail
image=${1:?immutable ECR image digest required}
region=${2:?AWS region required}
instance_id=${3:?exact instance ID required}
source_sha=${4:?source revision required}
manifest_sha=${5:?operator-pinned release manifest hash required}
[[ $(id -u) == 0 ]]
[[ "$image" =~ ^209300895845\.dkr\.ecr\.ap-northeast-1\.amazonaws\.com/simy-hp-agent@sha256:[a-f0-9]{64}$ ]]
[[ "$region" == ap-northeast-1 && "$instance_id" =~ ^i-[a-f0-9]+$ && "$source_sha" =~ ^[a-f0-9]{40}$ ]]
repo_root=$(cd "$(dirname "$0")/../.." && pwd)
verify=(python3 "$repo_root/infra/hp-agent/verify-release.py" --root "$repo_root" \
  --manifest "$repo_root/release-manifest.json" --sha256 "$manifest_sha" --source "$source_sha" --image "$image")
findmnt -rn /srv/hp-agent >/dev/null
"${verify[@]}" --migration-marker /srv/hp-agent/migration-verified.json
if docker container inspect hp-agent >/dev/null 2>&1; then
  echo 'Existing service requires an explicit owned-process upgrade; refusing replacement.' >&2
  exit 1
fi
runner="$repo_root/examples/hp-management/runner"
install -d -m 700 /opt/hp-agent-runtime
install -m 600 "$runner/seccomp-codex.json" /opt/hp-agent-runtime/seccomp-codex.json
install -m 600 "$runner/apparmor-codex.profile" /etc/apparmor.d/simy-hp-codex
install -m 700 "$repo_root/infra/hp-agent/health.py" /opt/hp-agent-runtime/health.py
apparmor_parser -r -W /etc/apparmor.d/simy-hp-codex

# A dedicated container network prevents access to instance-role credentials
# and other private services. Permit only the VPC resolver before private CIDRs.
if docker network inspect hp-agent >/dev/null 2>&1; then
  [[ $(docker network inspect hp-agent --format '{{(index .IPAM.Config 0).Subnet}}') == 172.30.250.0/24 ]]
else
  docker network create --driver bridge --subnet 172.30.250.0/24 hp-agent
fi

cat > /opt/hp-agent-runtime/restore-egress.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
iptables -N DOCKER-USER 2>/dev/null || true
iptables -N HP_AGENT_EGRESS 2>/dev/null || true
# Runs before Docker starts, or during first installation with no agent present.
iptables -F HP_AGENT_EGRESS
iptables -A HP_AGENT_EGRESS -d 172.31.0.2/32 -p udp --dport 53 -j RETURN
iptables -A HP_AGENT_EGRESS -d 172.31.0.2/32 -p tcp --dport 53 -j RETURN
for cidr in 169.254.0.0/16 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16; do
  iptables -A HP_AGENT_EGRESS -d "$cidr" -j REJECT
done
iptables -A HP_AGENT_EGRESS -j RETURN
iptables -C DOCKER-USER -s 172.30.250.0/24 -j HP_AGENT_EGRESS 2>/dev/null || iptables -I DOCKER-USER 1 -s 172.30.250.0/24 -j HP_AGENT_EGRESS
# Host-local services use INPUT, not DOCKER-USER. No host port is needed.
iptables -C INPUT -s 172.30.250.0/24 -j REJECT 2>/dev/null || iptables -I INPUT 1 -s 172.30.250.0/24 -j REJECT
SH
chmod 700 /opt/hp-agent-runtime/restore-egress.sh
/opt/hp-agent-runtime/restore-egress.sh
cat > /etc/systemd/system/hp-agent-egress.service <<'UNIT'
[Unit]
Description=HP agent dedicated container egress restrictions
After=apparmor.service
Before=docker.service
RequiresMountsFor=/srv/hp-agent
[Service]
Type=oneshot
ExecStart=/opt/hp-agent-runtime/restore-egress.sh
RemainAfterExit=yes
[Install]
RequiredBy=docker.service
UNIT

registry=${image%%/*}
aws ecr get-login-password --region "$region" | docker login --username AWS --password-stdin "$registry"
docker pull "$image"
docker logout "$registry"
# Inspect immutable image payload with no network or credential mounts.
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
  --entrypoint python3 "$image" -c 'import hashlib,json,pathlib; p=pathlib.Path("/opt/hp-agent"); print(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [*p.glob("*.py"),p/"requirements.txt"]},sort_keys=True))' \
  > /opt/hp-agent-runtime/image-hashes.json
"${verify[@]}" --image-hashes /opt/hp-agent-runtime/image-hashes.json \
  --migration-marker /srv/hp-agent/migration-verified.json
docker create --name hp-agent --restart unless-stopped --init \
  --label codex.task=hp-always-on --label "codex.source=$source_sha" \
  --network hp-agent --memory 3g --cpus 1.5 --pids-limit 256 \
  --cap-drop ALL --cap-add CHOWN --cap-add SETUID --cap-add SETGID \
  --security-opt no-new-privileges \
  --security-opt seccomp=/opt/hp-agent-runtime/seccomp-codex.json \
  --security-opt apparmor=simy-hp-codex --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m \
  --mount type=bind,source=/srv/hp-agent/control,target=/control,readonly \
  --mount type=bind,source=/srv/hp-agent/state,target=/state \
  --mount type=bind,source=/srv/hp-agent/work,target=/work \
  --mount type=bind,source=/srv/hp-agent/codex-auth,target=/home/node/.codex \
  --log-driver awslogs --log-opt awslogs-region="$region" \
  --log-opt mode=non-blocking --log-opt max-buffer-size=4m \
  --log-opt awslogs-group=/simy/hp-agent --log-opt "awslogs-stream=$instance_id" \
  "$image" --config /control/config.json --db /state/agent.sqlite3

cat > /etc/systemd/system/hp-agent-health.service <<UNIT
[Unit]
Description=Publish HP agent health metric
After=docker.service network-online.target
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/hp-agent-runtime/health.py $region $instance_id
TimeoutStartSec=0
UNIT
cat > /etc/systemd/system/hp-agent-health.timer <<'UNIT'
[Unit]
Description=Check HP agent health every minute
[Timer]
OnBootSec=120
OnUnitActiveSec=60
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable hp-agent-egress.service
systemctl enable --now hp-agent-health.timer
docker start hp-agent
