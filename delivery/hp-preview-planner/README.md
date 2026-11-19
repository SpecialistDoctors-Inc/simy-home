# Production preview planner change

The shared homepage editor queues edit jobs for the production tetsuo worker. `codex-runner/server.mjs` calls the edit branch of `codex-runner/worker.mjs`, which imports `preview-editor/planner.mjs`. This patch covers that module and its tests. It preserves the request schema, the edit operation allowlist, image validation, and retry and inspection behavior.

| Item | SHA-256 |
| --- | --- |
| Installed planner before this change | `03bf8dfc57693d259ef4b2c08735efaedc912a5d4b48f4d343de4f15b4dfdb68` |
| Planner after this change | `1f21e062847fece59c2d79cb502cc70cbb0fd3e16381305746a398703746de7b` |

Apply the patch with `patch -p1` in a staging directory containing the installed `preview-editor` sources. Verify both checksums and run `node --test preview-editor/planner.test.mjs` using the runner's Node runtime. Save the current source for rollback, replace the validated planner file atomically, and restart only `simy-hp-codex-tetsuo.service`. Verify the new process and exercise the public preview through the production form. The Sites gateway and queue configuration use the existing contract.
