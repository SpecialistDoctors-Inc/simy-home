// Browser geometry regression for the clinic service page. Run against a local server or production.
const assert = require('node:assert/strict');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
 const browser = await chromium.launch({channel:'chrome',headless:true});
 try {
  const page=await browser.newPage();
  for (const width of [1440,1024,768,390,320]) {
   await page.setViewportSize({width,height:1000});
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
   console.log(`${width}px: form targets, edges and overflow passed`);
  }
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
