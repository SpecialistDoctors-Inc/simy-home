# アクセシビリティ・性能とアーキテクチャの公開原則レビュー

2026-11-19。対象は `simy-home` の公開サイト。以下は著名な実践者20名の公開資料から構成した評価視点であり、客観的な世界ランキング、本人の参加・発言、本人によるSIMY評価ではない。「適用」は今回の設計上の推論である。ユーザーが過去の各ページへ与えたコンセプト原文とチャット履歴は未照合のため、このレビューと共通実装だけで依頼の全要件を完了したとは扱わない。

## 第1ラウンド：公開原則からの提案

### アクセシビリティ：10視点

| 実践者 | 公開資料 | 原則を今回へ適用する仮説 |
|---|---|---|
| Heydon Pickering | [Inclusive Components](https://inclusive-components.design/) | 意味のあるHTMLを基礎にし、不必要に複雑な操作を増やさない |
| Sara Soueidan | [Accessible Icon Buttons](https://www.sarasoueidan.com/blog/accessible-icon-buttons/) | アイコン操作にも認識できる名前と操作領域を確保する |
| Adrian Roselli | [公開記事アーカイブ](https://adrianroselli.com/) | カスタム操作の前にネイティブHTMLで成立するか確認する |
| Scott O’Hara | [The details and summary elements](https://www.scottohara.me/blog/2018/09/03/details-and-summary.html) | detailsナビゲーションの意味とキーボード操作を維持する |
| Léonie Watson | [tink.uk](https://tink.uk/) | 見た目に加えてランドマークと読み上げ順を評価する |
| Hidde de Vries | [hidde.blog](https://hidde.blog/) | 操作順、文書の意味、利用者の設定を設計条件にする |
| Lindsey Kopacz | [a11y with Lindsey](https://a11ywithlindsey.com/) | マウスを使わない閲覧を実際に確認する |
| Marcy Sutton | [公開サイト・教育資料](https://marcysutton.com/) | 自動検査と利用者の操作を組み合わせる |
| Steve Faulkner | [HTML5 accessibility chops: main](https://www.tpgi.com/html5-accessibility-chops-the-main-element/) | 装飾用コンテナーと本文ランドマークを区別する |
| Jared Smith / WebAIM | [Contrast and Color Accessibility](https://webaim.org/articles/contrast/) | 本文・補足・操作状態ごとにコントラストを評価する |

個人サイトのトップ／アーカイブを示す行は単一記事からの逐語引用ではなく、その公開活動を参照先とした設計視点である。WebAIMの記事は組織資料であり、Jared Smith個人の発言として扱わない。

### 性能とアーキテクチャ：10視点

| 実践者 | 公開資料 | 原則を今回へ適用する仮説 |
|---|---|---|
| Steve Souders | [High Performance Web Sites](https://www.stevesouders.com/) | 最初に必要な資源を先に届ける |
| Ilya Grigorik | [Optimizing Web Font Rendering Performance](https://www.igvita.com/2014/01/31/optimizing-web-font-rendering-performance/) | フォント待ちと差し替え時の表示変動を抑える |
| Addy Osmani | [Native image lazy-loading](https://addyosmani.com/blog/lazy-loading/) | 画面外画像を遅延し、ヒーロー画像を不用意に遅延しない |
| Philip Walton | [Optimize LCP](https://web.dev/articles/optimize-lcp) | LCPの発見・優先度・転送・描画を分けて診断する |
| Barry Pollard | [Optimize CLS](https://web.dev/articles/optimize-cls) | 画像や遅延挿入コンテンツの領域を予約する |
| Jeremy Wagner | [Optimize long tasks](https://web.dev/articles/optimize-long-tasks) | 長い同期処理を避け、入力に応答できる状態を守る |
| Tim Kadlec | [The Cost of Javascript Frameworks](https://timkadlec.com/remembers/2020-04-21-the-cost-of-javascript-frameworks/) | 静的HTMLで成立する公開ページへ重いランタイムを追加しない |
| Scott Jehl | [More Weight Doesn’t Mean More Wait](https://www.filamentgroup.com/lab/weight-wait) | 総容量だけでなく読み込み順と初期表示を評価する |
| Harry Roberts | [CSS and Network Performance](https://csswizardry.com/2018/11/css-and-network-performance/) | CSSの発見タイミングと描画阻害を確認する |
| Zach Leatherman | [A Comprehensive Guide to Font Loading Strategies](https://www.zachleat.com/web/comprehensive-webfonts/) | フォント戦略を端末と接続環境とともに評価する |

ここで採用するアーキテクチャは、既存の静的HTMLを継続し、変更を生成元へ集約し、リンクとdetailsはJavaScriptなしでも機能する漸進的拡張を維持するもの。主要表示資源を優先し、画面外画像と重いインタラクションの処理を分離する。別フレームワークへの移行自体を品質向上とは扱わない。

## 取得方法と制約

検索サービスは利用不可を返したため、公開URLへHTTPで直接アクセスした。上記20参照のうちTPGi記事以外の19URLはHTTP200を確認した。TPGiは403のため本文を取得できず、読了または内容の検証済みとは主張しない。mainの仕様上の根拠には[HTML main要素](https://html.spec.whatwg.org/multipage/grouping-content.html#the-main-element)と[WCAG 2.2 Bypass Blocks](https://www.w3.org/WAI/WCAG22/Understanding/bypass-blocks.html)を用いる。専門家による独立した査読や、実際の本人同士の議論を実施したものではない。

LCP・CLS・INPの良否をソース検査だけで断定しない。画像width/height属性がなくてもCSS aspect-ratioで領域予約できるため、属性欠如をそのままCLS不具合と呼ばない。ヒーローと画面外画像の識別は実際の画面とネットワークで確認する。

## 第2ラウンド：SEO・UXとの相互批判と採否

| 論点 | 対立する要求 | 採否・理由 |
|---|---|---|
| 本文へ移動 | 全ページ統一と各テンプレートの独自性 | **採用**：main一意・実効skipを共通契約にする。既存skipの文言・リンク先とmainの既存IDを保持。各ページの構成は統一しない |
| ナビゲーション | 見た目刷新と操作安定 | **既存維持**：details、Escape、フォーカス復帰が既にある。新メニューへの置換を見送る |
| 漫画の豊かさ | ブランド表現と初期表示速度 | **選択適用**：漫画を残して初期表示画像を優先。全画像lazy／全画像eagerの一律方針は不採用 |
| 動き軽減 | 演出と利用者設定 | **採用**：共有CSSのsmooth scrollを軽減設定で停止。skip表示は通常・軽減設定とも即時にし、focusを画面外へ残すtransitionを除く。全要素への!important禁止 |
| 本文量 | SEO網羅性と読みやすさ | **構造を採用**：見出し・main・skipで読み飛ばし可能にする。根拠のないSEO長文追加を見送る |
| 生成元単一 | 横断修正速度と再生成の安定性 | **採用**：`scripts/site_header.py` の最終工程から `page_accessibility.py` を適用。生成HTMLへ手作業だけの修正を残さない |
| 例外の扱い | 全199ファイルへの機械処理と文書用途 | **分類を採用**：認証、転送、verification、既存Reactアプリを通常公開文書と区別。アプリのrootにmainを重ねない |

## ソース監査と実装範囲

HTML199件を分類した。通常公開文書184、転送12、認証callback1、verification1、legacy application `old/contact.html` 1。共通化前の通常公開文書ではmain不足16、skip不足35。初回の文字列検査で得たskip不足117はclass="skip"を見落とす誤集計だったため採用せず、HTMLParserでリンク・IDを照合して修正した。

`clinic-security-sample.html` は既存skipが #main を参照する一方mainにIDがなかったため、既存リンクを維持してmainへIDを補った。clinic/law-firmは専用ヘッダーと既存 #main を保持した。旧アプリ `old/contact.html` はbundleがmainを生成するため、静的mainで包まない。実行時DOMのmainとskipはブラウザー検証で扱い、静的検査だけでは確認済みとしない。

横断テストは通常公開文書のmain一意、ID一意、tabindex=-1、skipリンク先一致、共通CSS、再生成の冪等性を検査する。CSSの見た目だけで完了にせず、代表ページで最初のTab、skip表示、Enter後のactiveElement、stickyヘッダーとの位置、軽減設定をブラウザー確認する。本文・価格・リンクの原意を変更する監査とは分離する。
