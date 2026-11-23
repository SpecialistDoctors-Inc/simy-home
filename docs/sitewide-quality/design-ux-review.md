# 全公開ページのデザイン・UXレビュー

作成日: 2026-11-19（日本時間）。対象: `simy-home` の公開ページ。調査時点の `origin/main` の文書・HTML・共通CSS/JSを読み、デザイン10視点とUX10視点で評価した。

## 方法と根拠

以下は公開活動・原則を参考にした**当方の適用仮説**である。本人への依頼、参加、発言、推薦はない。客観的な世界トップ10ランキングでもない。ラウンド1・2は参照視点を用いた設計上の反論と裁定の記録であり、実在人物同士が議論した記録ではない。

参考URLは今回本文を取得・読了していない。既存リポジトリに詳述された原則と、一般に公開されている活動を参照した候補であり、直接の引用や本人への意見の帰属には使用しない。後述のHTTP確認は到達性だけを示す。

元の体験原則は [2026-09-30-guide-pages-handoff.md](../handoff/2026-09-30-guide-pages-handoff.md) の「2026-10-01 追記: 全ページ共通の体験原則（ユーザー指示）」にある。

1. 読者が「そんなことがやりたかった」と気づく場面を見せる。
2. 文字を読み込まなくても、眺めて理解できる構成にする。

同文書ではこの2点を共起語率・文字数より優先する。一方、「SEO本文をdetailsに集める」ブループリントは「案・未承認」とされており、そのまま確定要件として適用しない。

併用した根拠:

- [HPマンダラチャート](../handoff/hp-mandala-2026-10-01.md): ガイドから顧客になる流れ、数値の根拠、実画面、更新日、運営者、登録手順、回遊、技術整合。
- [For Engineer設計根拠](../engineer-wow/design-rationale.md): 具体的な仕事と結果、画像の出典・提供状態、手動操作、減動、JSなしの説明、共有失敗時の回復。既存の専門家参照もここから引き継ぐ。
- [Clinic表示ルール](../design/clinic-presentation-rules.md): 3つの便益の章順、漫画の維持、価格の共通表現。
- [ロセンズ表示ルール](../design/rosenz-presentation-rules.md): 対象業務、操作、料金・条件、通貨・税区分、共通ヘッダー、幅320–1440pxの検証。
- [共通ヘッダー設計](../shared-header/compact-header.md): native details、JSなし、Escape、フォーカス復帰、小画面の1行ヘッダー。

**要件網羅の限界:** これらは過去要件の一部を示す二次資料である。Codex過去全チャット原文を取得・照合しておらず、全要件の網羅を確認したとは言えない。取得できた原文の日時・対象ページ・要求・後続訂正・実装状況を別途台帳へ記録し、取得できなかった範囲を明示する必要がある。

## デザイン分野の10視点

| 参照する実践者 | 公開原則・参考URL | 今回への適用仮説 |
| --- | --- | --- |
| Brad Frost | [Atomic Design](https://atomicdesign.bradfrost.com/chapter-2/) | ヘッダーに加え、本文余白・操作・料金表の共通部品を既存実装から抽出する。 |
| Karri Saarinen | [10 rules / Figma](https://www.figma.com/blog/karri-saarinens-10-rules-for-crafting-products-that-stand-out/) | 対象と便益を絞り、細部の一貫性で品質を伝える。既存漫画や職種別の物語は維持する。 |
| Ethan Marcotte | [Responsive Web Design](https://alistapart.com/article/responsive-web-design/) | 流動レイアウトと可変画像を用い、320pxから分割PCまで確認する。 |
| Jen Simmons | [Intrinsic Web Design](https://www.youtube.com/watch?v=AMPKmh98XLY) | 端末幅だけでなく、翻訳の文字量や拡大にも耐える内容中心のレイアウトにする。 |
| Andy Bell | [CUBE CSS](https://cube.fyi/) | 共通の基礎、組合せ、例外を区別し、全ページ上書きの副作用を抑える。 |
| Dan Mall | [本人サイト](https://danmall.com/) | 既存の画面から共通性を抽出し、デザインシステム自体を目的とする全面改築を避ける。 |
| Vitaly Friedman | [著者ページ](https://www.smashingmagazine.com/author/vitaly-friedman/) | 複雑な料金・業種分類を、見出し・比較・手順で判断可能にする。 |
| Rauno Freiberg | [Craft](https://rauno.me/craft) | フォーカス、切替後の状態、拡大画像、共有失敗まで操作の細部を整える。 |
| Emil Kowalski | [You Don’t Need Animations](https://emilkowal.ski/ui/you-dont-need-animations) | 動きは変化の説明に限定し、停止・減動・静止状態でも理解可能にする。 |
| Josh W. Comeau | [Animation](https://www.joshwcomeau.com/animation/) | 動画だけに依存せず、手動で探索できる例と静止した本文を併設する。 |

## UX分野の10視点

| 参照する実践者 | 公開原則・参考URL | 今回への適用仮説 |
| --- | --- | --- |
| Don Norman | [Emotional Design](https://jnd.org/emotional-design-people-and-things/) | 第一印象の魅力を、分かる操作と信頼できる提供条件へ接続する。 |
| Jakob Nielsen | [10 Usability Heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/) | 進行・判断待ち・提供予定・未確認を区別し、操作結果を正しく知らせる。 |
| Steve Krug | [Don’t Make Me Think](https://sensible.com/) | 誰のどの仕事がどう変わるかを冒頭で示し、CTAを具体的にする。 |
| Luke Wroblewski | [Showing the Work of Agents](https://www.lukew.com/ff/2142/showing-the-work-of-agents-in-ui) | 全ログを読ませず、便益→見どころ→実画面→詳細の順に深掘り可能にする。 |
| Jared Spool | [UX Articles](https://articles.uie.com/) | ページ閲覧数だけでなく、目的達成と次の行動の障害で評価する。 |
| Gerry McGovern | [Top Tasks](https://gerrymcgovern.com/books/top-tasks-a-how-to-guide/) | ガイド閲覧、対応可否確認、料金確認、利用開始という主要タスクを優先する。 |
| Peter Morville | [User Experience Honeycomb](https://semanticstudios.com/user_experience_design/) | 有用性・発見性・使いやすさ・信頼性・アクセシビリティを個別に確認する。 |
| Susan Weinschenk | [The Team W](https://blog.theteamw.com/) | 長文を意味単位に分け、見出しと図で認知負荷を下げる。 |
| Indi Young | [著書一覧](https://indiyoung.com/books/) | 職種名だけでなく、会議後の転記やAIへの再指示という実際の行動から構成する。 |
| Whitney Quesenbery | [A Web for Everyone](https://rosenfeldmedia.com/books/a-web-for-everyone/) | キーボード、減動、拡大、多言語、支援技術を標準の利用条件として扱う。 |

## ラウンド1: 分野内の反論と採否

| 論点 | デザイン側の反論 | UX側の反論 | 裁定 |
| --- | --- | --- | --- |
| 全ページ同一レイアウト | 共通性は必要だが職種別の既存物語を壊す | ガイド・料金・法務で読者の目的が違う | **却下**。色・操作・読みやすさの基礎を共通化し、ページ種別の情報構造を残す。 |
| 大きな動くデモを全ページへ | 印象は強くても注目箇所が散る | 自動切替・待ち時間・減動対応の負担が増える | **条件付き採用**。説明上必要な既存デモを維持し、停止・手動選択・静止説明を要求する。新規の全ページ追加は採らない。 |
| 本文の大幅削減 | 見出しと図で視線を整理できる | 必要な条件や手順まで削ると判断できない | **条件付き採用**。重複説明を整理し、主要回答・条件・根拠は保持する。短さ自体は採点しない。 |
| 全ログや実画面をそのまま掲載 | 実物の説得力はある | 小さな文字と状態の曖昧さが理解を妨げる | **条件付き採用**。短い説明、拡大手段、設計・合成・実績の注記を隣接させる。 |
| 既存の操作を再実装 | 整った既存details・Escapeを壊す危険がある | 到達性と回復の検証に労力を使うべき | **却下**。実在する欠落と障害を補完し、既存挙動を回帰検証する。 |

## ラウンド2: SEO・アクセシビリティ・性能との横断裁定

| 提案・対立 | 反論と採否 | 受入条件 |
| --- | --- | --- |
| SEOの最低文字数・共起語率を品質条件から外す | **採用**。元の体験原則と整合。ただし短いほど高品質という代替指標も却下。 | 検索意図に必要な回答、利用条件、根拠、更新情報を欠かさない。 |
| 主要回答を先頭、詳細を本文へ | **条件付き採用**。法務・料金・ニュースまで同じheroにしない。 | ガイドは質問への回答、LPは対象業務と便益、料金は課金条件を先に示す。既存の意味ある章順を保持する。 |
| schemaと可視内容の一致、10新ガイド＋2ニュースの著者・日付透明性 | **採用**。架空の執筆者・監修者を作らない。 | 実在情報が確認できる担当だけ掲載。編集日を第三者情報の確認日へ転用しない。対象件数はSEO側の対象表と照合する。 |
| 159 index／40 nonindexの保護 | **条件付き採用**。これはSEO側の調査値で、このレビューで独立再集計していない。 | 変更前台帳と差分を検証し、個別の検索意図変更がある場合のみ理由を残す。 |
| main／skip欠落の補完 | **採用**。存在だけでなく操作結果まで検証する。 | 一意の本文対象、キーボード移動、表示、sticky headerとの重なりを確認。既存details／Escapeの作り直しはしない。 |
| 全画像へwidth/heightを必須化 | **条件付き採用**。属性数だけでは表示安定性を評価できない。 | HTML寸法またはCSSのaspect-ratio等で読込み前の領域を予約し、実際のレイアウト移動を確認する。 |
| 動く説明 vs 性能・アクセシビリティ | **条件付き採用**。巨大動画の追加を品質向上と同一視しない。 | 画面外停止、減動、手動操作、静止説明、必要な遅延読込みを維持する。 |
| 導入率の強化 vs 正確性 | **正確性を優先**。架空の実績、処理速度、無人実行保証は却下。 | 現行・予定、月額・年額、税区分、画像の出典を明示し、CTAの行き先を表示名と一致させる。 |

## 全ページ基準として確認する具体的な8項目

以下は全ページに同じ不具合があるとの断定ではない。実在した差異・実装から、対象全体に適用する検査と修正候補を示す。

| # | 観察した根拠 | 修正候補・確認 |
| --- | --- | --- |
| 1 | `site/site-theme.css` は色・ボタン中心。aboutはGeist、ガイドは別のsansと行高、engineersは共通テーマを参照。 | 読み物本文16px、行高、行長、段落・見出し余白を共通の基礎へ抽出する。専門LPの固有構成は維持。 |
| 2 | aboutの補足色 `#7a7a78` / `#9a9a98` と背景 `#f9f9f6` は通常文字のAAを要精査。 | 実際の使用箇所と背景で4.5:1を測定。未使用変数を変えただけで完了としない。 |
| 3 | codexガイドはskipとmainがある一方、about/contact/privacyで同等のskipが見つからず、engineersはmainのみ確認。 | 生成元で一意の本文対象とskip導線を補完。ガイドのskip z-index:100とヘッダー1000の重なりも検証する。 |
| 4 | 共通ボタンのlight最小幅15rem、primary12.75rem。 | 320px・長い翻訳・200%拡大で確認。必要な箇所へ幅制限と折返しを加える。 |
| 5 | 共通button hoverは3px移動。既存の減動対応はあるが、ガイドはsmooth scrollを独自指定。 | focusを見える状態に保ち、各ページ独自の動きも減動設定で検証する。 |
| 6 | engineersは画像拡大・出典注記・no-JS説明を設計済み。他ページへ同じ保証は確認できていない。 | 意味ある画像に代替文、画像外の説明、必要な拡大手段。設計・合成・実績を混同しない。 |
| 7 | contact本文は見出し、短文、mailtoのメールアドレスが中心。 | メール連絡であること、相談対象、送る内容を具体化。架空フォームや未確認の回答時間は加えない。 |
| 8 | 共通JSは言語のaria-currentを更新するが、通常ナビの現在地は一律ではない。 | 同じ内容の翻訳先と現在地を検査。未翻訳は実態を示し、JSなしでも行き止まりにしない。 |

## 実装を受け入れる際の証拠

- ページ一覧と生成元を対応付け、適用した基準と例外理由を記録する。
- 320px、小画面、デスクトップ、200%相当、長い翻訳で本文・CTA・表の欠落や横はみ出しを確認する。
- キーボード、skip、共通メニュー、Escape、減動、JSなしの確認結果を残す。
- 変更後の画像を保存し、HTML検査だけで視覚品質を達成したとしない。
- 「読者が価値を自分の言葉で説明できる」「導入率が改善する」は設計仮説であり、静的検査・ブラウザテストだけでは立証しない。

## 参考URLの到達確認

2026-11-19に `curl -IL`（証明書検証あり、リダイレクト追従、接続3秒・全体8秒上限）で確認した。本文内容・原則の帰属・最新性の確認ではない。403は参照内容の否定を意味しない。

| 結果 | 対象 |
| --- | --- |
| HTTP 200 | Brad Frost、Karri Saarinen、Ethan Marcotte、Jen Simmons、Andy Bell、Dan Mall、Vitaly Friedman、Rauno Freiberg、Emil Kowalski、Josh W. Comeau、Don Norman、Jakob Nielsen、Steve Krug、Luke Wroblewski、Jared Spool、Gerry McGovern、Peter Morville、Susan Weinschenk、Indi Youngの上記URL。 |
| HTTP 403 | Whitney Quesenberyの出版社書籍URL。外部アクセス制限等の可能性があり、本文未確認のままとする。 |

初回候補の `https://www.blog.theteamw.com/` はcurl終了コード60（証明書検証失敗）、`https://indiyoung.com/books/mental-models/` は404だったため、上表で200だったブログの正規ホストと著書一覧へ変更した。証明書検証の無効化はしていない。Indi Youngの出版社側書籍URLも403のため、著書一覧を参照候補としている。
