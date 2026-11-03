// Browser geometry regression for the clinic service page. Run against a local server or production.
const assert = require('node:assert/strict');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
 const browser = await chromium.launch({channel:'chrome',headless:true});
 try {
  const page=await browser.newPage();
  for (const [width,height] of [[1440,1000],[1024,1000],[768,1000],[390,844],[320,568],[844,390]]) {
   await page.setViewportSize({width,height});
   await page.goto(process.env.CLINIC_URL || 'http://127.0.0.1:8899/hp-management/clinic-service-v2.html');
   await page.evaluate(()=>document.fonts.ready);
   const data=await page.evaluate(()=>{
    const box=e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height}};
    return {overflow:document.documentElement.scrollWidth>innerWidth,forms:['diagnosis','rebuild'].map(id=>{const form=document.querySelector('#'+id+'-form');return {id,input:box(form.querySelector('input[type=text]')),button:box(form.querySelector('button[type=submit]'))}}),plans:[...document.querySelectorAll('#pricing .plan')].map(box)};
   });
   assert.equal(data.overflow,false,`${width}: page overflow`);
   for(const f of data.forms){
    assert.ok(f.input.width>=Math.min(240,width-100),`${width}: ${f.id} input squeezed`);
    assert.ok(f.button.height>=44,`${width}: ${f.id} button target`);
    if(Math.abs(f.input.top-f.button.top)<2)assert.ok(Math.abs(f.input.bottom-f.button.bottom)<=1,`${width}: ${f.id} lower edge`);
    else {assert.ok(f.button.top>=f.input.bottom,`${width}: ${f.id} overlap`);assert.ok(Math.abs(f.input.left-f.button.left)<=1&&Math.abs(f.input.right-f.button.right)<=1,`${width}: ${f.id} column edges`);}
   }
   if(data.plans.length===2&&Math.abs(data.plans[0].top-data.plans[1].top)<=1)assert.ok(Math.abs(data.plans[0].bottom-data.plans[1].bottom)<=1,`${width}: plan bottoms`);
   await page.locator('[data-plan=basic]').first().click();
   await page.locator('#preview-application[open]').waitFor();
   await page.locator('#application-close').click();
   // Open the existing application dialog only for layout measurement; no submission.
   await page.locator('#preview-application').evaluate(e=>e.showModal());
   const app=await page.locator('#preview-application').evaluate(e=>({w:e.clientWidth,scroll:e.scrollWidth,radios:[...e.querySelectorAll('[type=radio]')].map(i=>i.getBoundingClientRect().width),cards:[...e.querySelectorAll('.application-plan')].map(i=>({display:getComputedStyle(i).display,height:i.getBoundingClientRect().height,textWidth:i.querySelector('span').getBoundingClientRect().width,radioLeft:i.querySelector('input').getBoundingClientRect().left,textLeft:i.querySelector('span').getBoundingClientRect().left}))}));
   assert.ok(app.scroll<=app.w+1,`${width}: application overflow`);
   assert.ok(app.radios.every(w=>w===20),`${width}: radio stretched`);assert.ok(app.cards.every(x=>x.display==='grid'&&x.height<180&&x.textWidth>=Math.min(150,width-125)&&x.radioLeft<x.textLeft),`${width}: application card layout overridden`);
   await page.keyboard.press('Escape');
   console.log(`${width}x${height}: forms, pricing entry, application controls and overflow passed`);
  }
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
