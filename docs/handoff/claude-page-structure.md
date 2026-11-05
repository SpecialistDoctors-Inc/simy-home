# 「Claude」検索流入 → SIMYユーザー化ページ 構成案

> 対象キーワード: Claude（クロード）＋ビジネス／業務／Claude Code／Cowork 系ロングテール
> 参考ページ: `/plaud.html`（origin/dev、`site/plaud.html`）の構成をそのまま踏襲
> データ: ①ユーザー提供の共起語（上位20ページ） ②Ahrefs Keywords Explorer（Google JP、2026-09-29更新） ③製品ソースコード（simy-web / simy-backend / simy-cli / simy-crew、各 origin/main・origin/dev、2026-09-29〜30時点）
> 製品事実は §7 の実装ファクトシートに従う。サイト既存ページの文言（index / pricing / plaud）より §7 を優先する。
> 作成日: 2026-09-30

---

## 1. 共起語から読める「上位20ページの正体」

上位20ページは、ほぼ全部が **「Claudeとは？使い方・料金・モデル（Opus/Sonnet）・ChatGPTとの違いを解説」型の総合ガイド記事**。

| 見出しでの出現回数 | 語 |
| --- | --- |
| 17 | クロード |
| 13 | AI、プラン |
| 11 | モデル |
| 10 | Opus |
| 9 | 違い、活用、データ |
| 8 | 生成、作成、ChatGPT |
| 7 | 機能、Sonnet、Pro、料金、ビジネス |
| 6 | 導入、解説、アプリ |
| 5 | 無料、文章、要約、長文、Max、安全性、Enterprise、Free |

タイトルで多いのは「料金(5)」「モデル(5)」「解説(4)」「使い方(3)」「違い(3)」。
つまり **料金・モデル・使い方・ChatGPTとの違い** の4本は「入っていないと上位に並べない」必須カバー要素。

### PLAUDページと決定的に違う点

- 「会議」「議事録」「録音」が共起語に **一切出てこない**。Claude検索者は会議起点ではなく、**文章・資料・コード** 起点。
- 「法人向け／法人／社内／部門／機密情報／契約書／導入」が4〜6サイトに出る。**仕事で使う・会社に入れる** という検討層が確実にいる。
- 「Claude Code／コーディング／コード／バグ／修正／PR／開発」が7〜10サイト。**開発者層** も同じ検索語に混ざっている。
- 「Cowork」「MCP」「Slack」「Notion」「Codex」「Copilot」は共起語に出てこない。ただし Ahrefs では **Cowork 3.2万／月、連携系 1.1万／月** の需要があり（§2）、上位20ページがまだ書いていない ＝ SIMYが語る余地。

## 2. Ahrefs で補強した需要データ（Google JP・月間検索数）

### 2-1. 主要クエリの規模と難易度

| キーワード | 月間検索数 | KD | 備考 |
| --- | --- | --- | --- |
| claude | 1.0M | 29 | 指名・ナビ。1位 claude.ai、App Store、Google Play、claude.com。AI Overview・PAA・トップニュース有り。**狙わない** |
| claude code | 241K | 22 | クロードコード 52K（KD 12）も別に存在 |
| **クロード ai** | **69K** | **0** | 親トピック「クロード ai 何ができる」。カタカナ情報検索の最大口。上位: aismiley「Claude（クロード）とは？できること・料金・使い方」、teachme biz、RICOH |
| **claude cowork** | **32K** | **0** | 2026年3月に出現、予測 102K。上位は flinters「非エンジニアの業務活用事例」、Udemy「AI秘書を雇って仕事を任せる」、書籍「業務自動化の教科書」、note「業務効率を100倍」 |
| claude design | 22K | 0 | デザイン生成。SIMYと遠い |
| claude code 料金 | 19K | 0 | 料金クエリの最大口は Claude Code 側 |
| claude desktop | 19K | 0 | |
| **claude code 使い方** | **15K** | **0** | 上位に ITmedia「チーム開発で使い倒す5つの勘所」、e-sales「**Claude Codeを営業活動に活用する方法10選**」、ai-heartland「hooks・MCP・サブエージェント」 |
| claude in chrome | 11K | 23 | |
| claude 読み方 | 10K | 0 | 「読み方」系は合計 16K |
| claude mythos | 9.4K | 0 | claude fable 5: 14K、claude fable: 8.1K |
| claude プラン | 8.0K | 0 | claude pro 5.1K、claude team 3.8K、claude max 3.1K、claude plan 3.0K、有料プラン 2.4K |
| claude api | 6.6K | 0 | |
| claude opus | 5.9K | 2 | claude 3.5 sonnet 5.4K、haiku 系 5.7K |
| **claude 使い方** | **5.8K** | **4** | 上位: lion-ai 完全ガイド、support.claude.com、aismiley、侍エンジニア、teachme biz、note（プロンプトのコツ）、RICOH、SHIFT AI |
| claude code とは | 4.9K | 0 | claudeとは 4.0K、claude とは 3.2K |
| claude 無料 | 4.3K | 3 | 無料版 2.3K、無料 制限 800、利用制限 450 |
| claude skills | 4.3K | 0 | Skills / MCP は各 19K の修飾語合計 |
| claude 料金 | 3.7K | 1 | クロード 料金 1.8K、料金プラン 1.8K、cowork 料金 1.6K、api 料金 1.4K、enterprise 1.2K、team プラン 1.1K |
| claude 会社 | 1.6K | 0 | 「どこの会社」600＋500。開発元 Anthropic を問う層 |
| claude 日本語 | 1.8K | 6 | |
| claude excel | 1.5K | – | 修飾語 excel 合計 7.0K。業務系で最大の「できること」 |
| claude chatgpt 比較 | 1.3K | 2 | gemini 比較 1.0K、chatgpt 違い 400、どっちがいい 500 |
| claude 学習させない | 900 | 0 | 信頼系の最大クエリ。code 学習させない 350＋200 |
| claude cowork 使い方 | 900 | 0 | cowork とは 1.4K、何ができる 600 |
| claude opus sonnet 違い | 800 | 2 | モデル 違い 500 |
| claude できること | 800 | 2 | 何ができる 600 |
| claude エージェント | 700 | – | code サブエージェント 800、サブエージェント 400、マルチエージェント 200、エージェントチーム 200 |
| claude セキュリティ | 600 | 0 | code セキュリティ 450、安全性 300、利用規約 300、機密情報 150、商用利用 100 |
| claude 法人契約 | 400 | – | 法人プラン 300、法人 200、契約 350、企業 150 |
| claude 資料作成 | 450 | – | 文章作成 200、pdf 200、翻訳 200 |
| claude slack 連携 | 500 | – | notion 連携 400、google drive 連携 300、github 連携 350、obsidian 連携 500、gmail 240、outlook 160、スプレッドシート 210、teams 180 |
| claude 活用 | 300 | – | 活用事例 60、code活用事例 400 |
| claude 自動化 | 200 | – | code 自動化 200 |
| claude 議事録 | 150 | – | 要約 20、メール 30、営業 20、仕事 20 |
| claude 業務効率化 | 70 | – | 業務 系は合計 440 |

**読み方**: 「業務／営業／要約／メール」など SIMY に直結する修飾語は **単体では月100件未満**。流入を作るのは
「クロード ai（69K）」「claude cowork（32K）」「claude code 使い方（15K）」「claude 使い方（5.8K）」「claude 料金（3.7K）」の5本で、いずれも **KD 0〜4**。
これらで上位に入り、本文で「回答のあとの仕事」に引き込む設計にする。

### 2-2. 一致キーワード全体（151,716語・合計 2.7M）の修飾語ランキング

| 帯 | 修飾語（月間合計） |
| --- | --- |
| 10万〜 | code 676K |
| 3〜7万 | ai 72K、cowork 53K、料金 47K、使い方 42K、fable 40K、anthropic 36K、design 34K、プラン 31K、opus 30K、desktop 30K |
| 1.5〜3万 | 無料 25K、pro 24K、sonnet 23K、api 22K、chrome 21K、skills 19K、mcp 19K、違い 18K、mythos 18K、比較 17K、制限 17K、install 17K、読み方 16K、team 16K、chatgpt 15K |
| 1〜1.5万 | agent 14K、md 13K、github 13K、max 13K、vscode 13K、cli 13K、windows 13K、gemini 13K、codex 12K、pricing 11K、**連携 11K**、インストール 10K、status 10K、plan 10K、vs 10K |
| 5千〜1万 | 日本 9.9K、使用 8.4K、設定 8.3K、日本語 8.3K、作成 8.2K、できる 8.2K、skill 8.2K、障害 8.1K、mac 7.8K、copilot 7.7K、cursor 7.6K、**excel 7.0K**、おすすめ 6.9K、**エージェント 6.9K**、ログイン 6.8K、有料 6.8K、モデル 6.7K、機能 6.4K、課金 6.2K、生成 5.9K、haiku 5.7K、始める 5.7K、拡張 5.6K、方法 5.1K、figma 5.1K |
| 〜5千 | plugin 4.8K、teams 4.7K、画像 4.7K、bedrock 4.4K、コマンド 4.3K、利用 4.2K |

### 2-3. 業務系30語で絞った一致キーワード（1,795語・合計 47K）の修飾語

連携 11K ＞ エージェント 6.9K ＞ 利用 4.2K ＞ 会社 4.1K ＞ 学習 4.0K ＞ セキュリティ 2.7K ＞ サブ(エージェント) 2.5K ＞ プロンプト 2.5K ＞ 契約 2.2K ＞ 活用 2.2K ＞ 法人 2.0K ＞ 設定 1.5K ＞ 作成 1.3K ＞ 導入 1.3K ＞ 資料 1.1K ＞ obsidian 1.0K ＞ github 1.0K ＞ 事例 990 ＞ 自動 850 ＞ 企業 820 ＞ slack 760 ＞ 制限 730 ＞ cowork 710 ＞ codex 700 ＞ cursor 680 ＞ notion 660 ＞ チーム 660 ＞ figma 640 ＞ google 630 ＞ 安全 570 ＞ 個人 560 ＞ 業務 440 ＞ drive 410 ＞ 規約 400 ＞ 議事録 360 ＞ 機密 350 ＞ notebooklm 340 ＞ 翻訳 330 ＞ canva 300 ＞ 仕事 250 ＞ gmail 240 ＞ スプレッドシート 210 ＞ 効率 210 ＞ 商用 190 ＞ teams 180 ＞ outlook 160 ＞ メール 160 ＞ 要約 160 ＞ リスク 140

→ 業務文脈で人が実際に打つのは **「連携」「エージェント」「学習させない」「セキュリティ」「契約／法人」**。「効率化」「要約」「メール」ではない。見出し語はこちらに寄せる。

### 2-4. 質問クエリ（917語・合計 48K）

とは（code 4.9K／claude 4.0K＋3.2K／cowork 1.4K／design 1.4K／mythos 800）、どこの会社・どこの国（600＋600＋500）、何ができる（claude 600／cowork 600／code 600）、chatgpt どっちがいい 500、claude.md とは 450、何がすごい（code 450／claude 400／mythos 400）、artifacts とは 350、いくら 300、**課金すべき 300**、プロジェクトとは 300、pro 何ができる 250、スキルとは 200、何が得意 200、code pro どれくらい使える 150。

## 3. 共起語クラスタと SIMY ユーザーとの距離（Ahrefs反映後）

| クラスタ | 代表語 | 月間規模 | SIMYとの親和性 | ページでの扱い |
| --- | --- | --- | --- | --- |
| A. 業務適用・連携 | 連携、エージェント、活用、導入、法人、契約、Slack、Notion、Drive、Gmail、Excel | 連携 11K、エージェント 6.9K、excel 7K | ◎ 「AIを使っているのに仕事が減らない」層そのもの | ページの **背骨**。ピボット章と連携章 |
| **B'. Cowork** | claude cowork、とは、何ができる、料金、使い方、windows | **32K（急成長）** | ◎ 上位ページが全て「非エンジニアがAIに仕事を任せる」文脈。SIMYの `/compare` に既に Cowork 列あり。トップの「Bring in: Cowork chats」とも一致 | **新設章**。Cowork と SIMY の役割分担を明示 |
| B. 開発 | claude code 使い方、料金、サブエージェント、hooks、MCP、skills、codex 連携 | 使い方 15K、料金 19K、skills/mcp 各 19K | ◎ Claude Code チャットの取り込み、Quality Monitor、Delivery Loop と直結。「営業活動に活用」記事が上位にいる＝非開発者も混在 | 連携方法C・サンプル(b)・活用例「開発チーム」。将来 `/claude-code.html` へ分割 |
| C. 文書作業 | Excel、資料作成、PDF、文章作成、翻訳、長文、要約 | excel 1.5K、資料作成 450 | ○ 「要約は仕事の終わりではない」物語 | できること章＋ピボット章 |
| D. 料金 | 料金、プラン、Free/Pro/Max/Team/Enterprise、Code 料金、Cowork 料金、無料 制限、課金すべき | 料金 47K 合計 | ○ SEO必須。「今のプランのままSIMYを足す」 | 独立章 |
| E. モデル | Opus、Sonnet、Fable、Mythos、Haiku、違い | opus 30K、fable 40K、mythos 18K | ○ SEO必須。「工程ごとにモデルを使い分ける」 | 独立章 |
| F. 比較 | ChatGPT、Gemini、Codex、Copilot、Cursor、どっちがいい | chatgpt 15K、gemini 13K、codex 12K | ○ SEO必須。「SIMYは Codex／Claude 両対応」 | 比較表章 |
| G. 信頼 | 学習させない、セキュリティ、安全性、利用規約、商用利用、機密情報、法人契約、どこの会社 | 学習させない 900、セキュリティ 600 | ○ 法人検討のゲート。上位20ページが薄い | 独立章 → `/security.html` |
| H. はじめかた | 使い方、読み方、アプリ、デスクトップ、Chrome、Windows、ログイン、日本語 | 使い方 42K、読み方 16K | △ 情報系。PLAUDの「届いたらやること」相当 | 冒頭に短く。「読み方＝クロード」「開発元＝Anthropic」を1行ずつ |
| I. その他 | design、画像生成、figma、canva | design 34K | × SIMYと遠い | 触れない or FAQ一行 |

**結論**: 「Claudeを仕事で使っている／会社に入れようとしている人」に向けた **総合活用ガイド** を1ページで作り、
PLAUDと同じく「Claudeはここまで ／ ここからSIMY」の **ハンドオフ図** を背骨にする。
Ahrefs で判明した **Cowork（32K・KD0）** を独立章として追加し、Cowork＝Claude の中で仕事を任せる／SIMY＝Claude の外側で「そのあとの仕事」を自分のやり方で回す、と役割を分ける。

## 4. ページ仕様（PLAUD準拠）

| 項目 | 内容 |
| --- | --- |
| URL | `https://simy.one/claude.html`（JA） |
| 主ターゲットKW | クロード ai（69K）／claude 使い方（5.8K）／claude 料金（3.7K）／claude cowork（32K）／claude できること（800） |
| title 案 | `Claude（クロード）とは？できること・使い方・料金・Coworkまで仕事目線で解説｜回答のあとを自動化するSIMY連携 \| SIMY` |
| description 案 | Claude（クロード）の使い方、Free/Pro/Max/Team/Enterpriseと Claude Code・Cowork の料金、Opus・Sonnet・Fableの選び方、ChatGPTとの違い、学習させない設定まで仕事目線で解説。回答のあとに残る貼り付け・共有・記録更新・毎週の繰り返しは、SIMYが進めます。 |
| og:title 案 | `Claudeの回答を、コピペで終わらせない。｜SIMY` |
| H1 案 | 「Claudeの回答を、／**コピペと共有で**／終わらせない。」（PLAUD H1の構文をそのまま） |
| eyebrow | 「Claude（クロード）を仕事で使う人のための活用ガイド」 |
| 構造化データ | Article ＋ BreadcrumbList ＋ FAQPage（PLAUDと同じ3種） |
| UTM | `utm_campaign=claude_guide`、`utm_content=header/hero/final` |
| 免責 | 「Claude、Claude Code、Claude Cowork および Anthropic は Anthropic PBC の商標です。SIMYは独立したプロダクトです。」（トップのCodex免責と同形式） |
| 内部リンク | `/compare`（Cowork列あり）、`/security.html`、`/pricing.html`（※現行プランに要更新、§8）、`/plaud.html`（会議起点の人向け）、`app.simy.one/local-cli/delivery-loop`（Delivery Loop 導線） |
| ヒーロー右側 | PLAUDの relay 図を流用。ファイル名を「提案書_A社_v3.md」等に、01〜03を Claude ✓（下書き／要約／コード）、ハンドオフ線、04〜07をSIMY（**Gmail に下書き保存**／Notion 追記（承認付き）／Slack 共有（承認後に投稿）／あなたの確認）。送信・投稿を SIMY が勝手に行う表現は使わない（§7-6） |
| hero-points | 「Claude の Free・Pro・Max、Claude Code・Cowork どれでも」「`simy` を入れるだけで、Claude Code／Cowork の会話が WorkFlow 候補になる」「実行はお使いの ChatGPT（Codex）。Claude のプラン追加は不要」 |

## 5. 章構成（目次）

PLAUDは「届いたら→できること→残る仕事→連携→サンプル→比較→活用例→料金→プライバシー→FAQ」。
Claude検索は「購入後」ではなく「理解・比較・検討中」が中心なので、**料金とモデルをピボットの前に置き**、SEO必須要素を先に満たしてから SIMY に引き込む。Ahrefs反映で **Cowork 章を新設**（03）し、全13章。

| # | id | H2（案） | カバーする語（月間規模） | SIMYの接点 |
| --- | --- | --- | --- | --- |
| 01 | `#start` | Claude（クロード）を仕事で使いはじめる5つのこと | 使い方 42K、読み方 16K、アプリ、デスクトップ、Chrome、Windows、ログイン、日本語 8.3K、どこの会社 1.1K | 冒頭1行で「読み方はクロード、開発元は米Anthropic」。5つ目を「成果物の置き場所を決める（Notion / Google ドライブ）」にして連携章へ橋渡し |
| 02 | `#features` | Claudeでできること：文章・長文要約・Excel・PDF・コード・リサーチ | できる 8.2K、作成 8.2K、excel 7.0K、資料作成、文章作成、翻訳、pdf、Artifacts、プロジェクト、Skills 19K、MCP 19K | 各カードの末尾に「→ このあと残る仕事」を1行 |
| **03** | **`#cowork`** | **Claude Coworkとは？非エンジニアが仕事を任せる使い方と、その先** | **cowork 53K、とは 1.4K、何ができる 600、使い方 900、料金 1.6K、windows 1.3K** | Cowork は「Claude の中で、その場の指示で」仕事を進める。SIMY は Cowork／Claude Code のチャットからあなたの確認事項を学び、Notion・Slack・Drive 側で「そのあとの仕事」を毎回同じ品質で回す。`/compare` の Cowork 列へリンク |
| 04 | `#models` | モデルの違いと選び方：Opus・Sonnet・Fable・Mythos（2026年9月時点） | opus 30K、fable 40K、sonnet 23K、mythos 18K、haiku 5.7K、opus sonnet 違い 800、モデル 違い 500、何がすごい | SIMY は Claude のモデルを選ばせない。クラウド実行は接続した ChatGPT（Codex）、ローカル実行は PC 上の Claude Code（既定 claude-sonnet-4-5、選択で claude-opus-4-6）。「トークンROI」という機能名は存在しないので使わない（§7-9） |
| 05 | `#pricing` | 料金プランの比較：Free・Pro・Max と Team・Enterprise、Claude Code・Cowork の料金 | 料金 47K、プラン 31K、code 料金 19K、pro 5.1K、team 3.8K、max 3.1K、有料プラン 2.4K、cowork 料金 1.6K、api 料金 1.4K、無料 制限 800、利用制限 450、課金すべき 300 | 「プランを上げる前に、回答のあとの作業を減らす」→ ピボットへ |
| 06 | `#after` | 回答のあとに、まだ残っている仕事 | 業務、作業、タスク、整理、メール、資料、管理、プロンプト 2.5K | **ピボット章**。2カラム「Claudeが終わらせてくれること／あなたにまだ残ること」。引用「問題はプロンプトではない。回答のあとに生まれる空白だ。」 |
| 07 | `#connect` | Claudeと仕事のツールをつなぐ：主要連携と、SIMYへの渡し方 | **連携 11K**、slack 760、notion 660、google/drive 1.0K、gmail 240、excel、github 1.0K、obsidian 1.0K、codex 連携 450、エージェント 6.9K | H3-1: Claude 公式の連携（Slack・Notion・Google Drive・Gmail・GitHub・MCP）を事実ベースで。H3-2: SIMY へつなぐ3方法（§7-3・7-4）— **A: `simy` デスクトップアプリ／CLI を入れる（おすすめ）**: Claude Code／Cowork の会話履歴を自動で読み、WorkFlow 候補「SIMYからの提案」に変える。書き出し・アップロード不要。会話本文は保存しない／ **B: Claude Code に SIMY プラグインを入れる**: `/simy:delivery-loop`（フック式の Delivery Loop）、`/simy:sqm-loop`・`/simy:pr-review`（品質モニター、Pro＋ITエンジニアパッケージ）。Claude Code から SIMY へ MCP 接続し、承認付きで SIMY の接続先を操作／ **C: Claude で作った成果物を Notion・Google ドライブに置く**: SIMY の Notion（MCP）・Google 連携が参照する。補助的な方法として短く |
| 08 | `#sample` | 1件で比較：Claudeの回答と、SIMYが仕上げる下書き | 修正、バグ、レビュー、評価、精度 | (a) ビジネス: 提案メールの回答 → Gmail 下書き／Notion 顧客メモ（承認付き）／Slack 共有（承認後）／あなたの確認。 (b) 開発: Claude Code の実装 → 品質モニターが Slack・GitHub の過去インシデントから作った検査を `simy sqm min-check`→`check` で実行し、署名付き `proof.json` を残す → PR。**「1/5→5/5」「387件の不具合」はバックエンドに裏付けが無いので使わない**（§7-9） |
| 09 | `#compare` | ChatGPT・Gemini・Codex・Claude Code 単体との違い、そしてSIMY | chatgpt 15K、gemini 13K、codex 12K、copilot 7.7K、cursor 7.6K、比較 17K、違い 18K、どっちがいい 500 | 表の最終列をSIMY。「どれが良い悪いではなく、得意なことが違う」（PLAUD文をそのまま）。SIMYは Codex／Claude 両対応で「選ばせない」 |
| 10 | `#usecases` | ビジネスでの活用例 | 活用 2.2K、事例 990、法人 2.0K、企業 820、業務 440 | 営業・商談（「Claude Codeを営業に活用」が上位にいる事実を引用）／FP・保険の面談／歯科・クリニック／開発チーム（Claude Code）／経営・1on1 |
| 11 | `#safety` | 学習させない設定・セキュリティ・法人契約：会社で使うときの確認事項 | **学習させない 900**、セキュリティ 600、安全性 300、利用規約 300、機密情報 150、商用利用 100、法人契約 400、法人プラン 300、契約 350、リスク 140 | H3: Claude 側 — 学習させない設定の手順／利用規約と商用利用／Team・Enterprise と法人契約／ハルシネーションを減らす「元資料も一緒に渡す」コツ。SIMY 側（§7-8）— 会話本文は解析中のみ使用し保存しない、履歴の走査期間は既定90日（1〜365日で変更可）、無効化すると派生データも削除、外部への送信・投稿は承認制、録画は暗号化して保存。「学習に使わない」「物理DB分離」「SSO」は現行コードに無いので書かない。詳細は `/security.html`（要更新） |
| 12 | `#faq` | よくある質問（FAQPage JSON-LD） | 質問クエリ 917語 | 下記12問 |
| 13 | 最終CTA | 次にClaudeへ頼むとき、回答を読み返す前にSIMYへ。 | — | PLAUD最終CTAの構文を流用 |

### FAQ 案（12問・Ahrefs質問クエリ準拠）

1. Claude（クロード）の読み方と、開発元はどこの会社ですか？（どこの会社 1.1K・読み方 10K）
2. Claudeの無料版では、どこまで仕事に使えますか？制限は？（無料 4.3K・無料 制限 800）
3. Claudeは課金すべきですか？Pro・Max・Team はどう選ぶ？（課金すべき 300・いくら 300）
4. Claude Cowork とは何ですか？何ができますか？（cowork とは 1.4K・何ができる 600）
5. Claude Cowork と SIMY は何が違いますか？併用できますか？
6. ChatGPTとClaude、仕事で使うならどっちがいいですか？（どっちがいい 500）
7. Opus・Sonnet・Fable は、どう使い分ければいいですか？（opus sonnet 違い 800）
8. 入力した内容をClaudeに学習させない設定はありますか？（学習させない 900）
9. 機密情報や契約書を入れても大丈夫ですか？法人契約は必要ですか？（機密情報 150・法人契約 400）
10. Claude Code は非エンジニアでも業務に使えますか？SIMYとの違いは？（code 使い方 15K）
11. SIMYを使うのにClaudeのプランは必要ですか？（→ 不要。SIMYの実行はお使いのChatGPT（Codex）アカウント。Claude Code はPC上でそのまま使え、会話は自動で学習元になる）
12. Claudeで作った下書きを、毎週同じ手順で共有・記録しています。自動化できますか？

## 6. 優先順位（SEO必須 vs SIMY転換）

- **SEO必須（これが無いと上位に並べない）**: 01 はじめかた、02 できること、03 Cowork、04 モデル、05 料金、09 比較、11 安全性、12 FAQ
- **SIMY転換（ここでユーザーに近づく）**: ヒーロー、03 Cowork 後半、06 残る仕事、07 連携、08 サンプル、10 活用例、13 CTA
- 文字量配分の目安: SEO必須 55%／SIMY転換 45%。PLAUDより SEO側を厚くする（検索意図が「検討中」寄りのため）。
- 見出しに入れる語の優先: **クロード、Cowork、使い方、料金、連携、エージェント、学習させない、Opus/Sonnet/Fable、ChatGPT**。「効率化」「要約」「メール」は本文で使い、見出しからは外す（需要が月100件未満）。

## 7. 実装ファクトシート（ページに書く製品事実の唯一の根拠）

調査対象: `simy-web` origin/main `6e43b0ef9`（2026-09-29）と origin/dev、`simy-backend` origin/main `c7e2fdfc3`、`simy-cli` `f17ce5b`（2026-09-30）、`simy-crew` origin/dev `addff99aa`。ローカルのチェックアウトは3リポジトリとも数百コミット古いので、必ず `git show origin/main:<path>` で読む。**[dev]** は origin/dev のみ。[flag] は本番フラグが既定オフの可能性。

### 7-1. 実行エンジン（ユーザーの発言「Claudeサブスクでは動かない。Codex か Gemini」の実装上の意味）

| 役割 | 実装 | 根拠 |
| --- | --- | --- |
| クラウド実行（Workflow・Autorun・チャット・会議解析） | **ユーザー自身の ChatGPT アカウント（Codex）**。設定カード「Codex (ChatGPT)」でデバイスコードサインイン。複数アカウント登録と上限到達時の自動切替あり。Codex 利用料は SIMY 料金に含まれない | simy-web `settings.codex.*`、`app.signupV2.description`（"Codex usage fees are not included in SIMY pricing"）、`src/lib/billing/execution-access.ts`（`SUBSCRIPTION_REQUIRED` 402／`CHATGPT_CONNECTION_REQUIRED` 428） |
| クラウド側チャットモデル | OpenAI `gpt-5.6-terra`／`gpt-5.6-sol`、推論強度 low〜Very high | simy-web `src/services/chat-model-config.ts` |
| SIMY 内部処理（構造化出力・一部 Edge Function） | **Gemini／OpenAI／Azure OpenAI を SIMY 側のキーで使用**（例: chat Edge Function は `gemini-2.5-flash-lite`／`gemini-3.1-flash-lite`、Crew の既定 `azure:gpt-5.6-terra`）。ユーザーが Gemini アカウントを接続する機能は無い（`backend=gemini` は拒否） | simy-backend `supabase/functions/_shared/model_tier.ts`、simy-crew `llm_provider.py`／`model_routing.py`、simy-web `local-tasks/readiness/route.test.ts` |
| Claude をクラウド実行に使うか | **使わない**。Claude／Anthropic のアカウント・APIキーを接続する画面は無い。Crew の Claude（Bedrock）プロバイダーは 2026-09-27 に削除、コーディング実行は Codex に統一。AI開発画面の「SIMY Cloud · Claude」はコード上で除外 | simy-crew コミット #2551、`.env.example` `CODING_AGENT_BACKEND=codex`、simy-web `coding-loop-control-panel.tsx` `CODING_LOOP_EXECUTION_MODES` |
| Claude をローカル実行に使うか | **使える**。`simy` デスクトップアプリ／CLI が PC 上の Claude Code を実行役にする（「このPC · Claude CLI」、`/executor claude`、`claude -p … --output-format stream-json`）。モデルは `claude-sonnet-4-5`（既定）／`claude-opus-4-6`。使用量は Claude Code 側で計上され SIMY は課金しない。CLI は Anthropic／OpenAI／Google の API を直接呼ばない | simy-web `local-claude-model-config.ts`、`codingLoop.control.providerBillingExplanation`、simy-cli `src/desktop-executor.js:114-137`、`docs/claude-code-parity/provider-boundaries.md` |
| 代替エンジン | **[dev]** Z.AI の GLM APIキー登録で ChatGPT の代わりに実行（画像入力・Web検索非対応、課金は Z.AI） | simy-web origin/dev `settings.codex.glm.*` |

→ ページの書き方: 「SIMY のクラウド実行は、お使いの ChatGPT（Codex）アカウントで動きます。Claude のプランを追加する必要はありません。Claude Code は、お使いの PC 上で SIMY の実行役として使えます。」 Gemini はユーザーが接続するものではないので、ユーザー向けコピーでは「Gemini で動く」と書かない（SIMY 内部利用の説明が必要なときだけ）。

### 7-2. Claude Code／Cowork の会話取り込み（「全て可能」の実装）

- **仕組み**: `simy --daemon`（デスクトップアプリ）が起動時と最大15分ごとに `~/.claude/projects` と `~/.codex/sessions`・`archived_sessions` の全 `.jsonl` を走査。1回の巡回で最大10ファイル、カーソルで残りを順次処理するため、期間内の会話は最終的に全て対象になる。ファイル書き出し・手動アップロードは無い。— simy-cli `src/codex-work-pattern-sync.js:57-62,106,539-589`、simy-web `settings.workPattern.cliReady`
- **期間**: 既定90日、サーバー設定で1〜365日。— simy-backend `20260907113000_enable_work_pattern_discovery_by_default.sql`
- **送るもの**: ユーザーとアシスタントの本文のみ（サブエージェント、思考・分析チャンネル、AGENTS.md 等の注入文脈は除外）。1スレッド最大24メッセージ、1メッセージ1,500文字に分割、1リクエスト最大10スレッド／512KiB。ID は SHA-256 ハッシュ。— simy-cli 同ファイル `:126-130,427-434,677-693,803-849`、simy-web `api/local-cli/work-pattern-observations/route.ts`
- **サーバーに残るもの**: ハッシュID・時刻・短い分類タグのみ（`pattern_hypotheses` 等4種）。応答は `raw_content_persisted: false`。生テキストは「短時間の抽象化呼び出しの中にしか存在しない」。— simy-backend `20260905110000_add_work_pattern_discovery_automation.sql`、simy-crew `work_pattern_runtime.py:3-5`
- **UIの約束**: 「会話テキストは解析中のみ使用し保存しません。SIMY が保持するのは抽象的な手順・品質チェック・完了条件です」。— simy-web `settings.workPattern.privacy`
- **結果**: 7日ごと（新規3スレッド以上で）Crew が履歴を見て、既存パターン→組合せ→新提案の順に WorkFlow 候補を作る。候補は本人が明示的に承認するまで保存されない。私的テンプレートで他ユーザーには見えない。— simy-backend `20260914165226_create_independent_workflows.sql`、simy-web `workPatternTemplates.personal.subtitle`
- **既定オン（オプトアウト）**。無効化すると派生データを削除。— simy-backend `20260907113000_…`
- **Cowork**: コード上に「Cowork」の文字列は無い（seed の demo 行のみ）。ユーザー確認では「全て可能」。Cowork のセッションが `~/.claude/projects` に書き出される前提で同じ仕組みが働く。ページには「Claude Code・Cowork の会話」と書き、§8 で保存パスを確認する。
- **Microsoft 365 Copilot** の履歴も同様（オプトイン、90日、本文非保存）。GitHub Copilot チャットの取り込みは無い。— simy-backend `20260907084341_add_microsoft_copilot_history_sync.sql`

### 7-3. Claude Code 側に入るもの（プラグイン・フック・MCP）

- **プラグイン `simy@simy-local`**（`simy --daemon --install-workflows` で生成、`claude plugin install simy@simy-local`）。スキル: `/simy:delivery-loop`、`/simy:sqm-loop`、`/simy:pr-review`。個人スキル `simy-sqm-pr-check` も `~/.claude/skills` に配置。全てオプトイン。— simy-cli `README.md:58-68`、`src/sqm/claude-plugin.js`
- **Delivery Loop**（フック式）: SessionStart でセッションIDを注入、エージェントは各ターン終了前に `simy delivery checkpoint`、Stop フックが次の一手を返して継続。既定上限 6継続／3失敗／30分。状態は `~/.simy/delivery-hooks` にローカル保存、「これらのフックは会話・トークン・プロンプトをアップロードしない」。SIMY 0.5.32 以降。設定ページ `app.simy.one/local-cli/delivery-loop`。— simy-cli `docs/delivery-hooks.md`、simy-web `ui-copy-delivery-loop.ts`
- **品質モニター（SQM）**: `simy sqm min-check`（差分の決定的プリフライト）→ `simy sqm check`（規則・シナリオ評価、`proof.json` をデバイス鍵で署名）。署名付き知識バンドルをダウンロードし、証跡のみアップロード。「ソーステキストはアップロードしない」。ローカルレビューワーカーは `claude --print --json-schema` をツール・フック・MCP 無効で実行。利用条件は **Pro プラン＋ITエンジニアパッケージ**。— simy-cli `src/sqm/command.js`、`src/sqm/review-worker.js`、simy-web `ui-copy-sqm-knowledge.ts`
- **セッション監督**: デスクトップの「Sessions」で既存の Codex／Claude 会話を元の目的に向けて継続。Claude は元プロセス内の生きたフック経由のみ（Windows は監視のみ）。— simy-cli `docs/session-supervision.md:126-145`
- **MCP**: Claude Code から SIMY へ MCP 接続でき、設定に「Codex または Claude Code に付与した SIMY 接続と権限」「書き込み承認」の管理がある。— simy-web `ui.domain.settings.mcpConnections.*`、`mcpApprovals.*`
- **前提**: Node 20+、Claude Code 2.1.200+、Codex 0.144+。macOS（Apple Silicon、署名済み DMG）／Windows x64 インストーラー、Linux は npm のみ。— simy-cli `src/backend-executable.js`、`packaging/README.md`

### 7-4. 連携アプリ（設定「Connected apps」・`connector-catalog.ts`）

| 連携 | 読む | 書く | 注意 |
| --- | --- | --- | --- |
| Google（Gmail・カレンダー・Drive・Meet） | Gmail（10分ごと）、予定、Meet 録画（Drive 経由） | **Gmail は下書きのみ**（`drafts` API、送信エンドポイント無し）。Drive 作成は承認後 | 本番の Google OAuth は読み取り権限のみ承認済み（"Production Google verification has not approved Gmail write scopes yet"）→ **「メールを送る」とは書かない。「下書きを用意する」まで** |
| GA4・Search Console | 指標 | – | 別権限 |
| Microsoft（Outlook・Teams） | メール、Teams チャット、Teams 会議録画・文字起こし（過去30日、管理者同意） | 送信コード無し | |
| Microsoft 365 Copilot | 履歴90日（オプトイン） | – | 本文非保存 |
| Slack | 選択チャンネルの履歴、`:bug:`/`:fire:` リアクション | `chat.postMessage`（承認付き） | 既定 WorkFlow は投稿しない設定 |
| GitHub（App） | リポジトリ・PR・Issue・失敗チェック | PR ジョブ（「Generate PR」） | Issue が起点になる |
| Zoom・Webex・Meet・Teams 会議 | Recall.ai ボット参加＋各プラットフォームの録画・文字起こし取り込み | – | 「録音・文字起こしを開始はしない」 |
| Notion | ホスト型 MCP（読み） | MCP 書き込み（承認必須） | |
| Box | 文書検索 | – | |
| X | 投稿検索 | 投稿 | Crew 側実装 |
| LINE・WeChat | 受信 | LINE は連携案内の返信のみ | |
| Datadog・Sentry・CloudWatch | アラート→トリアージ | – | |
| Chrome 拡張 | ログイン済みタブで作業 | 同左 | 初回に確認 |
| 近日公開 | Salesforce、HubSpot、Sansan、kintone、Jira、Veeva Vault | | 接続不可 |
| **[dev]** Plaud | 録音・文字起こし・要約の検索参照 | – | デバイス登録済みアカウント |

未実装: Dropbox、GitHub Copilot、Claude Cowork の直接コネクタ。ページの連携章 H3-2 は上表に無い経路を書かない。

### 7-5. 画面に出る機能名（この名前だけを使う）

My AI（Chat／Meetings／Pipeline／Agentic Loop の切替）、**My Actions**（Active／Backlog／Complete／Archive、P0〜「AI automated」レーン、「SIMY-owned Actions continue in the background」）、**Autorun**（プラン表示「Autoruns」、「Review before SIMY starts」の承認、WorkFlow ごとにオプトイン、`read_draft`＋外部効果は承認必須、繰り返し送信を事前承認する Standing Delegation）、**WorkFlow**（「目標・手順・遷移条件・完了条件を自分のやり方として保存」、「SIMYからの提案」）、**Meetings**（録画・文字起こし・話者・要約・決定・アジェンダ提案、Zoom ボット）、**ヒアリングモード**（FP 向けリアルタイム質問提案・チェックリスト、業界パッケージ）、**品質モニター**（SQM：Incidents／Safeguards／CLI runs）、**Delivery Loop**、**Agentic Loop**、**成長ステータス**、**通知**（メール・ブラウザ・プッシュ）、**ファイルアップロード**（10ファイル・各50MB、Action や会議記録に変換。チャット履歴の取り込みではない）、**Chrome 拡張**、**MCP 接続と書き込み承認**。UI は日本語・英語、サイドバーに常時「Beta」表示。

### 7-6. 承認モデル（コピーの語尾を決める）

外部への送信・投稿・予定作成は人の承認が必要（Gmail 送信は不可・下書きまで、Slack 投稿は承認付き、Notion 書き込みは承認必須、カレンダー作成は確認要）。→ PLAUD ページの relay 図にある「フォローメール 完了」は、Claude ページでは「フォローメール **下書き保存**」に直す。「あなたがやるのは、レビューして送ることだけ」は実装と一致するので使える。— simy-backend `connector_preflight_policy.ts`、`docs/standing-delegation-v1.md`

### 7-7. 料金（現行・`pricing-v2.ts`、Stripe、月額・USDのみ）

| プラン | 税抜／税込（月） | Autorun | ストレージ | ユーザー |
| --- | --- | --- | --- | --- |
| Starter | $30／$33 | 100回／月（バックエンドでは無制限化済み・要確認） | 10GB | 1 |
| Pro | $50／$55 | 無制限 | 50GB | 1 |
| Team | $80／$88 | 無制限 | 100GB | 3 |

追加ストレージ 30GB $10／月。業界パッケージ（Standard／FP／MR／ITエンジニア）は価格を変えない。**無料プランは無い**（実行は有料プラン必須）。Enterprise は問い合わせ。年額・円建ては無い。旧トークン制プラン（Starter Trial $10・80Mトークン等）は終了扱い。— simy-web `src/lib/billing/pricing-v2.ts`、simy-backend `20260815082529_add_pricing_v2_billing_contract.sql`
→ ページでは「有料プラン（Starter $30／月〜）が必要。Codex の利用料は別」と書く。

### 7-8. セキュリティ・プライバシーで書けること／書けないこと

書ける: 会話本文は解析中のみ使用し保存しない（7-2）、履歴走査は既定90日・1〜365日で変更可、無効化で派生データ削除、CLI からの Delivery Loop フックは何もアップロードしない、SQM はソースを送らず証跡のみ、外部書き込みは承認制、録画は非公開 S3・TLS・SSE-KMS で保存、イベント本文は30日で削除、組織単位の行レベルセキュリティ、アカウント削除で個人ワークスペースを削除、CLI セッションは48時間で失効、Enterprise 管理に保持期間（1〜3,650日）・監査ログ・法的保留。
書けない（コードに根拠が無い）: 「学習に使わない」方針、暗号化の一般的な主張（録画以外）、**物理的な DB 分離**（論理分離のみ）、SSO／SAML／2FA（「近日公開」）、録音同意の文言。— simy-web `admin.security.*`、simy-backend `20260902150000_pricing_authz_foundation_v1.sql`

### 7-9. 使ってはいけない表現（コード上に存在しない）

「トークンROIダッシュボード」「トークスクリプト」「Memory」（内部に Autorun Work Memory v1 はあるが UI 名ではない）、「387件の不具合を学習」「監査リプレイ 1/5→5/5」（バックエンドに証跡無し。387 は SQM セルフチェックのレコード数）、「無料の Starter プラン」、「Claude のプランで動く」、「Gemini を接続」、「メールを自動送信」、「Cowork 連携」（コネクタとしては無い。会話取り込みの文脈のみ）。

## 8. 残る確認事項（ページ公開前）

1. **Cowork の会話の保存先**が `~/.claude/projects` か。違う場合は取り込み方法の記述を変える。
2. **Claude Code → SIMY の MCP 接続で何ができるか**（Notion 等の接続先操作か、SIMY の Action 操作か）。§07-B の1文をそれに合わせる。
3. **ローカル Claude Code 実行に有料プラン・ChatGPT 接続が要るか**（クラウドは必須と確認済み。ローカルは未確認）。
4. **Starter の Autorun 上限**（UI は100回、バックエンドは無制限化）。
5. **既存ページとの食い違い**の扱い（§9）。特に `plaud.html` の「無料の Starter プランでも使えます」と「フォローメール 完了」。

## 9. サイト既存ページとの食い違い（ソース照合で判明・別タスクで修正）

| ページ | 現在の文言 | 実装 |
| --- | --- | --- |
| `site/plaud.html`（dev） | 「NotionとGoogle ドライブを使う方法は、無料のStarterプランでも使えます」 | 無料プランは無い。Starter は $30／月 |
| `site/plaud.html`（dev） | relay 図「お礼とフォローのメール … 完了」 | Gmail は下書き保存まで。送信は人 |
| `site/plaud.html`（dev） | 連携方法 A/B/C（Notion 経由・Drive 経由・PLAUD MCP） | dev には Plaud コネクタ（接続ボタン）あり。既存メモどおり「接続するだけ」 |
| `site/index.html` | 「387 historical defects」「1/5 → 5/5 audit replay」 | バックエンドに根拠なし |
| `site/index.html` | 「Codex App Server」 | ユーザーには見せない内部名。UI は「Codex (ChatGPT)」 |
| `site/pricing.html`・`lang/ja.json` | Standard／Pro／Enterprise、トークン配分、年額20%引き、Scale | 現行は Starter／Pro／Team、月額 USD、トークンは実行を制限しない |
| `site/privacy.html`（ja.json） | Enterprise は「物理的なデータベース分離」「AIトレーニング不使用」 | 論理分離のみ。学習方針の記述はコードに無い |

## 10. 将来の分割候補（今回は1ページで良い）

| 候補 | 主KW（月間・KD） | 理由 |
| --- | --- | --- |
| `/claude-cowork.html` | claude cowork 32K・KD0（予測 102K） | 単独で最大の伸び。上位が全て「非エンジニアが仕事を任せる」＝SIMYの顧客そのもの。`/claude.html` §03 が育ったら分割 |
| `/claude-code.html` | claude code 使い方 15K・KD0、claude code 料金 19K・KD0、サブエージェント 800 | 開発者向け。Delivery Loop・Quality Monitor・PR監査を主題に |
| `/claude-vs-chatgpt.html` | claude chatgpt 比較 1.3K、どっちがいい 500 | 「違い」単独クエリ用。SIMYの「両対応・選ばせない」を主題に |

いずれも `/claude.html` から内部リンクし、`/claude.html` をハブにする。
