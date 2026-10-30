# HP管理の設定手順 はじめに読むページ

更新日：2026-10-30。対象は、医院のCodexで要望を受け付け、Google Sheetsを介して
SIMYのCodexが静的ホームページを修正する構成です。

**最初は、SIMY担当者が同席してサンプル1件をdevへ反映するところまで設定します。**
現在、自動着手とメール通知は未接続です。シートに依頼が入った後は、SIMY担当者が
開発側Codexに着手を指示します。実装・テスト・dev反映をCodexへ依頼する手順はあります。

## 1. 誰が何を用意するか

| 担当 | 用意するもの | 読む手順書 |
| --- | --- | --- |
| SIMY担当者 | 医院と依頼者の確認、専用シート、対象サイト情報、受け渡し窓口 | [SIMY向け設定手順](hp-management-setup-guide.md)の2〜4 |
| 医院の担当者 | Codexへのログイン、Google Drive接続、受付スキル | [医院向け設定手順](hp-management-customer-guide.md)の1〜4 |
| SIMY開発担当者 | 開発用Codexとスキル、Google接続、GitHub・AWS配信設定 | [SIMY向け設定手順](hp-management-setup-guide.md)の6〜7 |

医院側にGitHub・AWSの管理認証やDockerを配る必要はありません。
Dockerは、担当者が新しい環境から導入試験を再現するときだけ使います。

## 2. SIMYが先に準備する

1. 対象医院と依頼できる担当者を確認し、管理するサイトを決めます。
   サンプルではサイトIDを `sample-clinic` とします。
2. 医院専用のGoogle Sheetsを作成し、`ご利用ガイド`、`Requests`、`Events` の
   3タブを用意します。データ用の見出しは4行目、依頼・イベントは5行目からです。
   貼り付け用の見出しは[設定手順の3](hp-management-setup-guide.md#3-医院専用google-sheetsを作る)にあります。
3. 確認済みの医院用Googleアカウントと、SIMY開発用Googleアカウントに共有します。
4. 確認用URL、公開先、変更できるリポジトリ・パス、SIMYの着手担当者を照合します。
5. サンプル試験の対象と許可範囲を、[設定手順の4](hp-management-setup-guide.md#4-医院利用者と対象を結び付ける)
   に従って試験セッションへ渡します。実医院向けの登録・利用開始手続きは未提供です。

| サンプルの設定 | 値 |
| --- | --- |
| 確認用ページ | [sample-clinic-dev.simy.one](https://sample-clinic-dev.simy.one/#news) |
| 本番公開先 | [sample-clinic.simy.one](https://sample-clinic.simy.one/) |
| リポジトリ | `SpecialistDoctors-Inc/simy-home` |
| サイトの対象パス | `examples/sample-clinic/` |
| お知らせなどの編集元 | `examples/sample-clinic/content/clinic.json` |
| 確認用ブランチ／公開処理ブランチ | `dev` / `main` |

URLは用途を示します。本番への今回の依頼の反映は、公開処理と実ページの確認で判断します。

## 3. 医院が設定する

[医院向け設定手順](hp-management-customer-guide.md)を開き、次の順に進めます。
同手順書には、Codexへそのまま貼り付ける導入・接続確認メッセージがあります。

1. 公式アプリをインストールし、自分のChatGPTアカウントでログインしてCodexを選びます。
2. **Plugins → Google Drive** を導入し、SIMYがシートを共有したGoogleアカウントで接続します。
3. Codexに専用シートを読ませ、接続先アカウント・シート名・3つのタブを確認します。
4. `hp-customer-intake` スキルを指定された固定版から導入します。
5. 新しいチャットでスキルを認識し、同梱の契約ファイルを読めることを確認します。

アプリ内のCodexの選び方は[公式クイックスタート](https://learn.chatgpt.com/docs/quickstart)、
接続の操作は[公式Plugins案内](https://learn.chatgpt.com/docs/plugins)を参照します。

受付スキルは、変更する場所、正しい文章、必要な日付、画像や予約への影響、
確認方法を必要に応じて質問します。最初から医院に技術的な要件書を書いてもらう必要はありません。

## 4. SIMY開発側を設定する

1. SIMYの開発環境で `hp-developer-delivery` スキルを導入します。
   [導入メッセージ](hp-management-setup-guide.md#6-simy開発側のcodexを設定する)を使います。
2. 開発用のGoogle接続で同じ専用シートを読めることを確認します。
   医院側と別の接続を用意します。既存の同一管理アカウントによる試験は、権限分離の検証に数えません。
3. GitHubの対象リポジトリと専用worktreeを確認します。
4. [配信設定](hp-management-setup-guide.md#7-dev本番の配信設定を用意する)に従い、
   dev・本番のGitHub Environment、AWS OIDC role、S3・CloudFrontの対応を確認します。
   既存のサンプル環境は再作成せず、設定を読み戻して照合します。

受付と開発は別のCodexチャットで行い、共通の依頼IDとrevisionで引き継ぎます。

## 5. 最初の1件を往復させる

| 順番 | 行う操作 | 完了の確認 |
| --- | --- | --- |
| 1 医院 | [サンプル依頼文](hp-management-customer-guide.md#5-更新を依頼する)をCodexへ送る | `Requests` と `ready_for_dev` イベントを読戻し、依頼ID・revision・本文が一致する |
| 2 SIMY | 依頼ID・revisionを指定して[開発側へ着手を指示](hp-management-setup-guide.md#8-依頼を受けdevへ反映する)する | Codexが同じ依頼を読み、修正・テスト・レビューを行う |
| 3 SIMY | 許可されたdev向けPR・マージ・配信を進める | 配信版と、PC・スマートフォンの変更箇所を確認する |
| 4 開発側Codex | 結果と確認用URLを `Events` に追記する | `test_result`・`dev_preview_ready` に版と検証結果が記録される |
| 5 医院 | 新しいCodexチャットから同じ依頼の結果を取得する | 記録された版の確認用ページを開き、依頼内容を確認できる |

この往復が初回設定の合格条件です。シートへの保存だけではdev反映は完了していません。

## 6. 本番公開とメール通知

本番公開は、医院が確認した **依頼ID・revision・source SHA・artifactHash・artifact ID**
に対する公開意思を確認してから進めます。
[公開手順](hp-management-setup-guide.md#9-承認された版を本番へ公開する)では、
main上の手動workflowと保護されたEnvironmentを使い、承認されたdev成果物を公開します。
mainへのマージだけではサンプルは公開されません。

メール通知は未接続です。現状の確認案内はSIMY担当者が行います。自動化するには、
確認済みの宛先・送信元・メールprovider・重複送信防止・送達確認を接続する必要があります。
詳細は[残作業](hp-management-setup-guide.md#10-メール通知と自動運用を有効にするための残作業)を参照してください。

## 7. スキルだけで自動運用が始まるか

| 部品 | 役割 | 現在の状態 |
| --- | --- | --- |
| 受付・開発スキル | Codexが確認する項目と処理手順を定める | サンプルで導入・利用済み |
| Google DriveプラグインのMCPツール | 認証された接続でGoogle Sheetsを読み書きする | サンプルで実書込・読戻し済み |
| SIMY WorkFlow受付基盤 | 依頼・権限・重複・取消を管理する | 2026-10-30の記録でdev配備済み。HP機能は既定OFF |
| 受付から開発・配信への接続 | 依頼を受けて開発を起動し、devの完了まで追跡する | 未接続。現在はSIMY担当者が着手を指示 |
| メール通知 | 確認準備完了・公開完了を届ける | 未接続・未送信 |

受付基盤の配置と、Codex＋Sheetsの手動試験は別の経路です。HP機能フラグを有効にするだけで
両者が接続されるわけではありません。基盤の受付結果 `HP_DELIVERY_NOT_CONFIGURED` は、
依頼が保存されても配信設定がないことを示します。

新規環境からの導入を再現する担当者は、[Dockerでの試験記録](hp-management-zero-setup-test.md)を参照します。
