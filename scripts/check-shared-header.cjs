// Run against a local preview with Playwright available through NODE_PATH.
// SITE_URL defaults to http://localhost:8766; no external account actions are sent.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const base = process.env.SITE_URL || 'http://localhost:8766';
    for (const width of [1440, 1251, 1250, 960, 720, 390, 320]) {
      await page.setViewportSize({ width, height: 900 });
      for (const path of ['/', '/about.html', '/guides/plaud.html', '/legal.html', '/for/en/engineers/', '/download.html']) {
        await page.goto(base + path);
        const geometry = await page.locator('.sh-frame').evaluate(frame => {
          const rect = element => {
            const r = element.getBoundingClientRect();
            return { left: r.left, right: r.right, center: (r.top + r.bottom) / 2 };
          };
          return {
            items: [...frame.querySelectorAll('.sh-brand,.sh-navigation>*,.sh-account>*,.sh-stores>*')].map(rect),
            navigation: [...frame.querySelector('.sh-navigation').children].map(rect),
          };
        });
        assert.ok(geometry.items.every(r => r.left >= 0 && r.right <= width), `${path} at ${width}: overflow`);
        const centers = geometry.navigation.map(r => r.center);
        assert.ok(Math.max(...centers) - Math.min(...centers) <= 1, `${path}: navigation alignment`);
        assert.equal(await page.locator('.sh-stores img').count(), 2);
        assert.ok(await page.locator('.sh-stores img').evaluateAll(images => images.every(image => image.complete && image.naturalWidth > 0)), `${path}: store badge assets`);
        const product = page.locator('.sh-navigation summary').first();
        await product.click();
        assert.ok(await page.getByRole('link', {name: 'Overview', exact: true}).isVisible());
        await page.keyboard.press('Escape');
        assert.ok(!await page.getByRole('link', {name: 'Overview', exact: true}).isVisible());
      }
    }
    await page.goto(base + '/about.html?lang=ja');
    await page.waitForFunction(() => document.querySelector('.sh-language summary').textContent.includes('JA'));
    await page.locator('.sh-language summary').click();
    await page.locator('.sh-language a[lang="fr"]').click();
    await page.waitForURL('**/about.html?lang=fr');
    await page.waitForFunction(() => document.querySelector('.sh-language summary').textContent.includes('FR'));
    assert.equal(await page.locator('.sh-brand').innerText(), 'SIMY');
    const noJS = await browser.newPage({ javaScriptEnabled: false });
    await noJS.goto(base + '/');
    await noJS.locator('.sh-navigation summary').first().click();
    assert.ok(await noJS.getByRole('link', { name: 'Overview', exact: true }).isVisible());
    assert.deepEqual(errors, []);
    console.log('PASS: 42 responsive layouts, aligned menu centers, dropdown/Escape, same-page language navigation, and no-JS navigation.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
