"""Pipe this file into `codex sandbox -c 'sandbox_mode="read-only"' python3 -`."""

from pathlib import Path
import errno
import json
import socket
import tempfile

try:
    result = {"read": bool(Path("/etc/os-release").read_bytes())}
except OSError:
    result = {"read": False}
# Use the user's home: /tmp may be intentionally writable in read-only mode.
try:
    with tempfile.NamedTemporaryFile(prefix=".onboarding-probe-", dir=Path.home()):
        result["writeBlocked"] = False
except OSError as error:
    result["writeBlocked"] = error.errno in (errno.EROFS, errno.EACCES, errno.EPERM)

try:
    with socket.create_connection(("1.1.1.1", 443), timeout=3):
        result["networkBlocked"] = False
except OSError as error:
    # A timeout or DNS failure is not proof that sandbox policy blocked access.
    result["networkBlocked"] = error.errno in (errno.EACCES, errno.EPERM)

print(json.dumps(result))
raise SystemExit(0 if all(result.values()) else 1)
