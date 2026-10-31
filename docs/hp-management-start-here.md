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

## サンプルの検証結果

2026-10-31に、サンプルの受付から公開・通知受信までの検証を完了しました。

| 確認項目 | 確認できた事実 | 状態 |
| --- | --- | --- |
| 初回dev成果物 | [PR #313](https://github.com/SpecialistDoctors-Inc/simy-home/pull/313) を dev へ反映し、[run 41163859006](https://github.com/SpecialistDoctors-Inc/simy-home/actions/runs/41163859006) は成功。8つの静的ファイルが保存済み artifact `13028320719` と byte-for-byte 一致し、source `fc4355a5d74b32488d7c10ece465df38ed8d70e0`、artifact hash `3bd47d30e529c42e7eb081234b3376963202cf0bf42d30aafd912ed527570b7b` を照合した。 | 確認済み |
| Sheet の往復 | 新規コンテナの医院側 Codex が標準の自動承認レビューで `Requests` 1行と `ready_for_dev` を書込み、別 Google 接続の開発側が読取り・進捗追記。その後、医院側が `dev_preview_ready` の同じ成果物タプルを読戻した。heartbeat による2件目も、医院側が一意の依頼、`claimed`、`test_result`、`dev_preview_ready` の同一タプルを読み戻し、先行する `published` イベントが残ることを確認した。 | 確認済み |
| メール | 開発側 Gmail が設定済み宛先へ初回の preview・公開通知と heartbeat 起点の preview 通知を各1回送信し、provider の `SENT` と読戻しを確認。受信者が初回2通と追加1通の到着をそれぞれ確認し、台帳へ `inbox_verified` を記録した。台帳は同じ通知の重複送信を許可しない。 | 3通とも受信者確認済み |
| 本番 | 人による同一成果物の承認を private ledger に記録し、既存の本番 Environment reviewer を通過。 [run 41165087996](https://github.com/SpecialistDoctors-Inc/simy-home/actions/runs/41165087996) が成功し、main release `32d33b8e23a2d0af2f8136925b13911379fd857b` で公開した。2026-10-31T03:38:01.079056Z に本番の8ファイルが同じ ZIP と byte-for-byte 一致し、デスクトップと iPhone 16 幅でお知らせの展開・表示を確認した。 | 確認済み |
| 定期実行 | 5分のローカル heartbeat が実際に新しい Sheet 依頼を検出し、台帳で claim、許可範囲のお知らせ文追加、PR・dev 配信・確認まで進めた。[run 41166888036](https://github.com/SpecialistDoctors-Inc/simy-home/actions/runs/41166888036) は成功。source `f5a596c156dc6851a4978221b409c27fb723b3de`、artifact `13028304194`、hash `a4bb55ad97d63981103e0c9b0cfa899abbf192d37e02cb11c2caf38983e54891` を照合し、dev の8ファイルと artifact が byte-for-byte 一致、PC・モバイル表示を確認した。本番の既存8ファイルは変更していない。 | サンプル範囲で確認済み |

固定版 `fc4355a5d74b32488d7c10ece465df38ed8d70e0` の受付スキルをテスト環境に導入し、医院側の Codex から公開完了イベントまで読み戻せることも確認しました。Docker はこの導入検証用で、医院の通常利用に必要なものではありません。

この heartbeat は、端末上の Codex アプリが動いている間だけ動くローカル定期実行であり、24時間稼働のホスト型サービスではありません。試験用スケジュールは、この往復検証後に削除しました。継続運用には運用側設定ガイドに従って定期実行を設定します。メールの到達は受信者の回答により確認したもので、受信箱APIを直接読んだ証拠とは区別しています。

新しい環境での初回導入を試した履歴は、[ゼロ設定からの試験記録](hp-management-zero-setup-test.md)にあります。これは履歴であり、上記の自動化完了を意味しません。
