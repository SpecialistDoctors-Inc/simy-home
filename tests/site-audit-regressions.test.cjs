const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const site = path.join(__dirname, '../site');
const files = fs.readdirSync(site, {recursive:true}).filter(file => file.endsWith('.html'));

test('every shared header exposes deployable guide and legal destinations', () => {
  let checked = 0;
  for (const file of files) {
    const source = fs.readFileSync(path.join(site,file),'utf8');
    const header = source.match(/<header class="simy-header"[\s\S]*?<\/header>/)?.[0];
    const excluded = file === 'auth-callback.html' || !/<body\b/i.test(source) || /http-equiv=["']refresh/i.test(source);
    if (excluded) continue;
    assert.ok(header, `${file}: every rendered public page needs the shared header`);
    assert.equal((source.match(/<header class="simy-header"/g) || []).length, 1, `${file}: one shared header`);
    checked++;
    const href = header.match(/href="([^"]+)">Guides<\/a>/)?.[1];
    assert.ok(href?.endsWith('/index.html'), `${file}: Guides must target a real S3 object`);
    assert.ok(fs.existsSync(path.join(site,href)), `${file}: Guides destination exists`);
    for (const target of ['/legal.html', '/seller-info.html']) assert.ok(header.includes(`href="${target}"`), `${file}: ${target} is reachable`);
    const android = header.match(/class="sh-store sh-google-play" href="([^"]+)"/)?.[1];
    assert.ok(android?.endsWith('#android'), `${file}: Android badge has an explained destination`);
    assert.ok(fs.readFileSync(path.join(site,android.split('#')[0]),'utf8').includes('id="android"'));
  }
  assert.equal(checked,171);
});

test('seller pricing describes tax separately and uses the verified name', () => {
  const seller = fs.readFileSync(path.join(site,'seller-info.html'),'utf8');
  assert.ok(seller.includes('塩飽 哲生'));
  assert.ok(seller.includes('プランの主表示価格は税抜'));
  assert.ok(seller.includes('購入確定前'));
  assert.ok(!seller.includes('該当する税金はすべて表示価格に含まれています'));
});

test('shared header regeneration is clean and preserves authentication callback', () => {
  const {execFileSync} = require('node:child_process');
  execFileSync('python3', ['scripts/site_header.py', '--check'], {cwd:path.join(__dirname, '..')});
  const callback = fs.readFileSync(path.join(site, 'auth-callback.html'), 'utf8');
  assert.ok(!callback.includes('site-header.js'));
});

test('nested legacy pages retain their same-page language alternatives', () => {
  const source = fs.readFileSync(path.join(site, 'old/compare/index.html'), 'utf8');
  for (const locale of ['en','ja','hi','es','fr','zh-Hans']) {
    assert.ok(source.includes(`href="/old/compare/index.html?lang=${locale}" lang="${locale}"`));
  }
});
