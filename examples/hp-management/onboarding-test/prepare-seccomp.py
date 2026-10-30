#!/usr/bin/env python3
"""Create the pinned Docker profile used by the isolated onboarding test."""

import hashlib
import json
from pathlib import Path
import sys
import urllib.request

SOURCE = (
    "https://raw.githubusercontent.com/moby/profiles/"
    "4b8214fc4971e06172938a1f1554ccff6647ee80/seccomp/default.json"
)
SHA256 = "6416b47770785a41ac59073cdc77d9fe98517df2799dc83ef207e622de3053f6"


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: prepare-seccomp.py OUTPUT.json")
    destination = Path(sys.argv[1])
    if destination.exists():
        raise SystemExit("Refusing to overwrite an existing profile")
    with urllib.request.urlopen(SOURCE, timeout=30) as response:
        raw = response.read()
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise SystemExit("Upstream profile checksum mismatch")
    profile = json.loads(raw)
    # Bubblewrap needs nested namespaces and mounts. Keep the default deny
    # policy, including clone3's ENOSYS fallback and unrelated syscall rules.
    profile["syscalls"].append({
        "names": ["clone", "unshare", "mount", "umount2", "pivot_root", "setns"],
        "action": "SCMP_ACT_ALLOW",
    })
    with destination.open("x") as output:
        json.dump(profile, output, indent=2)
        output.write("\n")


if __name__ == "__main__":
    main()
