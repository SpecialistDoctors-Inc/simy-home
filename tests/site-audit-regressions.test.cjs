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
    if (!header) continue;
    checked++;
    const href = header.match(/href="([^"]+)">Guides<\/a>/)?.[1];
    assert.ok(href?.endsWith('/index.html'), `${file}: Guides must target a real S3 object`);
    assert.ok(fs.existsSync(path.join(site,href)), `${file}: Guides destination exists`);
    for (const target of ['/legal.html', '/seller-info.html']) assert.ok(header.includes(`href="${target}"`), `${file}: ${target} is reachable`);
    const android = header.match(/class="sh-store sh-google-play" href="([^"]+)"/)?.[1];
    assert.ok(android?.endsWith('#android'), `${file}: Android badge has an explained destination`);
    assert.ok(fs.readFileSync(path.join(site,android.split('#')[0]),'utf8').includes('id="android"'));
  }
  assert.equal(checked,145);
});

test('seller pricing describes tax separately and uses the verified name', () => {
  const seller = fs.readFileSync(path.join(site,'seller-info.html'),'utf8');
  assert.ok(seller.includes('塩飽 哲生'));
  assert.ok(seller.includes('プランの主表示価格は税抜'));
  assert.ok(seller.includes('購入確定前'));
  assert.ok(!seller.includes('該当する税金はすべて表示価格に含まれています'));
});
