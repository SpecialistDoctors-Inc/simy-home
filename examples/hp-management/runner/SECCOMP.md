# Codex inner sandbox in Docker

`seccomp-codex.json` is derived from the [Moby default profile](https://github.com/moby/profiles/blob/4b8214fc4971e06172938a1f1554ccff6647ee80/seccomp/default.json),
commit `4b8214fc4971e06172938a1f1554ccff6647ee80`, original SHA256
`6416b47770785a41ac59073cdc77d9fe98517df2799dc83ef207e622de3053f6`.
The upstream Apache 2.0 license is retained in `seccomp-codex.LICENSE`.

The default profile blocks the bundled Codex 0.166.0 bubblewrap helper from
creating its filesystem/network sandbox. This modified copy preserves the
upstream rules and default deny action and adds only the observed setup calls:

- `clone` with flags exactly `0x78020011` on amd64/arm64: a new user, mount,
  IPC, PID and network namespace plus SIGCHLD. Other namespace combinations
  remain subject to the upstream profile.
- `unshare` with exactly `CLONE_NEWUSER` for bubblewrap's final privilege drop.
- `mount` with eleven exact flag combinations observed during setup, including
  read-only remounts, a writable nosuid/nodev bind remount for a persistent
  workspace volume, tmpfs and private/slave propagation.
- `pivot_root`, and `umount2` with exactly `MNT_DETACH`, to replace and detach
  the old root inside the new namespace.

These calls still require kernel namespace/capability permission. The outer
container keeps `cap_drop: ALL`, only CHOWN/SETUID/SETGID for its controller,
`no-new-privileges`, a read-only root, and private provider volumes. It does not
receive SYS_ADMIN, host namespaces or a Docker socket. Codex keeps its
workspace-write or read-only inner sandbox and disabled command network.
Do not replace this profile with `unconfined` or use a privileged container.

`test_codex_sandbox.py` invokes the actual packaged Codex sandbox without model
credentials. It verifies a workspace write, denies a write to a world-writable
sibling, denies reading the controller's private fixture and requires a network
operation to fail with EPERM/EACCES. The separate controller smoke uses fake
model executables to verify process ownership and result/review receipt replay.
CI exercises both on the packaged image. If the host disallows unprivileged
user namespaces, stop and use a compatible host; do not change shared host
security settings from the service.
