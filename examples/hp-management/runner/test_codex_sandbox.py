"""Exercise the packaged Codex sandbox without a model, credentials or providers."""
import errno
import json
import os
from pathlib import Path
import sys
import tempfile

from codex_worker import run_owned


def main():
    if sys.platform != 'linux' or os.getuid() != 0:
        raise SystemExit('requires isolated Linux root controller')
    if os.environ.get('EXPECT_APPARMOR_PROFILE'):
        profile = Path('/proc/self/attr/current').read_text().strip()
        assert profile == os.environ['EXPECT_APPARMOR_PROFILE'] + ' (enforce)', profile
        print(json.dumps({'apparmor_profile': profile}), flush=True)
    root = Path(tempfile.mkdtemp(dir='/work'))
    root.chmod(0o711)
    workspace = root / 'workspace'
    workspace.mkdir(mode=0o755)
    os.chown(workspace, 1000, 1000)
    outside = root / 'outside'
    outside.mkdir(mode=0o777)
    outside.chmod(0o777)
    private = root / 'private'
    private.mkdir(mode=0o700)
    (private / 'provider-secret-fixture').write_text('not-a-real-secret')
    # The sibling is writable by this UID outside the sandbox. Failure to write
    # it inside therefore proves the inner filesystem policy, not just chmod.
    program = '''import errno, json, socket
from pathlib import Path
Path('allowed.txt').write_text('ok')
assert Path('allowed.txt').read_text() == 'ok'
try:
    Path(%r).write_text('unexpected')
except OSError as exc:
    assert exc.errno in (errno.EROFS, errno.EACCES, errno.EPERM), exc
else:
    raise AssertionError('outside write allowed')
try:
    Path(%r).read_text()
except OSError as exc:
    assert exc.errno in (errno.EACCES, errno.EPERM), exc
else:
    raise AssertionError('private provider file readable')
try:
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection.settimeout(1)
    connection.connect(('127.0.0.1', 9))
except OSError as exc:
    assert exc.errno in (errno.EPERM, errno.EACCES), exc
else:
    raise AssertionError('network permitted')
print(json.dumps({'workspace_write': True, 'outside_write_denied': True,
                  'provider_read_denied': True, 'network_denied': True}))
''' % (str(outside / 'forbidden.txt'), str(private / 'provider-secret-fixture'))
    env = {key: value for key, value in os.environ.items() if key in {'PATH', 'LANG', 'LC_ALL'}}
    env.update({'HOME': '/home/node', 'CODEX_HOME': '/home/node/.codex'})
    try:
        run_owned(['codex', 'sandbox', '-c', 'sandbox_mode="workspace-write"',
                   '-c', 'sandbox_workspace_write.network_access=false', '--',
                   'python3', '-c', program], workspace, private / 'sandbox.log',
                  private / 'sandbox-process.json', env=env, user=1000, group=1000,
                  extra_groups=[], timeout=60)
    except RuntimeError:
        # This credential-free fixture runs in a disposable CI container.
        # Keep the actual sandbox failure visible after that container exits.
        print((private / 'sandbox.log').read_bytes()[-16384:].decode(errors='replace'), flush=True)
        raise
    assert not (outside / 'forbidden.txt').exists()
    print((private / 'sandbox.log').read_text())


if __name__ == '__main__':
    main()
