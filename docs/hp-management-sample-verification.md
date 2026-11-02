# 運用担当向け: サンプルの検証記録

この文書は2026-10-31の受入検証の記録です。医院での使い方は[医院向け手順書](hp-management-customer-guide.md)、環境の準備は[運用側設定ガイド](hp-management-setup-guide.md)を参照してください。


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

## 専用更新サービスの継続検証

2026-11-02からは、親Codexチャットの定期実行に依存しない専用更新サービスを追加で検証しています。医院の担当者が扱うものは従来どおり Codex と Google Sheet だけで、SIMY への登録、SIMY API、WorkFlow は使いません。運用担当は [更新サービスの運用手順](../examples/hp-management/runner/OPERATOR.md) に従って、専用の Google 接続、Codex ログイン、Docker ホスト、GitHub 権限を設定します。

新規依頼 `dabb94d2-ed77-4dfa-8bd5-fee5984bd227` revision 2 について、サービスが受付表を定期読取りし、許可済みのお知らせ本文に「この追記は独立した自動更新サービスの動作確認です。」を1回追加しました。今回の依頼登録は、このチャットのCodexと専用Google接続で行ったものです。医院側の新規環境からの登録は上記10月31日の検証と区別します。

専用Codexによる修正、実際のサイトのビルド・テスト、別Codexによる変更案のレビューが成功しました。確認処理の不具合は修正し、保存済みの修正結果を保持して運用者が確認処理だけを復旧しました。その後、確認済み変更案の段階でサービスを正常終了し、同じ保存領域から別のサービスプロセスで再開しました。この再開では修正・レビューを繰り返していません。

| 確認項目 | 実際の結果 |
| --- | --- |
| 開発版への反映 | サービスが [PR #342](https://github.com/SpecialistDoctors-Inc/simy-home/pull/342) を作成し、CI成功後にdevへ統合。[配信run 41403577869](https://github.com/SpecialistDoctors-Inc/simy-home/actions/runs/41403577869) が成功。 |
| 正確な成果物 | source `73377b98757c2615024964a632f10736f3f62a85`、artifact `13122009048`、hash `48fe936bafa996fd7d93f09ba5e717f0bdf4facbf392c08093e7736032c83f21` を照合し、8静的ファイルとversion.jsonが保存成果物と一致。 |
| 表示 | 実ブラウザでお知らせを展開し、パソコンと390pxのスマートフォン幅で追記と折り返しを確認。 |
| 受付表 | サービスが `test_result` と `dev_preview_ready` を各1件記録。専用Google接続から同じ依頼・revision・成果物を読戻し。 |
| 通知 | 許可済み宛先に1通送信。送信済み本文の照合に加え、2026-11-02T07:06:02Zに同じメッセージが宛先アカウントの `INBOX` に存在することを確認し、台帳を `inbox_verified` に更新。 |
| 重複防止 | 完了後12回の定期読取りで追加処理なし。保存した修正・検証・レビュー記録のハッシュが同じで、PR作成・dev統合・各結果記録・通知は各1件のまま。 |
| 本番の保持 | 既存本番の8静的ファイルとversion.jsonの全9ファイルが、試験前と同じSHA-256。今回の変更は未公開。 |

実機の受付から開発版・通知までの検証は上記の範囲で成功しています。サービス実装と配布設定は [PR #341](https://github.com/SpecialistDoctors-Inc/simy-home/pull/341) にあります。実装の独立レビューはClaude Code、依頼の変更案のレビューは別のCodexが担当しました。68件の回帰テストに加え、LinuxのCIでも専用AppArmorプロファイルの強制モードを確認し、実際のCodexで作業範囲外の書込み・運用側秘密ファイルの読取り・コマンドからの通信が拒否されることを確認しました。

新しい本番公開には、この revision の同一成果物を示す医院の明示承認と既存の本番 Environment 承認が必要です。常時稼働は運用ホストとDockerの稼働に依存し、今回のMacを24時間稼働サーバーと扱いません。
