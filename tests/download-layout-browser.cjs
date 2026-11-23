// Run with the existing Playwright installation; one browser, sequential cases.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const base = process.env.BASE_URL || 'http://127.0.0.1:8770';
  const output = process.env.OUTPUT_DIR;
  if (output) fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch();
  const results = [];
  try {
    const page = await browser.newPage({ reducedMotion: 'reduce' });
    await page.addInitScript(() => localStorage.setItem('simy-cookies', '0'));
    await page.route('**/*', route => new URL(route.request().url()).origin === new URL(base).origin ? route.continue() : route.abort());
    for (const locale of ['ja', 'en', 'es', 'fr', 'hi', 'zh-hans']) {
      for (const width of [1440, 1100, 861, 860, 390, 320]) {
        await page.setViewportSize({ width, height: 1000 });
        await page.goto(base + (locale === 'ja' ? '/download.html' : `/download/${locale}.html`), { waitUntil: 'networkidle' });
        const geometry = await page.evaluate(() => {
          const rect = selector => document.querySelector(selector).getBoundingClientRect().toJSON();
          return {
            wrap: rect('.dl-main > .wrap'), header: rect('.simy-header'), heading: rect('h1'),
            funnel: rect('.funnel'), cards: [...document.querySelectorAll('.paths > .path')].map(el => el.getBoundingClientRect().toJSON()),
            overflow: document.documentElement.scrollWidth - innerWidth,
            clippedButtons: [...document.querySelectorAll('.path .btn')].filter(el => el.scrollWidth > el.clientWidth + 1).length,
            downloads: document.querySelectorAll('.path [data-os]').length,
            platforms: [...document.querySelectorAll('.path [data-os]')].map(el => ({
              card: el.getBoundingClientRect().toJSON(),
              button: el.querySelector('.btn').getBoundingClientRect().toJSON(),
            })),
          };
        });
        const context = `${locale}/${width}`;
        assert.ok(geometry.heading.top >= geometry.header.bottom, `${context}: heading under navigation`);
        assert.ok(Math.abs(geometry.wrap.left - (width - geometry.wrap.right)) <= 1, `${context}: content off center`);
        assert.ok(Math.abs(geometry.funnel.left - geometry.wrap.left) <= 1, `${context}: funnel left edge`);
        assert.ok(Math.abs(geometry.funnel.right - geometry.wrap.right) <= 1, `${context}: funnel right edge`);
        assert.ok(geometry.overflow <= 1, `${context}: page overflow`);
        assert.equal(geometry.clippedButtons, 0, `${context}: button text clipped`);
        assert.equal(geometry.downloads, 3, `${context}: missing platform card`);
        const [left, right] = geometry.cards;
        assert.ok(right.top >= left.bottom, `${context}: account/download sections overlap`);
        assert.ok(Math.abs(left.left - right.left) <= 1 && Math.abs(left.right - right.right) <= 1, `${context}: section edges`);
        if (width > 860) {
          for (const platform of geometry.platforms) {
            for (const key of ['width', 'top', 'bottom']) assert.ok(Math.abs(platform.card[key] - geometry.platforms[0].card[key]) <= 1, `${context}: unequal platform ${key}`);
            for (const key of ['top', 'bottom']) assert.ok(Math.abs(platform.button[key] - geometry.platforms[0].button[key]) <= 1, `${context}: unequal action ${key}`);
          }
        }
        results.push({ locale, width, ...geometry });
        if (output && locale === 'ja' && [1440, 390].includes(width)) {
          await page.screenshot({ path: `${output}/download-${width}.png`, fullPage: true });
          await page.locator('.paths').screenshot({ path: `${output}/cards-${width}.png` });
        }
      }
    }
    if (output) fs.writeFileSync(`${output}/report.json`, JSON.stringify(results, null, 2));
    console.log(`PASS ${results.length} download locale/width cases`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
