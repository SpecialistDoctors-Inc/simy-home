// Local-only browser regression: no account creation, enquiry, or payment.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');
const site = path.resolve(__dirname, '../site');
const output = process.env.SIMY_PURCHASE_EVIDENCE_DIR;
if (!output) throw new Error('Set SIMY_PURCHASE_EVIDENCE_DIR outside the repository');
const key = 'Online signup is available for Starter and Industry (IT Engineer, Financial Planner and Pharmaceutical MR). Please contact us about Dental Clinic, Realtime and additional storage.';
const vm = require('node:vm');
const runtime = fs.readFileSync(path.join(site, 'home-i18n.js'), 'utf8');
const marker = 'const JA_COPY = Object.freeze(';
const start = runtime.indexOf(marker) + marker.length;
const japanese = Function('return ' + runtime.slice(start, runtime.indexOf(');', start)))();
const context = { window: {} };
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(site, 'home-locales.js'), 'utf8'), context);
const dictionaries = { en: { [key]: key }, ja: japanese, ...context.window.SIMY_HOME_LOCALES };
const server = http.createServer((request, response) => {
  const pathname = new URL(request.url, 'http://localhost').pathname;
  const file = path.resolve(site, '.' + pathname + (pathname.endsWith('/') ? 'index.html' : ''));
  if (!file.startsWith(site + path.sep)) return response.writeHead(403).end();
  fs.readFile(file, (error, data) => error ? response.writeHead(404).end() : response.writeHead(200, { 'Content-Type': ({ '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json' })[path.extname(file)] || 'application/octet-stream' }).end(data));
});
(async () => {
  fs.mkdirSync(output, { recursive: true });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({ channel: 'chrome' });
  const report = [];
  try {
    const page = await browser.newPage();
    await page.route('**/*', route => route.request().url().startsWith(origin) ? route.continue() : route.abort());
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 1000 });
      for (const [locale, dictionary] of Object.entries(dictionaries)) {
        assert.ok(dictionary[key], `Missing availability translation: ${locale}`);
        console.log(`Checking ${locale}/${width}`);
        await page.goto(`${origin}/?lang=${locale}`);
        const note = page.locator('[data-purchase-availability]');
        await page.waitForFunction(text => document.querySelector('[data-purchase-availability]')?.textContent.includes(text), dictionary[key]);
        assert.equal(await note.locator('a').getAttribute('href'), 'mailto:sales@simy.one');
        assert.ok(await note.isVisible());
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Overflow: ${locale}/${width}`);
        for (const interval of ['annual', 'monthly']) {
          await page.locator(`[data-billing-cycle="${interval}"]`).click();
          const links = await page.locator('a[href*="/signup"][href*="plan="]').evaluateAll(nodes => nodes.map(node => node.href));
          assert.equal(links.length, 2);
          for (const href of links) {
            const params = new URL(href).searchParams;
            assert.ok(['starter', 'quality'].includes(params.get('plan')));
            assert.equal(params.get('interval'), interval);
            assert.equal(params.get('lang'), locale);
          }
        }
        if (['en', 'ja', 'ar'].includes(locale) && width !== 320) {
          await note.scrollIntoViewIfNeeded();
          await page.screenshot({ path: path.join(output, `availability-${locale}-${width}.png`) });
        }
        report.push({ locale, width, billingCycles: 2, checkoutLinksPerCycle: 2, localized: true, overflow: false });
      }
    }
    fs.writeFileSync(path.join(output, 'browser-report.json'), JSON.stringify(report, null, 2));
    console.log(`Passed ${report.length} locale/viewport states and ${report.length * 4} signup handoffs`);
  } finally { await browser.close(); server.close(); }
})().catch(error => { console.error(error); server.close(); process.exitCode = 1; });
