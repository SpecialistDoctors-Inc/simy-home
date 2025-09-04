#!/bin/bash

# バケット名を引数から取得
if [ -z "$1" ]; then
    echo "使用方法: ./deploy.sh <bucket-name>"
    echo "例: ./deploy.sh ai-mentor-website-123456789"
    exit 1
fi

BUCKET_NAME=$1

echo "ファイルをS3にアップロード中..."

# HTMLファイルをアップロード
aws s3 cp index.html s3://$BUCKET_NAME/index.html --content-type "text/html; charset=utf-8"
aws s3 cp privacy.html s3://$BUCKET_NAME/privacy.html --content-type "text/html; charset=utf-8"
aws s3 cp terms.html s3://$BUCKET_NAME/terms.html --content-type "text/html; charset=utf-8"
aws s3 cp seller-info.html s3://$BUCKET_NAME/seller-info.html --content-type "text/html; charset=utf-8"
aws s3 cp error.html s3://$BUCKET_NAME/error.html --content-type "text/html; charset=utf-8"

# CSSファイルをアップロード
aws s3 cp styles.1.css s3://$BUCKET_NAME/styles.1.css --content-type "text/css"

# jsファイルをアップロード
aws s3 cp carousel.js s3://$BUCKET_NAME/carousel.js --content-type "application/javascript"
aws s3 cp header-animation.js s3://$BUCKET_NAME/header-animation.js --content-type "application/javascript"

# 画像ファイルをアップロード
aws s3 cp img/ s3://$BUCKET_NAME/img/ --recursive --content-type "image/png"

# app-ads.txtをアップロード
aws s3 cp app-ads.txt s3://$BUCKET_NAME/app-ads.txt

echo "アップロード完了！"
echo "ウェブサイトを確認してください："
echo "http://$BUCKET_NAME.s3-website-ap-northeast-1.amazonaws.com"