// Run against the local static preview with the existing Playwright runtime.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const site = path.join(__dirname, '../site');
const locales = ['en','ja','hi','es','fr','zh-Hans'];
(async () => {
 const browser = await chromium.launch({channel:'chrome',headless:true});
 try {
  const page = await browser.newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  const base = process.env.SITE_URL || 'http://localhost:8767';
  let states = 0;
  for (const width of [1440,390,320]) {
   await page.setViewportSize({width,height:1000});
   for (const locale of locales) {
    const dict = JSON.parse(fs.readFileSync(path.join(site,`lang/${locale}.json`)));
    for (const file of ['404.html','error.html','integrations.html','privacy.html']) {
     await page.goto(`${base}/${file}?lang=${locale}`);
     const key = file==='404.html'?'e404.guides':file==='error.html'?'e404.p':file==='integrations.html'?'int.plaudGuide':'privacy.google.h';
     await page.waitForFunction(({key,value}) => document.querySelector(`[data-i18n="${key}"]`).textContent===value, {key,value:dict[key]});
     if (file==='404.html'||file==='error.html') {
      const geometry=await page.evaluate(()=>{const h=document.querySelector('.simy-header').getBoundingClientRect(),m=document.querySelector('main.container').getBoundingClientRect();return {top:h.top,left:h.left,right:h.right,bottom:h.bottom,mainTop:m.top,width:innerWidth}});
      assert.ok(Math.abs(geometry.top)<=1 && Math.abs(geometry.left)<=1 && Math.abs(geometry.right-geometry.width)<=1,`${file}: full-width header at top`);
      assert.ok(geometry.mainTop>=geometry.bottom,`${file}: content below header`);
     }
     const copy = await page.locator('[data-i18n]').evaluateAll(nodes => nodes.filter(n=>n.getBoundingClientRect().height>0 && /^(e404\.(guides|download)$|int\.(plaud|pl[1-4]|allGuides)|privacy\.google\.)/.test(n.getAttribute('data-i18n'))).map(n=>({key:n.getAttribute('data-i18n')||n.getAttribute('data-i18n-html'),text:n.textContent})));
     for (const item of copy) assert.equal(item.text.trim(),dict[item.key].trim(),`${file} ${locale}: ${item.key}`);
     assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${file} ${locale} ${width}: overflow`);
     const prefix = locale==='ja'?'/guides/':`/guides/${locale.toLowerCase()}/`;
     const shortcuts = await page.locator('[data-localized-guide]').evaluateAll(nodes=>nodes.map(n=>({path:n.getAttribute('data-localized-guide'),href:n.getAttribute('href')})));
     for (const link of shortcuts) {assert.equal(link.href,prefix+link.path);assert.ok(fs.existsSync(path.join(site,link.href)));}
     if (file==='404.html') assert.equal(await page.locator('[data-localized-download]').getAttribute('href'),locale==='ja'?'/download.html':`/download/${locale.toLowerCase()}.html`);
     if (process.env.SCREENSHOT_DIR && width===1440 && locale==='en') await page.screenshot({path:path.join(process.env.SCREENSHOT_DIR,file+'.png'),fullPage:false});
     states++;
    }
   }
  }
  await page.goto(`${base}/integrations.html?lang=ja`);
  await page.waitForFunction(()=>document.querySelector('[data-localized-guide="plaud.html"]').getAttribute('href')==='/guides/plaud.html');
  await page.locator('.sh-language summary').click();
  await page.locator('.sh-language a[lang="fr"]').click();
  await page.waitForFunction(()=>document.querySelector('[data-localized-guide="plaud.html"]').getAttribute('href')==='/guides/fr/plaud.html');
  await page.locator('[data-localized-guide="plaud.html"]').click();
  assert.equal(await page.locator('html').getAttribute('lang'),'fr');
  assert.deepEqual(errors,[]);
  console.log(`PASS: ${states} locale/viewport states, localized copy and real destinations, JA→FR switching and guide navigation; no overflow or page errors.`);
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
