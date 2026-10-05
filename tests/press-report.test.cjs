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
    assert.match(content, /src="\/news\/press-gallery.js" defer/);
    for (let i = 1; i <= 30; i++) {
      const n = String(i).padStart(2, '0');
      for (const size of ['', '-800']) {
        const asset = `assets/press/ai-mentor-20261005${suffix}/slide-${n}${size}.webp`;
        assert.ok(content.includes(asset), `missing image reference ${asset}`);
        assert.ok(fs.statSync(path.join(site, asset)).size > 1000, `missing image ${asset}`);
      }
    }
    if (language === 'en') assert.match(content, /money worries remained<\/h3>/);
  });
}
