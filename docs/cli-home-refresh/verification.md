# SIMY CLI 日本語ページ

対象: `/for/engineers/`。HTMLをローカルで作成。コミット・push・公開は行っていない。

## 機能の一次情報

2026年11月17日（日本時間）確認。

- 配布メタデータ: <https://simy.one/downloads/simy-cli/windows/latest.json>。
  `version: 1.2.8`, `publishedAt: 2026-11-16T14:05:25.572Z`, x64, unsigned。
- GitHub `SpecialistDoctors-Inc/simy-cli` の `v1.2.8` タグ:
  `1c4f7d7ccd55bfbe007477885776c275f952b8a6`。
- インストール済みCLIの `simy --version`: `1.2.8`。
- 同リリースに同梱された `README.md` の Bridge / Requirements / Projects and @simy /
  Delivery Loop / SQM record / Notifications / Other computers を参照。
  導入条件、対象になる会話、停止条件、SQMの明示的な有効化、SSH接続を照合。
- `simy update --check` は自動更新を無効化した起動環境のため `disabled`。
  この結果を最新版の根拠には使わず、配布メタデータとリリースタグを確認した。
- GitHub Releases の latest は旧0.7系を返したため、最新版判定には使っていない。

## 掲載画面

`site/assets/cli-ui/{overview,goal,sqm,connection,usage}.png`。
5枚とも2360×1600。ネイティブSwiftUIの描画結果であり、HTMLで模造したUIではない。

v1.2.8タグから取得した `packaging/macos-app/Sources` を、同梱の `build.sh --dev`
でビルド。ローカルSDKの27.2ではSwiftUIのマクロが不足したため、既存の
`SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk` を指定した。
パッケージ追加・CLI本体の変更・実ユーザーのホストへの接続は行っていない。

`scripts/capture-cli-ui.py` は公式の `ok` fixtureとネイティブsnapshot機能を使う。
`scripts/cli-ui-fixture.mjs` で説明用データだけを日本語に置き換え、古いfixtureの
バージョン表示を実際のリリース情報に合わせた。接続情報・件数・指摘・結果はサンプル。
実作業、プロバイダー実行、本番での成果、実アカウントの接続試験を示すものではない。
画像のハッシュと出典は `site/assets/cli-ui/manifest.json` に記録した。

再取得には、対応するv1.2.8ソースで作成したdev実行ファイルと同リリースのCLIを指定:

```sh
python3 scripts/capture-cli-ui.py --app /path/to/SIMY-Dev-executable \
  --node /path/to/release/runtime/bin/node --entry /path/to/release/cli/src/index.js
python3 scripts/build-engineering-pages.py
```

共有画像のHTMLは `scripts/engineering-cli-social.html`。
1200×630のブラウザーキャプチャーをPNGに変換して `site/assets/cli-ui/social.png`
に保存。共有画像の一括生成も、同じテンプレートを参照する。

## 表示・操作の観察

- in-app BrowserでローカルHTMLを表示し、5枚すべての読込を確認。
- 360 / 390 / 720 / 768 / 1024 / 1440 CSS pxを測定。
  `document.documentElement.scrollWidth === innerWidth` がすべての幅で成立。
- セクションの左右端は各幅ですべて一致。デスクトップの3つの機能リンクの
  上下端差は0px。計測値は `geometry.json`。
- 720pxは1440pxの200%相当のリフロー幅。実ブラウザーのネイティブズーム操作や
  Safari・Firefox・物理端末での確認は行っていない。
- 各ページ内アンカーの遷移先が存在。全ローカルリンク・リソースの実在を確認。
- スマートフォンで導入条件を開き、条件が縦に表示され、横はみ出しがないことを確認。
- FAQの開閉、原寸画像リンク、ダウンロードページへの導線を確認。
- キャプチャー: `desktop.jpg`, `mobile.jpg`, `full-page.jpg`。

## コマンドの結果

```text
python3 scripts/build-engineering-pages.py --check
Engineering pages verified.
python3 scripts/build-localized-home.py --check
Localized homepages and sitemap verified.
python3 scripts/check-home-seo.py
SEO checks passed: 6 raw-HTML locales, metadata, hreflang, schema, FAQ, navigation, local assets and sitemap.
```

関連テストは `engineering-pages`, `home-localized-links`, `home-seo-routing`,
`occupation-publishing`, `social-preview`。実行出力は `tests.log`。
生成済み日本語HTMLは生成元と一致し、他言語の生成HTMLは変更していない。
既存の無関係な変更や作業中のファイルは保持した。

## 2026-11-17 日英画像の再確認

言語別のv1.2.11ネイティブ画面・紹介画面・公式バッジへ更新。
[画像の棚卸しと確認記録](image-locales/verification.md)を参照。

## 2026-11-17 機器の向きの修正

漫画3コマ目のパソコン背面に描かれていた画面を修正。
[画像・編集指示・検証記録](device-geometry/verification.md)を参照。

## 2026-11-17 実装・確認・続行の役割説明

SIMYが自ら修正・操作確認するように読めた漫画と説明を修正。
[公式資料との照合と検証記録](mechanism-clarity/research-and-verification.md)を参照。
