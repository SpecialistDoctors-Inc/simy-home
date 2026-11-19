# 全ページレビューのExcelと改善計画の実行結果

2026年11月19日（日本時間）。対象はsimy.oneの199 HTML。今回の実装は前回の共通アクセシビリティ改善に続くもので、元ブランチの既存変更と混在しないworktreeで行った。本番への公開状況は改善計画Q35と配信証跡で管理する。

## Excelの範囲

`SIMY_全ページレビューと改善計画_20261119.xlsx` に38の指摘・管理項目、改善の優先度・依存条件・概算工数・合格条件・実測結果、199ページ、2,388のページ別検査、50の専門家視点、分野内・分野間の採否、740のブラウザーケース、2,534の構造化データのフィールド観察、FAQ1,114組の照合を収録した。フィルター、固定見出し、状態一覧、Excel内の件数式、集計グラフを付けた。Excelの保存後に読み戻し、シート・行数・数式・専門家件数を検証した。

「完了」は各行に定義した実装・ローカル検証の範囲を指す。38項目中30項目が完了、2項目が部分完了、1項目が公開検証中、5項目が外部確認待ち。欠落を件数進捗で相殺せず、全要件達成や本番反映済みとは扱わない。専門家の本人参加、実発言、客観的な世界順位も主張しない。

Mac側の一覧1,382件を追加調査し、候補56件と既知2件から987メッセージを取得した。重要要件30件を原文に対応付け、公開用Excelに要約の照合シートを追加した。原文を含む私用版には取得範囲・メッセージ・要求候補・訂正・同文集約の5シートを追加する。一部の履歴は取得ツールのサイズ上限で未確認。詳細はrequirements-coverage.mdを参照。

## 実行した改善

- main/skipを185の描画文書へ適用。後ろに置かれていた14テンプレートの既存skipをナビ前へ移し、先頭のTabで到達させた。
- 現行・旧contactで、旧React bundleが静的本文を消す問題を修正。不要な起動を外し、JSなしでも本文・連絡先を保持した。32px見出し、読みやすい本文、44px以上のメール導線を専用CSSで整え、相談方法と必要情報を6言語で具体化。既存18言語の辞書・bundleを保持した。
- 新ガイド10件の著者・公開日を可視情報とschemaに一致させた。公開日は初回追加Git記録の2026-10-04を根拠とする。14文書のパンくずの名称・順序・URL・positionを共通データから生成するようにした。
- ニュース2件で本文に裏付けのある公開日2026-10-05を可視timeとschemaへ追加。確実な編集日を判断できないdateModifiedは捏造していない。
- 日本語の生成見出しで負の字間を外した。共有CTAの固定最小幅を親に収め、長いラベルを折返すようにした。
- スペイン語の320pxヘッダーで12pxの横はみ出しを修正。signupラベルと登録URLのlang/localeを表示言語へ同期し、地域選択は言語と独立して保持した。サービス専用CTAは上書きしない。
- aboutの補足文字を濃くし、変更トークンを使う可視22要素で最小コントラスト5.0735:1を測定。サイト全体のWCAG適合を認定したわけではない。
- law-firmの6つの漫画要素に実PNG寸法を追加。clinic/lawの下方補助4画像をlazy化。ヒーローと、既存テストで早期読み込みを要求するISMSマークはeagerを維持した。属性だけでCLS改善の実測とはしない。
- 通常ナビの現在地、変更した共有CSS/JSの内容ハッシュ、生成器間の順序とlaw専用配信パッケージの整合を保った。checkout JSON/JSとpricing-catalogの保護ハッシュは変更していない。UI変更で変わるhome6HTMLのハッシュと、正しいパンくず追加によるsales2件のリンク台帳のみ更新した。

## 検証結果

- 全1,650テスト成功、失敗0、skip0。`node --test --test-concurrency=2 tests/*.test.cjs`。
- home、content、pharma、FP、engineering、料金予告、service pricing、HP業種、共通headerの生成check、およびhome/site SEO、law-firm release、guide intentが成功。
- 構造化データ監査：159 indexページ、2,534フィールド観察。FAQ1,114組すべてで、schemaの質問と同じ可視summary、および同じ回答領域内のschema回答を照合。内容の事実性・最新性、検索表示の適格性は別の確認事項。
- Chromium 1 browser、外部通信遮断、reduced-motion、320/390/768/1440 CSS pxで185文書×4幅=740ケース。最初のTab、skip表示、Enter後main focus、main一意、ページ横はみ出し、本文存在を測定。初回は16ページ・61ケースで問題を検出し、同条件で修正後は0。contact専用CSS追加後は対象8ケースを追加再確認した。
- JavaScript無効の変更代表6文書でmain1と本文を確認。640 CSS pxのリフローproxy6ケースで横はみ出し0。これは1280pxを200%にしたときのレイアウト相当の検査であり、実機ブラウザーズームを操作した記録ではない。
- accountの動的言語切替は6言語×320pxでmain1、表示言語と登録URLの一致、横はみ出し0を確認。
- 現行本番への読み取りHTTPで159/159 URLが200、159/159でcanonical一致。これは今回の変更版を本番へ公開した証拠ではない。

## 証跡

- `evidence/browser-expanded-before.json`：初回740ケースと61件の指摘。初版Excelから復元したスナップショットであることを記録。
- `evidence/browser-expanded.json`：修正後740ケース、no-JS、リフローproxy。
- `evidence/account-locale-browser.json`：動的言語切替6条件。
- `evidence/schema-inventory.json`：全schemaフィールドとFAQの対応。
- `evidence/about-contrast.json`：22要素の文字色・背景色・比率。
- `evidence/production-http.json`：現行本番の状態・最終URL・canonical・title。
- `evidence/contact-mobile.png`、`evidence/guide-ja-mobile.png`：変更後のローカル実画面。

## 残る条件

過去Codex依頼の原文と後続訂正の網羅、全ページの提供条件・一次資料との意味上の照合、母語品質、初見読者のタスク調査、Search Console、実利用p75のCore Web Vitals、認証・実送信・課金を伴う外部アプリの検証が残る。実施していない検証を成功扱いにせず、詳細はExcelの残件行に記録した。[ドラフトPR #494](https://github.com/SpecialistDoctors-Inc/simy-home/pull/494)を作成し、GitHubのStatic Site check成功を確認した。今回の差分で確認・修正した不具合を本番へ反映し、配信を検証する。原文照合と外部調査の残件は公開後も保持する。公開の成功を全依頼の充足とみなさない。

## 再生成

公開サイト本体に依存を追加せず、Excel出力だけで開発用のopenpyxl 3.1.5を使う。

```sh
python3 -m venv ~/.cache/simy-sitewide-quality-xlsx
~/.cache/simy-sitewide-quality-xlsx/bin/pip install openpyxl==3.1.5
~/.cache/simy-sitewide-quality-xlsx/bin/python scripts/export-sitewide-quality-review.py
```

レビューの状態は`improvement-plan.json`、観測値はHTMLと証跡JSONから再生成する。Excel内だけの手編集は再生成時に上書きされる。ブラウザーの再実行は既存PlaywrightをNODE_PATHで参照し、静的プレビューを起動したうえで`node tests/sitewide-quality-browser.cjs`を実行する。プレビューは検証終了後に停止する。
