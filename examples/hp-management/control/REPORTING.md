# Local-editor workbook reporting v2

The completed operation remains owned by the durable control ledger. Workbook
rows report facts and progress; they do not grant repository, recipient, approval,
or publication authority.

For `save_draft`, `submit_preview`, and `publish`, reporting freezes one immutable
Requests row and its Events result together in the durable outbox. Requests uses
`request_id = operation UUID`, `revision = 1`, and the server-bound site ID. These
v2 operation identifiers are distinct from legacy intake requests. A workspace
open has an Event only. Requests appears before its Events result because each
append is separately admitted and read back before the next effect.

Existing layouts stay unchanged: Requests has its exact 14-column header at row
4 and appends start at `Requests!A5:N`; Events has its exact nine-column header at
row 4 and appends start at `Events!A5:I`. Writes use RAW values and insert new
rows. Neither a prior request nor a shared status cell is overwritten.

Requests outcome uses the stored operation summary when present, otherwise a
truthful operation label. The target is the trusted development URL for draft or
preview, and the production URL for publication. Timing fields explicitly say
`確認・公開操作に従う`, `なし`, and `Asia/Tokyo`. Both asset/dependency fields say
`この操作の提出ファイルを参照`; this is not a rights-clearance claim. Acceptance
records the exact saved ZIP/commit or verified preview/publication artifact.
Requester is the verified `google-sub:<subject>`; the notification reference comes
from trusted site configuration or a stable server-owned site reference.

The only Requests states are `local_draft`, `local_preview`, and
`local_publication`. Reporting never writes `ready_for_dev`, changes a legacy
proposal, or manufactures customer approval. The legacy runner discovers
`ready_for_dev` events; these v2 rows are informational projections and are not
legacy execution requests. Events use the stable key
`hp-control:<operation UUID>:<kind>` with result kinds `workspace_ready`,
`draft_saved`, `dev_preview_ready`, and `published`.

The Requests `(request_id, revision)` key must be unique. Duplicate or modified
matching rows fail closed. A response lost after an admitted append allows only
readback by that frozen key and exact row; an absent result never authorizes a
resend. The shared fenced site lease blocks conflicting work until the prior
effect is reconciled. Cancellation or revoked membership allow reads of earlier
admitted effects but no new rows or sends.

Only preview-ready and published results can send mail, and only when trusted
configuration explicitly enables it. The same outbox freezes the exact envelope
and HP-NOTICE key before send. Provider acceptance/SENT readback remains separate
from recipient inbox delivery, which is reported as unknown. Configuration or
row mismatches require operator attention without claiming reporting succeeded.
