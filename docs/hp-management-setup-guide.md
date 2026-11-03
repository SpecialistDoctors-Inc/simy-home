# 開発・運用向け: HP管理を設定する

この手順は、医院の Sheet の依頼を安全に開発・配信する担当者向けです。**医院にSIMYへの登録、SIMY API、WorkFlowを求めません。** サイトへの書込み権限は、開発・運用担当だけが持ちます。通常運用では、SIMYが運用するAWS上の常時稼働サービスが Sheet を定期確認します。医院の Codex チャット、医院のパソコン、運用担当のデスクトップを起動し続ける必要はありません。

## 医院へ案内する前の準備

医院の担当者は非エンジニアを想定します。配布する説明は[医院向け手順書](hp-management-customer-guide.md)とし、本書のコマンドや設定値を医院へそのまま渡さないでください。GitHub、AWS、台帳、常時稼働サービスの準備はSIMY運用担当が行います。

初回サポートまでに、次を準備します。

- 医院専用Sheetと、その医院のGoogleアカウントへの共有
- 通知先、問い合わせ先、受付時間、公開を承認できる担当者の確認
- 医院端末への固定版 `hp-customer-intake` と同梱参照資料の導入支援
- 医院名・site ID・Sheet ID/URL・医院Googleアカウント・dev/公開URLを記入済みの「利用開始メッセージ」
- 本番公開を伴わない練習の内容と、保存・開発側受付・確認ページ・メール受信を一緒に確かめる時間

受付スキルの導入元は `examples/hp-management/skills/hp-customer-intake`、検証済み固定refは `fc4355a5d74b32488d7c10ece465df38ed8d70e0` です。既存の同名スキルを無断で上書きせず、導入後に新規チャットで認識を確認します。医院にコミットSHAを選ばせたり、インストールコマンドの入力を求めたりしません。Googleログインと接続への同意は医院の担当者自身が行います。

「利用開始メッセージ」は、次を**運用担当がすべて記入した上で**非公開の連絡手段で渡します。医院側のスキルが受け取れる明示的なサイト設定であり、権限の新規付与を意味しません。

```text
ホームページ更新の受付を始めます。hp-customer-intake の手順を使ってください。
以下は運用担当と確認した、この医院専用の設定です。
医院名: <医院名>
サイト識別子: <site_id>
受付表: <共有Sheet URL>
受付表ID: <sheet_id>
医院のGoogleアカウント: <医院の確認済みアカウント>
確認用ページ: <dev URL>
公開先: <production URL>

接続中のGoogleアカウントと受付表を読み取り、医院名と表が合っているか教えてください。
今回は接続の確認だけで、依頼の登録はまだ行いません。
依頼するときは必要なことだけを質問し、普段の言葉で案内してください。
```

初回は、この接続確認と合意済みの練習1件を医院側の通常チャットで実施し、書込みと読戻しを確認します。医院が利用するのはアプリのCodexです。サンプルの新規環境検証にはCLIを使用したため、各医院の端末での初回確認を省略しません。アプリの準備は[公式の開始案内](https://learn.chatgpt.com/docs/quickstart?setup=app)と[プラグイン案内](https://learn.chatgpt.com/docs/plugins)を参照します。

公開確認は「依頼名・確認URL・変更点」を読みやすく示します。同じ確認メッセージに正確な依頼ID・revision・source SHA・artifact ID/hashを結び付け、元の質問と本人の回答を証跡として保持します。医院に識別子を転記させる必要はありません。単独の「OK」、Sheetの記入、準備完了メールへのアクセスだけを承認と扱わず、同じ成果物への本人の明示的な返答を第8節の照合に用います。

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
SpecialistDoctors-Inc/simy-home の
examples/hp-management/skills/hp-developer-delivery を、
固定リビジョン fc4355a5d74b32488d7c10ece465df38ed8d70e0 で導入してください。
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

## 6. 専用の更新サービスを設定する

継続運用では、[`examples/hp-management/runner/OPERATOR.md`](../examples/hp-management/runner/OPERATOR.md) の手順で、医院用 Sheet を読む専用の更新サービスをSIMY運用のAWS環境へ設定します。これは医院側の Codex とは別に稼働し、許可された1つのサイト・1つの編集範囲だけを扱います。Sheetの新しい依頼を検出すると、変更案の作成、別の確認、テスト、開発版への反映、結果の Sheet 記録を順に行います。

初回設定はSIMY運用担当の作業です。AWSの専用ホスト、専用の Google 接続、専用の Codex ログイン、必要最小限の GitHub 権限を用意します。医院には Docker、GitHub、AWS、トークン、コマンドを渡しません。サービスの保守はSSMを使って行い、外部からの管理用受信接続は設けません。ホストまたはサービスが停止している間は新しい依頼の受付処理も停止します。再開後は保存済みの状態を確認してから続きます。

サービスは、作成や確認が途中で止まった依頼を自動で作り直したり、メールを再送したりしません。運用担当が保存済みの依頼・成果物・送信結果を確認して復旧します。設定方法、Google の同意範囲、再起動時の扱い、復旧時の注意は[運用手順](../examples/hp-management/runner/OPERATOR.md)を正とします。

2026-11-03に、AWSの常時稼働構成で新しいSheet依頼を自動受付し、Codexによる変更、独立レビュー、テスト、dev配信、Sheet読戻し、確認メール送信までを実測しました。EC2は東京リージョンの専用t4g.medium、状態は暗号化済み20 GiB EBSに保存し、管理経路はSSMのみです。初期の暗号化スナップショット完了と、日次7世代のDLM設定も確認しました。DLMの初回スケジュール実行はまだ観測していません。正確な成果物と受入証跡は[サンプルの検証記録](hp-management-sample-verification.md)を参照してください。

### 途中で止まったときの扱い

医院に復旧操作をお願いする必要はありません。確認ページが届かない、または運用通知が来た場合は、SIMY運用担当が保存済みの依頼番号と版数を使い、まず「どこまで済んだか」を確認します。たとえば、変更がdevに出ているか、メールが送信済みか、Sheetに結果が記録済みかを読み戻します。結果が不明なときは同じ変更やメールを送信し直さず、照合が完了するまで止めます。

運用担当には、依頼ごとに `Agent --recover acknowledge --request-id … --revision … --operator …`（確認記録のみ）と、原因解消後の `Agent --recover resume --request-id … --revision … --operator …`（安全な再開）の手順があります。受付全体がGoogle接続の失効などで停止した場合は、本人によるGoogle再同意とアカウント照合後に `Agent --recover-intake --operator …` を使います。これらは運用台帳に記録され、手作業で台帳を書き換えて状態だけを進めることはしません。詳細な確認項目・コマンド・単一writerの注意は[運用手順](../examples/hp-management/runner/OPERATOR.md#障害の確認と復旧)を参照してください。

自動再試行は回数と待ち時間を限定しており、認証切れ、外部操作の結果不明、独立レビューの却下は人による確認が必要です。未解決の障害は死活監視に反映され、設定済みの場合は専用の運用メール宛SNS通知で知らせます。通知設定済みと判断するには、受信側のsubscription確認とアラーム試験の読戻しが必要です。この復旧機能と通知条件を含む版のAWS本番適用・実地受入は、別途の検証証跡が揃うまで未完了です。

バックアップは元の状態を壊さず、隔離した暗号化volumeでSQLiteの整合性と記録件数を確認してから判断します。復元したbackupで更新サービスや外部接続を起動せず、本番と同時に二つの更新サービスを動かしません。

## 7. 手動で依頼を dev まで進める

手動で進める場合は、運用担当が次の順で、1件ずつ明示して進めます。

1. Sheet の最新 `Requests` revision と `Events` を読み、対象・依頼者参照・通知先参照・受入条件を確認します。
2. 台帳に取り込み、依頼ID・revision・内容ハッシュを記録します。同じ内容は再処理せず、異なる revision は新しい依頼として扱います。
3. 台帳で claim を取得してから、非公開設定で許可された worktree・ブランチ・編集範囲だけを操作します。
4. 実装、テスト、dev 配信、表示確認を行います。`Events` に `claimed`、`test_result`、`dev_preview_ready` などの事実を追記します。
5. `dev_preview_ready` には依頼ID、revision、dev URL、実際の source SHA、artifact ID / hash、実行したテストを残します。

サンプルでは、[PR #313](https://github.com/SpecialistDoctors-Inc/simy-home/pull/313) の dev 成果物について、[run 41163859006](https://github.com/SpecialistDoctors-Inc/simy-home/actions/runs/41163859006) の保存済み artifact `13028320719` と dev 上の8ファイルが byte-for-byte 一致することを確認しました。source は `fc4355a5d74b32488d7c10ece465df38ed8d70e0`、artifact hash は `3bd47d30e529c42e7eb081234b3376963202cf0bf42d30aafd912ed527570b7b` です。

5分ごとの heartbeat は、実際に1件の新規 Sheet 依頼を検出し、台帳で claim、スコープ内のお知らせ文追加、PR・dev 配信・表示確認を行いました。[run 41166888036](https://github.com/SpecialistDoctors-Inc/simy-home/actions/runs/41166888036) は成功し、source は `f5a596c156dc6851a4978221b409c27fb723b3de`、artifact は `13028304194`、hash は `a4bb55ad97d63981103e0c9b0cfa899abbf192d37e02cb11c2caf38983e54891` です。dev の8ファイルと artifact は byte-for-byte 一致し、デスクトップ・モバイル表示を確認しました。本番の既存8ファイルは変更していません。

この手動手順は、初回の練習やサービス障害時の確認に限ります。通常運用の受付を、親Codexチャットの Scheduled task や個人端末の定期実行に置き換えません。専用サービスは、保存済みの依頼ID・revision・処理状態を使って重複を防ぎます。

## 8. 本番を公開する

本番は dev の成功とは別の工程です。次の全てを照合します。

1. 依頼ID・revision・source SHA・artifact ID・artifact hash を結び付けた公開確認メッセージに、医院の人がその内容を確認して明示的に同意したこと。識別子は運用側が提示・記録し、医院に転記させない。
2. SQLite 台帳が、その確認を同じ immutable な dev 成果物に結び付けていること。
3. 既存の GitHub 本番 Environment の人による承認が通ること。
4. main の公開手順が、承認済み artifact を再ビルドせずに公開し、公開後の URL と成果物を読戻して確認できること。

Sheet の `approved`、PR のマージ、main への push だけでは公開してはいけません。別 revision、異なる SHA、異なる artifact hash、期限切れの成果物は承認をやり直します。

サンプルでは、承認済みの dev source `fc4355a5d74b32488d7c10ece465df38ed8d70e0` と artifact hash `3bd47d30e529c42e7eb081234b3376963202cf0bf42d30aafd912ed527570b7b` を変えずに、[run 41165087996](https://github.com/SpecialistDoctors-Inc/simy-home/actions/runs/41165087996) が本番へ公開しました。main release は `32d33b8e23a2d0af2f8136925b13911379fd857b` です。公開後は8つの静的ファイルが保存済み ZIP と byte-for-byte 一致し、デスクトップと iPhone 16 幅でお知らせの展開・閲覧を確認しました。これはこの承認済み成果物の証跡であり、以後の依頼を無承認で公開できることを意味しません。

## 9. Gmail と連絡

Gmail 接続は開発・運用側だけに設定します。宛先は非公開設定の `notification_recipient_ref` から解決し、Sheet に入力されたメールアドレスを使用しません。

通知の順番は固定です。

1. `outbox-reserve` で通知キーを予約します。この結果だけでは送信できません（`may_send: false`）。
2. 同じ依頼ID・revision・kind・lease token と予約済みキーを使って `outbox-admit` を実行します。返り値が **`may_send: true` のときだけ1回だけ** Gmail の送信を試行します。
3. 送信後は、同じキーと元の token を使って `outbox-record` に provider message ID と読戻し結果を記録します。lease が期限切れでも、すでに許可済みの送信結果の記録には元の token が必要です。

送信結果が不明なら `ambiguous` と記録し、同じ通知キーで Gmail の送信済み記録を検索・照合します。**不明な送信をそのまま再送しません。** `sending` または `ambiguous` が残る間は、サイト設定の変更、取込、claim が停止するため、先に配信結果を照合します。`outbox-reserve` は送信許可ではありません。

サンプルでは、開発側 Gmail から設定済み宛先へ初回の preview・公開通知を各1件、heartbeat 起点の preview 通知を1件送信し、provider の `SENT`・本文・宛先の読戻しを確認しました。受信者から初回2通と追加1通の到着回答を受け、3件とも台帳へ `inbox_verified` を記録しました。これは受信者の確認に基づく証拠であり、受信箱APIの読取りとは区別します。heartbeat 通知の replay は台帳が拒否し、claim は解放済みです。設定または権限が不足する新しい環境では、下書きまたは手動連絡として扱います。

## 10. サンプルの受入結果

ローカルの台帳テスト17件とサイトのテスト8件が通り、独立した Codex レビューでは blocker / P1 はありませんでした。本番の人による承認、Environment を通す公開、公開後の読戻しも完了しています。heartbeat の実際の起動・claim・dev 成果物・通知 provider 証跡、医院側による2件目の `claimed` / `test_result` / `dev_preview_ready` の読戻し、通知3通の受信者確認が揃い、2026-10-31にサンプル範囲の受入検証を完了しました。試験用の定期実行は削除済みです。別の医院・端末で継続運用する場合は、本書に沿って設定と初回確認を行います。

詳細な実行番号・成果物照合の履歴は[サンプルの検証記録](hp-management-sample-verification.md)を参照してください。

## 11. 将来の SIMY 連携

SIMY を後から使う場合も、今日の医院に登録を求める必要はありません。Sheet の `request_id`・`revision` と、台帳の immutable な成果物承認を維持したまま、受付・実行・通知のアダプターを置き換える選択肢です。
