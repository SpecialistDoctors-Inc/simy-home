const fs = require('fs');
const path = require('path');

const env = process.env.ENV || 'dev';
const sourcePath = path.join(__dirname, '..', 'aasa', `${env}.json`);
const destDir = path.join(__dirname, '..', 'public', '.well-known');
const destPath = path.join(destDir, 'apple-app-site-association.json');

// ディレクトリがなければ作成
if (!fs.existsSync(destDir)) {
  fs.mkdirSync(destDir, { recursive: true });
}

// ファイルをコピー
fs.copyFileSync(sourcePath, destPath);

console.log(`Copied AASA file for ${env} environment`);