const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const langs = ['ja', 'en', 'es', 'fr', 'hi', 'zh-hans'];
const corrections = require('../docs/seo/codex-plan-corrections.json');

for (const lang of langs) {
  const dir = path.join(root, 'site/guides', lang === 'ja' ? '' : lang);
  test(`${lang}: practical answers precede the marketing narrative in every guide`, () => {
    for (const file of fs.readdirSync(dir).filter(f => f.endsWith('.html') && f !== 'index.html')) {
      const html = fs.readFileSync(path.join(dir, file), 'utf8');
      const ids = [...html.matchAll(/<section class="sec" id="([^"]+)"/g)].map(m => m[1]);
      const expected = file === 'qwen-local.html' ? 'basics' : file === 'china-llm.html' ? 'compare' : 'reference';
      assert.equal(ids[0], expected, file);
      assert.ok(ids.indexOf('scene') > ids.indexOf(expected), file);
      const graph = JSON.parse(html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1])['@graph'];
      const article = graph.find(n => n['@type'] === 'Article');
      const modified = html.match(/<meta property="article:modified_time" content="([^"]+)"/)[1];
      const byline = html.match(/<p class="byline">[\s\S]*?<time datetime="([^"]+)"/)[1];
      assert.equal(modified, article.dateModified, file);
      assert.equal(byline, modified, file);
    }
  });
  test(`${lang}: Codex availability matches the checked official plan information`, () => {
    for (const topic of ['codex', 'chatgpt']) {
      const html = fs.readFileSync(path.join(dir, `${topic}.html`), 'utf8');
      const graph = JSON.parse(html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1])['@graph'];
      const faq = graph.find(n => n['@type'] === 'FAQPage');
      assert.ok(faq.mainEntity.some(q => q.acceptedAnswer.text === corrections.copy[lang][0]));
      const rows = html.match(/<tr><th scope="row">(?:Free|Go)[\s\S]*?<\/tr>/g);
      assert.ok(rows.length > 0);
      for (const row of rows) assert.match(row, /GPT-6 Luna/);
    }
  });
}

test('static pages do not mount a hidden React 404', () => {
  for (const name of ['careers', 'how-it-works', 'integrations', 'security', 'status']) {
    const html = fs.readFileSync(path.join(root, 'site', `${name}.html`), 'utf8');
    assert.doesNotMatch(html, /<script type="module"[^>]*src="\/assets\/index-/);
    assert.doesNotMatch(html, /id="root"/);
  }
});
