# 国別検索調査と多言語SEO改善（2026-10-03）

## 目的と範囲

各国で業務自動化・AIエージェントを探す業務担当者が、自分の言語でSIMYの機能、使い方、管理方法を理解し、機能・料金の確認へ進めること。成功条件は、実測した関連語を自然な説明へ反映し、全6言語の本文をJSなしでも取得でき、言語URL・canonical・hreflang・サイトマップが一致すること。さらに、翻訳更新の漏れを公開前の自動検査で防ぐ。

対象は現行サイトの英語・日本語・ヒンディー語・スペイン語・フランス語・簡体字中国語。優先国の指定がないため、日本、米国、英国、インド、スペイン、メキシコ、フランス、シンガポールを調査した。新しい対応言語、国名だけを替えたページ、他社比較、未確認の製品機能・実績、外部リンク獲得、検索順位の保証は範囲外。

## 調査方法と読み方

Chrome Extensionでログイン済みAhrefsのKeywords Explorerを操作。Google・国別データベースで、Related terms → **Also talk about / Top 100**を確認した。これは上位ページが言及する関連語であり、単なる同義語でも共起回数でもない。表のSVはその国の推定月間検索ボリューム。KDやSVは観測時点の推定値で、獲得可能トラフィック・成約数を意味しない。

各レポートの最初の表示ページを記録した標本調査。全キーワード・全世界の網羅調査ではない。Ahrefs画面には9月29日からGoogle SERPデータの不整合があり得るとの告知があるため、KD 0を難易度ゼロと断定しない。一般語、無関係なブランド、ナビゲーション語は本文への採用から除外した。

一次記録: [ahrefs-observations-2026-10-03.json](ahrefs-observations-2026-10-03.json)。各レポートURL、シード、表示語、SV、KD、更新表示を保存。

| 国 | シード | 確認した関連語とSV（例） | 採用方針 |
|---|---|---|---|
| 日本 | AIエージェント | AIエージェント 42K、AIエージェントとは 16K、agentic ai 3.2K | タイトルでAIエージェントと業務自動化を明示し、FAQで動作を説明 |
| 米国 | ai workflow automation | workflow automation 61K、AI agents 46K、decision making 26K | 自動化・ワークフロー・意思決定資料を具体化 |
| 英国 | ai workflow automation | workflow automation 16K、AI agents 4.2K、ai workflow automation 700 | 英語共通ページで業務自動化の仕組みと管理を説明 |
| インド | ai workflow automation | workflow automation 39K、AI agents 33K、ai workflow automation 1.2K | 英語検索需要を確認。ヒンディー語は同じ製品説明を自然に翻訳 |
| スペイン | agentes de ia | agentes ia 1.4K、tomar decisiones 700、lenguaje natural 100 | agentes de IA、自然言語の依頼、意思決定、顧客フォローを説明 |
| メキシコ | agentes de ia | lenguaje natural 2.2K、tomar decisiones 1.7K、agentes ia 350 | スペイン語共通ページ。国固有の価格・提供条件は捏造しない |
| フランス | agent ia | agent ia 8.1K、tâches 1.5K、agents ia 1.1K、langage naturel 250 | agents IA、業務タスク、自然言語、会議・顧客対応を説明 |
| シンガポール | ai agents | ai agent 3.3K、customer service 2.4K、AI agents 1.4K、decision making 500 | 英語ページで顧客対応と判断のための資料を説明 |

インドの「एआई एजेंट」とシンガポールの「智能体」はAlso talk aboutで **No keywords found**。検索需要ゼロを意味しない。ヒンディー語・中国語コピーは製品内容に基づく翻訳であり、各語の検索ボリューム検証済みとは扱わない。シンガポールのai workflow automationは使用可能な行を取得できず、ai agentsへ調査を広げた。中国本土の検索エンジン・百度は未調査。

## 実装と判断

- 英語 `/` と日本語 `/ja.html`、ヒンディー語 `/hi.html`、スペイン語 `/es.html`、フランス語 `/fr.html`、簡体字 `/zh-Hans.html`。既存の`.html`配信規約を利用し、S3で扱いの違う新しいディレクトリURLは増やさない。
- 既存の翻訳辞書を使い本文全体を事前生成。`lang`、検索タイトル、説明、OG情報、SoftwareApplicationのURL・説明も各言語で整合させる。
- 全ページが自分自身をcanonicalにし、同一の相互hreflang集合とx-defaultを持つ。言語リンクは通常の`a href`で、JSなしでも利用可能。
- Google推奨の言語別URLを採用。同じ言語圏に独自条件がないため、国ごとのコピーを増殖させず共通言語ページを利用。国別検索データとURLの言語区分は別概念。
- 本文に業務自動化の仕組み、会議・顧客対話後の活用、進捗管理・アクセス範囲のFAQを追加。実機能を超える無制限な自律実行・保証は記載しない。FAQ構造化データのリッチリザルトは標榜しない。
- 旧`?lang=`リンクはCloudFrontで言語URLへ301転送。言語以外のクエリは保持。ホームへの国・Accept-Language推定リダイレクトを止め、URLによる言語選択を安定させる。プレビューの静的サーバーでも明示的な旧言語リンクをJSで引き継ぐ。
- サイトマップへ全言語を追加。ホームの古いlastmodは除き、毎回架空の更新日を付けない。既存下層ページは維持。
- 生成物をコミット可能なHTMLとして保持し、公開前チェックで再生成漏れを検出。新しいnpm/pip依存は追加しない。

根拠: [Googleの多言語サイト指針](https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites)、[Google hreflang仕様](https://developers.google.com/search/docs/specialty/international/localized-versions)、[Ahrefs Related terms説明](https://ahrefs.com/academy/how-to-use-ahrefs/keywords-explorer/related-terms)。

## 更新と検証

編集元: `site/index.html`、`site/home-i18n.js`（日本語・メタ情報）、`site/home-locales.js`（他言語）、`site/home.css`。生成された5言語HTMLを直接編集しない。

```sh
python3 scripts/build-localized-home.py
python3 scripts/build-localized-home.py --check
python3 scripts/check-home-seo.py
node --test tests/*.test.cjs
```

`check-home-seo.py`は生HTMLの本文・FAQ・メタ情報・schema・相互hreflang・言語選択・リンク先ファイル・同一ページアンカー・サイトマップを検査。CloudFrontテストはprodソースとTerraform埋め込みコードの両方で転送の終端、クエリ保持、繁体字の誤変換防止、dev認証、配布ファイルへの非干渉を確認する。実ブラウザー検証の記録は実施後に追記する。

## 公開・計測・残る制約

当初のローカル実装に続き、ユーザーから本番反映の明示的な承認を受領。最新mainのガイド・料金・連携一覧の更新を保持して統合し、PRのCI後に通常のmainマージ・本番デプロイを行う。devへの先行配信は未実施。devのCloudFront FunctionはTerraform管理なので、devへHTMLだけをpushしてもエッジ転送の更新にはならない。

prod公開時はHTMLとCloudFront Functionの両方が必要。Function更新のcontinue-on-errorを外し、失敗時はデプロイを失敗として扱う。加えて実URLへのHTTP確認を必須とする。Terraform適用は行っていない。認証・S3バケット・IAM権限への変更はない。

ロールバックは以前のサイトHTML/JS/CSSとCloudFront Functionを同じ版へ戻してキャッシュを無効化する。DB変更なし。生成HTMLの容量増加とソース/生成物の二重管理はCIの再生成一致検査で管理する。

公開後にSearch Consoleでサイトマップを送信し、6URLの取得・canonical・言語・インデックス状況を確認。国×ページ別に28日単位の表示回数、クリック、CTR、対象語の順位を比較し、言語ページから料金・登録への遷移も計測する。直後の順位上昇は保証しない。転送ループ、404、言語誤表示、登録遷移低下をガードレールとする。

下層ページ全体の翻訳・内容更新、リンク獲得、国別導入事例、Search Console実測、インドの現地語・中国本土の追加調査は今回の未実施項目。順位の最大化には公開後の検索実績を基にした継続改善が必要。

## ブラウザー検証（ローカル、Chrome Extension）

全6言語 × 幅1440/720/390px、計18表示を検証。FAQをEnterキーで開き、言語・canonicalを確認。ページ全体の横スクロール発生なし、FAQ全行の左右端は差0px、ヘッダーとナビゲーションの重なり0px、検出されたconsole warn/errorは0件。フランス語の長いブランド説明がナビゲーションに重なる既存の表示を修正し、全言語で再検査した。

実際の言語選択リンクでフランス語→日本語への遷移を確認。日本語のClaude Codeデモ切替で動的な文言も日本語を維持。`/?lang=es&utm_source=seo-check#workflow-faq`が、静的プレビューで`/es.html?utm_source=seo-check#workflow-faq`へ引き継がれることを確認。720px検査は狭い幅でのリフロー検査であり、ブラウザーの200%ズーム操作そのものではない。

画像と測定値: `artifacts/international-seo/`（ローカル証拠、S3公開対象外）。生HTMLの検証はJSを実行しないパーサーによるもの。実CloudFront・別ブラウザー・検索インデックス・登録完了・課金処理は未検証。


独立レビュー1回目の対応: CloudFront Function更新の失敗許容を除去。Terraformを含むPR/push向けの検証専用ワークフローを追加（Terraformの変更だけで公開処理を起動させない）。長い翻訳H1とヒンディー語の母音記号が重ならない行間へ調整。Python bytecodeは生成を抑止・ignore指定し、実体がJPEGの証拠画像を`.jpg`へ修正。

見出し修正後、ページ先頭も全6言語 × 幅1440/720/390pxで再検証（`hero-checks.json`と`*-hero-*.jpg`）。H1の矩形はhero領域内に収まり、横はみ出しなし。ヒンディー語FAQも新しい行間で撮り直した。Nodeテストはクエリの予約語キー対策を含め55件成功。`terraform fmt -check`、JS/Pythonの構文確認、ワークフローYAML解析、`git diff --check`も成功。Terraform plan/applyとGitHub上のCIは未実行。

独立レビュー: 別セッションの`gpt-5.5 / xhigh`で実施。1回目の4指摘を修正し、2回目のフォローアップレビューは **No findings**。レビュー記録は`artifacts/international-seo/independent-review-{1,2}.txt`。公開前のローカル実装・検証は完了。本番への反映と検索順位への効果は未検証。


## 本番統合時の追加検証

最新main（309480d）の変更を統合。料金表、Codex/Claude/Copilot表記、連携一覧、6言語ガイドおよびNotta導線を維持して5言語のホームを再生成。生成HTMLのガイド・ダウンロードリンクも各言語の配信URLへ合わせた。全1,110件のNodeテスト、再生成一致、SEO検査が成功。

統合前のChrome Extensionでの全6言語×3幅の証拠は上記の通り。統合後はChrome接続が利用できず、内蔵ブラウザーで日本語の構造・翻訳・料金リンクと英語1440pxのはみ出しなしを確認した後、ブラウザー操作がタイムアウト。統合後のモバイル・全言語再撮影は未完了であり、以前のスクリーンショットを最新main統合後の証拠とは扱わない。本番ではHTTPによるHTML・言語URL・旧URLの301・サイトマップ・静的リソースの配信を確認する。

統合後の独立レビュー3回目では今回の変更による回帰なし。既存の英語ホームHTML内リンクが日本語ガイド/ダウンロードを指すP2指摘を受け、英語の静的リンクを修正。生成時に日本語を含む各言語へ変換し、6言語すべての生HTMLリンクを検査に追加。修正後も1,110件成功。

リンク処理の追加補強: runtimeでも既知の全言語パスを扱い、計測クエリ・複数値・ハッシュを保持。6言語で旧URL・英語URL・フランス語URLからの変換と再実行を検査する6テストを追加し、全1,116件成功。なお保存済み/ブラウザー言語が静的ページの言語を上書きするというレビュー4の前提は該当しない（rendered locale優先）。クエリ保持とパス形式の堅牢性については改善を採用した。

最終の独立フォローアップレビュー（gpt-5.5 / xhigh）は **No findings**。対象のパス変換・クエリ保持・再実行テスト6件も成功。記録: `artifacts/international-seo/independent-review-5.txt`。本番公開後の結果はPRと配信検証記録を参照。
