# Codexをインストールした直後からのHP更新受付テスト

これは通常の医院向け導入手順ではない。通常ChatGPTからの入口は準備中であり、
現時点ではCodex、Google接続、ローカルスキルを不要にする受付を提供していない。
現在の[Codexによるサンプル受付テスト手順](hp-management-customer-guide.md)と
[SIMY向け初期設定・運用手順](hp-management-setup-guide.md)を参照する。
この文書はDocker/CLIを使う担当者向けの再現試験手順。

このテストは、端末にSIMYの設定・スキル・Codex認証がまだない状態を
対象にする。既存アカウントにあるGoogle接続は復元されることがある。
DockerではLinux版Codex CLIを確認する。
デスクトップアプリのインストーラー、画面操作、OSの権限ダイアログは
別の実機テストが必要。

## 独立した環境を作る

`examples/hp-management/onboarding-test/Dockerfile` はCodex CLI 0.166.0を
インストールし、一般ユーザー `node` で起動する。ホストのホーム、
認証情報、設定、スキル、Dockerソケットはマウントしない。

リポジトリのルートで実行する。`clinic_context` は、試験に使う稼働済みの
Docker context名に置き換える。グローバルなcontextは変更しない。

```sh
(
set -eu
clinic_context=YOUR_TEST_CONTEXT
clinic_image="simy-clinic-codex-onboarding:$(python3 -c 'import uuid; print(uuid.uuid4())')"
printf 'Test image: %s\n' "$clinic_image"
mkdir -p output/sample-clinic/onboarding
python3 examples/hp-management/onboarding-test/prepare-seccomp.py \
  output/sample-clinic/onboarding/seccomp.json
docker --context "$clinic_context" build -t "$clinic_image" \
  --label simy.task=clinic-onboarding-test \
  examples/hp-management/onboarding-test
docker --context "$clinic_context" run --rm -it --name simy-clinic-codex-onboarding-test \
  --label simy.task=clinic-onboarding-test \
  --cpus 1 --memory 1g --pids-limit 256 --cap-drop ALL \
  --security-opt no-new-privileges=true \
  --security-opt seccomp=output/sample-clinic/onboarding/seccomp.json \
  "$clinic_image" bash
)
```

同名コンテナが存在するときは停止・削除せず、今回作ったものか確認する。
シェルを終了すると、このコマンドで作ったコンテナは削除される。
認証情報を含むコンテナをイメージ化・配布しない。
終了後は表示された今回のイメージtagを記録し、利用中コンテナがないことを
確認して、そのtagだけを削除できる。他タスクのイメージやキャッシュは整理しない。
既存のseccomp.jsonがある場合は生成が停止する。内容を確認して別名の新規出力を
指定し、`docker run` 側も同じパスに合わせる。ベースイメージとCodex版は固定だが、
apt依存はビルド時に解決するため、同一イメージの再現を保証する構成ではない。

Dockerの標準seccompでは、Codexのbubblewrapが必要とする名前空間作成が
拒否される。生成スクリプトはMoby公式プロファイルを固定commitとSHA256で
確認し、6つの名前空間・マウント関連syscallのみ追加許可する。
Codex自体のsandboxは有効に保つ。この設定は試験用であり、顧客端末の
通常のCodexインストールにDocker設定を要求するものではない。

Ubuntu系エンジンではAppArmorも影響する。`Failed to make / slave` または
`Failed RTM_NEWADDR` が出る場合、試験エンジンの管理者が同梱
`container.apparmor` を読み、同名プロファイルが存在しないことを確認してから
`sudo apparmor_parser --add` の標準入力に渡してロードする。そのエンジンの
テスト用コンテナだけに `--security-opt apparmor=simy-clinic-codex-onboarding`
を追加する。このプロファイルは当該コンテナの `docker-default` を置き換える
ため、当該コンテナのAppArmor制限は実質無効になる。名前空間内のマウント等を
許すことでカーネル機能へのアクセスも増える。専用の試験VM/エンジンを推奨し、
本番運用の保護設定として流用しない。seccomp、非root、cap-drop、
no-new-privilegesを併用する。
グローバルsysctlや他コンテナの設定は変更しない。終了後、今回ロードした
プロファイルを使うコンテナがなくなったことを確認し、同じ本文を
`sudo apparmor_parser --remove` に渡して解除する。既存プロファイルは変更しない。

ログイン前に、コンテナ内で `codex sandbox -c 'sandbox_mode="read-only"'`
経由のコマンドが動くか確認する。同梱 `sandbox-check.py` を標準入力で渡し、
読み取り成功・ホームへの書き込み拒否・ネットワーク拒否の3項目を確認する。
タイムアウトや名前解決失敗はネットワーク制限の証拠としない。
ホストの別ターミナルから、実行中の試験コンテナに対して次のコマンドで確認できる。
このCLI版では `sandbox linux` というサブコマンドは使わない。

```sh
docker --context YOUR_TEST_CONTEXT exec -i simy-clinic-codex-onboarding-test \
  codex sandbox -c 'sandbox_mode="read-only"' python3 - \
  < examples/hp-management/onboarding-test/sandbox-check.py
```

## 初回操作と合格条件

1. `codex --version` でバージョンを確認する。初回起動前に
   `/home/node/.codex/auth.json`、独自設定、独自スキルがないことを記録する。
   `codex login status` が未ログインを示すことを確認する。
2. `codex login --device-auth` を実行する。本人が表示された公式URLを開き、
   一時コードを入力する。デバイスログインが無効なら、公式認証手順に従う。
   `codex login status` と実際のモデル応答の両方を確認する。
3. `codex` を開始し、`/plugins` からGoogle Driveの導入・接続を進める。
   本人が接続先Googleアカウントと権限を確認する。既存ChatGPTアカウントの
   Google接続が再利用された場合、Googleの初回OAuth成功とは記録しない。
   本当の初回接続の検証には、未連携のテスト用アカウントを使う。
4. 下記のスキル導入メッセージを渡す。CLIのworkspace-writeは `.codex` を
   保護するため、導入セッションだけ
   `codex --sandbox workspace-write --add-dir /home/node/.codex/skills`
   で起動する。公開GitHubへの取得アクセスを許可し、他の設定・認証ファイルを
   書込対象に加えない。非対話テストでは同じ限定許可を `codex exec` に渡し、
   `-c sandbox_workspace_write.network_access=true` も指定した。
   インストール後はこの追加許可を外した新しいセッションで
   `hp-customer-intake` が認識され、同梱の契約を読み込めることを確認する。
5. SIMYが確認した医院・利用者・専用シートの対応を用意する。
   利用者が入力したURLやメール文字列だけを権限の根拠にしない。
6. 本人がテスト依頼を伝える。Codexが不足事項を確認し、許可されたシートに
   `Requests` と `ready_for_dev` イベントを書き、再読込する。
   依頼ID・revision・本文の一致を確認する。手動の単発試験では、固定UUIDと
   試験専用keyを先に保存し、追記前と曖昧な応答後に重複を照合する。
   `appendCells` を使い、既存行や共有状態を上書きしない。これは並行処理時の
   exactly-once保証ではない。本サービスのrunnerには永続的な重複制御が必要。
   `codex exec` の承認ポリシーが `never` の場合、MCP書込が実行前に拒否される。
   対話CLIの承認操作、またはユーザーが許可した単発テストで
   `codex --approve-for-me exec` の標準レビューを使う。レビューの拒否は回避しない。
7. 開発側の独立した接続で同じ依頼を読み、devへ反映し、確認URLとテスト結果を
   `Events` に返す。ユーザー側の新しいセッションからその結果を取得する。

各段階の失敗を記録する。別の環境から書き込んだ行や、手動で補った設定を
この新規環境の成功として数えない。接続テストだけの依頼は、サイト変更を
実行する依頼と区別する。本番公開・メール送信は、この接続テストでは行わない。

## ユーザーが貼るスキル導入メッセージ

```text
SIMYのホームページ更新受付スキルをインストールしてください。
取得元は SpecialistDoctors-Inc/simy-home、
リビジョンは 80a04f7f3fe143df06767a4ae1eaf786e1297519、
パスは examples/hp-management/skills/hp-customer-intake です。
公式のskill-installerが利用できれば、それを使ってください。
同梱のreferencesも含めて導入し、既存の同名スキルがあれば上書きせず確認してください。
完了後、利用開始に必要な接続・医院の登録情報を教えてください。
このメッセージでは、シートへの依頼登録、本番公開、メール送信は依頼しません。
```

これはスキルを取得する入口であり、医院の本人確認やGoogle接続を行う
プログラムではない。現在の受付スキルは、確認済みの医院と利用者の対応が
得られない場合に書き込みを停止する。対応を登録・取得するサービスは未実装。

## 2026-10-30の実行結果

- 初回はディスク不足でビルドに失敗した。空き容量確保後、稼働済みのローカル
  Colimaエンジンでビルドが成功した。Docker Desktopの再起動は行っていない。
- 空のhome、認証なし、独自設定・スキルなし、ホストマウントなし、非rootから
  開始。本人によるデバイスログインと、実際のCodexモデル応答に成功した。
- seccompと当該コンテナだけに適用するAppArmor設定でbubblewrapが動作した。
  read-onlyで読取成功、書込はEROFS、ネットワークはEPERMを確認した。
- ランタイム設定のため作り直したコンテナには、この試験中に本人が作った
  auth.jsonだけをパイプで移した。ホストの既存認証の持ち込み、認証のログ出力、
  ホストファイルへの保存、認証入りイメージ作成はしていない。
- コンテナのCodexが公式skill-installerで指定リビジョンを取得し、標準スキル
  ディレクトリに導入した。2ファイルのSHA256が配布元と一致し、quick_validateに
  成功。初回の書込許可不足を修正するため、スキルディレクトリに限定許可を付与した。
- 別セッションが `hp-customer-intake` を利用可能一覧で認識し、本文と同梱契約を
  読んだ。Google Driveプラグインで実シートのmetadata・Requests・Eventsを取得できた。
- Google接続は既存アカウントからの復元。Googleへの初回OAuthや顧客別の権限分離を
  検証したものではない。医院登録サービスがない状態では書込を開始しないことも確認した。
- 明示的なサンプル限定fixtureを設定し、接続アカウントを検証後、コンテナ内Codexが
  RequestsとEventsへ同一batchで1行ずつ追記した。承認ポリシー `never` による拒否と
  未登録を先に確認し、標準の自動承認レビューを有効にした実行で追記と全値の
  読戻し一致に成功した。既存行は維持。サービスの本登録・顧客別OAuth・自動監視の
  成功とは扱わない。

詳細ログは、この作業の `output/sample-clinic/onboarding/` に保存する。

## 公式仕様

- [Codexの認証・ヘッドレス環境のログイン](https://learn.chatgpt.com/docs/auth)
- [Codex CLIのプラグイン](https://learn.chatgpt.com/docs/plugins)
- [Dockerのseccompプロファイル](https://docs.docker.com/engine/security/seccomp/)
- [UbuntuのAppArmor](https://ubuntu.com/server/docs/how-to/security/apparmor/)
