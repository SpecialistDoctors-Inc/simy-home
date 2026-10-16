# 営業・品質マネジメントの外部サンプル

- 営業：`https://simy-fp-management-demo.vercel.app/`
- 品質：`https://simy-fp-management-demo.vercel.app/?view=quality`
- 現在はVercelの独立したSIMYチーム内プロジェクト `simy-fp-management-demo` で公開する。Chrome/Safari等のHTTP Basic認証入力を使う。
- 人物・支社別数値・会話は体験用の架空データ。顧客データや共有DBへ接続しない。
- 担当・期限・次の対応を試すと、閲覧者のブラウザー内だけに保存する。
- ID・パスワードは別途共有する。リポジトリに平文の認証情報は置かない。

`scripts/build-fp-sample.mjs <simy-web checkout>` で、承認済みSonyWorkbenchと既存UI・デザイントークンを再利用して書き出す。`samples/fp-management/source.json` が出典コミットを記録する。公開対象はindex.html、app.js、app.cssだけ。

## Vercelでの配備

`node scripts/build-fp-vercel.mjs <dedicated deployment directory>` でBuild Output API v3の成果物を作る。3アセットはすべて認証関数のプライベートファイルとして梱包し、公開static領域には置かない。検証用ダイジェストだけを梱包し、平文パスワードは含めない。

専用ディレクトリで `vercel link --yes --project simy-fp-management-demo --scope simy-app`、`vercel deploy --prebuilt --prod --yes --scope simy-app` を実行する。既存SIMYアプリとDNSは変更しない。配備後に、共有する安定URLのHTML/JS/CSSそれぞれについて、未認証・誤認証の401と正しい認証の200、ローカル成果物とのバイト一致を確認する。生成された個別配備URLにはVercelの追加ログイン制限があるため、共有には上記の安定URLを使う。

## AWS経路（現在は権限不足で未公開）

通常のサイト同期はsamples/を除外する。専用Deploy protected FP sampleが、既存のprod配備ロールでCloudFrontの**現在のルーティングを保持して**認証を先に設定し、外部から401を確認してから専用3オブジェクトを配備する。権限が不足した場合、認証を省略した公開は行わない。

復帰は専用workflowを停止し、認証ガードを残したまま専用3オブジェクトをS3の前版へ戻すか削除する。認証を外して公開状態へ戻さない。資格情報を更新するときは専用SHA-256と本体ルーティング内の同じSHA-256を揃え、認証拒否・正しい認証のテストを再実行する。
