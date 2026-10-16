// Isolated navigation only: no external requests or account actions.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
(async () => {
  const site = path.resolve(__dirname, '../site');
  const out = process.env.HEADER_REPORT_DIR || path.resolve('artifacts/header-responsive');
  fs.mkdirSync(out, { recursive: true });
  const server = http.createServer((req, res) => {
    const pathname = new URL(req.url, 'http://localhost').pathname;
    const file = path.resolve(site, '.' + pathname + (pathname.endsWith('/') ? 'index.html' : ''));
    if (!file.startsWith(site + path.sep)) return res.writeHead(403).end();
    fs.readFile(file, (error, data) => {
      if (error) return res.writeHead(404).end();
      res.setHeader('Content-Type', ({'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.png':'image/png','.svg':'image/svg+xml'})[path.extname(file)] || 'application/octet-stream');
      res.end(data);
    });
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  let browser;
  const results = [];
  try {
    browser = await chromium.launch(process.env.HEADER_BUNDLED_CHROMIUM ? {} : { channel: 'chrome' });
    for (const js of [true, false]) for (const locale of ['ja', 'en']) for (const width of [390, 1280]) for (const zoom of [1, 2]) {
      const id = `${locale}-${width}-${zoom}-${js ? 'js' : 'nojs'}`;
      const page = await browser.newPage({ javaScriptEnabled: js, viewport: { width, height: 900 } });
      page.setDefaultTimeout(15000);
      page.setDefaultNavigationTimeout(15000);
      console.log(`START ${id}`);
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.route('**/*', route => new URL(route.request().url()).origin === base ? route.continue() : route.fulfill({ status: 204, body: '' }));
      try {
        console.log(`${id}: navigate`);
        await page.goto(base + (locale === 'ja' ? '/ja.html' : '/'));
        console.log(`${id}: set zoom`);
        await page.addStyleTag({ content: `html { zoom: ${zoom}; }` });
        const header = page.locator('.simy-header');
        if (js) await page.waitForFunction(() => document.querySelector('.simy-header').hasAttribute('data-enhanced'));
        const toggle = page.locator('.sh-menu-toggle');
        if (await toggle.isVisible()) {
          await toggle.focus(); await page.keyboard.press('Enter');
          await page.locator('.sh-navigation summary').first().waitFor({ state: 'visible' });
          if (js) {
            await page.keyboard.press('Tab');
            assert.equal(await page.locator('.sh-navigation summary').first().evaluate(el => el === document.activeElement), true, id);
          }
        }
        console.log(`${id}: menu open`);
        const groups = page.locator('.sh-navigation > *');
        const boxes = await groups.evaluateAll(nodes => nodes.map(node => { const r = node.getBoundingClientRect(); return { left: r.left, right: r.right }; }));
        if (width / zoom <= 960) for (const box of boxes) {
          assert.ok(Math.abs(box.left - boxes[0].left) <= 1 && Math.abs(box.right - boxes[0].right) <= 1, `${id}: navigation edges`);
        }
        await page.locator('.sh-navigation summary').nth(1).click();
        const sales = page.locator('.sh-navigation a[href*="/sales/"]');
        assert.equal(await sales.innerText(), locale === 'ja' ? '営業' : 'For sales');
        assert.equal(await sales.getAttribute('href'), locale === 'ja' ? '/for/sales/' : '/for/en/sales/');
        console.log(`${id}: menu screenshot`);
        await page.screenshot({ path: path.join(out, `${id}-menu.png`) });
        if (js) {
          await page.keyboard.press('Escape');
          assert.equal(await page.locator('.sh-navigation summary').nth(1).evaluate(el => el === document.activeElement), true);
          if (await toggle.isVisible()) await page.keyboard.press('Escape');
        } else if (await toggle.isVisible()) { await toggle.click(); }
        await page.locator('.sh-language summary').click();
        const language = page.locator('.sh-language .sh-panel');
        await language.waitFor({ state: 'visible' });
        const bounds = await language.boundingBox();
        assert.ok(bounds.x >= -1 && bounds.x + bounds.width <= width + 1, `${id}: language bounds`);
        for (const selector of ['.sh-brand', '.sh-menu-toggle', '.sh-signup', '.sh-language summary']) {
          const control = header.locator(selector);
          if (!await control.isVisible()) continue;
          const box = await control.boundingBox();
          assert.ok(box.x >= -1 && box.x + box.width <= width + 1, `${id}: ${selector} bounds`);
        }
        await page.screenshot({ path: path.join(out, `${id}-language.png`) });
        assert.deepEqual(errors, []);
        console.log(`PASS ${id}`);
        results.push({ id, navigationEdges: boxes, languageBounds: bounds, passed: true });
      } catch (error) {
        console.error(`${id}: ${error.stack}`);
        await page.screenshot({ path: path.join(out, `${id}-failure.png`), timeout: 5000 }).catch(() => {});
        throw error;
      } finally { await page.close(); }
    }
    console.log(`PASS ${results.length} responsive keyboard/layout states`);
  } finally {
    fs.writeFileSync(path.join(out, 'responsive.json'), JSON.stringify({ head: process.env.GITHUB_SHA || null, results }, null, 2));
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
