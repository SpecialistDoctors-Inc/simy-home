const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try {
  const page=await browser.newPage({reducedMotion:'reduce'});
  const errors=[];page.on('pageerror',e=>errors.push({url:page.url(),message:e.message}));
  const files=fs.readdirSync(path.join(__dirname,'../site'),{recursive:true}).filter(f=>f.endsWith('.html')&&f!=='google-site-verification-TODO.html'&&fs.readFileSync(path.join(__dirname,'../site',f),'utf8').includes('class="simy-header"'));
  for(const width of [1440,320]){
   await page.setViewportSize({width,height:1000});
   for(const file of files){
    await page.goto((process.env.SITE_URL||'http://localhost:8767')+'/'+file);
    const g=await page.locator('.simy-header').evaluate(n=>{const r=n.getBoundingClientRect();return{left:r.left,top:r.top,right:r.right,width:innerWidth}});
    assert.ok(Math.abs(g.left)<=1&&Math.abs(g.top)<=1&&Math.abs(g.right-g.width)<=1,`${file} ${width}: header at viewport edges`);
    await page.keyboard.press('End');await page.waitForTimeout(50);
    await page.keyboard.press('Home');await page.waitForTimeout(50);
   }
  }
  assert.deepEqual(errors,[]);
  console.log(`PASS: ${files.length} public pages at desktop/mobile, headers aligned within 1px, End/Home scrolling without page errors.`);
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
