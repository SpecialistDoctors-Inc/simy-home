# 医院ホームページ編集の検証（2026-10-31）

## 検証範囲

35医院の公開HTMLを取得。文字コードを誤って復号した1医院（No.24）を成功件数から除外し、34医院を検証した。第三者サイトの公開・予約・フォーム送信は行っていない。

大量検証は、手元のアプリの再制作処理・編集プランナー・入力／出力検証・CLI推論ランタイムを使い、実際のAI推論結果をブラウザのDOMに適用した。API応答のモックは使用していない。ただし、大量検証を本番APIの負荷・安定性試験とは扱わない。医師紹介などの下層6ページは編集エンジンの検証であり、製品の下層ページ生成機能の合格を意味しない。

## 結果

- 30医院で、見出し変更・曖昧な依頼・写真未添付を各1件、計90件。文章変更は最終DOMと属性を再確認し30件合格。曖昧な依頼30件、写真未添付30件は変更せず確認を返した。
- 34医院のお知らせ依頼：29医院で実AIによる追加を適用。4医院は公開HTMLから編集可能なお知らせ一覧を特定できず確認。1医院は既存の休診日と依頼が矛盾するため確認。確認応答を「追加成功」に数えていない。
- 編集可能な30医院について、1440px・390pxの60画面で新旧記事の書体・色・行間・余白・罫線・アウトラインを比較。意図しない書式変更0件。カテゴリー見出しやラベルの不変も確認。日付の桁数による自然な文字幅の差は保持。
- 下層6ページの本文指定変更6件・添付画像差し替え6件、計12件合格。さらに自然文での紹介文の短縮を6件検証し、4件を適用、対象の本文が見つからない2件は確認を返した（詳細はJSON）。
- 既存の自動テスト1,564件が通過。ブラウザ回帰テストは、DL/UL/OL、カード、リンクで包まれたDL、日付専用欄、日本語日付、カテゴリーのラベル、3カテゴリーの枠、同一箇所の重複指示、別の箇所の同文指示、非初期化スライドの表示を確認。

## 修正内容

1. DL/UL/OL以外の既存記事の繰り返し構造にも対応。医院概要やページ全体・カテゴリー全体を追加先にしない。
2. 新しい記事は既存の要素・入れ子・クラスを複製し、カテゴリーのラベルを本文やタイトルで上書きしない。
3. 日付だけの欄と、日付＋タイトルの欄を区別。日本語の日付表記も維持する。
4. AIが親要素・子要素へ同じ指示を出した場合、同一の物理的な文章箇所への重複適用だけを除く。別箇所にある同文への変更は保持する。
5. 元サイトのスライド用スクリプトを停止したプレビューでも、カードを非表示にしない。横スクロール可能にし、カード幅を画面内に収める。
6. 以前の緑の強調線は復活させない。

## 医院別の結果

| No. | 公開サイト | 文章変更 | お知らせ | PC・スマートフォンの書式 |
|---:|---|---|---|---|
| 1 | [https://urachil.com/](https://urachil.com/) | 合格 | 追加適用 | 2画面一致 |
| 2 | [https://takinomizu-cl.com/](https://takinomizu-cl.com/) | 合格 | 追加適用 | 2画面一致 |
| 3 | [https://kotoni-hifuka-cl.com/](https://kotoni-hifuka-cl.com/) | 合格 | 追加適用 | 2画面一致 |
| 4 | [https://www.ginzahospital.com/](https://www.ginzahospital.com/) | 合格 | 追加適用 | 2画面一致 |
| 5 | [https://tnf-clinic.com/](https://tnf-clinic.com/) | 合格 | 追加適用 | 2画面一致 |
| 6 | [https://sapporo-shiroishi-hifuka.jp/](https://sapporo-shiroishi-hifuka.jp/) | 合格 | 追加適用 | 2画面一致 |
| 7 | [https://www.kojinkai.org/clinic/sapporo/](https://www.kojinkai.org/clinic/sapporo/) | 合格 | 追加適用 | 2画面一致 |
| 8 | [https://www.kitanoclinic.com/](https://www.kitanoclinic.com/) | 合格 | 確認を返す | 対象一覧なし |
| 9 | [https://ds-clinic.jp/](https://ds-clinic.jp/) | 合格 | 追加適用 | 2画面一致 |
| 10 | [https://soen-skinclinic.com/](https://soen-skinclinic.com/) | 合格 | 確認を返す | 2画面一致 |
| 11 | [https://takinomizu-hifuka.com/](https://takinomizu-hifuka.com/) | 合格 | 追加適用 | 2画面一致 |
| 12 | [https://keimei-kids-clinic.com/](https://keimei-kids-clinic.com/) | 合格 | 追加適用 | 2画面一致 |
| 13 | [https://www.shiozaki-naika.jp/](https://www.shiozaki-naika.jp/) | 合格 | 追加適用 | 2画面一致 |
| 14 | [https://www.brave.or.jp/](https://www.brave.or.jp/) | 合格 | 確認を返す | 対象一覧なし |
| 15 | [https://shinjuku-naika.jp/](https://shinjuku-naika.jp/) | 合格 | 追加適用 | 2画面一致 |
| 16 | [https://ebisu-naika.jp/](https://ebisu-naika.jp/) | 合格 | 追加適用 | 2画面一致 |
| 17 | [https://www.kureclinic.jp/](https://www.kureclinic.jp/) | 合格 | 追加適用 | 2画面一致 |
| 18 | [https://www.oyama-clinic.com/](https://www.oyama-clinic.com/) | 合格 | 追加適用 | 2画面一致 |
| 19 | [https://www.noge-neurology.com/](https://www.noge-neurology.com/) | 合格 | 追加適用 | 2画面一致 |
| 20 | [https://navitasclinic.jp/shinjuku-top/](https://navitasclinic.jp/shinjuku-top/) | 合格 | 追加適用 | 2画面一致 |
| 21 | [https://www.tana-kotori.com/](https://www.tana-kotori.com/) | 合格 | 追加適用 | 2画面一致 |
| 22 | [https://clinic-arai.jp/](https://clinic-arai.jp/) | 合格 | 追加適用 | 2画面一致 |
| 23 | [https://www.creaclinic.jp/](https://www.creaclinic.jp/) | 合格 | 追加適用 | 2画面一致 |
| 24 | [https://yoshitakeclinic.jp/](https://yoshitakeclinic.jp/) | — | 文字コード問題で除外 | 対象一覧なし |
| 25 | [https://www.itonaika-clinic.jp/](https://www.itonaika-clinic.jp/) | 合格 | 追加適用 | 2画面一致 |
| 26 | [https://fujii-naika-clinic.jp/](https://fujii-naika-clinic.jp/) | 合格 | 追加適用 | 2画面一致 |
| 27 | [https://sendai-douki-clinic.com/](https://sendai-douki-clinic.com/) | 合格 | 追加適用 | 2画面一致 |
| 28 | [https://yell-clinic.com/](https://yell-clinic.com/) | 合格 | 追加適用 | 2画面一致 |
| 29 | [https://www.taihakuclinic.com/](https://www.taihakuclinic.com/) | 合格 | 確認を返す | 対象一覧なし |
| 30 | [https://kyotoclinic.jp/](https://kyotoclinic.jp/) | 合格 | 追加適用 | 2画面一致 |
| 31 | [https://nakano-tsr.com/](https://nakano-tsr.com/) | 合格 | 追加適用 | 2画面一致 |
| 32 | [https://takada-naika.com/](https://takada-naika.com/) | — | 確認を返す | 対象一覧なし |
| 33 | [https://maedaclinic.com/](https://maedaclinic.com/) | — | 追加適用 | 2画面一致 |
| 34 | [https://kimachisasaki.jp/](https://kimachisasaki.jp/) | — | 追加適用 | 2画面一致 |
| 35 | [https://goto-naika-clinic.com/](https://goto-naika-clinic.com/) | — | 追加適用 | 2画面一致 |

## 証跡と限界

詳細な対象URL・結果・計測値・推論結果ファイルのSHA-256は [検証JSON](clinic-editor-2026-10-31.json) に記録。原HTML・推論プラン・スクリーンショットはローカルの検証フォルダに保存し、第三者のHTMLを公開サイトへ配置していない。

公開HTMLを使うため、会員画面、予約システム内部、JavaScript実行後だけ現れる情報、全サイトの画像配信・フォント・動作まで同一になることは未検証。4医院のお知らせ一覧の抽出、およびNo.24の文字コード対応は未解決であり、全医院・あらゆる依頼への完全対応とは認定しない。

本番反映と本番画面の正式API経由の確認は、この大量検証とは分けて記録する。
