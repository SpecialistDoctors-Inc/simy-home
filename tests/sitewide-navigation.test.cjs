const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../site/i18n.js'), 'utf8');
function fn(name, next, context) {
  const start = source.indexOf(`  function ${name}(`);
  const end = source.indexOf(`  function ${next}(`, start);
  assert.ok(start >= 0 && end > start);
  vm.runInNewContext(source.slice(start, end), context);
  return context[name];
}
for (const lang of ['en','ja','hi','es','fr','zh-Hans']) {
  test(`${lang}: static language URLs survive legacy navigation decoration`, () => {
    const context = {URL, location: {href:'https://simy.one/about.html',hostname:'simy.one'}, CURRENT_LANG:lang,
      document:{documentElement:{lang}}, isLegalPath:()=>false, currentRegionForApp:()=> 'JP'};
    const decorate = fn('decorateSiteUrl','decorateAppLinks',context);
    for (const href of ['/fr.html?utm_source=guide#pricing','/guides/fr/notta.html','/download/en.html','/download.html']) {
      assert.equal(decorate(href), href);
    }
    const home = lang === 'en' ? '/' : `/${lang}.html`;
    assert.equal(decorate('/?utm_source=guide#pricing'), `${home}?utm_source=guide#pricing`);
    assert.equal(decorate('/?lang=ja&locale=ja&tag=one&tag=two#pricing'), '/ja.html?tag=one&tag=two#pricing');
    assert.equal(decorate('https://other.example/guides/en/x.html'), 'https://other.example/guides/en/x.html');
    assert.equal(decorate('#pricing'), '#pricing');
  });
}
test('reviewed server HTML metadata is not overwritten by obsolete client SEO', () => {
  const context = {document:{documentElement:{hasAttribute:n=>n==='data-reviewed-seo'}}};
  fn('applySEO','applyDictionarySEO',context)('ja');
  const start = source.indexOf('  function applyDictionarySEO(');
  const end = source.indexOf('\n  /*', start);
  vm.runInNewContext(source.slice(start,end),context);
  context.applyDictionarySEO({'home.h1':'stale'},'ja');
});

test('repeated locale changes recompute home links and preserve explicit alternatives', () => {
  const makeLink = href => ({attrs:{href}, getAttribute(k){return this.attrs[k] || null;}, setAttribute(k,v){this.attrs[k]=v;}});
  const links = [makeLink('/?utm_source=footer#pricing'),makeLink('/fr.html#pricing')];
  const context = {URL, location:{href:'https://simy.one/about.html',hostname:'simy.one'}, CURRENT_LANG:'fr',
    document:{documentElement:{lang:'en'},querySelectorAll:()=>links},isLegalPath:()=>false,currentRegionForApp:()=> 'FR'};
  fn('decorateSiteUrl','decorateAppLinks',context);
  const decorate = fn('decorateAppLinks','syncRegionToCurrentLanguage',context);
  decorate();
  assert.equal(links[0].attrs.href,'/fr.html?utm_source=footer#pricing');
  context.CURRENT_LANG='ja';
  decorate();
  assert.equal(links[0].attrs.href,'/ja.html?utm_source=footer#pricing');
  assert.equal(links[1].attrs.href,'/fr.html#pricing');
  links[0].attrs.href='/contact.html';
  decorate();
  assert.equal(links[0].attrs.href,'/contact.html?lang=ja&locale=ja&region=FR');
});
