#!/usr/bin/env bash
set -euo pipefail
require_no_signatures() {
  local signatures
  # --output is uppercase -O; lowercase -o is a byte offset. Keep the probe
  # separate so a failed inspection cannot be mistaken for an empty result.
  signatures=$(wipefs --no-act --noheadings --output TYPE "$1")
  [[ -z "$signatures" ]]
}

prepare_volume() {
volume_id=${1:?exact task-owned EBS volume ID required}
[[ "$volume_id" =~ ^vol-[a-f0-9]+$ ]]
[[ $(id -u) == 0 ]]
serial=${volume_id//-/}
device=""
for candidate in /dev/nvme*n1; do
  [[ -b "$candidate" ]] || continue
  if [[ $(lsblk -dn -o SERIAL "$candidate" | tr -d ' ') == "$serial" ]]; then
    [[ -z "$device" ]]
    device=$candidate
  fi
done
[[ -n "$device" ]]
if findmnt -rn -S "$device" >/dev/null; then
  [[ $(findmnt -rn -S "$device" -o TARGET) == /srv/hp-agent ]]
else
  signature=$(blkid -p -s TYPE -o value "$device" || true)
  if [[ -z "$signature" ]]; then
    # Only the explicitly supplied, new task volume may be initialized.
    [[ $(blockdev --getsize64 "$device") == 21474836480 ]]
    [[ -z $(lsblk -n -o MOUNTPOINTS "$device" | tr -d '[:space:]') ]]
    require_no_signatures "$device"
    mkfs.ext4 -L hp-agent-data "$device"
  else
    [[ "$signature" == ext4 ]]
    [[ $(blkid -s LABEL -o value "$device") == hp-agent-data ]]
  fi
  install -d -m 700 /srv/hp-agent
  disk_uuid=$(blkid -s UUID -o value "$device")
  if ! findmnt --fstab -rn -S "UUID=$disk_uuid" >/dev/null; then
    printf 'UUID=%s /srv/hp-agent ext4 defaults,nofail 0 2\n' "$disk_uuid" >> /etc/fstab
  fi
  mount /srv/hp-agent
fi
chmod 700 /srv/hp-agent
findmnt -rn -o SOURCE,TARGET,FSTYPE /srv/hp-agent
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
  prepare_volume "$@"
fi
