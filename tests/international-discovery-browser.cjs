// Isolated real HTTP/Chrome checks. No installer, account or external send actions.
// NODE_PATH must provide Playwright. Evidence stays outside the deployed site.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require('playwright');
const site = path.resolve(__dirname, '../site');
const out = process.env.PR108_EVIDENCE_DIR || '/tmp/pr108-browser';
const mime = { '.html':'text/html', '.js':'application/javascript', '.css':'text/css', '.json':'application/json', '.webp':'image/webp', '.png':'image/png', '.svg':'image/svg+xml' };
const report = { home:[], downloads:[], errors:[] };
const counts = new Map();
const manifest = { version:'0.0.1', artifacts:[
  {platform:'darwin', arch:'arm64', url:'https://simy.one/downloads/simy-cli/0.0.1/test.dmg'},
  {platform:'win32', arch:'x64', url:'https://simy.one/downloads/simy-cli/windows/0.0.1/test.exe'}
] };
const server = http.createServer((req,res) => {
  const url = new URL(req.url, 'http://localhost');
  if (url.pathname.endsWith('/latest.json')) {
    const count = (counts.get(url.pathname) || 0) + 1;
    counts.set(url.pathname, count);
    res.writeHead(count === 1 ? 502 : 200, {'Content-Type':'application/json'}).end(JSON.stringify(manifest));
    return;
  }
  const file = path.resolve(site, '.' + url.pathname + (url.pathname.endsWith('/') ? 'index.html' : ''));
  if (!file.startsWith(site + path.sep)) { res.writeHead(403).end(); return; }
  fs.readFile(file, (error,data) => {
    res.writeHead(error ? 404 : 200, {'Content-Type':mime[path.extname(file)] || 'application/octet-stream'}).end(error ? '' : data);
  });
});
(async () => {
  fs.mkdirSync(out, {recursive:true});
  await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({channel:'chrome'});
  try {
    for (const js of [false,true]) {
      const context = await browser.newContext({javaScriptEnabled:js, reducedMotion:'reduce'});
      await context.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
      for (const locale of ['en','ja','es','fr','hi','zh-Hans']) {
        const page = await context.newPage();
        page.on('pageerror',error => report.errors.push(error.message));
        for (const width of [390,1440]) {
          await page.setViewportSize({width,height:1000});
          for (const zoom of [1,2]) {
            await page.goto(origin + (locale === 'en' ? '/' : `/${locale}.html`));
            await page.evaluate(zoom => document.body.style.zoom = zoom,zoom);
            const entry = page.locator('.hero-work-entry a');
            assert.ok(await entry.isVisible());
            assert.equal(await entry.getAttribute('href'),locale === 'ja' ? '/for/' : '/for/en/');
            const geometry = await page.evaluate(() => {
              const rect = selector => {const r=document.querySelector(selector).getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom};};
              return { width:innerWidth, scrollWidth:document.documentElement.scrollWidth, entry:rect('.hero-work-entry'), copy:rect('.hero-copy'), heading:rect('#hero-title'), copyPaddingRight:parseFloat(getComputedStyle(document.querySelector('.hero-copy')).paddingRight)*parseFloat(document.body.style.zoom), overflowing:[...document.querySelectorAll('body *')].filter(e => e.checkVisibility() && e.getBoundingClientRect().right > innerWidth + 1).slice(0,12).map(e => ({tag:e.tagName,class:e.className,right:e.getBoundingClientRect().right})) };
            });
            // Shared-header zoom repair belongs to PR131; preserve overflow diagnostics.
            if (zoom === 1) assert.ok(geometry.scrollWidth <= width, JSON.stringify({locale,width,zoom,js,geometry}));
            assert.ok(geometry.entry.left >= 0 && geometry.entry.right <= width);
            assert.ok(Math.abs(geometry.entry.left-geometry.heading.left) <= 1);
            assert.ok(Math.abs(geometry.entry.right-(geometry.copy.right-geometry.copyPaddingRight)) <= 1);
            assert.ok(geometry.entry.bottom <= geometry.heading.top);
            report.home.push({locale,width,zoom,js,geometry});
            if (zoom === 1) await page.screenshot({path:path.join(out,`${locale}-${width}-${js}.png`)});
            await entry.click();
            assert.equal(new URL(page.url()).pathname,locale === 'ja' ? '/for/' : '/for/en/');
            assert.equal(await page.locator('h1').count(),1);
          }
          counts.clear();
          await page.goto(origin + (locale === 'ja' ? '/download.html' : `/download/${locale.toLowerCase()}.html`));
          if (js) await page.waitForFunction(() => document.querySelector('[data-meta="mac"]').textContent.startsWith('v0.0.1') && document.querySelector('[data-meta="win"]').textContent.startsWith('v0.0.1'));
          for (const key of ['mac','win']) {
            assert.match(await page.locator(`[data-dl="${key}"]`).getAttribute('href'),js ? /0\.0\.1\/test\./ : /0\.6\.10\/SIMY-CLI-/);
            if (!js) assert.match(await page.locator(`[data-release-status="${key}"]`).innerText(),/0\.6\.10/);
          }
          assert.deepEqual([...counts.values()],js ? [2,2] : []);
          report.downloads.push({locale,width,js,requests:[...counts.values()]});
        }
        await page.close();
      }
      await context.close();
    }
    assert.deepEqual(report.errors,[]);
    console.log(`PASS: ${report.home.length} discovery views; ${report.downloads.length} download views`);
  } finally {
    fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));
    await browser.close();
  }
})().catch(error => {console.error(error);process.exitCode=1;}).finally(() => server.closeAllConnections?.() || undefined).finally(() => server.close());
