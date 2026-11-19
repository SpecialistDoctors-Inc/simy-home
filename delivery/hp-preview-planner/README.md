# Production preview planner change

The shared homepage editor queues edit jobs for the production tetsuo worker. `codex-runner/server.mjs` calls the edit branch of `codex-runner/worker.mjs`, which imports `preview-editor/planner.mjs`. This patch covers that module and its tests. It preserves the request schema, the edit operation allowlist, image validation, and retry and inspection behavior.

| Item | SHA-256 |
| --- | --- |
| Installed planner before this change | `03bf8dfc57693d259ef4b2c08735efaedc912a5d4b48f4d343de4f15b4dfdb68` |
| Planner after this change | `73aea163965c6dfe53ccfdcc9d42b76786808b27be970630ac1f0af7b984b2dd` |

Apply the patch with `patch -p1` in a staging directory containing the installed `preview-editor` sources. Verify both checksums and run `node --test preview-editor/planner.test.mjs` using the runner's Node runtime. Save the current source for rollback, replace the validated planner file atomically, and restart only `simy-hp-codex-tetsuo.service`. Verify the new process and exercise the public preview through the production form. The Sites gateway and queue configuration use the existing contract.

## Contextual structure and attachment inspection

After the grounding release above, apply `contextual-editing.patch` against planner SHA-256
`73aea163965c6dfe53ccfdcc9d42b76786808b27be970630ac1f0af7b984b2dd`.
The resulting planner SHA-256 is `c3d894f47d6c1542843afdd2b0a174c78d7003dbb9b0655ee29f36af35597799`.

Release the static editor first, then apply the patch with `patch -p1` and follow the
same worker staging and validation steps. The existing one-shot `inspect` response
accepts a current attachment ID in its question field. The new editor returns that
attachment's thumbnail under the existing image limit. A cached editor may return
no thumbnail, which the worker must treat as an uninspected attachment.

## Remaining site and wording assumptions

Apply `grounded-fields.patch` after `contextual-editing.patch`.
The starting planner SHA-256 is `c3d894f47d6c1542843afdd2b0a174c78d7003dbb9b0655ee29f36af35597799`.
The resulting planner SHA-256 is `be0b253d9ea7e85829f0b261658899b04a4e46098f43372b9db9a9b83699e56e`. Release the static editor first.
Read [the entry-point audit](audit.md) for source and publication coverage.
