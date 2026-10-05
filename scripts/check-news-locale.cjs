const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
  const browser=await chromium.launch({channel:'chrome',headless:true});
  try {
    const page=await browser.newPage();
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    const base=process.env.SITE_URL||'http://localhost:8767';
    for(const width of [1440,390,320]){
      await page.setViewportSize({width,height:1000});
      for(const locale of ['en','ja','fr','es','hi','zh-Hans']){
        await page.goto(base+'/press-release.html?lang='+locale);
        const copy=JSON.parse(fs.readFileSync(path.join(__dirname,`../site/lang/${locale}.json`)));
        await page.waitForFunction(locale=>document.documentElement.lang===locale,locale);
        await page.waitForFunction(title=>document.querySelector('#latest-release-title a').textContent===title,copy['newpress.latest.title']);
        const latest=page.locator('#latestRelease');
        assert.equal(await latest.getAttribute('lang'),locale);
        assert.equal(await latest.locator('[data-i18n="newpress.latest.summary"]').innerText(),copy['newpress.latest.summary']);
        const target=locale==='ja'?'/news/20261005.html':'/news/20261005-en.html';
        assert.equal(await latest.locator('[data-latest-report]').first().getAttribute('href'),target);
        assert.equal(await latest.locator('[data-other-report]').getAttribute('href'),locale==='ja'?'/news/20261005-en.html':'/news/20261005.html');
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
        const geometry=await page.evaluate(()=>({title:document.querySelector('h1').getBoundingClientRect().left,latest:document.querySelector('#latest-release-title').getBoundingClientRect().left,body:document.querySelector('article.article').getBoundingClientRect().left+parseFloat(getComputedStyle(document.querySelector('article.article')).paddingLeft),size:parseFloat(getComputedStyle(document.querySelector('h1')).fontSize)}));
        assert.ok(Math.abs(geometry.title-geometry.latest)<=1);
        assert.ok(Math.abs(geometry.title-geometry.body)<=1);
        assert.ok(geometry.size<=56);
        if(locale==='en') assert.ok(!/[\u3040-\u30ff\u3400-\u9fff]/.test(await latest.innerText()));
      }
    }
    await page.goto(base+'/press-release.html?lang=de');
    await page.waitForFunction(()=>document.documentElement.lang==='de');
    assert.equal(await page.locator('#latestRelease').getAttribute('lang'),'en');
    assert.ok((await page.locator('#latestRelease').innerText()).includes('Four in five'));
    await page.locator('.sh-language summary').click();
    await page.locator('.sh-language a[lang="ja"]').click();
    await page.waitForFunction(()=>document.querySelector('#latestRelease').lang==='ja');
    await page.locator('.sh-language summary').click();
    await page.locator('.sh-language a[lang="en"]').click();
    await page.waitForFunction(()=>document.querySelector('#latestRelease').lang==='en');
    await page.locator('#latestRelease [data-latest-report]').first().click();
    assert.equal(await page.locator('html').getAttribute('lang'),'en');
    assert.ok((await page.locator('h1').innerText()).includes('Four in five'));
    assert.deepEqual(errors,[]);
    console.log('PASS: 18 locale/viewport states, aligned content, correct announcement copy and article links, JA→EN switching, English article destination, no page errors.');
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
