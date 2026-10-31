# 開発・運用向け: HP管理を設定する

この手順は、医院の Sheet の依頼を安全に開発・配信する担当者向けです。**SIMY のサービス、ログイン、API、登録台帳は現在必要ありません。** サイトへの書込み権限は、開発・運用担当だけが持ちます。

## 1. 用意するもの

- Codex と、開発・運用担当の ChatGPT アカウント
- 医院側とは別の Google Drive 接続。必要になったときだけ Gmail 接続
- 医院ごとの共有 Google Sheet
- 非公開のサイト設定、ローカル SQLite 台帳、対象リポジトリの専用 worktree
- GitHub と AWS の、既存の dev / 本番配信に必要な権限

Codex へのログインは [公式の Codex CLI ガイド](https://learn.chatgpt.com/docs/cli) と [認証ガイド](https://learn.chatgpt.com/docs/auth) に従います。ログイン済みかはプロフィールまたは `codex login status` で確認します。医院側の ChatGPT や Google アカウントを開発用端末で使い回さないでください。

## 2. 共有 Sheet を準備・接続する

医院ごとに専用のネイティブ Google Sheet を作り、医院と開発・運用担当の Google アカウントだけに共有します。リンクを知る全員への編集公開は使いません。

タブは次の3つです。

| タブ | 役割 |
| --- | --- |
| `ご利用ガイド` | 医院への説明と問い合わせ先 |
| `Requests` | 依頼の各 revision を残す台帳 |
| `Events` | 質問、回答、着手、プレビュー、結果を追記する履歴 |

`Requests` と `Events` は4行目を見出し、5行目からデータにします。接続ごとに見出し名を読戻してから使い、1〜3行目をデータとして処理しません。詳細な列と追記規約は [スプレッドシート契約](hp-management-spreadsheet-workflow.md) を参照します。

Sheet は依頼と監査記録の共有面であり、認可・ロック・本番承認の根拠ではありません。開発側は、専用 Sheet が指定の Google アカウントと共有されていることを確認しますが、セルの入力者を暗号学的に証明するものではありません。

## 3. スキルを固定版で導入する

開発環境には `hp-developer-delivery` を、配布元と **承認済み候補タグまたはコミットSHA** を指定して導入します。「最新版」だけで更新しないでください。スキルは、反復する作業の手順と参照資料をまとめる仕組みです。一般的な導入・利用は [公式の Skills & Plugins ガイド](https://learn.chatgpt.com/docs/skills-and-plugins) を参照できます。

```text
<配布元> の hp-developer-delivery スキルを、
固定版 <承認済み候補タグまたはコミットSHA> で導入してください。
references も導入し、既存の同名スキルは確認なしに上書きしないでください。
導入後は、依頼の実装、公開、メール送信を開始せず、認識できたスキル名だけを返してください。
```

Google Drive で `<共有Sheet URL>` を読み、シート名、3タブ、4行目の見出しを確認します。医院側と同じ Google 接続を使ったことは、権限分離の確認にはなりません。

接続できて読取りに成功しても、Codex の実行ポリシーが外部 Sheet への書込みを拒否することがあります。初回の `Requests` / `Events` 追記は、承認内容を確認できる通常の対話型セッションで1件だけ行い、固定IDで読戻します。`codex exec` などの非対話実行が書込み可能だと仮定しないでください。保護や承認設定を無効にして回避しません。

## 4. 非公開のサイト設定を作る

サイトごとに、Sheet とは別のアクセス制限された設定を用意します。少なくとも次を固定します。

| 項目 | 記入例 |
| --- | --- |
| `site_id` と `sheet_id` | `<site_id>` / `<Sheet ID>` |
| 受付者・通知先の参照 | `<requester_ref>` / `<notification_recipient_ref>` |
| リポジトリと編集可能な範囲 | `<owner/repository>` / `<許可するcontent path>` |
| 確認・公開先 | `<dev URL>` / `<production URL>` |
| 検証方法 | `<テストコマンドと確認項目>` |
| 配信参照 | `<GitHub Environment>` / `<AWS role・配信先の参照>` |
| 通知設定 | `<確認済みの宛先参照>` / `<Gmail接続の有効状態>` |

シートの URL、任意のセル、依頼本文からリポジトリ・AWS・メール宛先を決めません。トークン、AWS キー、GitHub 秘密情報、実メールアドレスを Sheet・公開リポジトリ・チャット記録に保存しないでください。

## 5. SQLite 台帳を初期化する

台帳は [`examples/hp-management/runner/ledger.py`](../examples/hp-management/runner/ledger.py) にあります。サイト設定、依頼の内容ハッシュ、claim、プレビュー証跡、成果物承認、通知の重複防止をローカル SQLite に記録します。外部の API 呼出しや SIMY ログインは行いません。

次はサンプル用の最小手順です。`HP_STATE_DIR` は専用の非同期・非共有ディレクトリを指す任意の変数で、`HOME` は使いません。作業開始前に、対象リポジトリのルールと現在の site 設定を読み直してください。

```sh
umask 077
HP_STATE_DIR="$PWD/.private/hp-management"
install -d -m 700 "$HP_STATE_DIR"
chmod 700 "$HP_STATE_DIR"
```

`config.json` は公開リポジトリへ入れません。下記の `sheet_id` と `recipient` は必ず実際の非公開値に置き換え、`requester_ref` と `notification_recipient_ref` は医院ごとの固定参照にします。

```json
{
  "site_id": "sample-clinic",
  "sheet_id": "REPLACE_WITH_GOOGLE_SHEET_ID",
  "repo": "SpecialistDoctors-Inc/simy-home",
  "content_path": "examples/sample-clinic/content/clinic.json",
  "dev_url": "https://sample-clinic-dev.simy.one",
  "prod_url": "https://sample-clinic.simy.one",
  "recipient": "operator@example.invalid",
  "requester_ref": "sample-clinic-requester",
  "notification_recipient_ref": "sample-clinic-notification-recipient"
}
```

保存後、台帳を作成または更新します。

```sh
python3 examples/hp-management/runner/ledger.py \
  --db "$HP_STATE_DIR/state.sqlite3" config < "$HP_STATE_DIR/config.json"
```

実際の Sheet の `Requests` 行を読戻してから、同じ14列を次の JSON に転記します。これは動作確認用の安全な例であり、行を推測して登録するためのものではありません。

```json
{
  "request": {
    "request_id": "11111111-1111-4111-8111-111111111111",
    "revision": 1,
    "site_id": "sample-clinic",
    "outcome": "お知らせを追加する",
    "target": "https://sample-clinic-dev.simy.one/#news",
    "effective_at": "",
    "expires_at": "",
    "timezone": "Asia/Tokyo",
    "assets_rights": "confirmed",
    "dependencies": "none",
    "acceptance": "dev確認ページのお知らせ欄に表示される",
    "requester_ref": "sample-clinic-requester",
    "notification_recipient_ref": "sample-clinic-notification-recipient",
    "proposal_state": "ready_for_dev"
  }
}
```

このファイルを `request.json` として保存した場合の取込、claim、状態確認、lease 延長は次のとおりです。claim の出力にある `token` を安全な一時変数へコピーしてから次の操作へ進みます。トークンを Sheet、Git、チャットログへ保存しません。

```sh
python3 examples/hp-management/runner/ledger.py \
  --db "$HP_STATE_DIR/state.sqlite3" ingest < "$HP_STATE_DIR/request.json"

python3 examples/hp-management/runner/ledger.py \
  --db "$HP_STATE_DIR/state.sqlite3" claim <<'JSON'
{"site_id":"sample-clinic","request_id":"11111111-1111-4111-8111-111111111111","revision":1,"owner":"<operator-id>","ttl":900}
JSON

python3 examples/hp-management/runner/ledger.py \
  --db "$HP_STATE_DIR/state.sqlite3" status <<'JSON'
{"site_id":"sample-clinic","request_id":"11111111-1111-4111-8111-111111111111","revision":1}
JSON

CLAIM_TOKEN='<claim の出力に含まれる token>'
python3 examples/hp-management/runner/ledger.py \
  --db "$HP_STATE_DIR/state.sqlite3" renew <<JSON
{"site_id":"sample-clinic","request_id":"11111111-1111-4111-8111-111111111111","revision":1,"token":"$CLAIM_TOKEN","ttl":900}
JSON
```

利用可能な操作は `config`、`ingest`、`claim`、`renew`、`release`、`status`、`cancel`、`revoke`、`preview`、`approve`、`publish`、通知 outbox 操作です。各操作は JSON を標準入力から受け取ります。台帳の操作が成功しても、Sheet の追記、dev 配信、本番公開、メール送信が済んだことにはなりません。

設定変更後は設定ハッシュが変わるため、既存依頼をそのまま実行せず、台帳が `config_drift` と判断することを確認してから再評価します。

## 6. 手動で依頼を dev まで進める

自動ポーリングは未完了です。運用担当が次の順で、1件ずつ明示して進めます。

1. Sheet の最新 `Requests` revision と `Events` を読み、対象・依頼者参照・通知先参照・受入条件を確認します。
2. 台帳に取り込み、依頼ID・revision・内容ハッシュを記録します。同じ内容は再処理せず、異なる revision は新しい依頼として扱います。
3. 台帳で claim を取得してから、非公開設定で許可された worktree・ブランチ・編集範囲だけを操作します。
4. 実装、テスト、dev 配信、表示確認を行います。`Events` に `claimed`、`test_result`、`dev_preview_ready` などの事実を追記します。
5. `dev_preview_ready` には依頼ID、revision、dev URL、実際の source SHA、artifact ID / hash、実行したテストを残します。

`ready_for_dev` を Sheet に追記しても、自動で開発や配信が始まるとは限りません。将来 Codex の Scheduled tasks を使う場合は、まず通常チャットでプロンプトを試し、初回の実行結果を確認してください。ローカルプロジェクトを扱う定期実行は、端末の電源とデスクトップアプリの稼働が必要です。[公式の Scheduled tasks ガイド](https://learn.chatgpt.com/docs/automations) を参照してください。

## 7. 本番を公開する

本番は dev の成功とは別の工程です。次の全てを照合します。

1. 医院の人が、確認した依頼ID・revision・source SHA・artifact ID・artifact hash を明示して承認したこと。
2. SQLite 台帳が、その確認を同じ immutable な dev 成果物に結び付けていること。
3. 既存の GitHub 本番 Environment の人による承認が通ること。
4. main の公開手順が、承認済み artifact を再ビルドせずに公開し、公開後の URL と成果物を読戻して確認できること。

Sheet の `approved`、PR のマージ、main への push だけでは公開してはいけません。別 revision、異なる SHA、異なる artifact hash、期限切れの成果物は承認をやり直します。

## 8. Gmail と連絡

Gmail 接続は開発・運用側だけに設定します。宛先は非公開設定の `notification_recipient_ref` から解決し、Sheet に入力されたメールアドレスを使用しません。

通知の順番は固定です。

1. `outbox-reserve` で通知キーを予約します。この結果だけでは送信できません（`may_send: false`）。
2. 同じ依頼ID・revision・kind・lease token と予約済みキーを使って `outbox-admit` を実行します。返り値が **`may_send: true` のときだけ1回だけ** Gmail の送信を試行します。
3. 送信後は、同じキーと元の token を使って `outbox-record` に provider message ID と読戻し結果を記録します。lease が期限切れでも、すでに許可済みの送信結果の記録には元の token が必要です。

送信結果が不明なら `ambiguous` と記録し、同じ通知キーで Gmail の送信済み記録を検索・照合します。**不明な送信をそのまま再送しません。** `sending` または `ambiguous` が残る間は、サイト設定の変更、取込、claim が停止するため、先に配信結果を照合します。`outbox-reserve` は送信許可ではありません。

メールの自動送信と到達確認は、まだ完了・検証済みではありません。上記は台帳の安全な記録手順であり、Gmail の接続、provider 受理、受信箱到達を実証するものではありません。設定または権限が不足する間は、下書きまたは手動連絡として扱います。

## 9. 将来の SIMY 連携

SIMY を後から使う場合も、今日の医院に登録を求める必要はありません。Sheet の `request_id`・`revision` と、台帳の immutable な成果物承認を維持したまま、受付・実行・通知のアダプターを置き換える選択肢です。
