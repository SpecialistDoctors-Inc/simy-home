# SIMY HP ページ戦略 & SEO強化プラン

> 対象: https://simy.one (SIMY - AI Code Generation from Meetings)
> 運営: AwakApp Inc.
> 導入企業: Pocket IC (pocket-ic.com) / IKIGAI TOWN (ikigai.town)

---

## 現状のページ構成 (Ver9)

| ファイル | 目的 | 状態 |
|---------|------|------|
| index.html | LP / トップページ | 実装済 |
| pricing.html | 料金プラン | 実装済 |
| contact.html | お問い合わせ / デモ申込 | 実装済 |
| how-it-works.html | 使い方 (4ステップ) | 実装済 |
| about.html | 会社概要 (AwakApp Inc.) | 実装済 |
| security.html | セキュリティ | 実装済 |
| compare.html | 競合比較 (vs Copilot, Cursor) | 実装済 |
| integrations.html | 連携サービス | 実装済 |
| press.html | プレスキット | 実装済 |
| careers.html | 採用 | 実装済 |
| status.html | システムステータス | 実装済 |
| privacy.html | プライバシーポリシー | 実装済 |
| terms.html | 利用規約 | 実装済 |
| 404.html | エラーページ (noindex) | 実装済 |

---

## 導入企業プロフィール

### Pocket IC (pocket-ic.com)
- **業種**: 医療 / ヘルスケア SaaS
- **サービス内容**: 動画インフォームドコンセントプラットフォーム。専門医監修の説明動画をLINE経由で配信し、対面説明時間を1/5に削減
- **ターゲット**: 医療機関（手術・外来を行う医師）
- **技術スタック**: LINE連携、動画配信、理解度確認クイズ、患者情報非保持設計
- **SIMYとの関連**: 開発ミーティングで決まった機能仕様をSIMYがコード化。HIPAA準拠の医療系プロダクトでも安全にPRを自動生成。エンジニア2名の小規模チームで月間PR数が17.7倍に

### IKIGAI TOWN (ikigai.town)
- **業種**: フィンテック / ライフプランニング
- **サービス内容**: 40-60代向けの経済リスク診断・FPオンライン面談プラットフォーム。AIで数百パターンのシミュレーションを実行し、オーダーメイドのライフプラン表を作成
- **ターゲット**: 40-60代の個人（会社員〜経営者）
- **技術スタック**: AIシミュレーション、オンライン面談、録画記録、ポイントシステム
- **SIMYとの関連**: 週次スプリントミーティングの内容をSIMYが解析し、フィンテック特有の複雑なビジネスロジックもコードに変換。リリースサイクルを2週間から3日に短縮

---

## ページ優先度別 強化プラン

### 🔴 優先度高（CVR・SEOに直結）

#### 1. Pricing（料金）— pricing.html ✅ 実装済

**現状の課題:**
- Terms内でStandard/Pro/Enterpriseプランに言及しているが、専用ページとして十分なSEO対策がない
- 検索意図「SIMY pricing」「SIMY 料金」の受け皿として最適化されていない

**強化ポイント:**
- 各プランの機能比較表に「導入企業の利用例」列を追加
  - Standard: 個人開発者・フリーランス向け
  - Pro: Pocket IC のような2-10名のスタートアップチーム向け（月間PR数17.7倍の実績付き）
  - Enterprise: IKIGAI TOWN のようなフィンテック企業向け（コンプライアンス対応、SSO、監査ログ）
- FAQ追加: 「医療系プロダクトでも使えますか？」→ Pocket IC導入事例への内部リンク
- FAQ追加: 「金融・フィンテック企業での導入実績はありますか？」→ IKIGAI TOWN事例への内部リンク
- CTA強化: 「Pocket ICはProプランで月間PR数を17.7倍に。まずは無料トライアル」

**SEOキーワード:**
- 主: "SIMY pricing" "SIMY plans"
- 副: "AI code generation pricing" "meeting to code cost"
- 関連: "developer productivity tool pricing" "copilot alternative pricing"

**検索意図分類:** 比較検討検索対応ページ

---

#### 2. Contact / Demo Request — contact.html ✅ 実装済

**現状の課題:**
- メールリンク（info@simy.one）のみでフォームがない
- デモリクエストの受け皿としてCVRが低い

**強化ポイント:**
- お問い合わせフォーム実装（名前・メール・会社名・チーム規模・用途）
- 「導入業種」プルダウン追加（医療/ヘルスケア、フィンテック、SaaS、EC、その他）
- 社会的証明セクション:
  - 「Pocket IC（医療SaaS）とIKIGAI TOWN（フィンテック）が導入済み」
  - 「エンジニア説明時間を40分→5分に短縮したPocket ICチームの声」
- デモ動画のプレビューサムネイル設置
- CTA文言: 「14日間無料トライアルを始める」「デモを見る」の2択

**SEOキーワード:**
- 主: "SIMY demo" "SIMY contact"
- 副: "AI code generation demo" "meeting to code trial"
- 関連: "try SIMY free" "request demo"

**検索意図分類:** 購入/問い合わせ直前検索対応ページ

---

### 🟡 優先度中（信頼性・SEO強化）

#### 3. How It Works（使い方）— how-it-works.html ✅ 実装済

**現状の課題:**
- LP内に概要はあるが、詳細な手順ページとして「SIMY 使い方」等のロングテール検索に弱い

**強化ポイント:**
- 4ステップの各段階に導入企業の具体例を追加:
  - Step 1 (Recording): 「Pocket ICチームはZoomでのスプリントプランニングを録画」
  - Step 2 (AI Processing): 「IKIGAI TOWNのフィンテック特有の用語もAIが正確に理解」
  - Step 3 (Code Generation): 「医療データのセキュリティ要件を踏まえたコードを自動生成」
  - Step 4 (PR Shipping): 「IKIGAI TOWNでは週次リリースが日次リリースに進化」
- 「業種別活用シナリオ」セクション追加:
  - 医療SaaS（Pocket IC事例）: HIPAA準拠開発フロー
  - フィンテック（IKIGAI TOWN事例）: 金融ロジックの正確な実装
- FAQ追加: 「どの言語に対応していますか？」「機密情報は安全ですか？」

**SEOキーワード:**
- 主: "SIMY how it works" "SIMY 使い方"
- 副: "meeting to code automation" "AI PR generation workflow"
- 関連: "how to auto-generate code from meetings" "voice to code process"

**検索意図分類:** 情報収集検索対応ページ

---

#### 4. About / Company — about.html ✅ 実装済

**現状の課題:**
- AwakApp Inc.の紹介として基本情報はあるが、B2Bでは「誰が作っているか」が信頼に直結
- 投資家・パートナー向け情報が不足

**強化ポイント:**
- 「導入企業」セクション追加:
  - Pocket IC（医療/ヘルスケア領域）のロゴとリンク
  - IKIGAI TOWN（フィンテック領域）のロゴとリンク
  - 「業種を問わず、ミーティングからコードを生成するプラットフォーム」
- チームメンバー紹介の充実（開発者の信頼性向上）
- ミッションステートメント: 「Voice to Code, One Shot — すべての開発チームがミーティングだけでソフトウェアを出荷できる世界を」
- 沿革タイムライン:
  - 創業 → Pocket IC初期導入 → IKIGAI TOWN導入 → Enterprise版リリース

**SEOキーワード:**
- 主: "AwakApp Inc" "SIMY company"
- 副: "SIMY developer" "who made SIMY"
- 関連: "AI code generation startup" "meeting to code company"

**検索意図分類:** 指名検索対応ページ

---

#### 5. Security — security.html ✅ 実装済

**現状の課題:**
- Enterpriseプラン訴求に重要。SOC2未取得でも、現在のセキュリティ対策を明示すると信頼感UP

**強化ポイント:**
- 業種別セキュリティ対応セクション:
  - **医療 (Pocket IC事例)**: 患者情報非保持設計との整合性、HIPAA対応ロードマップ、コード内の機密データ検出・マスキング
  - **金融 (IKIGAI TOWN事例)**: 金融規制準拠、データ暗号化、監査ログ、SOC2取得ロードマップ
- 信頼バッジ/認証ロードマップの可視化
- 「お客様の声」: 「Pocket ICは患者データを扱う医療SaaSですが、SIMYのセキュリティ設計に納得して導入を決めました」
- データフロー図: ミーティング音声 → AI処理 → コード生成の各段階でのセキュリティ対策を図解

**SEOキーワード:**
- 主: "SIMY security" "SIMY data protection"
- 副: "AI code generation security" "meeting recording security"
- 関連: "HIPAA compliant AI tool" "fintech AI security" "SOC2 AI development"

**検索意図分類:** 比較検討検索対応ページ（Enterprise検討層）

---

### 🟢 優先度低（成長フェーズで追加）

#### 6. Case Studies（導入事例）— 🆕 未実装

**理由:** 導入実績ができたため、最優先で追加すべき新規ページ

**構成案:**

##### case-studies.html（一覧ページ）
- Pocket IC と IKIGAI TOWN のサマリーカード
- 業種タグ（医療, フィンテック）
- 主要指標ハイライト: PR数17.7倍、リリースサイクル2週→3日

##### case-study-pocket-ic.html（個別ページ）
- **タイトル**: 「Pocket IC: 医療SaaSの2人チームがSIMYでPR数17.7倍に」
- **構成**:
  - 企業概要（動画IC、LINE連携、患者情報非保持）
  - 課題: エンジニア2名で機能開発が追いつかない
  - 導入経緯: スプリントミーティングの内容が直接コードに
  - 成果: 月間PR数17.7倍、コードレビュー時間50%削減
  - 担当者の声（テスティモニアル）
  - CTA: 「同じ成果を出したい方はデモをリクエスト」

##### case-study-ikigai-town.html（個別ページ）
- **タイトル**: 「IKIGAI TOWN: フィンテック企業がSIMYでリリースサイクルを2週間→3日に」
- **構成**:
  - 企業概要（40-60代向けリスク診断、AIシミュレーション、FP面談）
  - 課題: 金融ロジックの複雑さによる開発ボトルネック
  - 導入経緯: 週次スプリントの議論がそのままコードに
  - 成果: リリースサイクル2週→3日、バグ率30%低下
  - 担当者の声（テスティモニアル）
  - CTA: 「フィンテック開発をSIMYで加速」

**SEOキーワード:**
- 主: "SIMY case study" "SIMY導入事例"
- 副: "AI code generation case study" "meeting to code results"
- ロングテール: "医療SaaS AI開発ツール" "フィンテック 開発効率化"

**検索意図分類:** 比較検討検索対応ページ

---

#### 7. Blog — 🆕 未実装

**理由:** コンテンツSEOの柱。「AI コード生成」「会議 自動化」等で流入を狙える

**初期コンテンツ案:**
1. 「ミーティングからコードを自動生成する時代が来た — SIMYの挑戦」
2. 「Pocket ICが実践する、医療SaaSの開発効率化術」
3. 「IKIGAI TOWNに学ぶ、フィンテック開発のAI活用最前線」
4. 「GitHub Copilot vs Cursor vs SIMY — AI開発ツール徹底比較」
5. 「エンジニア2人でPR数17.7倍。小規模チームのための開発戦略」

**SEOキーワード:**
- "AI code generation" "meeting to code" "AI PR generation"
- "developer productivity" "engineering efficiency"
- "医療SaaS 開発" "フィンテック 開発効率化"

---

#### 8. Changelog — 🆕 未実装

**理由:** プロダクト更新履歴。既存ユーザー向け＋SEOで「SIMY update」系クエリの受け皿

**構成案:**
- 日付順のアップデートログ
- 各エントリ: バージョン、概要、詳細、影響範囲
- 導入企業からのフィードバック反映を明示:
  - 「Pocket ICのフィードバックにより医療用語辞書を強化」
  - 「IKIGAI TOWNの要望で金融計算ロジック生成精度を向上」

---

#### 9. Documentation — 🆕 未実装

**理由:** ヘルプ・API仕様。ユーザー数が増えてから

**初期構成案:**
- Getting Started
- API Reference
- Integration Guide (GitHub, Slack, Zoom)
- Security & Compliance
- FAQ

---

## 技術的SEO 改善タスク一覧

### 即時対応（Critical）

| # | タスク | 対象 | 詳細 |
|---|--------|------|------|
| 1 | ドメイン設定 | 全ページ | `https://example.com` → `https://simy.one` に全置換 |
| 2 | lang属性修正 | 全ページ | `lang="en"` のまま統一（英語サイト確認済み） |
| 3 | sitemap更新 | sitemap.xml | 全公開ページ（14ページ）を追加。現在はindex, privacy, termsの3つのみ |
| 4 | robots.txt更新 | robots.txt | ドメイン修正 + sitemap URL更新 |
| 5 | Search Console登録 | 新規 | google-site-verification-TODO.html の設置またはmetaタグ |

### 短期対応（High）

| # | タスク | 対象 | 詳細 |
|---|--------|------|------|
| 6 | canonical URL修正 | 全ページ | example.com → simy.one |
| 7 | OGP URL修正 | index.html | og:url, og:image等のドメイン |
| 8 | 構造化データ拡充 | 主要ページ | WebSite, Organization, SoftwareApplication, FAQPage |
| 9 | 内部リンク網強化 | 全ページ | 各ページのフッターに主要ページリンクを網羅 |
| 10 | Contact フォーム実装 | contact.html | メールリンクのみ → Webフォーム追加 |

### 中期対応（Medium）

| # | タスク | 対象 | 詳細 |
|---|--------|------|------|
| 11 | Case Studies新設 | 新規3ページ | 一覧 + Pocket IC + IKIGAI TOWN |
| 12 | Blog新設 | 新規 | 初期5記事 |
| 13 | パンくずリスト | 全サブページ | BreadcrumbList JSON-LD + UI表示 |
| 14 | サイト内検索対応 | index.html | WebSite JSON-LDのSearchAction |

---

## 構造化データ（JSON-LD）実装計画

### 全ページ共通
```json
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "SIMY",
  "url": "https://simy.one",
  "description": "AI Code Generation from Meetings",
  "publisher": {
    "@type": "Organization",
    "name": "AwakApp Inc."
  }
}
```

### index.html — SoftwareApplication + Organization
```json
{
  "@type": "SoftwareApplication",
  "name": "SIMY",
  "applicationCategory": "DeveloperApplication",
  "operatingSystem": "Web",
  "offers": {
    "@type": "AggregateOffer",
    "priceCurrency": "USD",
    "lowPrice": "0",
    "highPrice": "499"
  }
}
```

### pricing.html — Product + Offer
各プランをProduct + Offerとして構造化

### case-studies.html — Article
各事例をArticleとして構造化

### contact.html — ContactPage
組織の連絡先情報を構造化

---

## 内部リンク設計

### グローバルナビゲーション（全ページ共通）
```
Home | How It Works | Pricing | Case Studies | Contact
```

### フッターリンク（全ページ共通）
```
Product: How It Works | Pricing | Integrations | Compare | Security
Company: About | Careers | Press | Status
Resources: Case Studies | Blog | Changelog | Documentation
Legal: Privacy | Terms
```

### ページ間の相互リンク戦略
- index.html → pricing, how-it-works, contact, case-studies
- pricing.html → contact (CTA), case-studies (社会的証明)
- how-it-works.html → pricing (次ステップ), case-studies (実例)
- case-studies.html → contact (CTA), pricing (プラン選択)
- security.html → contact (Enterprise相談), case-studies (医療/金融実績)
- about.html → case-studies (導入実績), careers (採用)
- compare.html → pricing (プラン), case-studies (実績)

---

## キーワード戦略マップ

| ページ | 検索意図 | 主キーワード | 副キーワード | CTA |
|--------|---------|-------------|-------------|-----|
| index | 指名/情報収集 | SIMY, AI code generation | meeting to code, voice to code | Try Free / Contact |
| pricing | 比較検討 | SIMY pricing, SIMY plans | AI dev tool cost, copilot alternative price | Start Trial |
| contact | 購入直前 | SIMY demo, contact SIMY | request demo, free trial | Submit Form |
| how-it-works | 情報収集 | how SIMY works | meeting to PR, auto code generation | Try Free |
| about | 指名 | AwakApp Inc, SIMY company | who made SIMY | Learn More |
| security | 比較検討 | SIMY security | AI tool data protection, HIPAA AI | Contact Enterprise |
| compare | 比較検討 | SIMY vs Copilot | AI code tools comparison | Try SIMY |
| case-studies | 比較検討 | SIMY case study | AI dev productivity results | Request Demo |
| blog | 情報収集 | AI code generation (各記事テーマ) | developer productivity | Read More → Trial |

---

## 更新履歴

- 2026-03-09: 初版作成。Pocket IC / IKIGAI TOWN導入情報を反映
