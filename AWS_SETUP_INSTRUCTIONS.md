# AWS S3 静的ウェブサイトホスティング セットアップ手順

## 前提条件
- AWS CLIがインストールされていること
- AWS CLIが設定されていること（`aws configure`実行済み）
- 適切なIAMユーザー権限があること

## セットアップ手順

### 1. スクリプトに実行権限を付与
```bash
chmod +x setup-s3-website.sh
chmod +x deploy.sh
```

### 2. バケットポリシーファイルを更新
`bucket-policy.json`ファイルを開き、`BUCKET_NAME`を実際のバケット名に置き換える必要があります。
これは手順3の後に行います。

### 3. S3バケットを作成して設定
```bash
./setup-s3-website.sh
```

このスクリプトは：
- 一意のS3バケットを作成
- 静的ウェブサイトホスティングを有効化
- パブリックアクセスを許可
- バケット名とウェブサイトURLを表示

**重要**: 表示されたバケット名をメモしてください。

### 4. バケットポリシーを更新
1. `bucket-policy.json`を開く
2. `BUCKET_NAME`を手順3で表示された実際のバケット名に置き換える
3. ファイルを保存

### 5. バケットポリシーを適用
```bash
aws s3api put-bucket-policy --bucket <your-bucket-name> --policy file://bucket-policy.json
```

### 6. ウェブサイトファイルをデプロイ
```bash
./deploy.sh <your-bucket-name>
```

## ウェブサイトへのアクセス

デプロイ完了後、以下のURLでアクセスできます：
```
http://<your-bucket-name>.s3-website-ap-northeast-1.amazonaws.com
```

## Google APIでの使用

Google APIの設定で以下のURLを使用してください：

- **Application privacy policy link**: 
  `http://<your-bucket-name>.s3-website-ap-northeast-1.amazonaws.com/privacy.html`
  
- **Application terms of service link**: 
  `http://<your-bucket-name>.s3-website-ap-northeast-1.amazonaws.com/terms.html`

## 更新方法

ファイルを更新した場合は、再度デプロイスクリプトを実行：
```bash
./deploy.sh <your-bucket-name>
```

## カスタムドメインの設定（オプション）

独自ドメインを使用したい場合：
1. Route 53でドメインを管理
2. CloudFrontディストリビューションを作成
3. SSL証明書を設定（ACM使用）

## トラブルシューティング

### アクセスが拒否される場合
- バケットポリシーが正しく設定されているか確認
- パブリックアクセスブロックが無効になっているか確認

### ページが表示されない場合
- ファイルが正しくアップロードされているか確認
- ウェブサイトホスティングが有効になっているか確認

## コスト

S3の静的ウェブサイトホスティングのコスト：
- ストレージ: 約$0.025/GB/月
- データ転送: 最初の1GBは無料、その後約$0.114/GB
- リクエスト: GET要求は$0.0004/1000リクエスト

通常の使用では月額$1未満で運用可能です。