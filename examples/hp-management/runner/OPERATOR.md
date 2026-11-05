# HP 更新エージェントの初回設定

これは、SIMYが運用するAWS上の単一サービスです。医院の利用者は引き続き Codex と共有 Google Sheet だけを使い、SIMYへの登録、SIMY API、WorkFlowは必要ありません。運用者のGoogle accountはprivate configで明示します。親Codexチャット、医院のパソコン、運用者のホームディレクトリには依存しません。

## 運用先と管理経路

本番運用先は、SIMYが管理するUbuntu 24.04 arm64の専用EC2（t4g.medium）です。インターネットからの受信管理ポートは公開せず、運用者はAWS Systems Manager (SSM) を通じて管理します。サービスのSQLite状態、作業領域、専用Codex認証、運用設定は暗号化された専用EBS上に置きます。インスタンス、ボリューム、SSM権限の具体的な作成方法は [`infra/hp-agent/README.md`](../../../infra/hp-agent/README.md) を参照してください。

2026-11-03に、この構成で実際の新規Sheet依頼を自動処理し、dev配信、Sheet読戻し、確認メールの受信まで確認しました。現在の反映対象はsource `2967a35` と、記録済みの immutable ECR image digest（`sha256:af205527…`）です。計画したOS再起動後の復帰も確認済みです。実際の文章修正後の停止と、PR・統合・Sheet記録・メールの応答喪失からの復旧、およびその後の通常更新を確認済みです。ローカルDockerでの検証は、AWSサービスの稼働証明にはなりません。確認済み範囲は[復旧検証記録](../../../docs/hp-management-recovery-verification.md)を参照してください。

## AWS本番運用の手順

EC2へ直接このディレクトリをコピーして `docker compose up` を実行してはいけません。AWS本番では、[`infra/hp-agent/README.md`](../../../infra/hp-agent/README.md) の順に、SSMでのデータボリューム準備、コミット済みファイルとイメージdigestを結び付けたリリース確認、暗号化アーカイブの復元、`/srv/hp-agent` へのランタイム導入を行います。これにより、ルートディスクではなく専用EBSを使い、リリースmanifestとegress制限を経由します。

既存の専用Codex認証は、暗号化アーカイブに含めて専用EBSへ復元します。通常は新しいdevice loginを要求しません。認証が失効または復元不能と確認できた場合だけ、運用者本人が再ログインします。Google OAuth、GitHub、Codexの認証情報をSSMコマンド、Terraform、Git、ログに含めません。

## 先に用意するもの

- AWS上の専用EC2、暗号化済みの専用EBS、SSMでの運用権限
- Docker Compose と、このディレクトリのコピー
- 管理する Google Sheet ID、Google OAuth の Desktop app client JSON、運用者 Google subject
- configured repository のcontents/pull-requests write、Actions/checks read、承認後のdev mergeを行う最小GitHub token
- GitHub Actions 側で既に設定された dev/prod 配備権限。AWS key をこのサービスへ置かない。

## ローカル準備・試験での秘密の置き場所

以下の手順は、初回のOAuth同意やコンテナ試験を行うローカル準備環境だけに使います。EC2本番の導入手順ではありません。本番の状態はAWS本番運用の手順に従って専用EBSへ復元します。Docker socket、`$HOME`、既存のCodex設定を mount しません。

```sh
cd examples/hp-management/runner
sudo install -d -m 700 runtime/control runtime/state runtime/codex-auth
sudo install -d -m 711 runtime/work
sudo chown 1000:1000 runtime/codex-auth
sudo install -m 600 runtime/config.example.json runtime/control/config.json
sudo sh -c 'umask 077; : > runtime/control/github-token.txt'
sudoedit runtime/control/config.json
sudoedit runtime/control/github-token.txt
```

`config.json` の `google_email` と `google_subject` は、OAuth 接続する運用者profileのemailと不変subjectに置き換えます。`site` の値は顧客入力から受け取らず、運用者が確認して設定します。

## ローカル準備時のGoogle同意

Google OAuth の同意は、ブラウザを使える運用者が手動で行います。`google_oauth_setup.py` は Desktop app client JSON を受け取り、127.0.0.1 callback でこの操作を行い、既存credentialやglobal ADCを変更しません。保存前に設定予定のsubjectとemailを照合します。

長期運用前に Google Auth platform の consent screen を確認してください。組織が実際に選択した運用者accountを含む Google Workspace であり、利用条件を満たす場合だけ **Internal** を選びます。そうでなければ External/Testing は試験用です。Google は External + Testing で、openid/profile/email 以外のscopeを含むrefresh tokenを7日で失効させるため、このserviceのSheets/Gmail scopeで恒久運用はできません。ユーザーの取消、Gmail scopeを含むpassword変更、未使用期間などでもrefresh tokenは失効し得ます。失効時は受付を保留し、運用者が再同意してsubject/emailを再照合します。無期限tokenを前提にしません。今回の運用者Googleアカウントは `s.mo@simy.one` です。 [Google OAuth refresh token expiration](https://developers.google.com/identity/protocols/oauth2/#expiration) [Google Workspace consent configuration](https://developers.google.com/workspace/guides/configure-oauth-consent)

ローカル準備環境で専用venvを作り、operator所有の一時directoryで実行します。container内のlocalhost callbackをホストbrowserに転送する手順はまだ提供していないため、無理にCompose内で実行しないでください。生成した認証情報をEC2へ直接コピーせず、AWS本番運用の手順の暗号化アーカイブに含めます。

```sh
python3 -m venv .hp-oauth-venv
. .hp-oauth-venv/bin/activate
pip install -r requirements.txt
install -d -m 700 runtime/oauth-setup
install -m 600 /path/to/installed-client.json runtime/oauth-setup/installed-client.json
python google_oauth_setup.py \
  --installed-client-json runtime/oauth-setup/installed-client.json \
  --output runtime/oauth-setup/google-oauth.json \
  --expected-subject 'REPLACE_WITH_GOOGLE_SUBJECT' \
  --expected-email 'REPLACE_WITH_OPERATOR_GOOGLE_EMAIL'
deactivate
rm -rf .hp-oauth-venv
sudo install -o root -g root -m 600 runtime/oauth-setup/google-oauth.json runtime/control/google-oauth.json
rm -rf runtime/oauth-setup
```

通知メールも有効にする場合だけ、最後のコマンドへ `--enable-gmail-send` を加えます。これは Gmail 送信と送信済みreadback の scope を追加します。

### Google scope とプライバシー

Googleにはユーザーが選択したfileだけを扱う `drive.file` scopeがあります。ただし、このserviceの現在の実装はそれを使わず、より広いSheets scopeを要求します。そのため接続した運用者がアクセスできるSpreadsheetに対してscopeが有効です。また、Gmail `readonly` はメールボックス全体のread accessをGoogleへ要求します。アプリの実装はtrusted config内の1 Sheet ID、ならびに `in:sent` と `HP-NOTICE-<key>` に一致する送信済みメールだけを読みますが、これはGoogle OAuth scope自体の制限ではありません。専用の最小権限Google accountを使い、scopeとconsent画面を運用者が確認してください。

## ローカル準備時のCodexログイン

`runtime/codex-auth` は worker UID 1000だけが読む専用ログイン領域です。Google/GitHub credential はここへコピーしません。下記のdevice loginは、初回のローカル準備・試験で認証が存在しない場合だけ行います。すでに用意した専用Codex認証を本番へ移す場合は、AWS本番運用の暗号化アーカイブを使い、重複ログインしません。ホストの `~/.codex` をコピー・mount しないでください。

```sh
docker compose run --rm --user 1000:1000 --entrypoint codex hp-agent login --device-auth
docker compose run --rm --user 1000:1000 --entrypoint codex hp-agent login status
```

表示されたdevice codeは運用者本人がブラウザで承認します。credentialを貼り付けたり、hostのCodex authをコピーしたりしません。

## ローカル準備・試験での起動と停止

LinuxホストでAppArmorが有効な場合は、運用者が [隔離設定の説明](SECCOMP.md) を確認し、このサービスだけに適用するプロファイルを登録します。既定の `docker-default` やホスト全体の設定を変更しません。Docker DesktopのLinux VMでは、この追加手順は不要です。

```sh
sudo apparmor_parser -r -W apparmor-codex.profile
docker compose -f compose.yaml -f compose.apparmor.yaml config
```

表示された設定で `no-new-privileges`、`seccomp`、`apparmor=simy-hp-codex` が全て残ることを確認します。以下のComposeコマンドにも同じ2つの `-f` を付けます。プロファイルの登録権限がないホストでは、管理者に設定を依頼してください。

`--once` はread-onlyではありません。有効なready eventがあるとclaim/worker起動などを進めます。空の専用Sheetでの接続確認以外には使わず、実運用の最初のtickは準備済みの依頼として扱ってください。実際の変更には有効なready event、agentのlease、独立レビュー、運用者の明示承認が必要です。

```sh
docker compose build
docker compose run --rm hp-agent --config /control/config.json --db /state/agent.sqlite3 --once
docker compose up -d
docker compose logs -f hp-agent
docker compose stop hp-agent
```

`mail_enabled` と `auto_merge_dev` は初期値 `false` のままにします。`mail_enabled=true` の場合だけ、admitted envelopeをGmail APIへ直接送信し、SENT readbackで照合します。本番公開とAWS操作はこのcontainerから直接行いません。公開は既存GitHub Actionsの保護Environmentと、その承認済みartifactを通します。

本番ではsystemdがデータ領域・通信制限・Dockerの起動順と死活監視を管理し、専用コンテナはDockerの `restart unless-stopped` で自動再起動します。本番の導入には検証済みの `install-runtime.sh` を使います。再起動後はSQLiteに保存したeffect/outboxを先にreadback照合します。worker・検証・独立reviewの中断は、前回のプロセス終了と保存済み成果物を確認できる場合に限り、回数・待機時間を限定した新しいattemptとして再試行できます。認証不良、review却下、外部効果が不明なjobは運用者の判断を待ち、再送しません。control・state・work・Codex authはそれぞれ専用の永続領域へ置き、controlはroot所有0700・ファイル0600を確認してread-onlyでmountします。workerが読むCodex authや作業領域にprovider credentialを混在させません。

## 障害の確認と復旧

ここでいう「復旧」は、同じ外部操作を闇雲にもう一度実行することではありません。まず保存済みの台帳、GitHub Actions、dev の表示、Sheet、Gmail の送信済み記録を照合します。結果を取得するための限定したreadbackは実行でき、完全一致が見つかればその既存結果を記録して次の工程へ進めます。特に `ambiguous`、`sending`、`provider_reconciliation_required` は、外部操作が成功したか判定できない状態です。readback で一致を確認するまで、書込みの再送・再マージ・再公開をしません。

状態確認は運用者だけがSSM上で行います。以下は秘密値やlease tokenを表示しない読み取り専用の例です。SQLiteを直接更新して「復旧済み」に見せかけることは禁止です。

```sh
sqlite3 -readonly /srv/hp-agent/state/agent.sqlite3 <<'SQL'
.headers on
.mode column
SELECT request_id, revision, stage, error FROM agent_jobs ORDER BY rowid DESC;
SELECT request_id, revision, stage, attempt, failures, retry_at, resume_stage
  FROM agent_job_runtime ORDER BY rowid DESC;
SELECT request_id, revision, code, opened_at, acknowledged_at, resolved_at
  FROM agent_incidents ORDER BY opened_at DESC;
SELECT failures, retry_at, paused FROM agent_service_runtime WHERE id=1;
SQL
```

`acknowledge` は「担当者が障害を確認した」という監査記録だけです。依頼を再開せず、incidentも解決済みにしません。原因を除去し、上のreadbackで外部効果を照合した後にだけ `resume` を使います。どちらも `--config` と `--db` は本番の同じ値を指定し、request ID と revision を必ず指定します。

```sh
# <operator-id> は監査用の運用者IDであり、tokenやメール本文ではない。
docker exec hp-agent python3 /opt/hp-agent/agent.py \
  --config /control/config.json --db /state/agent.sqlite3 \
  --recover acknowledge \
  --request-id '<request-id>' --revision '<revision>' --operator '<operator-id>'

docker exec hp-agent python3 /opt/hp-agent/agent.py \
  --config /control/config.json --db /state/agent.sqlite3 \
  --recover resume \
  --request-id '<request-id>' --revision '<revision>' --operator '<operator-id>'
```

これらのCLIは台帳の単一writer lockを取得してから動くため、通常はcontrollerを止める必要がありません。lockを取得できない場合は、controllerの現在のtickを待ってから再度状態を読みます。同じSQLiteへ別の書込みツールを直接つなげたり、lockを回避したりしません。この文書のコマンドはプロセスを停止しません。プロセスへsignalを送る必要がある場合も、実行者がこの作業で起動・記録した正のPIDだけを、PID・親PID・開始時刻・コマンドを直前に再照合して扱います。名前、パターン、process group/tree、共有サービスを対象に停止しません。

`retry_wait` は設定された期限と回数の範囲でのみ自動再試行します。標準の設定例は次のとおりです。認証不良、入力の不整合、独立reviewの却下、外部効果が不明な場合は自動再試行の対象ではありません。

```json
"recovery": {
  "enabled": true,
  "max_retries": 3,
  "base_delay_seconds": 30,
  "stage_timeout_seconds": 1800
}
```

### Google接続によって受付が保留された場合

Googleの401/403またはrefresh失敗では、サービスは `authentication_required` として受付を保留します。運用者がGoogleの同意画面で再接続し、emailと不変subjectを再照合してから、providerを読み取りで確認します。その後、サービス全体の受付だけを安全に戻すには次を一度だけ実行します。これはSheet・GitHub・有効な場合はGmailの認証確認を行いますが、依頼の変更、メール送信、公開は行いません。

```sh
docker exec hp-agent python3 /opt/hp-agent/agent.py \
  --config /control/config.json --db /state/agent.sqlite3 \
  --recover-intake --operator '<operator-id>'
```

### サーバー側Codexのログインが必要な場合

`codex_auth_required` は、専用Codexのログイン状態の確認に失敗し、対象の依頼が `needs_input` で保留された状態です。上のGoogle用 `--recover-intake` だけではCodexの再ログインも依頼の再開もできません。まず対象の受付番号・revision・失敗記録を照合します。前回のworker/reviewerが終了し、別のworker/reviewerも動いていないことを保存済みprocess記録と実プロセスで確認してください。実行中・同一性不明なら認証を書き換えず、その状態の調査を先に行います。

既存のAWS専用コンテナで、workerと同じUIDの読み取り専用確認を行います。以下は検証済みimageの `worker_uid=1000`、`worker_home=/home/node`、専用認証領域 `/home/node/.codex` の構成です。

```sh
docker exec --user 1000:1000 hp-agent codex login status
```

ログインが必要と確認できた場合だけ、運用者のSSM対話セッションで、同じ台帳の排他lockを保持する保守用shellを開きます。lockを取得できなければshellは開始せず、既存処理の終了を待ちます。lock中は受付が進まないため、運用担当は保守作業として扱います。

```sh
flock -n /srv/hp-agent/state/agent.lock /bin/bash
```

このlockを取得したshell内で、先ほどの状態と保存済みprocess記録を再読し、worker/reviewerが動いていないことをもう一度確認します。lock取得前の確認だけで進めません。終了を確認できなければ `exit` で保守用shellだけを終了し、認証を書き換えません。確認できた場合に限り、同じshell内で次を実行し、最後に `exit` でlockを解放します。

```sh
docker exec -it --user 1000:1000 hp-agent codex login --device-auth
docker exec --user 1000:1000 hp-agent codex login status
exit
```

運用者本人が表示されたURLとコードを使い、既存のサービス用ChatGPTアカウントで許可します。医院側のCodexやMacの認証は変更しません。`auth.json`、token、passwordは表示・コピー・ログ保存せず、認証情報をリポジトリへ入れません。`login status` の成功は保存された認証の存在を示すため、実際のモデル実行と復旧の成功は、その後の対象依頼の進行で確認します。参照: [OpenAIのdevice code認証](https://learn.chatgpt.com/docs/auth#login-on-headless-devices)、[login status](https://learn.chatgpt.com/docs/developer-commands#codex-login)。

再ログイン後、同じ受付番号・revisionについて最新のSheet、保存済み成果物、PR/dev、外部effectと通知outboxを読み戻します。`admitted`、`sending`、`ambiguous` の操作があれば先に既存結果を照合し、書込み・公開・メールを再送しません。原因が解消し、最新の依頼が有効であることを確認したら、上の依頼単位の `--recover acknowledge` と `--recover resume` を使います。元の試行を消さず、新しい試行が検証済みの次工程へ進み、incidentが解決して監視が復帰するまで確認してください。ログインだけで「復旧完了」とはしません。

incidentは、前進できる状態へ遷移したときにのみ解決済みになります。`acknowledged_at` があるだけでは解決ではありません。health check は未解決incident、停止したworker/reviewer、provider照合待ち、期限超過、読めない台帳を異常としてCloudWatchへ出します。運用用SNS通知を設定する場合は専用運用メールアドレスのsubscription確認とアラーム試験のreadbackが必要です。通知には依頼本文・認証情報を含めません。この復旧機能のAWS反映、実際の障害通知の受信、中断からの復旧は[復旧検証記録](../../../docs/hp-management-recovery-verification.md)で確認できます。

## バックアップからの検証と復元

日次DLMスナップショットは、初期手動snapshotとは別に、DLMが作成した時刻・source volume・保持タグを記録して初めて実行証跡になります。復元試験では本番volumeや本番controllerにsnapshotを接続しません。既存の専用ホストに**新しい読み取り専用の検証用ディスク**だけを接続し、SQLiteの確認用コピーはroot所有のtmpfsにだけ置きます。別のEC2は作成しません。agent container、Codex、Google/GitHub/Gmailのcredentialを起動せずにSQLiteの `PRAGMA integrity_check`、上記の件数・stage・incident readback、archive hashを確認します。

元のbackupは保存したまま、検証用ディスクは確認後にresource IDを再照合して切り離します。本番へ戻す必要がある場合は、まず本番writerが存在しないことと外部効果の照合を確認し、同時に二つのwriterを動かさない移行手順で復元します。snapshotから復元した状態をそのまま起動してproviderへ接続することはしません。

## 運用上の境界

- `/control` はcontainer内rootだけが読めます。Google refresh token、GitHub token、設定、SQLite台帳を worker promptへ渡しません。
- controller はrootでstate/leaseを扱い、Codex workerは UID 1000 でrequest専用workspaceのみを扱います。`/work` はroot-owned mode 0711で、root controllerが作成してworkerへchownしたchild workspaceだけにアクセスさせます。
- workerの永続Codex auth は `/home/node/.codex` 専用volumeです。provider secretとは別です。
- Composeはhost network、Docker socket、host homeを使用しません。Docker daemonの再起動はこの手順に含みません。
- 同梱の `seccomp-codex.json` は、Codexの作業用サンドボックスをDocker内で起動するための限定設定です。`unconfined` や特権コンテナへ置き換えないでください。根拠と検証方法は [SECCOMP.md](SECCOMP.md) にあります。
- ambiguous なSheet/Gmail/GitHub外部効果は再送せず、readbackで照合するまで停止します。
