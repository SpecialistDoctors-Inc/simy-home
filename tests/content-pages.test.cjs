const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const pages = require('../scripts/content-pages.json').pages;
const read = url => fs.readFileSync(path.join(root, 'site', url + (url.endsWith('/') ? 'index.html' : '')), 'utf8');

test('occupation and workflow pages are reproducible from their reviewed copy', () => {
  execFileSync('python3', ['scripts/build-content-pages.py', '--check'], { cwd: root });
});

test('every declared locale has an indexable reciprocal destination and a reachable entry', () => {
  const urls = new Set();
  for (const page of pages) {
    assert.deepEqual(Object.keys(page.paths).sort(), ['en', 'ja']);
    for (const [lang, url] of Object.entries(page.paths)) {
      assert.ok(!urls.has(url), `duplicate URL ${url}`);
      urls.add(url);
      const html = read(url);
      assert.match(html, new RegExp(`<html lang="${lang}">`));
      assert.ok(html.includes(`<link rel="canonical" href="https://simy.one${url}">`));
      const prefix = lang === 'ja' ? '/guides/' : '/guides/en/';
      const entry = page.kind === 'guide' ? read(prefix + 'index.html')
        : page.kind === 'role' ? read(lang === 'ja' ? '/for/' : '/for/en/')
          : read(lang === 'ja' ? '/ja.html' : '/index.html');
      assert.ok(entry.includes(`href="${url}"`), `missing entry to ${url}`);
      for (const [targetLang, target] of Object.entries(page.paths)) {
        assert.ok(html.includes(`hreflang="${targetLang}" href="https://simy.one${target}"`));
        assert.match(read(target), new RegExp(`<html lang="${targetLang}">`));
      }
    }
  }
});

test('legacy guide topics keep all six translations', () => {
  for (const topic of ['claude', 'codex', 'cowork', 'chatgpt', 'plaud', 'notta', 'meeting-notes', 'china-llm', 'deepseek', 'qwen', 'qwen-local', 'kimi', 'glm', 'minimax', 'doubao']) {
    for (const lang of ['en', 'es', 'fr', 'hi', 'zh-hans']) assert.ok(read(`/guides/${lang}/${topic}.html`));
  }
});

test('role URLs stay separate from instructional guide URLs', () => {
  for (const p of pages) {
    for (const url of Object.values(p.paths)) {
      if (p.kind === 'guide') assert.match(url, /^\/guides\/(?:en\/)?[a-z-]+\.html$/);
      else assert.match(url, /^\/for\/(?:en\/)?(?:[a-z-]+\/)?$/);
    }
  }
});
