# SIMY CLIの悩み・漫画・料金案

2026年11月17日。ユーザーの追加確認を受けて日本語CLIページを改善。公開・決済設定・閉域製品の実装は未実施。

## 一次投稿から整理した課題

Redditの一次投稿を本文まで確認。少数の自己申告による事例であり、代表性をもつ市場調査、発生率の測定、SIMYへの推薦ではない。販促目的の可能性もあるため、定量的な優位性や解決保証の根拠にはしていない。

| 投稿 | 観察した課題 | ページでの対応 | 製品の範囲 |
| --- | --- | --- | --- |
| [Vibe coding is fun until your app ends up in superposition](https://www.reddit.com/r/vibecoding/comments/1s5whm6/vibe_coding_is_fun_until_your_app_ends_up_in/) | 小変更で周辺機能が壊れ、公開前に何度も操作確認する | 「直すたび、別の場所が壊れる。」からSQM説明へ | 対象の過去ルールによる確認。全回帰や不具合ゼロの保証ではない |
| [I rewrote my Claude Code session rules 41 times in six weeks](https://www.reddit.com/r/ClaudeCode/comments/1xvc77s/i_rewrote_my_claude_code_session_rules_41_times/) | 自作テストが成功しても後段の利用では動かず、未実施監査が合格に見える | 「完了でも、実際には動かない。」から完了条件と独立レビューへ | 実行・観察できた根拠と未確認を区別。実運用の受入は別 |
| [The real issue... Here's the fix... Loop](https://www.reddit.com/r/ClaudeCode/comments/1rw0bn9/the_real_issue_is_wait_actually_heres_the_fix/) | 原因の推測と修正を繰り返して進まない | 「同じ修正で、時間とトークンが減る。」から停止条件と利用状況へ | 進展なし等で判断を求める。プロバイダーの自動支出上限は保証しない |
| [What finally stopped Claude Code from undoing my old decisions](https://www.reddit.com/r/ClaudeAI/comments/1xhl3zz/what_finally_stopped_claude_code_from_undoing_my/) | 新しいセッションで過去の意図を破壊、文章のルールだけでは守れない | 守る動きを完了条件・チェックとして残し、SQMを次の確認へつなぐ | 適用できる知識と実行可能なチェックの範囲 |

調査からの編集判断として、コード生成の速さより「直した後の確認」「未確認の完了」「同じ修正の繰返し」を優先。出典はページの折りたたみ内にも掲載。利用者の声・実績として扱わない。

## 漫画・文字

既存 `site/assets/engineer-manga/release-crew-ja.webp` を再利用。元画像を変更せず、既存PANELSのピクセル境界に沿ってCSSで8コマを表示。デスクトップは2列、760px以下は1列。全コマに18pxの見出しと16pxのHTML説明。画像が読めなくてもHTMLだけで手順がわかる。

漫画とネイティブUIキャプチャーは役割を分離。漫画は説明例と表示し、実際のUI5画面は出典・サンプル注記とともに保持。本文の主要説明は16px、注釈は14pxへ拡大。

## 一般料金の仮案

既存 `site/pricing-catalog.js` を生成時に読み込み、金額のコピーを別管理しない。Starterと、既存Quality価格帯を使ったCLI品質確認向けQualityの案。機能配分も案と表示。

| 案 | 毎月払い・税別 | 毎月払い・税込参考 | 年払いの月換算・税別 | 年の支払総額・税別 | 年総額・税込参考 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Starter | USD35.80 | USD39.38 | USD29.80 | USD357.60 | USD393.36 |
| Quality | USD71.80 | USD78.98 | USD59.80 | USD717.60 | USD789.36 |

税込参考額は既存カタログに従い日本の10%。為替換算は行わない。販売未開始、仮料金、既存SIMY契約者への追加課金の有無は未確定と明記。決済やsignupへの購入リンク、新Stripe Priceは追加せず、相談リンクを設置。AI利用料は別途。

閉域は確定済みの個別見積もりを保持。紹介制度も独立の見出しへ引き上げ、10%・14日・50日・1万円という制度案と受付未開始を確認できる。紹介プログラムの台帳・API・DBは今回変更していない。

## 検証

- `python3 scripts/build-engineering-pages.py --check`: Engineering pages verified.
- `node --test tests/engineering-pages.test.cjs tests/site-audit-regressions.test.cjs`: 11 passed、0 failed。
- `python3 scripts/check-home-seo.py`: SEO checks passed。
- 価格と税込・年総額がカタログに一致し、購入リンクが混入しない回帰チェックを追加。
- in-app Browserで360/390/720/768/1024/1440 CSS px。横はみ出し0。16px本文・14px注記をcomputedStyleで確認。
- 768px以上の2列料金カード・CTAの上端差0px。720px以下は1列。漫画は760px以下で1列。geometry.json。
- モバイルは漫画1コマ全体とHTML説明を確認。原画への拡大リンクあり。ネイティブズーム・物理端末・Safari/Firefoxの試験は未実施。
- 上部ナビから漫画・料金・閉域・紹介へ操作。紹介制度のリンクからaffiliate.htmlへ遷移して画像ロードを確認。開発専用の紹介者画面サンプルも別タブで表示。
- スクリーンショットは同ディレクトリのJPEG。顧客データ・実際の報酬を示すものではない。

## 2026-11-17 日英画像の再確認

言語別のv1.2.11ネイティブ画面・紹介画面・公式バッジへ更新。
[画像の棚卸しと確認記録](../image-locales/verification.md)を参照。
