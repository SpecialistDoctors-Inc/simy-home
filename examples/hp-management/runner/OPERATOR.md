# HP 更新エージェントの初回設定

これは SIMY 登録、親Codexチャット、ホストのホームディレクトリに依存しない単一サービスです。医院の利用者は引き続き Codex と共有 Google Sheet だけを使います。運用者のGoogle accountはprivate configで明示します。mosyn/SIMY のアカウント登録は要求しません。

## 先に用意するもの

- Docker Compose と、このディレクトリのコピー
- 管理する Google Sheet ID、Google OAuth の Desktop app client JSON、運用者 Google subject
- configured repository のcontents/pull-requests write、Actions/checks read、承認後のdev mergeを行う最小GitHub token
- GitHub Actions 側で既に設定された dev/prod 配備権限。AWS key をこのサービスへ置かない。

## 秘密を置く場所

以下は運用ホストで owner-only にします。Docker socket、`$HOME`、既存のCodex設定を mount しません。

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

## Google の一回だけの同意

Google OAuth の同意は、ブラウザを使える運用者が手動で行います。`google_oauth_setup.py` は Desktop app client JSON を受け取り、127.0.0.1 callback でこの操作を行い、既存credentialやglobal ADCを変更しません。保存前に設定予定のsubjectとemailを照合します。

長期運用前に Google Auth platform の consent screen を確認してください。組織が実際に選択した運用者accountを含む Google Workspace であり、利用条件を満たす場合だけ **Internal** を選びます。そうでなければ External/Testing は試験用です。Google は External + Testing で、openid/profile/email 以外のscopeを含むrefresh tokenを7日で失効させるため、このserviceのSheets/Gmail scopeで恒久運用はできません。ユーザーの取消、Gmail scopeを含むpassword変更、未使用期間などでもrefresh tokenは失効し得ます。失効時はagentを停止し、運用者が再同意してsubject/emailを再照合します。無期限tokenを前提にしません。 [Google OAuth refresh token expiration](https://developers.google.com/identity/protocols/oauth2/#expiration) [Google Workspace consent configuration](https://developers.google.com/workspace/guides/configure-oauth-consent)

hostで専用venvを作り、operator所有の一時directoryで実行してからroot-only control領域へinstallします。container内のlocalhost callbackをホストbrowserに転送する手順はまだ提供していないため、無理にCompose内で実行しないでください。

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

## Codex の一回だけのログイン

`runtime/codex-auth` は worker UID 1000だけが読む永続ログイン領域です。Google/GitHub credential はここへコピーしません。worker の device login は、このservice用の別手順として運用者が実施します。ホストの `~/.codex` をコピー・mount しないでください。

```sh
docker compose run --rm --user 1000:1000 --entrypoint codex hp-agent login --device-auth
docker compose run --rm --user 1000:1000 --entrypoint codex hp-agent login status
```

表示されたdevice codeは運用者本人がブラウザで承認します。credentialを貼り付けたり、hostのCodex authをコピーしたりしません。

## 起動と停止

`--once` はread-onlyではありません。有効なready eventがあるとclaim/worker起動などを進めます。空の専用Sheetでの接続確認以外には使わず、実運用の最初のtickは準備済みの依頼として扱ってください。実際の変更には有効なready event、agentのlease、独立レビュー、運用者の明示承認が必要です。

```sh
docker compose build
docker compose run --rm hp-agent --config /control/config.json --db /state/agent.sqlite3 --once
docker compose up -d
docker compose logs -f hp-agent
docker compose stop hp-agent
```

`mail_enabled` と `auto_merge_dev` は初期値 `false` のままにします。`mail_enabled=true` の場合だけ、admitted envelopeをGmail APIへ直接送信し、SENT readbackで照合します。本番公開とAWS操作はこのcontainerから直接行いません。公開は既存GitHub Actionsの保護Environmentと、その承認済みartifactを通します。

`restart: unless-stopped` はhost Dockerが稼働している間だけcontrollerを再起動します。親Codex chatには依存しません。再起動後はSQLiteに保存したeffect/outboxを先にreadback照合します。workerまたは独立reviewが中断されたjobは自動で再実行・再送せず、運用者の復旧判断を待ちます。意図的な `docker compose stop hp-agent` は明示的に再開するまで停止状態を保ちます。Mac上のUID差異を避ける必要がある運用では、control・state・work・Codex authをそれぞれ別の専用named volumeへ置く構成を選べます。controlはroot所有0700・ファイル0600を確認してread-onlyでmountし、workerが読むCodex authや作業volumeにprovider credentialを混在させません。

## 運用上の境界

- `/control` はcontainer内rootだけが読めます。Google refresh token、GitHub token、設定、SQLite台帳を worker promptへ渡しません。
- controller はrootでstate/leaseを扱い、Codex workerは UID 1000 でrequest専用workspaceのみを扱います。`/work` はroot-owned mode 0711で、root controllerが作成してworkerへchownしたchild workspaceだけにアクセスさせます。
- workerの永続Codex auth は `/home/node/.codex` 専用volumeです。provider secretとは別です。
- Composeはhost network、Docker socket、host homeを使用しません。Docker daemonの再起動はこの手順に含みません。
- 同梱の `seccomp-codex.json` は、Codexの作業用サンドボックスをDocker内で起動するための限定設定です。`unconfined` や特権コンテナへ置き換えないでください。根拠と検証方法は [SECCOMP.md](SECCOMP.md) にあります。
- ambiguous なSheet/Gmail/GitHub外部効果は再送せず、readbackで照合するまで停止します。
