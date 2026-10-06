const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const site = path.join(__dirname, '../site');
const locales = ['en', 'ja', 'hi', 'es', 'fr', 'zh-Hans'];
const context = {window:{}};
vm.runInNewContext(fs.readFileSync(path.join(site, 'lang/i18n-bundle.js'), 'utf8'), context);
for (const locale of locales) {
  const dictionary = JSON.parse(fs.readFileSync(path.join(site, `lang/${locale}.json`)));
  test(`${locale}: every public runtime translation has copy and offline fallback`, () => {
    for (const file of fs.readdirSync(site).filter(f => f.endsWith('.html'))) {
      const source = fs.readFileSync(path.join(site,file),'utf8');
      if (!source.includes('src="i18n.js?')) continue;
      for (const match of source.matchAll(/data-i18n(?:-html|-placeholder)?="([^"]+)"/g)) {
        const key = match[1];
        assert.equal(typeof dictionary[key], 'string', `${file}: ${key}`);
        assert.ok(dictionary[key].trim(), `${file}: empty ${key}`);
        assert.equal(context.window.SIMY_I18N_BUNDLE[locale][key], dictionary[key], `${file}: stale offline ${key}`);
      }
    }
  });
}
