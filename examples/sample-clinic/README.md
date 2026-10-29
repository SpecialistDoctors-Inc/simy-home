# SIMY sample clinic

架空のクリニックの静的HP。`sample-clinic.simy.one` と
`sample-clinic-dev.simy.one` 向けの配布物を生成します。
このディレクトリだけをビルドでき、既存のSIMYホームページから独立しています。

## Build and inspect

```sh
node examples/sample-clinic/build.mjs
node --test examples/sample-clinic/tests/*.test.mjs
python3 -m http.server 8766 --bind 127.0.0.1 --directory examples/sample-clinic/dist
```

`content/clinic.json` が院名・トップの文章・写真・診療時間・お知らせの
編集元です。`site/index.html`、`site/styles.css`、`site/site.js` は構成・見た目・
操作の編集元です。生成先 `dist/` はGit管理せず、直接編集しません。
データの文字列はHTMLエスケープし、画像は同梱したローカル画像だけを許可します。

`SITE_ENV=dev|prod` と `SOURCE_REVISION=<full Git SHA>` を指定すると環境名と
ソースSHAを `version.json` に記録します。`artifactHash` は静的配布物の
ファイル名とバイト列から計算します。未コミットのローカル表示では
`sourceRevision` はベースのコミットであり、変更内容の識別は `artifactHash` を
使います。ローカル表示はデプロイ済みの証拠ではありません。

## Verification scenario

初回の受付例は「12月12日の臨時休診をお知らせに追加」です。
ユーザー側Codexが掲載箇所、年、時刻・タイムゾーン、掲載終了の扱いを確認し、
Spreadsheetに依頼版を追記します。開発側Codexが依頼を読み、
`content/clinic.json` を変更してビルド・テストし、devのプレビューを返します。
確認対象の版をユーザーが承認した後、同じ配布物をmainの公開に結びつけます。

ローカルテストは、依頼でお知らせを追加した場合に新しい静的HTMLとハッシュが
変わり、元の配布物は変わらないことを確認します。Spreadsheetの実接続、
Codexの自動起動、メール配信、AWSへの反映はこのテストの範囲外です。

共有Sheetと二つのCodexの手順は
[運用契約](../../docs/hp-management-spreadsheet-workflow.md)、AWS設定は
[配置手順](../../docs/sample-clinic-deployment.md) を参照してください。

## Assets

`site/assets/clinic-interior.png` はbuilt-in ImageGenで制作した架空の院内写真です。
制作プロンプト：自然光が入る日本の街の内科クリニックの待合室。淡いオーク材、
アイボリーの壁、セージ色の椅子、窓際の植物。人物・文字・ロゴ・透かしなし。
写実的な建築写真、横長。実在の医院や患者を表しません。
ロゴとアクセス図はSVGで制作したオリジナルの図形です。
