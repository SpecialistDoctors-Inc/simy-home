# ガイドページ執筆ブリーフ（site/guides/ 共通）

テンプレートは `site/guides/plaud.html`（2026-10-01 版）。CSS、ヘッダー、フッター、JSON-LD の形、セクションの型をそのまま流用する。

## 守ること

1. **2原則**（`docs/handoff/2026-09-30-guide-pages-handoff.md` 末尾）: 読者が「そんなことがやりたかった」と気づき「SIMY でないとできない」と自然に感じる。文字で説明せず、眺めて分かる。
2. **骨格**: Hero（relay 図）→ 01 こうなっていませんか（pain カード3枚）→ 02 本当はこうしたかった（wish カード4枚、4枚目は「判断だけ」）→ 03 ○○はここで止まる（timeline、gap マス）→ 04 SIMY がつなぐ（timeline 2段＋3語＋接続手順）→ 05 1件で比較（sample）→ 06 業種別（ind）→ 07 はじめ方 3ステップ（steps3）→ 08 リファレンス（fold details に SEO 本文を折りたたむ）→ 09 FAQ → 10 参考情報 → closing CTA。
3. **差別化の軸**は3つだけ: 「会議・チャットから拾う（起点が自分でない）」「あなたのやり方で（会話から学ぶ、毎回頼まない）」「判断だけ返す（My Actions）」。「定期実行できる」「下書きで止める」「承認付き」は Cowork・Codex・Copilot にもあるので売りにせず、安心材料として書く。
4. **SIMY の仕様で書いてよいこと**（ソース確認済み）: クラウド実行はユーザー自身の ChatGPT アカウント（Codex）で、Codex の利用はお使いの ChatGPT プランの範囲。ローカルでは `simy` デスクトップアプリ／CLI が PC 上の Claude Code を実行役にできる。Claude Code と Codex の会話履歴（`~/.claude/projects`、`~/.codex/sessions`）をデーモンが既定90日分読み、本文はサーバーに保存せず WorkFlow 候補「SIMY からの提案」を作る。Gmail は下書き保存まで。Slack 投稿・Notion 書き込みは承認付き。iOS アプリあり。Plaud／Notion／Google 連携あり。
5. **書かないこと**: 「Claude のプランで動く」「Gemini で動く」、SIMY の具体的な金額（料金は `/?lang=ja#pricing` へリンク）、「387 defects」「1/5→5/5」、期限付きの情報（「6/22 まで無料」など）、未確認の製品名（Codex App Server は FAQ の既存文にだけ残す）。
6. **事実の扱い**: 他社製品の機能・料金は `docs/handoff/youtube-research-2026-10-01.md` と各構成案に「確度 高」とあるものだけ書き、「2026年10月時点」と添える。価格は税込か税別かを明記。引用は場面カードの語彙に溶かし、動画名・チャンネル名は本文に書かない。
7. **技術**: 外部 CSS/JS/フォントなし。canonical と og:url は `https://simy.one/guides/<name>.html`。og:image は `https://simy.one/ogp.png`（1200×630）。役割 `role="img"` の図には必ず「イメージです」の caption。FAQPage JSON-LD の質問と回答は、可視 FAQ（`<details><summary>Q</summary><div class="a"><p>A</p></div></details>`）と文字どおり一致させる。BreadcrumbList は可視パンくずと一致。TOC の href は `section.sec` の id と同順。内部リンクは存在するファイルだけ（`/guides/plaud.html`、`/guides/chatgpt.html`、`/integrations.html`、`/security.html`、`/privacy.html`、`/terms.html`、`/?lang=ja#pricing`）。
8. **分量**: 本文（script 除く可視テキスト）は 1.2〜1.8 万字。pain/wish カードは見出し12字以内＋1行。fold の中以外に3文を超える段落を置かない。
9. **UTM**: `utm_campaign=<name>_guide`、`utm_content=header|hero|closing`。
10. 相互リンク: フッターに他ガイドへのリンクを入れる（PLAUD、ChatGPT、Claude、Codex、Cowork、AI議事録）。存在しないページには張らない（この時点で存在するのは plaud と chatgpt）。
