// Run against a local preview with Playwright available through NODE_PATH.
// SITE_URL defaults to http://localhost:8766; no external account actions are sent.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    const openNavigation = async () => { if (await page.locator('.sh-menu-toggle').isVisible() && await page.locator('.sh-menu').getAttribute('open') === null) await page.locator('.sh-menu-toggle').click(); };
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
            items: [...frame.querySelectorAll('.sh-brand,.sh-navigation>*,.sh-account>*,.sh-stores>*')].filter(e => e.checkVisibility()).map(rect),
            navigation: [...frame.querySelector('.sh-navigation').children].filter(e => e.checkVisibility()).map(rect),
          };
        });
        assert.ok(geometry.items.every(r => r.left >= 0 && r.right <= width), `${path} at ${width}: overflow`);
        const centers = geometry.navigation.map(r => r.center);
        if (width > 960) assert.ok(Math.max(...centers) - Math.min(...centers) <= 1, `${path}: navigation alignment`);
        assert.equal(await page.locator('.sh-stores img').count(), 2);
        await openNavigation();
        if (width <= 960) {
          const edges = await page.locator('.sh-navigation').evaluate(nav => [...nav.children].map(e => {const r=e.getBoundingClientRect();return [r.left,r.right];}));
          assert.ok(edges.every(e => Math.abs(e[0]-edges[0][0])<=1 && Math.abs(e[1]-edges[0][1])<=1), `${path}: mobile navigation edges`);
        }
        const product = page.locator('.sh-navigation summary').first();
        await product.click();
        await page.waitForFunction(() => [...document.querySelectorAll('.sh-stores img')].every(image => image.complete && image.naturalWidth > 0));
        assert.ok(await page.locator('.sh-stores img').evaluateAll(images => images.every(image => image.complete && image.naturalWidth > 0)), `${path}: store badge assets`);

        assert.ok(await page.locator('a[href$="#product"]').isVisible());
        await page.keyboard.press('Escape');
        assert.ok(!await page.locator('.simy-header').locator('a[href$="#product"]').isVisible(), `${path}/${width}: Escape, focus=`+await page.evaluate(()=>document.activeElement.outerHTML.slice(0,180)));
      }
    }
    // Follow the actual menu link; directory indexes can work locally and 404 on S3.
    for (const locale of ['en', 'ja', 'hi', 'es', 'fr', 'zh-Hans']) {
      await page.goto(base + '/about.html?lang=' + locale);
      await page.waitForFunction(locale => document.documentElement.lang === locale, locale);
      const store = new URL(await page.locator('.sh-store:not(.sh-google-play)').getAttribute('href'));
      assert.equal(store.hostname, 'apps.apple.com');
      assert.ok(store.pathname.endsWith('/id6745385262'));
      assert.equal(new URL(await page.locator('.sh-google-play').getAttribute('href'),base).pathname, locale === 'ja' ? '/download.html' : `/download/${locale.toLowerCase()}.html`);
      assert.equal(new URL(await page.locator('.sh-google-play').getAttribute('href'),base).hash, '#android');
      await openNavigation();
    await page.locator('.sh-navigation summary').nth(2).click();
      const guides = page.locator('.sh-navigation').locator('a[href*="/guides/"]');
      assert.ok((await guides.getAttribute('href')).endsWith('/index.html'));
      await guides.click();
      assert.equal(await page.locator('h1').count(), 1);
      assert.notEqual(await page.locator('h1').innerText(), '404');
    }
    await page.setViewportSize({width:320,height:900});
    const fs = require('node:fs');
    const path = require('node:path');
    const site = path.join(__dirname, '../site');
    const pages = fs.readdirSync(site, {recursive:true}).filter(file => !file.startsWith('old/') && file.endsWith('.html') && fs.readFileSync(path.join(site,file),'utf8').includes('class="simy-header"'));
    for (const file of pages) {
      await page.goto(base + '/' + file);
      await page.evaluate(() => document.fonts.ready);
      const size = await page.evaluate(() => ({width:innerWidth,content:document.documentElement.scrollWidth}));
      assert.ok(size.content <= size.width, `${file}: body overflow ${size.content}/${size.width}`);
    }
    for (const width of [320,390,720,1250,1440]) {
      await page.setViewportSize({width,height:900});
      await page.goto(base + '/guides/codex.html');
      await page.getByRole('link',{name:'使い方・選び方を読む',exact:true}).click();
      await page.waitForFunction(() => document.querySelector('#reference').getBoundingClientRect().top <= document.querySelector('.simy-header').getBoundingClientRect().bottom + 18);
      assert.ok(await page.evaluate(() => document.querySelector('#reference h2').getBoundingClientRect().top >= document.querySelector('.simy-header').getBoundingClientRect().bottom));
      await page.goto(base + '/download/en.html#android');
      await page.waitForFunction(() => document.querySelector('#android').getBoundingClientRect().top <= document.querySelector('.simy-header').getBoundingClientRect().bottom + 18);
      assert.ok(await page.evaluate(() => document.querySelector('#android h2').getBoundingClientRect().top >= document.querySelector('.simy-header').getBoundingClientRect().bottom));
    }
    await page.goto(base + '/');
    await openNavigation();
    await page.locator('.sh-navigation summary').nth(2).click();
    await page.getByRole('link',{name:'Seller information',exact:true}).click();
    assert.ok((await page.locator('main').innerText()).includes('塩飽 哲生'));
    await page.goto(base + '/about.html?lang=ja');
    await page.waitForFunction(() => document.querySelector('.sh-language summary').textContent.includes('JA'));
    await page.locator('.sh-language summary').click();
    await page.locator('.sh-language a[lang="fr"]').click();
    await page.waitForURL('**/about.html?lang=fr');
    await page.waitForFunction(() => document.querySelector('.sh-language summary').textContent.includes('FR'));
    assert.equal(await page.locator('.sh-brand').innerText(), 'SIMY');
    const noJS = await browser.newPage({ javaScriptEnabled: false });
    await noJS.goto(base + '/');
    await noJS.locator('.sh-menu-toggle').click();
    await noJS.locator('.sh-navigation summary').first().click();
    assert.ok(await noJS.getByRole('link', { name: 'Overview', exact: true }).isVisible());
    assert.deepEqual(errors, []);
    console.log(`PASS: ${pages.length} pages without mobile body overflow; 6 Guides menu destinations; 10 anchor states; legal navigation; 42 responsive layouts, aligned menu centers, dropdown/Escape, same-page language navigation, and no-JS navigation.`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
