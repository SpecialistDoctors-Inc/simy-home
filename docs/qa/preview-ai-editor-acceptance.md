# ホームページ編集体験の合格基準

依頼文を貼り付ける機能ではなく、ページの構造と依頼の目的を理解して、適切な場所に変更する体験とする。

| 項目 | 合格条件 |
| --- | --- |
| お知らせの分類 | 休診は一般のお知らせ、担当医の変更は担当医のお知らせ。無関係なカテゴリーや先頭の帯へ追加しない |
| 日付 | 「明日」を日本時間の具体的日付に解決。午後の具体的時刻や休診理由を創作しない |
| 文意による編集 | 正確な置換文字列の入力を要求せず、見出しや文脈から編集対象を選ぶ |
| 会話 | 判断できない対象・範囲は一問で確認し、回答後に元の依頼を実行する |
| 実行可能性 | 対応できない操作は説明し、成功したと装わない。画像生成・他ページ・予約サービス内部はこの体験の対象外 |
| 継続編集 | 直前の変更後のページを再読込して次の依頼に使う。同じお知らせを重複登録しない |
| 視認・取消 | 変更箇所へ移動して枠で表示。ひとつ戻す・最初に戻すで復元可能 |
| 分離 | 公開サイトは変更しない。ページ内リンク移動・スクリプト・送信は停止 |
| エラー | API・モデル・検証に失敗した場合は変更しない。失敗を日本語で表示 |
| モデル | ChatGPT認証のサーバーCodexを利用。画面上だけの疑似AIやAPIキーへの代替は使わない |

機械テスト、実モデル検証、本番ブラウザー操作を分けて記録する。実装だけでは合格にしない。

## 2026-10-30 検証記録

- 実モデル：gpt-6.1-sol、ChatGPT認証のLinux Codex。APIキーへの代替なし。
- 実ページ：urachil.comの公開トップページ。一般お知らせ・担当医・感染症の3カテゴリーを抽出。
- 本番入力「明日は午後休診です」：一般お知らせへ2026年10月31日の午後休診を追加。先頭の帯は作らない。
- 本番追加依頼「今追加した休診を、午前休診に変更して」：タイトルと本文の両方を変更。
- 本番「ひとつ戻す」：午後休診に復元。
- 本番で再び同じ休診を依頼：既存の掲載を説明し、重複なし。
- 実モデル「いい感じに直して」：対象と目的を質問。
- 実モデル「予約案内の文字を大きくして」→「WEB予約ボタンです」：会話を引き継ぎ、該当する2ボタンを選択。
- 実モデル：紹介文の意味による書き換え、担当医変更の別カテゴリー追加を確認。
- 実モデル：写真生成は未対応と説明し、変更操作なし。
- フロント1,560テスト成功。追加の実DOM検査で分類、再編集、不正ターゲットの拒否を確認。
- バックエンド11テスト、型チェック、ビルド成功。Sites version 51で本番API応答を確認。

画像生成・複雑な配置変更・別ページ・外部予約システム内部の編集は、本体の制作環境とは異なりこの体験では行わない。

## 2026-10-30: broader preview editing

Photo replacement now uses a JPEG/PNG/WebP upload (5 MiB limit, browser resizing to 1600 px). Only asset ID/name go to the planner; photo bytes remain in the browser. Added bounded whole-page redesign (modern/editorial/warm with chosen accent), section addition, explicit removal, and moving elements. Previous statements that all image/layout changes are unsupported are superseded for these operations. Image generation, booking backend changes, editing another page and publishing to an external service remain unsupported.

Validation: 1,560 frontend tests; 10 planner tests; TypeScript/build; actual Codex selected the greeting-section director image for a named replacement, returned a warm green redesign for a whole-page request, and asked for photo/position when missing. DOM checks verify replacement asset binding, no mutation on missing asset, original text/image count retained by redesign, and notice regression. Theme layout is bounded, not unrestricted design generation.
