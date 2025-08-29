#!/bin/bash

# バケット名を引数から取得
if [ -z "$1" ]; then
    echo "使用方法: ./fix-s3-access.sh <bucket-name>"
    echo "例: ./fix-s3-access.sh ai-mentor-website-123456789"
    exit 1
fi

BUCKET_NAME=$1
REGION="ap-northeast-1"

echo "S3バケットのアクセス設定を修正中..."

# 1. パブリックアクセスブロックを完全に無効化
echo "パブリックアクセスブロックを無効化中..."
aws s3api put-public-access-block \
    --bucket $BUCKET_NAME \
    --public-access-block-configuration "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

# 2. バケットポリシーを更新
echo "バケットポリシーを更新中..."
cat > /tmp/bucket-policy.json << EOF
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

aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy file:///tmp/bucket-policy.json

# 3. 静的ウェブサイトホスティングを再設定
echo "静的ウェブサイトホスティングを設定中..."
aws s3 website s3://$BUCKET_NAME \
    --index-document index.html \
    --error-document error.html

# 4. オブジェクトの所有権を設定（オプション）
echo "オブジェクト所有権を設定中..."
aws s3api put-bucket-ownership-controls \
    --bucket $BUCKET_NAME \
    --ownership-controls="Rules=[{ObjectOwnership=BucketOwnerPreferred}]" 2>/dev/null || true

echo ""
echo "設定完了！"
echo "ウェブサイトURL: http://$BUCKET_NAME.s3-website-$REGION.amazonaws.com"
echo ""
echo "もし問題が続く場合は、AWSコンソールで以下を確認してください："
echo "1. S3 > バケット > $BUCKET_NAME > アクセス許可"
echo "2. 「パブリックアクセスをすべてブロック」がオフになっているか"
echo "3. バケットポリシーが正しく設定されているか"

# クリーンアップ
rm -f /tmp/bucket-policy.json