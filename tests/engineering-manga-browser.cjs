// Local static preview only. NODE_PATH must resolve the existing Playwright installation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require('playwright');
const base = process.env.MANGA_BASE_URL || 'http://127.0.0.1:8769';
assert.ok(['127.0.0.1', 'localhost'].includes(new URL(base).hostname));
const output = process.env.MANGA_EVIDENCE_DIR || '/tmp/simy-manga-minimal';
(async () => {
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ channel: 'chrome' });
  const errors = [];
  const geometry = [];
  try {
    const page = await browser.newPage({ reducedMotion: 'reduce' });
    page.on('pageerror', e => errors.push(e.message));
    page.on('requestfailed', r => errors.push(r.url()));
    page.on('response', r => { if (r.status() >= 400) errors.push(r.url()); });
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.goto(base + '/for/engineers/');
      assert.equal(await page.locator('[data-hero-demo], .manga-demo, .manga-entry').count(), 0);
      assert.equal(await page.locator('.manga-panel:visible').count(), 8);
      assert.equal(await page.locator('.manga-chapter').count(), 3);
      assert.equal(await page.locator('.manga-pains li').count(), 3);
      await page.locator('.manga-sources summary').focus();
      await page.keyboard.press('Enter');
      assert.equal(await page.locator('.manga-sources a:visible').count(), 3);
      await page.keyboard.press('Enter');
      assert.equal(await page.locator('.manga-sources a:visible').count(), 0);
      assert.equal(await page.locator('.experience-story:visible').count(), 0);
      await page.locator('.hero .secondary').click();
      assert.ok(page.url().endsWith('#manga'));
      const edges = await page.evaluate(() => {
        const rect = e => { const r = e.getBoundingClientRect(); return { left:r.left, right:r.right }; };
        return { width: innerWidth, overflow: document.documentElement.scrollWidth > innerWidth,
          panels: [...document.querySelectorAll('.manga-panels')].map(rect) };
      });
      assert.equal(edges.overflow, false);
      assert.ok(edges.panels.every(r => Math.abs(r.left - edges.panels[0].left) <= 1 && Math.abs(r.right - edges.panels[0].right) <= 1));
      geometry.push(edges);
      assert.equal(await page.locator('.mechanism-row').count(), 3);
      assert.ok(await page.evaluate(() => document.querySelector('#manga').compareDocumentPosition(document.querySelector('#mechanism')) & Node.DOCUMENT_POSITION_FOLLOWING));
      for (const img of await page.locator('.mechanism-image img').all()) {
        await img.scrollIntoViewIfNeeded();
        await img.evaluate(el => el.decode());
        assert.ok(await img.evaluate(el => el.naturalWidth === Number(el.getAttribute('width')) && el.naturalHeight === Number(el.getAttribute('height'))));
      }
      const imageEdges = await page.locator('.mechanism-image').evaluateAll(es => es.map(e => { const r = e.getBoundingClientRect(); return [r.left, r.right]; }));
      assert.ok(imageEdges.every(r => Math.abs(r[0]-imageEdges[0][0]) <= 1 && Math.abs(r[1]-imageEdges[0][1]) <= 1));
      await page.locator('#mechanism').screenshot({ path: output + '/mechanism-' + width + '.png', style: '.simy-header, .skip { visibility: hidden !important; }' });
      await page.locator('#manga').screenshot({ path: output + '/manga-' + width + '.png', style: '.simy-header, .skip { visibility: hidden !important; }' });
      await page.locator('.manga-more > summary').focus();
      await page.keyboard.press('Enter');
      assert.equal(await page.locator('.experience-story:visible').count(), 3);
      await page.locator('.manga-more > summary').press('Enter');
      assert.equal(await page.locator('.experience-story:visible').count(), 0);
      await page.locator('.manga-transcript summary').click();
      assert.equal(await page.locator('.manga-transcript li:visible').count(), 8);
    }
    for (const hash of ['#delivery', '#sqm', '#scene-build', '#scene-progress', '#scene-knowledge']) {
      await page.goto(base + '/for/engineers/' + hash);
      assert.equal(await page.locator('.experience-story:visible').count(), 3);
    }
    await page.close();
    const noJS = await browser.newPage({ javaScriptEnabled:false, viewport:{width:390,height:844} });
    await noJS.goto(base + '/for/engineers/');
    await noJS.locator('.manga-more > summary').click();
    assert.equal(await noJS.locator('.experience-story:visible').count(), 3);
    await noJS.close();
    assert.deepEqual(errors, []);
    fs.writeFileSync(output + '/report.json', JSON.stringify({geometry, errors, checks:['eight panels','no redundant demos','keyboard details','no-JS details','manga link']},null,2));
    console.log('PASS minimal manga: desktop/mobile, links, keyboard and no-JS; ' + output);
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode=1; });
