const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
for (const locale of ['en', 'ja', 'es', 'fr', 'hi', 'zh-Hans']) {
  test(`${locale}: manga demo preserves machine states across all three stories`, () => {
    const context = { scenarios: {}, renderScenario() {}, document: {
      querySelector() { return { textContent: '' }; },
      querySelectorAll() { return []; }
    }};
    vm.runInNewContext(fs.readFileSync(path.join(root, 'site', `home-manga-${locale}.js`), 'utf8'), context);
    assert.deepEqual(Object.keys(context.scenarios), ['codex', 'claude', 'cowork']);
    for (const story of Object.values(context.scenarios)) {
      assert.deepEqual(Array.from(story.steps, step => step[1]), ['Done', 'Done', 'Waiting', 'Next']);
      for (const key of ['source', 'prompt', 'acknowledgement', 'workflow', 'output']) {
        assert.ok(story[key].trim());
        if (locale !== 'ja' && locale !== 'zh-Hans') assert.doesNotMatch(story[key], /[ぁ-んァ-ン]/);
      }
    }
  });
  test(`${locale}: original homepage serves six matching localized manga assets`, () => {
    const file = locale === 'en' ? 'index.html' : locale + '.html';
    const source = fs.readFileSync(path.join(root, 'site', file), 'utf8');
    const scenes = [...source.matchAll(/<figure[^>]*data-story-scene="([^"]+)"[^>]*>[\s\S]*?<img[^>]*src="([^"]+)"/g)];
    assert.equal(scenes.length, 6);
    for (const [, scene, asset] of scenes) {
      assert.ok(asset.startsWith('/assets/home-manga-preview/'));
      if (locale !== 'ja') assert.ok(asset.endsWith(`-${locale}.webp`), `${scene}: wrong image language`);
      assert.ok(fs.existsSync(path.join(root, 'site', asset)), `${scene}: image missing`);
    }
    assert.match(source, new RegExp(`/home-manga-${locale}\\.js`));
    assert.doesNotMatch(source, /href="[^\"]*home-manga-preview\.html/);
  });
}
