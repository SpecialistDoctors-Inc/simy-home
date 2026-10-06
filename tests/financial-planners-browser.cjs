// NODE_PATH=<Playwright installation> node tests/financial-planners-browser.cjs
// Against a local static preview; interactions use synthetic examples only.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..');
const out=path.join(root,'docs/financial-planners/screenshots');
const assets=path.join(root,'site/assets/fp-experience');
const base=process.env.SITE_URL || 'http://127.0.0.1:8765';
fs.mkdirSync(out,{recursive:true});fs.mkdirSync(assets,{recursive:true});
(async()=>{
 const browser=await chromium.launch({channel:'chrome'});
 const report={checks:[],errors:[]};
 try {
 const locales=['ja','en','es','fr','hi','zh-Hans'];
 for(const lang of locales) {
  const route=`/for/${lang==='ja'?'':lang.toLowerCase()+'/'}financial-planners/`;
  const p=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  p.on('pageerror',e=>report.errors.push(e.message));
  p.on('console',m=>{if(m.type()==='error')report.errors.push(`${lang}: ${p.url()}: ${m.text()}`);});
  p.on('requestfailed',r=>{if(r.failure()?.errorText!=='net::ERR_ABORTED')report.errors.push(`${lang}: ${r.url()}: ${r.failure()?.errorText}`);});
  p.on('response',r=>{if(r.status()>=400)report.errors.push(r.status()+' '+r.url());});
  await p.goto(base+route);
  await p.locator('.fp-hero').screenshot({path:path.join(assets,`social-${lang}.png`)});
  for(const width of [1440,768,390,320,720]) {
   await p.setViewportSize({width,height:width===720?500:1000});
   const smallText=await p.evaluate(()=>{
    const groups=[
     {selector:'.hero-lead,.story-intro > p,.story-description,.risk-observation,.risk-evidence dd,.risk-followup p:not(.ui-kicker),.fact-list p,.email-draft,.roleplay-benefit p',min:16},
     {selector:'.speech,.phone-card,.phone-note,.phone-heading > p:last-child,.visual-caption,.risk-gate,.risk-method,.screen-tabs button',min:14}
    ];
    return groups.flatMap(({selector,min})=>[...document.querySelectorAll(selector)].filter(e=>parseFloat(getComputedStyle(e).fontSize)<min).map(e=>({text:e.textContent,font:getComputedStyle(e).fontSize,min})));
   });
   assert.deepEqual(smallText,[],`${lang}/${width}: critical text remains readable`);
   for(const demo of ['meeting','roleplay']) {
    for(let i=0;i<3;i++) {
     const d=p.locator(`[data-demo="${demo}"]`);
     await d.locator(`[data-step="${i}"]`).click();
     assert.equal(await d.locator('[data-panel]:visible').count(),1);
     assert.equal(await d.locator(`[data-panel="${i}"]`).isVisible(),true);
     assert.equal(await d.locator(`[data-step="${i}"]`).getAttribute('aria-pressed'),'true');
     const overflow=await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
     assert.equal(overflow,false,`${lang}/${width}/${demo}/${i}: page overflow`);
     const geometry=await d.locator('[data-controls] button').evaluateAll(bs=>bs.map(b=>{const r=b.getBoundingClientRect();return {top:r.top,bottom:r.bottom,width:r.width};}));
     assert.ok(Math.max(...geometry.map(r=>r.top))-Math.min(...geometry.map(r=>r.top))<=1);
     assert.ok(Math.max(...geometry.map(r=>r.bottom))-Math.min(...geometry.map(r=>r.bottom))<=1);
     assert.ok(Math.max(...geometry.map(r=>r.width))-Math.min(...geometry.map(r=>r.width))<=1);
     const clips=await d.locator('[data-panel]:visible').evaluateAll(ps=>ps.flatMap(panel=>[...panel.querySelectorAll('p,h3,b')].filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.textContent)));
     assert.deepEqual(clips,[],`${lang}/${width}: text fits`);
     if(width===1440)await (demo==='roleplay'?d.locator('.phone'):p.locator('#meeting .app-screen')).screenshot({path:path.join(out,`${lang}-${demo}-${i}.png`),style:'.simy-header,.skip { visibility: hidden !important; }'});
    }
   }
   const risk = p.locator('#red-flags');
   assert.equal(await risk.locator('[data-state="red"]').count(),2);
   assert.equal(await risk.locator('[data-state="amber"]').count(),3);
   assert.equal(await risk.locator('[data-state="green"]').count(),1);
   for (const card of await risk.locator('.risk-card').all()) {
    const details=card.locator('details');
    if(await details.getAttribute('open')===null) await details.locator('summary').click();
    assert.equal(await details.locator('dd').count(),2);
    assert.equal(await details.locator('dl').isVisible(),true);
   }
   const riskGeometry=await risk.locator('.risk-card').evaluateAll(cards=>cards.map(c=>{const r=c.getBoundingClientRect();return {width:r.width,left:r.left,right:r.right,overflow:c.scrollWidth>c.clientWidth+1};}));
   assert.ok(riskGeometry.every(c=>!c.overflow && c.left>=0 && c.right<=width));
   assert.ok(Math.max(...riskGeometry.map(c=>c.width))-Math.min(...riskGeometry.map(c=>c.width))<=1);
   if([1440,390].includes(width)) await risk.screenshot({path:path.join(out,`${lang}-red-flags-${width}.png`),style:".simy-header,.skip { visibility: hidden !important; }"});
   for (const card of await risk.locator('.risk-card').all()) {
    if(await card.getAttribute('data-state')!=='red')await card.locator('summary').click();
   }
   if([1440,390].includes(width)) {
    await p.locator('[data-demo="roleplay"] [data-step="1"]').click();
    await p.evaluate(()=>window.scrollTo(0,0));
    await p.screenshot({path:path.join(out,`${lang}-${width}.png`),fullPage:true});
    if(lang==='ja') {
     if(width===390) await p.screenshot({path:path.join(out,'ja-mobile-first-screen.png')});
     if(width===1440) await p.locator('#roleplay').screenshot({path:path.join(out,'ja-roleplay-section.png'),style:'.simy-header,.skip { visibility: hidden !important; }'});
    }
   }
   const peers=await p.locator('.fp-story > .fp-frame').evaluateAll(es=>es.map(e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right};}));
   assert.ok(Math.max(...peers.map(x=>x.left))-Math.min(...peers.map(x=>x.left))<=1);
   assert.ok(Math.max(...peers.map(x=>x.right))-Math.min(...peers.map(x=>x.right))<=1);
   report.checks.push(`${lang} ${width}px: all 6 demo states and 6 risk checks, body >=16px and screen/support text >=14px, no overflow, tab and section geometry within 1px`);
  }
  for (const otherLocale of locales.filter(code=>code!==lang)) {
   await p.goto(base+route);
   await p.locator('.sh-language summary').click();
   await p.locator(`.sh-language [data-locale-option="${otherLocale}"]`).click();
   assert.equal(new URL(p.url()).pathname,`/for/${otherLocale==='ja'?'':otherLocale.toLowerCase()+'/'}financial-planners/`);
   assert.equal(await p.locator('html').getAttribute('lang'),otherLocale);
  }
  await p.setViewportSize({width:1440,height:1000});
  await p.goto(base+route);
  await p.locator('.hero-actions .text-link').click();
  const anchor=await p.evaluate(()=>({target:document.querySelector('#experience').getBoundingClientRect().top,header:document.querySelector('.simy-header').getBoundingClientRect().bottom}));
  assert.ok(anchor.target>=anchor.header-1,JSON.stringify(anchor));
  const evidence=p.locator('[data-risk="timing"] summary');await evidence.focus();await p.keyboard.press('Enter');assert.equal(await p.locator('[data-risk="timing"] dl').isVisible(),true);
  await p.locator('.risk-followup a').click();assert.equal(new URL(p.url()).hash,'#roleplay');
  const talk=p.locator('[data-demo="roleplay"] [data-step="1"]');await talk.focus();await p.keyboard.press('Enter');assert.equal(await talk.getAttribute('aria-pressed'),'true');
  await p.locator('.availability summary').click();assert.equal(await p.locator('.availability').getAttribute('open'),'');
  const other=lang==='ja'?'en':'ja';await p.locator('.sh-language summary').click();await p.locator(`.sh-language [data-locale-option="${other}"]`).click();assert.equal(new URL(p.url()).pathname,`/for/${other==='ja'?'':other.toLowerCase()+'/'}financial-planners/`);
  await p.goto(base+(lang==='en'?'/':`/${lang}.html`));await p.locator('.sh-navigation details').nth(1).locator('summary').click();const nav=p.locator('.sh-navigation a', {hasText:'For financial planners'});assert.equal(new URL(await nav.getAttribute('href'),base).pathname,route);await nav.click();assert.equal(new URL(p.url()).pathname,route);
  await p.close();
  const nojs=await browser.newPage({javaScriptEnabled:false,viewport:{width:390,height:844}});await nojs.goto(base+route);assert.equal(await nojs.locator('[data-panel]:visible').count(),6);assert.equal(await nojs.locator('[data-controls]:visible').count(),0);await nojs.close();
 }
 assert.deepEqual(report.errors,[]);
 fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify(report,null,2));
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
