const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require('playwright');
const base = process.env.MANGA_LOCALE_BASE || 'http://127.0.0.1:8769';
const output = process.env.MANGA_LOCALE_EVIDENCE || '/tmp/simy-manga-locales';
(async () => {
  fs.mkdirSync(output, {recursive:true});
  const browser = await chromium.launch({channel:'chrome'});
  const errors = [], results = [];
  try {
    const page = await browser.newPage({reducedMotion:'reduce'});
    page.on('pageerror', e => errors.push(e.message));
    page.on('requestfailed', r => errors.push(r.url()));
    page.on('response', r => {if(r.status() >= 400) errors.push(r.status()+' '+r.url());});
    for (const lang of ['ja','en','es','fr','hi','zh-Hans']) {
      const route = lang === 'ja' ? '/for/engineers/' : `/for/${lang.toLowerCase()}/engineers/`;
      for (const width of [1440,390,320]) {
        await page.setViewportSize({width,height:1000});
        await page.goto(base + route);
        assert.equal(await page.locator('html').getAttribute('lang'), lang);
        assert.equal(await page.locator('.manga-panel').count(),8);
        assert.equal(await page.locator('.mechanism-image').count(),3);
        assert.equal(await page.locator('.experience-story:visible').count(),0);
        await page.locator('.hero .secondary').click();
        assert.ok(page.url().endsWith('#manga'));
        for (const img of await page.locator('.manga-panel img, .mechanism-image img').all()) {
          await img.scrollIntoViewIfNeeded();
          await img.evaluate(el=>el.decode());
          assert.ok(await img.evaluate(el=>el.naturalWidth===Number(el.width) || el.naturalWidth===Number(el.getAttribute('width'))));
          if(lang !== 'ja') assert.ok((await img.getAttribute('src')).includes(`-${lang}.webp`));
        }
        const text = await page.locator('#manga, #mechanism').evaluateAll(es=>es.map(el=>el.innerText).join(' '));
        if(lang !== 'ja') assert.doesNotMatch(text, /[\u3040-\u30ff]/u);
        if(['en','es','fr','hi'].includes(lang)) assert.doesNotMatch(text, /[\u3400-\u9fff]/u);
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
        await page.locator('.manga-more > summary').focus();
        await page.keyboard.press('Enter');
        assert.equal(await page.locator('.experience-story:visible').count(),3);
        await page.keyboard.press('Enter');
        await page.locator('.manga-transcript > summary').click();
        assert.equal(await page.locator('.manga-transcript li:visible').count(),8);
        await page.locator('.manga-transcript > summary').click();
        if(width!==320) {
          await page.locator('.hero').screenshot({path:`${output}/${lang}-hero-${width}.png`});
          await page.locator('#manga').screenshot({path:`${output}/${lang}-manga-${width}.png`});
          await page.locator('#mechanism').screenshot({path:`${output}/${lang}-mechanism-${width}.png`});
        }
        results.push({lang,width});
      }
      await page.goto(base+route+'#scene-progress');
      assert.equal(await page.locator('.experience-story:visible').count(),3);
    }
    assert.deepEqual(errors,[]);
    fs.writeFileSync(output+'/report.json',JSON.stringify({results,errors},null,2));
    console.log('PASS six locales at 1440/390/320px; localized assets, text, links and details');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
