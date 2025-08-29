#!/bin/bash

# S3バケット名（一意である必要があります）
BUCKET_NAME="ai-mentor-website-$(date +%s)"
REGION="ap-northeast-1"  # 東京リージョン

echo "S3バケットを作成中: $BUCKET_NAME"

# S3バケットを作成
aws s3 mb s3://$BUCKET_NAME --region $REGION

# パブリックアクセスブロックを無効化（最初に実行）
echo "パブリックアクセスブロックを無効化中..."
aws s3api put-public-access-block \
    --bucket $BUCKET_NAME \
    --public-access-block-configuration "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

# 少し待機（設定が反映されるまで）
sleep 2

# 静的ウェブサイトホスティングを有効化
echo "静的ウェブサイトホスティングを有効化中..."
aws s3 website s3://$BUCKET_NAME \
    --index-document index.html \
    --error-document error.html

# バケットポリシーを作成して適用
echo "バケットポリシーを設定中..."
cat > /tmp/bucket-policy-$$.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
        }
    ]
}
EOF

aws s3api put-bucket-policy \
    --bucket $BUCKET_NAME \
    --policy file:///tmp/bucket-policy-$$.json

# クリーンアップ
rm -f /tmp/bucket-policy-$$.json

echo ""
echo "設定完了！"
echo "バケット名: $BUCKET_NAME"
echo "ウェブサイトURL: http://$BUCKET_NAME.s3-website-$REGION.amazonaws.com"
echo ""
echo "次のステップ："
echo "1. ./deploy.sh $BUCKET_NAME を実行してファイルをアップロード"
echo "2. 数分待ってからウェブサイトにアクセス"