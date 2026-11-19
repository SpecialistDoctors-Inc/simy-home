# SEO・情報設計のレビューと横断判断

## 適用範囲と読み方

2026-11-19時点の `origin/main` を読み取り、公開資料を参照したレビュー。以下は世界順位の認定や本人への取材ではなく、10人の公開発信・専門領域を参考にした分析視点である。「適用仮説」は今回のレビューによる提案であり、本人の発言・承認・SIMYの推奨を意味しない。受入条件は [quality-standard.md](quality-standard.md) を参照する。

レビュー時の台帳は199 HTML、index 159、その他40。過去の148 HTML / index 122という記録を現在の母数や検証結果に転用しない。Codex関連スレッドのユーザー依頼原文との照合が終わるまでは、既存資料だけで全要求を網羅したとは扱わない。

## 10の分析視点

| 公開資料の発信者 | 資料URL | 今回の適用仮説 |
|---|---|---|
| Aleyda Solis | https://www.aleydasolis.com/en/ | 国際SEOとして翻訳URL、検索意図、提供条件を分けて確認する。国名だけの複製ページを増やさない。 |
| Lily Ray | https://www.amsive.com/insights/seo/ | 著者・会社・出典を明確にし、金融・医療・セキュリティの未実証の信頼主張を避ける。 |
| Marie Haynes | https://www.mariehaynes.com/ | 単語の出現率より、利用条件・手順・注意点への実用的回答を優先する。 |
| Glenn Gabe | https://www.gsqi.com/marketing-blog/ | URLやindex方針の変更を追跡し、宣言値だけでなく配信後の挙動まで検証する。 |
| Barry Adams | https://www.polemicdigital.com/blog | 情報構造、公開日・更新日、可視パンくずと構造化データを実態に合わせる。 |
| Cindy Krum | https://mobilemoxie.com/blog/ | 狭い画面とレンダリングを確認し、重要本文・主要リンクを静的HTMLに保持する。 |
| Brodie Clark | https://brodieclark.com/ | schemaの存在と実際の検索表示を区別し、リッチリザルトや順位改善を未観測で主張しない。 |
| Kevin Indig | https://www.growth-memo.com/ | 流入数に加え、適切なガイド・ダウンロード・問い合わせへの到達を評価する。 |
| Cyrus Shepard | https://zyppy.com/cyrus/ | 機械的なリンク量より、文脈に沿った次の行動と内部リンクの意味を明確にする。 |
| Patrick Stox | https://ahrefs.com/seo/technical-seo | canonical、クロール、サイトマップ、内部リンク、実配信を照合する。 |

上記URLは資料の入口であり、特定の文の引用元ではない。取得時にAmsive、Marie Haynes、Polemic Digital、MobileMoxie、Brodie Clark、Growth Memo、Zyppy、Ahrefsの入口はHTTP 200だった。HTTP 200だけで記事本文の完全な取得や精読を証明しない。Growth Memoは取得HTMLにJavaScriptを要求する表示を含む。Aleyda Solisの国際SEOページとGSQiのブログはHTTP 403で、今回本文を取得できていない。Marie Haynesの旧 `/resources/eeat/` とZyppyの旧 `/seo/internal-links/` は404だったため、そのURLの内容は根拠として採用していない。発信者への具体的な主張の帰属や引用には、取得可能な個別記事の追加確認が必要である。

技術判断の一次仕様は、[Googleの有用なコンテンツ指針](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)、[多言語サイト指針](https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites)、[hreflang仕様](https://developers.google.com/search/docs/specialty/international/localized-versions)、[Article仕様](https://developers.google.com/search/docs/appearance/structured-data/article)も参照する。

## 第1ラウンド：SEOと他分野の対立

| 論点 | 対立する要請 | 判断と理由 |
|---|---|---|
| 説明量 | SEOの詳しい説明とデザインの短いページ | 短い回答を先に置き、詳細を目次から到達できる本文へ。最低文字数や共起語率を合否基準にする案は却下する。 |
| 行動喚起 | 強いCTAと事実に慎重な説明 | 具体的で短いCTAを採用し、プラン・権限・データの条件を判断場所に表示する。未実証の保証表現は却下する。 |
| 多言語展開 | 検索対象の拡大と翻訳の品質・維持負荷 | 実在する静的翻訳だけをhreflangへ宣言する。クライアント翻訳と検索公開言語を区別し、国名差替えページの量産は却下する。 |

## 第2ラウンド：デザインとの最終調整

| 提案 | 採否 | 実装・検証への条件 |
|---|---|---|
| 共通CSSで包括的な `!important` を使わない | 採用 | 共有する振る舞いとページ固有の物語・図解を区別し、一括上書きで壊さない。 |
| 日本語本文16px・行高1.8 | 条件付き採用 | 長文本文に適用する。ナビゲーション、表、図中ラベルは用途別に判断し、全要素への強制は却下する。 |
| 描画ページのskip/main | 採用 | 一意のmainと機能するスキップ先を検証する。転送・認証コールバック等は用途別の対象台帳で扱う。 |
| 長いCTAの折返し | 採用 | ラベルの意味を保持し、320pxと拡大表示で本文・CTA・表を確認する。文字の過度な縮小で解決しない。 |
| 動くデモの減動・手動・noJS対応 | 採用 | noJSでも製品説明・価格・主要リンクが読めること。デモ操作だけに検索上重要な情報を依存させない。 |
| 職種別の物語を維持 | 採用 | 入力・成果物・人の判断を職種ごとに具体化する。未実証の成果や機能の断定は維持対象にしない。 |

最終案は、共通の技術基盤とページ種別ごとの本文設計を組み合わせる。ホーム・職種・ガイド・会社情報の目的を保持し、検索品質は回答・根拠・理解・次の行動で判断する。

## 読み取りで見つかった不足と検証境界

- `check-site-seo.py` はcanonical、固有title/description、H1数、schema構文と存在、OG/Twitter、相互hreflang、内部ファイルとアンカー、サイトマップを既に検査している。これらを保護し、本文との意味上の整合は別途確認する。
- 新しい5ガイドの日本語・英語、計10ページでArticleのauthor/datePublishedが未設定。ニュース2ページでArticleの日付が未設定。Googleの一律必須条件違反と断定せず、編集責任・日付の透明性の改善候補とする。日付を捏造しない。
- 法律事務所ページの同一画像を使う6要素にwidth/height属性がない。CSSによる領域確保を確認し、必要な寸法を補う。属性欠落だけでCLS悪化を実測済みとしない。
- 読み取り範囲では公開ページのviewport欠落と、内部からリンクのないHTMLは未検出。ただしライブ配信や全操作の成功を意味しない。
- 静的検査の成功は、CloudFront転送、フォーム送信、ダウンロード、言語切替、検索登録、順位改善の証拠にはならない。実行した検証と未検証を分けて記録する。

このレビュー文書自体は、上記の候補をすべて実装・検証したという完了報告ではない。
