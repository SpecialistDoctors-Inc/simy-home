# HP管理の業種一覧

`/hp-management/` は公開中の業種を選ぶ入口です。クリニックの公開URLは `/hp-management/clinic.html`、ソースは `site/hp-management/clinic/index.html` です。弁護士の公開URLは `/hp-management/law-firm.html` です。既存の詳細ページ・診断フォーム・料金・申込みは各業種で管理します。

業種一覧の正本は `scripts/hp-management-industries.json`（version 1）です。`scripts/hp_management_industries.py` が共通ヘッダー・一覧生成・SEOチェックに渡します。手動で業種リンクをヘッダーへ追加しません。

業種を追加するときは次の手順で更新します。

1. 安定した小文字スラッグの `id` と、`label`・`nav_label`・`description` を登録します。準備中は `status: "draft"` にします。draft は一覧・ナビゲーション・構造化データへ表示されません。
2. `url` は `/hp-management/` 配下の業種固有 `.html`、`source` は `site/` からのHTML相対パス、`checkout_config` は同配下の料金設定JSONにします。`url` と `source` が違う場合は公開処理にもその対応が必要です。カタログの登録だけで公開エイリアスは配信されません。
3. 公開可能な実体・無料診断の `#diagnosis`・料金の `#pricing`・有効な料金設定を用意し、`status: "published"` にします。公開業種はすべて一覧へ表示されます。`featured: true` の公開業種から登録順に最大2件がナビゲーションへ渡ります。
4. 新規ページのSEO inventory・サイトマップ・共有カードを登録し、公開対象の所有権マニフェストへ明示的に追加します。料金一覧の最低月額・税込額は登録済み料金設定から生成し、別契約や共通料金を作りません。
5. `python3 scripts/build-hp-management-industries.py` を実行します。共通ヘッダーを含む一覧HTMLだけを再生成します。共有ヘッダーを他ページにも反映する場合は、そのページの生成手順を実行します。
6. `python3 scripts/build-hp-management-industries.py --check`、`node --test tests/hp-industry-catalog.test.cjs tests/social-preview.test.cjs`、`python3 scripts/check-site-seo.py` で確認します。SEOチェッカーは `published_aliases()` で広告URLをソースへ解決し、クリニックHTMLを複製しません。

重複id・URL・ソース、ハブ予約URL、パストラバーサル、未作成の公開ソースは検証で拒否します。カタログ検証とHTML生成は標準ライブラリだけで動き、追加依存は不要です。

## 共通ナビゲーションの公開

`docs/seo/hp-industry-navigation-release.json` は一回の公開でレビューするオブジェクトと内容ハッシュを固定したスナップショットです。通常の本文変更や業種単独公開のたびには更新しません。共通ナビゲーションを公開するときに `python3 scripts/hp_industry_release.py --build` で作成し、`--check` と独立レビュー後に、そのSHAを指定して専用ワークフローを実行します。全サイト同期・削除は行いません。
