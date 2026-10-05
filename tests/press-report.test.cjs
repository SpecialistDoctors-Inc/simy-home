const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const site = path.join(__dirname, '..', 'site');
for (const language of ['ja', 'en']) {
  test(`${language} report has 30 complete slides and bilingual discovery`, () => {
    const suffix = language === 'en' ? '-en' : '';
    const content = fs.readFileSync(path.join(site, `news/20261005${suffix}.html`), 'utf8');
    assert.equal((content.match(/<figure id="slide-/g) || []).length, 30);
    assert.equal((content.match(/class="slide-text"/g) || []).length, 30);
    assert.match(content, /hreflang="ja"/);
    assert.match(content, /hreflang="en"/);
    assert.match(content, /src="\/news\/press-gallery.js\?v=20261005-r2" defer/);
    for (let i = 1; i <= 30; i++) {
      const n = String(i).padStart(2, '0');
      for (const size of ['', '-800']) {
        const asset = `assets/press/ai-mentor-20261005${suffix}/slide-${n}${size}.webp`;
        assert.ok(content.includes(asset), `missing image reference ${asset}`);
        assert.ok(fs.statSync(path.join(site, asset)).size > 1000, `missing image ${asset}`);
      }
    }
    if (language === 'en') assert.match(content, /Fewer selected anxiety or ability concerns after consultation<\/h3>/);
  });
}

test('news index localizes the latest announcement instead of embedding Japanese copy', () => {
  const content = fs.readFileSync(path.join(site,'press-release.html'),'utf8');
  assert.match(content, /id="latestRelease" lang="en"/);
  assert.doesNotMatch(content, /<section class="article" lang="ja"/);
  const keys=['category','title','summary','read','other'].map(key=>'newpress.latest.'+key);
  const bundle=JSON.parse(fs.readFileSync(path.join(site,'lang/i18n-bundle.js'),'utf8').replace(/^window\.SIMY_I18N_BUNDLE\s*=\s*/,'').replace(/;\s*$/,''));
  for(const locale of ['en','ja','es','fr','hi','zh-Hans']) {
    const dict=JSON.parse(fs.readFileSync(path.join(site,`lang/${locale}.json`),'utf8'));
    for(const key of keys){assert.ok(dict[key]);assert.equal(bundle[locale][key],dict[key]);assert.ok(content.includes(`data-i18n="${key}"`));}
  }
  const en=JSON.parse(fs.readFileSync(path.join(site,'lang/en.json'),'utf8'));
  assert.match(en['newpress.latest.title'],/Four in five/);
  assert.match(en['newpress.latest.summary'],/52 of 65/);
});
