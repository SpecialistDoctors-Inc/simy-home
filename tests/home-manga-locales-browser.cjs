// Run against the generated local site or deployed production site.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.HOME_MANGA_BASE || 'http://127.0.0.1:8771';
const out = process.env.HOME_MANGA_EVIDENCE || '/tmp/home-manga-locales-evidence';
fs.mkdirSync(out, { recursive: true });
(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  const page = await browser.newPage({ reducedMotion: 'reduce' });
  await page.addInitScript(() => localStorage.setItem('simy-cookies', '0'));
  const errors = [], reports = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => { if (response.status() >= 400 && response.url().startsWith(base)) errors.push(response.status() + ' ' + response.url()); });
  try {
    for (const locale of ['en', 'ja', 'es', 'fr', 'hi', 'zh-Hans']) {
      for (const width of [1440, 1024, 768, 720, 390, 320]) {
        await page.setViewportSize({ width, height: 1000 });
        await page.goto(base + (locale === 'en' ? '/' : '/' + locale + '.html'));
        assert.equal(await page.locator('html').getAttribute('lang'), locale);
        for (const img of await page.locator('[data-story-scene] img').all()) {
          await img.scrollIntoViewIfNeeded();
          await img.evaluate(async img => { try { await img.decode(); } catch (error) { throw new Error(img.src + ": " + error.message); } });
        }
        assert.equal(await page.locator('[data-story-scene] img').count(), 6);
        for (const story of ['codex', 'claude', 'cowork']) {
          await page.locator(`[data-scenario="${story}"]`).click();
          assert.deepEqual(await page.locator('[data-step-status]').evaluateAll(nodes => nodes.map(node => node.dataset.status)), ['done', 'done', 'waiting', 'next']);
          const text = await page.locator('#demo-panel').innerText();
          if (!['ja', 'zh-Hans'].includes(locale)) assert.doesNotMatch(text, /[ぁ-んァ-ン]/);
          assert.equal(await page.locator(`[data-scenario="${story}"]`).getAttribute('aria-selected'), 'true');
        }
        await page.locator('[data-scenario="cowork"]').press('ArrowLeft');
        assert.equal(await page.locator('[data-scenario="claude"]').getAttribute('aria-selected'), 'true');
        await page.locator('[data-billing-cycle="monthly"]').click();
        const signup = await page.locator('[data-pricing-plan="starter"] .pricing-plan-link').getAttribute('href');
        assert.equal(new URL(signup).searchParams.get('interval'), 'monthly');
        assert.equal(new URL(signup).searchParams.get('lang'), locale);
        await page.locator('[data-billing-cycle="annual"]').click();
        await page.locator('.home-more-features>summary').click();
        await page.locator('.apps-more>summary').click();
        const geometry = await page.evaluate(() => ({
          overflow: document.documentElement.scrollWidth > innerWidth,
          clippedHeadings: [...document.querySelectorAll('main h1, main h2, main h3')].filter(e => e.clientWidth && e.scrollWidth > e.clientWidth + 2).map(e => e.textContent),
          appHeights: [...document.querySelectorAll('.connected-apps .apps-grid:not(.apps-grid-ai) .app-tile')].map(e => e.getBoundingClientRect().height),
          sceneLanguages: [...document.querySelectorAll('[data-story-scene] img')].map(e => e.getAttribute('src'))
        }));
        assert.equal(geometry.overflow, false, locale + ':' + width + ' overflow');
        assert.deepEqual(geometry.clippedHeadings, [], locale + ':' + width + ' clipped heading');
        assert.ok(geometry.appHeights.length >= 8, locale + ": app tiles measured");
        assert.ok(geometry.appHeights.every(h => h < 150), locale + ':' + width + ' oversized app cell');
        reports.push({ locale, width, ...geometry });
        if ([1440, 390].includes(width)) {
          await page.locator('#top').scrollIntoViewIfNeeded();
          await page.screenshot({ path: out + '/' + locale + '-' + width + '-hero.png' });
          await page.locator('#how-it-works').scrollIntoViewIfNeeded();
          await page.screenshot({ path: out + '/' + locale + '-' + width + '-features.png' });
          await page.locator('#connected-apps').scrollIntoViewIfNeeded();
          await page.screenshot({ path: out + '/' + locale + '-' + width + '-apps.png' });
        }
      }
    }
    assert.deepEqual(errors, []);
    fs.writeFileSync(out + '/report.json', JSON.stringify({ reports, errors }, null, 2));
    console.log('Verified 6 languages × 6 viewport widths, 3 demo tabs, keyboard navigation, pricing, disclosures and 36 manga images.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
