# SEO活用ガイド5ページ 引き継ぎ（2026-09-30 統合）

5つのセッション（PLAUD / ChatGPT / Claude / Codex / Cowork）で進めていた「隣接プロダクトのユーザー向け活用ガイド」企画を、このチャネルに一本化する。

共通の型：`site/guides/plaud.html` の CSS・コンポーネント・JSON-LD（Article + BreadcrumbList + FAQPage）・UTM 付き CTA を流用した日本語1ページ。差別化の根拠は simy-cli の Delivery Loop / SQM の実装。製品仕様はサイト文言ではなく製品リポジトリのソースで確認する。

## 進捗一覧

| ページ | 状態 | ブランチ / 成果物 | dev |
| --- | --- | --- | --- |
| guides/plaud.html | **完成・dev検証済み**。未push・PR未作成 | `claude/simy-page-structure-5cafbd`（6コミット、ローカルのみ）。`docs/seo/seo-complete-definition.md`、`docs/seo/plaud-seo-check.md`、`tests/plaud-seo.test.cjs`（62/62合格）、`site/integrations.html` に Plaud カード、OGP画像 | 200 |
| guides/chatgpt.html | **完成・dev配信済み**。PR未作成 | `claude/chatgpt-cooccurrence-page-structure-fe88bd`（`94c526f`、push済み）。dev へは cherry-pick `839712b` | 200 |
| guides/claude.html | **構成案完成**。本文未着手 | `docs/handoff/claude-page-structure.md`（元は `simy-page-structure-8e29d0` の untracked ファイル。13章＋FAQ12問、実装ファクトシート付き） | 404 |
| guides/codex.html | **構成案完成（12章）**。本文未着手 | `docs/handoff/codex-keyword-research-ahrefs-2026-09-30.md`（元はスクラッチパッドのみ）。構成案本体はチャットのみ（下記に転記） | 404 |
| guides/cowork.html | **構成案完成**。ユーザーGO未取得 | 成果物はチャットのみ（下記に転記）。調査手順はメモリ `simy-seo-research-workflow.md` | 404 |

## 各ページの要点

### PLAUD（plaud.html）
- title「PLAUD NOTEの使い方｜AI文字起こし・要約の先を自動化 | SIMY」。H2 12、FAQ 16。
- SIMYアプリに Plaud 連携が内蔵（「接続する」だけ）。MCP/エクスポート経路の説明は不要。
- Ahrefs: plaud 23K/KD2。購入後語 使い方 6.8K、Plaud Web 6.5K、ログイン 4.6K、充電 1.4K、Plaud Desktop 1.1K を反映。共起語カバー 116/119。
- Lighthouse 全100、LCP 1.4s。
- 未解決: 「どのプラン・モデルでも接続できる」「過去の録音も参照できる」の裏付け、競合比較未実施、英語版の要否。
- 別セッションで判明した誤り: 「無料のStarterプラン」は誤り（Starter $30／Pro $50／Team $80、無料なし）。relay 図「フォローメール 完了」は Gmail が下書き保存までなので「下書き保存」に直す。

### ChatGPT（chatgpt.html）
- title「ChatGPT Work とは？使い方・料金・Chat／Codex との違い｜チャットGPT活用ガイド | SIMY」、H1「ChatGPT に、毎回頼まなくていい。」
- 軸を「ビジネス活用」から「Work・Codex・料金」へ変更（チャットgpt 料金 50K、使い方 40K、chatgpt work 4.1K）。
- SIMY の立ち位置: Work/Codex は「1件を仕上げる実行役」、SIMY は「拾い・動かし・終わりを確かめる管理役」で重ねて使う。フックは「お使いの ChatGPT プランの上で動く」。
- 未解決: Work 権限既定値・30日削除など第三者記事ベースの記述、Business/Enterprise 管理下での接続可否、plaud.html との相互リンク未実装。

### Claude（claude.html）
- title「Claude（クロード）とは？できること・使い方・料金・Coworkまで仕事目線で解説｜回答のあとを自動化するSIMY連携 | SIMY」、H1「Claudeの回答を、コピペと共有で終わらせない。」
- 料金・モデル章をピボット章の前に。Cowork 章を新設（claude cowork 32K/KD0）。
- ソース確認済みの事実: クラウド実行はユーザーの ChatGPT（Codex）のみ、Claude 接続画面なし、Gemini は SIMY 内部キー利用のみ（ユーザー向けには書かない）。ローカルは PC 上の Claude Code（sonnet-4-5 既定／opus-4-6）。デーモンが `~/.claude/projects` と `~/.codex/sessions` を既定90日走査、本文は保存しない。Gmail は下書きまで。
- 未解決: Cowork の保存先が `~/.claude/projects` か、Claude Code→SIMY の MCP で何ができるか、ローカル実行に有料プランが要るか、Starter の Autorun 上限、既存ページ（plaud/index/pricing/privacy）の食い違い修正。

### Codex（codex.html）
- title「OpenAI Codex の使い方・料金・利用制限ガイド｜CLI・アプリ・スマホの入口と、コードを書かない仕事への広げ方 | SIMY」。カタカナ「コーデックス」単独は塊根植物と混在するため使わない。
- 狙いは「料金・利用制限・入口」（入口 64K、料金・制限 27K）。非エンジニア語は SV ほぼゼロ。
- 構成（12章）: 01 Codex とは → 02 入口一覧（CLI・アプリ・VS Code・Cloud・スマホ）→ 03 導入手順 → 04 できること → 05 料金と利用制限 → 06 コードを書かない仕事に → 07 SIMY と Codex App Server のつなぎ方 → 08 商談1件で比較 → 09 Claude Code・Cursor・Copilot との比較と併用 → 10 職種別活用例 → 11 セキュリティと注意点 → 12 FAQ。
- 未解決: H1 最終文言（v1「Codexを、コードを書く仕事で終わらせない。」）、「Codex App Server 経由」「iOS アプリ」等の仕様裏取り。

### Cowork（cowork.html）
- title「Claude Cowork とは？使い方・料金・Copilot Coworkとの違いと、非エンジニアの業務活用事例 | SIMY」。流入見込み 2〜4K/月。
- SERP は弱ドメインの情報記事で参入余地あり（1位 flinters DR45）。比較の第一対象は Copilot Cowork（Claude Code の3倍）。
- 構成: Hero（読み方・定義1行）→01 とは（非エンジニア向け）→02 始め方（Windows）→03 料金・対応環境（無料不可）→04 業務活用事例（スキル・コネクタ・プラグイン）→05 安全性（短く）→新章「議事録作成からレポート、メール対応まで」→06 タスクのあとに残る仕事→07 商談1件で比較→08 比較（Copilot Cowork→Claude Code→SIMY）→09 業種別→10 FAQ（読み方・スマホ・いつから・統合）→CTA。
- 境界線: Cowork＝机で指示した1タスクをセッションで終わらせる／SIMY＝会議・チャットで生まれた仕事を拾い、毎回進め判断だけ返す。
- 未解決: 「お使いの Claude プランで動く」と書けるか（Claude セッションの結論では書けない。クラウドは Codex のみ）、経理・バックオフィスを業種例に入れるか、タイトル長。

## 横断的な課題

1. **dev の拡張子なし URL が 404**。prod の CloudFront Function は `/plaud`→`/plaud.html` にリダイレクトするが、その関数コードは `deploy-site.yml` が main のときだけ更新し、dev は `infra/terraform/main.tf` のテンプレートのまま。揃えるなら Terraform 側修正が別件で必要。
2. **dev ブランチが main から大きく乖離**（134 ファイル差分）。作業ブランチを手動デプロイすると `s3 sync --delete` で dev 限定ファイルが消えるため、dev への反映は cherry-pick 運用。修正は作業ブランチと dev の両方に入れる。
3. **main への PR が1本もない**。plaud / chatgpt はページ完成済みで PR 作成待ち。`integrations.html` は PR #87 と同ファイルを触るのでマージ順に注意。
4. **既存ページの誤記**（Claude セッション §9）: index.html の「387 historical defects」「1/5→5/5」、pricing.html / privacy.html のトークン制プラン・物理DB分離・AI学習不使用は現行実装と不一致。
5. **相互リンク未実装**: 5ページ間、および sitemap・フッターへの導線。
6. 各ページ共通で「お使いのプランで動く」系の表現は、**クラウド実行が Codex（ChatGPT）のみ**という実装事実に合わせる（Claude・Cowork ページで特に注意）。

## 次のステップ案

1. plaud.html のブランチを push し、chatgpt.html と合わせて main への PR を作る（plaud の「無料Starter」「フォローメール 完了」は先に直す）。
2. claude.html を構成案どおりに執筆し dev へ（未解決5点は裏付けの取れた範囲の表現に抑える）。
3. codex.html、cowork.html を順に執筆。cowork は「Claude プランで動く」表現を使わない前提で。
4. 5ページ完成後に相互リンク・sitemap・フッター導線を一括追加。
5. 別件: dev の CloudFront Function 修正、既存ページ誤記の修正。

## 2026-09-30 追記: フォルダ構成

ユーザー指示により、ガイドページはサイト直下ではなく `site/guides/` 配下に置く（例: `https://simy.one/guides/plaud.html`）。このブランチ `claude/channel-consolidation-4acadd` に PLAUD（6コミット）と ChatGPT（1コミット）を取り込み、`site/guides/` へ移動済み。canonical・og:url・パンくず・sitemap・integrations.html のリンク・テストを更新し、`tests/plaud-seo.test.cjs` は 31/31 合格。今後の claude / codex / cowork も `site/guides/` に作る。

## 2026-10-01 追記: 全ページ共通の体験原則（ユーザー指示）

1. **読者が「そんなことがやりたかった」と気づき、「それは SIMY を使わないとできない」と自然に感じる内容にする。** 読む前に自覚していなかった願望でもよい。押し付けではなく、場面を見せて納得させる。
2. **文字が多くて読まないと分からないものにしない。眺めながらでも頭にスーッと入る構成にする。**

この2原則は共起語カバー率や文字数より優先する。現行の plaud.html / chatgpt.html は原則2を満たしていない（本文約5万字、段落70超、13章のうち図があるのは2章のみ）。再設計の方針は下記「ガイドページ再設計ブループリント」を参照。
