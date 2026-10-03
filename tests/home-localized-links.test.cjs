const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../site/home-i18n.js'), 'utf8');
const start = source.indexOf('  function updateLinks(locale) {');
const end = source.indexOf('  function updateUrl(locale)', start);
assert.ok(start >= 0 && end > start);

for (const locale of ['en', 'ja', 'hi', 'es', 'fr', 'zh-Hans']) {
  test(`${locale}: runtime guide/download links preserve locale, attribution and anchor`, () => {
    const code = locale === 'zh-Hans' ? 'zh-hans' : locale;
    const guide = locale === 'ja' ? '/guides/notta.html' : `/guides/${code}/notta.html`;
    const download = locale === 'ja' ? '/download.html' : `/download/${code}.html`;
    const inputs = ['/guides/notta.html', '/guides/en/notta.html', '/guides/fr/notta.html', '/download.html', '/download/en.html', '/download/fr.html'];
    const suffix = '?utm_source=seo%20check&tag=one&tag=two#next';
    const links = inputs.map(href => ({
      dataset: {}, href: href + suffix,
      getAttribute(name) { assert.equal(name, 'href'); return this.href; },
      setAttribute(name, value) { assert.equal(name, 'href'); this.href = value; }
    }));
    const context = { URL, window: { location: { href: 'https://simy.one/', origin: 'https://simy.one' } },
      document: { querySelectorAll(selector) { assert.equal(selector, 'a[href]'); return links; } } };
    vm.runInNewContext(source.slice(start, end), context);
    context.updateLinks(locale);
    links.forEach((link, i) => assert.equal(link.href, (i < 3 ? guide : download) + suffix));
    context.updateLinks(locale);
    links.forEach((link, i) => assert.equal(link.href, (i < 3 ? guide : download) + suffix));
  });
}
