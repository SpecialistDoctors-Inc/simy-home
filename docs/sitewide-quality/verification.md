# 公開サイト共通基盤の検証結果

検証日 2026年11月19日。baseは4bdd65b0。これは今回の共通main/skip修正の検証であり、過去全依頼の実装完了報告ではない。

## 自動検証

- 199 HTMLの分類、うち184通常公開文書のmain一意・ターゲットID一意・tabindex・skip参照・共有CSS・再生成冪等性を検査。
- ローカライズhome、料金予告、service pricing、content、HP業種ページ、共通header、home SEO、site SEO、guide intentのcheckを同一ツリーで順次実行し全件成功。
- `node --test --test-concurrency=2 tests/*.test.cjs` は1648件成功、失敗0、skip0。
- `git diff --check` 成功。
- 共通CSSは2KiB未満、外部import/urlと包括的!importantなし。law-firm専用配信prefixにも同一CSSを含めrelease manifestを更新。
- HTML6件のbaseline hashをUI差分に合わせ更新。checkout JSON/JSとpricing-catalogのhashは維持。

## ブラウザー検証

Playwright Chromium、1 browser、390/1440px、reduced-motionで、about、careers、how-it-works、日本語home、英語home、claude-code guide、clinic、law-firm、legalの9ページを検証した。18ケースで最初のTabによるskip表示、ヘッダーより前面の表示、Enter後のmainフォーカス、main一意を確認。ページ全体の横はみ出し0件。初期の日本語homeで既存skipのtransitionが画面外表示を残す問題を再現し、修正後に同条件で通過した。

これはローカル静的サーバーの検証で、外部通信は遮断した。フォーム送信、認証、決済、実ダウンロード、本番CDN、Search Console、実利用のCore Web Vitals、実支援技術の手動検証を実施済みとはしない。320/768px、全6言語、200%拡大の全要件検証も残る。

`old/contact.html` は旧Reactアプリとして検査対象に含めたが、実行時mainは0だった。静的wrapper追加で将来mainを重複させる修正は行っていない。旧ルートの表示内容とアプリのルーティングを調べ、過去要件に合わせた修復または転送を確定する必要がある。

## 残る受入条件

過去スレッド原文の取得・訂正追跡・199ページへの割当、ページごとの本文/機能/提供条件の検証、残る表示条件、旧問い合わせ画面、本番マージ・配信確認が未完了。現在は本番へ未反映。要件網羅の入力不足はrequirements-coverage.mdに記載した。
