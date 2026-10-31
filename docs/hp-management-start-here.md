# HP管理を始める

医院のホームページ更新を、共有の Google Sheets を窓口にして進めるための最小構成です。現時点で **SIMY への登録・ログインは必要ありません**。将来必要になれば、同じ Sheet の依頼ID・revision を保ったまま連携できます。

| 役割 | 用意するもの | 担当すること |
| --- | --- | --- |
| 医院 | Codex、Google Drive 接続、共有 Sheet、受付スキル | 要望を記録し、dev の確認ページをレビューする |
| 開発・運用担当 | Codex、Google Drive / Gmail 接続、非公開サイト設定、SQLite 台帳、GitHub / AWS | 依頼を重複なく処理し、開発・配信・連絡を担当する |

医院側に GitHub、AWS、Docker、開発用の認証情報を渡す必要はありません。リポジトリと配信先を操作できるのは開発・運用担当だけです。

- 医院向け: [受付の使い方](hp-management-customer-guide.md)
- 開発・運用向け: [設定と運用の手順](hp-management-setup-guide.md)

## 進め方

1. 医院が `Requests` に変更要望を記録します。
2. 開発・運用担当が同じ Sheet を読み、SQLite 台帳で依頼ID・revision・内容ハッシュを記録して重複を除きます。
3. 開発・運用担当が許可済みのリポジトリで実装・テストし、dev 確認ページを用意します。
4. 医院が dev で内容を確認します。
5. 人が、依頼ID・revision・source SHA・artifact ID・artifact hash が一致する成果物を明示承認してから、本番の保護された公開手順へ進みます。

Sheet の状態やセルに `approved` と書くだけでは本番公開になりません。レビューと本番承認は別の操作です。

## サンプルの確認先

- dev: [sample-clinic-dev.simy.one](https://sample-clinic-dev.simy.one/#news)
- 本番: [sample-clinic.simy.one](https://sample-clinic.simy.one/)

これらの URL は確認先です。個別の依頼が反映済みであることは、依頼に結び付くテスト結果と成果物の照合で判断します。

## 現在は手動で行うこと

2026-10-31の試験では、新規Docker環境へのCodexログインと受付スキル導入、医院役のGoogle接続による依頼の実書込み、別Google接続の開発側による読戻しと着手イベント追記まで確認しました。書込みにはCLIの標準の自動承認レビューを使用しました。Dockerは検証用で、医院の通常利用に必要なものではありません。

自動ポーリング、dev / 本番への自動反映、メールの自動送信は、まだ完了・検証済みとして扱いません。依頼を Sheet に入れた後は、開発・運用担当が内容を読んで着手します。Gmail を使う場合も、設定済みの宛先、台帳の送信予約、実送信後の読戻しを確認できるまで手動連絡を使います。

新しい環境での初回導入を試した履歴は、[ゼロ設定からの試験記録](hp-management-zero-setup-test.md)にあります。これは履歴であり、上記の自動化完了を意味しません。
