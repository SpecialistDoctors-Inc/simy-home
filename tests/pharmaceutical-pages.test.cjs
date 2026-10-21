const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const locales = ['ja', 'en', 'es', 'fr', 'hi', 'zh-Hans'];
const route = locale => `/for/${locale === 'ja' ? '' : locale.toLowerCase() + '/'}pharmaceutical-companies/`;

test('all pharma locales are reproducible from the maintained sources', () => {
  execFileSync('python3', ['scripts/build-pharmaceutical-pages.py', '--check'], {cwd:root});
});
for (const locale of locales) {
  test(`${locale}: pharma language navigation preserves the same solution`, () => {
    const source = fs.readFileSync(path.join(root, 'site', route(locale), 'index.html'), 'utf8');
    assert.ok(source.includes(`<html lang="${locale}"`));
    assert.ok(source.includes(`rel="canonical" href="https://simy.one${route(locale)}"`));
    const header = source.match(/<header class="simy-header"[\s\S]*?<\/header>/)[0];
    for (const language of locales) {
      assert.ok(source.includes(`hreflang="${language}" href="https://simy.one${route(language)}"`));
      assert.ok(header.includes(`href="${route(language)}" lang="${language}"`));
    }
    const socialImage = `/assets/pharmaceutical-companies/social/next-meeting-${locale}-v1.png`;
    assert.ok(source.includes(`property="og:image" content="https://simy.one${socialImage}"`));
    assert.ok(source.includes(`name="twitter:image" content="https://simy.one${socialImage}"`));
    assert.ok(source.includes('property="og:image:width" content="1200"'));
    assert.ok(source.includes('property="og:image:height" content="630"'));
    assert.ok(source.includes('property="og:image:type" content="image/png"'));
    assert.ok(source.includes('property="og:image:alt" content="'));
    assert.ok(source.includes('name="twitter:image:alt" content="'));
    const png = fs.readFileSync(path.join(root, 'site', socialImage));
    assert.equal(png.subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
    assert.equal(png.readUInt32BE(16), 1200);
    assert.equal(png.readUInt32BE(20), 630);
    assert.equal((source.match(/class="panel"/g) || []).length, 8);
    assert.equal((source.match(/class="screen"/g) || []).length, 4);
    const main = source.match(/<main[\s\S]*?<\/main>/)[0];
    if (!['ja', 'zh-Hans'].includes(locale)) assert.ok(!/[\u3040-\u30ff\u4e00-\u9fff]/.test(main));
    assert.ok(main.includes(`/contact.html?lang=${locale}`));
  });
}
