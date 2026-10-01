# ガイドの多言語化ルール（翻訳エージェント向け）

## 対象と置き場所

日本語版（正本）は今の場所のまま。翻訳版は言語フォルダに置く。

| 日本語版（正本） | 翻訳版 |
| --- | --- |
| `site/guides/<name>.html` | `site/guides/<code>/<name>.html` |
| `site/guides/index.html` | `site/guides/<code>/index.html` |
| `site/download.html` | `site/download/<code>.html` |

`<name>`: claude, codex, cowork, chatgpt, plaud, meeting-notes。

| code | `<html lang>` | og:locale | ホームの言語パラメータ | 登録リンクのパラメータ |
| --- | --- | --- | --- | --- |
| en | en | en_US | `/?lang=en` | `lang=en&locale=en&region=us` |
| zh-hans | zh-Hans | zh_CN | `/?lang=zh-Hans` | `lang=zh-Hans&locale=zh-Hans`（region なし） |
| es | es | es_ES | `/?lang=es` | `lang=es&locale=es&region=es` |
| fr | fr | fr_FR | `/?lang=fr` | `lang=fr&locale=fr&region=fr` |
| hi | hi | hi_IN | `/?lang=hi` | `lang=hi&locale=hi&region=in` |

## 作り方

1. 日本語版をコピーし、CSS・構造・クラス名・JS・アニメーションは一切変えない。変えるのはテキストと、下のリンク・メタ情報だけ。
2. **直訳ではなく、その言語の読者に自然な文章にする。** 見出しは短く、場面カードは見出し・1行とも短く。「眺めて分かる」原則（`docs/handoff/2026-09-30-guide-pages-handoff.md` 末尾）を守る。
3. **日本固有の内容は置き換える。**
   - 円の金額（ChatGPT・Claude・PLAUD・各ツール）は書かない。「各社の公式料金ページで、お住まいの地域の価格を確認」に置き換え、公式リンクを残す。米ドルで確度が高いもの（ChatGPT Plus 月20ドル、Go 月8ドル、Claude Pro 約20ドル）は「2026年10月時点・税別」と添えて書いてよい。
   - 「消費税」「日本のデータセンター」「PLAUD株式会社」など日本向けの記述は、言語版では一般化するか省く。
   - 日本の YouTube 動画を根拠にした場面は、そのまま場面として使ってよい（出典の記述は「AI活用の解説動画を参考」とだけ書く）。
   - 「チャットGPT」「クロード」「コーデックス」の読み・表記ゆれの説明は日本語特有なので削る。
4. **SIMY の事実**は `docs/handoff/guide-page-brief.md` の4・5に従う。特に: SIMY のクラウド実行はお使いの ChatGPT アカウント（Codex）で動く。SIMY デスクトップアプリで Claude Code の会話を取り込み、Claude Code を動かせる。できないのは Claude のトークン連携だけ。Gemini のトークン連携は開発中。無料プランはない（登録はプラン選択→メール確認→カード決済）。SIMY の金額は書かず `/?lang=<home>#pricing` へリンク。
5. **リンクの書き換え**
   - 他ガイド・一覧へのリンクは同じ言語版へ（`/guides/<code>/<name>.html`、`/guides/<code>/index.html`）。
   - ダウンロードは `/download/<code>.html`。
   - ホームは `/?lang=<home>`、料金は `/?lang=<home>#pricing`。
   - `/privacy.html`・`/terms.html` には `?lang=<home>` を付ける。`/security.html`・`/integrations.html` はそのまま。
   - `app.simy.one` の signup・login リンクは上表のパラメータに置き換える。UTM の `utm_campaign` は日本語版と同じ値に `_<code>` を付ける（例 `claude_guide_en`）。
   - 外部の公式サイトは、英語版などの言語版 URL があればそれに替える（例 `https://openai.com/codex/`、`https://claude.com/pricing`、`https://www.plaud.ai/`）。存在が不確かな URL は日本語版の URL のまま残す。
6. **メタ情報**
   - `<title>` は検索語を先頭に、全角換算で35字前後（英語なら60文字以内）。`| SIMY` で終える。
   - description は英語で155文字以内、他言語も同程度。
   - canonical と og:url は翻訳版自身の絶対 URL。
   - og:image は `https://simy.one/ogp.png`（日本語の文字入り画像は使わない）。
   - JSON-LD の `inLanguage` を言語コードに。Article の headline・description、BreadcrumbList の name（「ガイド」→ Guides など）、FAQPage を訳す。**可視 FAQ と FAQPage の質問・回答は文字どおり一致させる。**
   - hreflang の `<link rel="alternate">` は入れない（後でまとめて入れる）。
7. **触らない**: `<script src="/analytics.js" defer>`、ダウンロードページの JS、`role="img"` の図の構造。図の中のテキストと `aria-label` は訳す。画像の説明 caption（「※ 画面は説明用のイメージです」）も訳す。
8. **品質確認（必須）**: 書き終えたら Bash で次を確かめ、全部通るまで直す。
   - JSON-LD がパースできる。
   - 可視 FAQ（`.faq details summary` と `.a`）と FAQPage の mainEntity が完全一致。
   - TOC の href が `section.sec` の id と同順。
   - `href="/..."` のリンク先がすべて `site/` に存在する（他言語版のファイルは、同じ担当範囲のものだけ確認。担当外の言語版・ページは存在しなくてよい）。
   - 日本語の文字（ひらがな・カタカナ）が本文に残っていない（`[぀-ヿ]`）。ただし製品名や引用は除く。

## 追記（2026-10-01 第2弾：中国系LLM・Qwen）

- 対象: qwen, china-llm, deepseek, kimi, minimax, glm, doubao（後で qwen-local）。日本語版はレビュー済みの正本。
- **データの扱い・規制の記述は意味を変えずに訳す。** 日本の当局（個人情報保護委員会、デジタル庁）の注意喚起は「Japan's Personal Information Protection Commission」など、固有名詞を明確にして残す。読者の国の規制を新たに書き足さない。
- **SIMY との関係の文は訳すだけで足さない。**「現時点では接続しない」「お使いの ChatGPT（Codex）アカウントと、PC上の Claude Code で動く」。提携・予定・開発中は書かない。
- 料金は日本語版にある米ドルの数字だけ残してよい（税の扱いは公式へ）。円は書かない。
- 言語切り替えとフッターは、後で一括で整えるので、日本語版のまま訳したリンク（同じ言語版のパス）で構わない。
- 各言語の `guides/<code>/index.html` に、日本語版 `guides/index.html` の「中国のAI・オープンモデルを使う人へ」区分（8枚のカード、ItemList JSON-LD の追加分、title・description の変更）を訳して追加する。
