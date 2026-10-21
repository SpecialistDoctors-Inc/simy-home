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
    assert.equal((source.match(/class="panel"/g) || []).length, 8);
    assert.equal((source.match(/class="screen"/g) || []).length, 4);
    const main = source.match(/<main[\s\S]*?<\/main>/)[0];
    if (!['ja', 'zh-Hans'].includes(locale)) assert.ok(!/[\u3040-\u30ff\u4e00-\u9fff]/.test(main));
    assert.ok(main.includes(`/contact.html?lang=${locale}`));
  });
}
