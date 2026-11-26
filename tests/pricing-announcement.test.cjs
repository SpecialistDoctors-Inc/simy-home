const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { test } = require('node:test');
const root = path.resolve(__dirname, '..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');

test('advance announcement is generated from all 23 approved public price rows', () => {
  const result = execFileSync('python3', ['scripts/build-pricing-announcement.py', '--check'], { cwd: root, encoding: 'utf8' });
  assert.match(result, /23 approved pricing rows/);
  const page = read('site/pricing-2026-11.html');
  for (const value of ['SIMY ロセンズ', '路線価評価', '¥14,800', '$99', '60件/月', '同時利用1人', '¥300', '$2', 'SIMY 開発支援', 'Delivery Loop', 'SQM', 'ChatGPTアカウント', 'Codex経由', '見直し中', '同時ヒアリング', '各利用者で個別管理', '契約開始日に合わせて毎月更新', '提供準備中']) {
    assert.ok(page.includes(value), `missing announcement condition: ${value}`);
  }
});

test('advance announcement states its status and cannot start signup or payment', () => {
  const page = read('site/pricing-2026-11.html');
  assert.match(page, /適用日未定・新料金での申込受付は開始していません/);
  assert.match(page, /現在の申込には現行料金が適用されます/);
  assert.match(page, /掲載金額は税別/);
  assert.doesNotMatch(page, /data-new-account-signup|<form\b|<input\b|<button\b|buy\.stripe\.com|checkout\.stripe\.com|\/signup/i);
  assert.doesNotMatch(page.match(/<main>[\s\S]*?<\/main>/)?.[0] ?? '', /app\.simy\.one/);
  assert.match(page, /data-existing-account-login/);
});

for (const locale of ['index', 'ja', 'es', 'fr', 'hi', 'zh-Hans']) {
  test(`${locale} homepage links to advance notice separately from current signup`, () => {
    const page = read(`site/${locale}.html`);
    const notice = page.match(/<aside class="pricing-announcement"[\s\S]*?<\/aside>/)?.[0];
    assert.ok(notice, 'missing advance notice');
    assert.match(notice, /href="\/pricing-2026-11\.html"/);
    assert.doesNotMatch(notice, /app\.simy\.one|stripe\.com|\/signup/);
    assert.match(page, /data-pricing-plan="starter"/);
    assert.match(page, /app\.simy\.one\/signup\//);
  });
}
