# 営業・品質マネジメントの外部サンプル

- 営業：`https://simy.one/samples/fp-management/`
- 品質：`https://simy.one/samples/fp-management/?view=quality`
- 人物・支社別数値・会話は体験用の架空データ。顧客データや共有DBへ接続しない。
- 担当・期限・次の対応を試すと、閲覧者のブラウザー内だけに保存する。
- ID・パスワードは別途共有する。リポジトリに平文の認証情報は置かない。

`scripts/build-fp-sample.mjs <simy-web checkout>` で、承認済みSonyWorkbenchと既存UI・デザイントークンを再利用して書き出す。`samples/fp-management/source.json` が出典コミットを記録する。公開対象はindex.html、app.js、app.cssだけ。

通常のサイト同期はsamples/を除外する。専用Deploy protected FP sampleが、既存のprod配備ロールでCloudFrontの**現在のルーティングを保持して**認証を先に設定し、外部から401を確認してから専用3オブジェクトを配備する。権限が不足した場合、認証を省略した公開は行わない。

復帰は専用workflowを停止し、認証ガードを残したまま専用3オブジェクトをS3の前版へ戻すか削除する。認証を外して公開状態へ戻さない。資格情報を更新するときは専用SHA-256と本体ルーティング内の同じSHA-256を揃え、認証拒否・正しい認証のテストを再実行する。
