# SEO対応が「完璧」である状態の定義

simy.one の個別ページ（まずは `site/plaud.html`）に適用する定義とチェックリストです。

## 1. 定義

検索順位そのものは保証できません。競合ページ、検索エンジンのアルゴリズム、被リンクなど、ページの外にある要因で決まるからです。

そこでこの文書では、次の2つがそろった状態を「SEO対応が完璧」と定義します。

1. **ページ側で制御できる要素が、すべて下のチェックリストの基準を満たしている。** 1項目でも未達なら「完璧」ではありません。
2. **公開後に、成果を計測して直せる状態になっている。** インデックス登録、サイトマップ送信、対象クエリの計測が回っていることです。

チェックは3種類に分けます。

| 種類 | 意味 | 確認方法 |
|---|---|---|
| 静的 | HTMLとリポジトリだけで判定できる | `node --test tests/plaud-seo.test.cjs` |
| 実測 | ブラウザで表示して測る | Lighthouse（モバイル）と、375px幅での表示確認 |
| 公開後 | 本番公開後にしか確認できない | Google Search Console と本番URLへのアクセス |

## 2. 対象クエリ

主クエリは「PLAUD 使ってる / 買った / 届いた」です。PLAUDを購入済みの人に届けることが最大の目的です。

| クエリ | 検索意図 | ページ内で答える場所 |
|---|---|---|
| PLAUD 使ってる | 既存ユーザーが活用法を探す | FAQ「すでに使っています」、01の導入文 |
| PLAUD 買った | 購入直後の人が始め方を探す | FAQ「買ったばかりです」、01の導入文 |
| PLAUD 届いた | 開封後の初期設定を探す | H2「PLAUDが届いたら、最初にやる5つのこと」 |
| PLAUD NOTE 文字起こし | 文字起こし機能を知りたい | H1、H2「主な機能」、H3「文字起こし」 |
| PLAUD 要約 | 要約機能を知りたい | H1、H2「主な機能」、H3「要約」 |
| PLAUD エクスポート | 書き出し方法と形式を知りたい | H3「PLAUDのエクスポート形式と使い分け」 |
| PLAUD MCP | AIツールとの接続方法を知りたい | H2「Ask Plaud・ChatGPT＋PLAUD MCPとSIMYの違い」、FAQ |
| PLAUD 料金 | プランの価格を知りたい | H2「PLAUDの料金プランと対応モデル」 |
| PLAUD Unlimited | 上位プランが必要か知りたい | H3「料金プランの価格比較」、FAQ「Unlimitedプランは必要ですか？」 |
| PLAUD NOTE Pro | 上位モデルを知りたい | H3「対応モデルの比較」 |
| Plaud NotePin | ウェアラブルモデルを知りたい | H3「対応モデルの比較」 |
| PLAUD 使い方 | 購入後に使い方を探す（Ahrefs：「使い方」を含む語で月6,800回） | title、H2「PLAUDの使い方：届いたら最初にやる5つのこと」 |
| Plaud Web | PCのブラウザで使いたい（月6,500回） | H3「PCで使うなら：Plaud WebとPlaud Desktop」、FAQ |
| Plaud Desktop | オンライン会議を録音したい（月1,100回） | H3「PCで使うなら：Plaud WebとPlaud Desktop」 |
| PLAUD どこの国 | 運営会社を知りたい（月90回） | FAQ「PLAUDはどこの国の会社ですか？」 |
| PLAUD 情報漏洩 | 安全性を確かめたい（「情報漏洩」を含む語で月440回） | H2「セキュリティ・情報漏洩対策と録音の同意」、FAQ |

共起語は、検索上位20ページの共起語データと、Ahrefs Keywords Explorer（日本、2026年9月30日）の「Also talk about」「Matching terms」から、「採用語」と「除外語」に分けてテストファイルに定義しています。除外語は、Amazon・在庫・最安・発送など、EC商品ページに寄せてしまう語です。

## 3. チェックリスト

### A. 検索意図とコンテンツ

| ID | 基準 | 種類 |
|---|---|---|
| A1 | 16の対象クエリそれぞれの中心語が、title・H1・H2・H3・FAQの質問のいずれかに入っている | 静的 |
| A2 | 採用した共起語の90%以上が、本文に出てくる | 静的 |
| A3 | 除外語が、本文に1つも出てこない | 静的 |
| A4 | 価格・仕様・機能に出典リンクがあり、確認日が書かれている | 静的 |
| A5 | 例示やサンプルは「例」「サンプル」「イメージ」と明記し、実績や口コミを装わない | 静的 |
| A6 | 最終更新日と発行者が画面に表示され、構造化データの日付と一致する | 静的 |
| A7 | 本文が5,000字以上あり、対象クエリを網羅している | 静的 |

### B. メタ情報

| ID | 基準 | 種類 |
|---|---|---|
| B1 | titleが「PLAUD」で始まり、全角換算25〜35字 | 静的 |
| B2 | meta descriptionが「PLAUD」を含み、全角換算80〜120字 | 静的 |
| B3 | canonicalが、自分自身の絶対URL（https://simy.one/plaud.html）を指す | 静的 |
| B4 | `html lang="ja"` と `og:locale=ja_JP` | 静的 |
| B5 | OGPとTwitterカードがそろい、og:urlがcanonicalと一致する | 静的 |
| B6 | og:imageがページ専用で、実在する1200×630の画像である | 静的 |
| B7 | robotsがindex, followで、noindexがない | 静的 |
| B8 | viewportが設定されている | 静的 |

### C. 見出しと構造

| ID | 基準 | 種類 |
|---|---|---|
| C1 | H1が1つだけで、主キーワード「PLAUD」を含む | 静的 |
| C2 | 見出しの階層が飛ばない（H1の次はH2、H2の次はH3） | 静的 |
| C3 | 目次が本文のすべてのH2節を指し、アンカーがすべて実在する | 静的 |
| C4 | パンくずが画面に表示され、構造化データと一致する | 静的 |

### D. 構造化データ

| ID | 基準 | 種類 |
|---|---|---|
| D1 | JSON-LDが構文エラーなく読める | 静的 |
| D2 | Articleに headline（110字以内）・image・datePublished・dateModified・author・publisher.logo・mainEntityOfPage がある | 静的 |
| D3 | FAQPageの質問と回答が、画面の表示と完全に一致する | 静的 |
| D4 | BreadcrumbListのitemが絶対URLで、画面のパンくずと一致する | 静的 |

FAQPageは正しく書いても、2023年以降は政府・医療系サイト以外でリッチリザルトが出ません。それでも、検索エンジンとAIに質問と回答の対応を伝える役割があるため入れます。

### E. クロールとインデックス

| ID | 基準 | 種類 |
|---|---|---|
| E1 | robots.txtでブロックされていない | 静的 |
| E2 | sitemap.xmlに正規URLがあり、lastmodが更新日と一致する | 静的 |
| E3 | サイト内の既存ページから、通常のaリンクで1本以上リンクされている | 静的 |
| E4 | ページ内のサイト内リンクとアンカーが、すべて実在するファイルとIDを指す | 静的 |
| E5 | 拡張子なしのURL（/plaud）が、本番で .html へ301転送される | 静的 |
| E6 | 公開先でHTTP 200が返り、配信ファイルがリポジトリと一致する | 実測 |

### F. 表示速度・モバイル・アクセシビリティ

| ID | 基準 | 種類 |
|---|---|---|
| F1 | Lighthouse（モバイル）のPerformanceが90以上 | 実測 |
| F2 | LCPが2.5秒以下、CLSが0.1以下、TBTが200ms以下 | 実測 |
| F3 | LighthouseのSEOが100 | 実測 |
| F4 | LighthouseのAccessibilityが100 | 実測 |
| F5 | LighthouseのBest Practicesが95以上 | 実測 |
| F6 | 375px幅で横スクロールが発生しない | 実測 |
| F7 | すべての画像にaltとwidth・heightがある | 静的 |
| F8 | 外部のCSS・JavaScript・Webフォントを読み込まない | 静的 |
| F9 | ページが読み込む画像の合計が50KB以下 | 静的 |

### G. 公開後の運用

| ID | 基準 | 種類 |
|---|---|---|
| G1 | Search ConsoleのURL検査で、インデックス登録をリクエストした | 公開後 |
| G2 | Search Consoleにsitemap.xmlを送信した | 公開後 |
| G3 | 対象クエリの表示回数・平均順位・CTRを、週1回記録している | 公開後 |
| G4 | PLAUDの価格と仕様を月1回確認し、変わったら本文と更新日を直している | 公開後 |

## 4. 判定の手順

```bash
node --test tests/plaud-seo.test.cjs
```

```bash
npx lighthouse http://localhost:8080/plaud.html --only-categories=performance,accessibility,best-practices,seo --output=json --output-path=./lighthouse-plaud.json --chrome-flags="--headless=new"
```

判定結果は [plaud-seo-check.md](plaud-seo-check.md) に記録します。
