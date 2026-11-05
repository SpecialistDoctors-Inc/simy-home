const assert = require('node:assert/strict');
const fs = require('node:fs');
const {chromium} = require('playwright');
const base = process.env.PHARMA_BASE || 'http://127.0.0.1:8775';
const output = process.env.PHARMA_EVIDENCE || '/tmp/pharmaceutical-manga-browser';
(async () => {
  fs.mkdirSync(output, {recursive:true});
  const browser = await chromium.launch({channel:'chrome'});
  const results = [], errors = [];
  try {
    for (const lang of (process.env.PHARMA_LANGS || 'ja,en,es,fr,hi,zh-Hans').split(',')) {
      const route = `/for/${lang === 'ja' ? '' : lang.toLowerCase()+'/'}pharmaceutical-companies/`;
      for (const width of (process.env.PHARMA_WIDTHS || '1440,390,320,720').split(',').map(Number)) {
        const page = await browser.newPage({reducedMotion:'reduce',viewport:{width,height:1000}});
        let closing=false;
        page.on('pageerror', e => errors.push(e.message));
        page.on('requestfailed', r => {if(!closing) errors.push(`${r.failure()?.errorText} ${r.url()}`);});
        page.on('response', r => {if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`);});
        await page.goto(base+route);
        await page.evaluate(()=>document.fonts.ready);
        assert.equal(await page.locator('html').getAttribute('lang'),lang);
        assert.equal(await page.locator('.manga-art img').count(),8);
        assert.equal(await page.locator('.dialogue img').count(),0);
        await page.locator('.manga-art img').evaluateAll(es=>es.forEach(el=>{el.loading='eager';}));
        const sources=[];
        for (const img of await page.locator('.manga-art img').all()) {
          await img.scrollIntoViewIfNeeded();
          await img.evaluate(el=>{el.loading='eager';});
          await page.waitForFunction(el=>el.complete && el.naturalWidth>0,await img.elementHandle()).catch(async e=>{console.error(await img.evaluate(el=>({src:el.src,currentSrc:el.currentSrc,complete:el.complete,w:el.naturalWidth,loading:el.loading,rect:el.getBoundingClientRect().toJSON(),scrollY}))); await page.screenshot({path:output+'/failure.png'}); throw new Error(`${lang}/${width}: ${await img.getAttribute('src')}: ${e.message}`);});
          await img.evaluate(el=>el.decode());
          const size=await img.evaluate(el=>({w:el.naturalWidth,h:el.naturalHeight}));
          assert.equal(size.w/size.h,1.5);
          sources.push(await img.getAttribute('src'));
        }
        assert.equal(new Set(sources).size,8);
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`${lang}/${width}: horizontal overflow`);
        const panels=await page.locator('.panel').evaluateAll(es=>es.map(el=>{const r=el.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom};}));
        if(width>700) for(let i=0;i<8;i+=2) {
          assert.ok(Math.abs(panels[i].top-panels[i+1].top)<=1);
          assert.ok(Math.abs(panels[i].bottom-panels[i+1].bottom)<=1);
          assert.ok(Math.abs(panels[i].left-panels[0].left)<=1);
          assert.ok(Math.abs(panels[i+1].right-panels[1].right)<=1);
        }
        else for(const p of panels) {
          assert.ok(Math.abs(p.left-panels[0].left)<=1);
          assert.ok(Math.abs(p.right-panels[0].right)<=1);
        }
        // The 720px viewport also covers the effective layout width of a
        // 1440px desktop at 200% zoom.
        if([1440,390].includes(width)) {
          await page.locator('.panels').screenshot({style:'.simy-header, #simy-consent { visibility: hidden !important; }',path:`${output}/${lang}-manga-${width}.png`});
          await page.evaluate(()=>scrollTo(0,0));
          await page.screenshot({path:`${output}/${lang}-page-${width}.png`,fullPage:true});
        }
        results.push({lang,width,scenes:8,overflow:false,alignedWithin:1});
        console.log(`PASS ${lang}/${width}`);
        await page.waitForLoadState('networkidle');
        closing=true;
        await page.close();
      }
    }
    assert.deepEqual(errors,[]);
    fs.writeFileSync(output+'/report.json',JSON.stringify({base,results,errors},null,2));
    console.log(`PASS ${results.length} locale/viewport checks; eight decoded scenes, aligned panels, no overflow or browser errors`);
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
