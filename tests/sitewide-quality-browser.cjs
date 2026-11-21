// Run with NODE_PATH pointing to an existing Playwright installation; one browser.
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const inventory=require('../docs/seo/sitewide-page-inventory.json');
const root=path.resolve(__dirname,'..');
const output=path.join(root,'docs/sitewide-quality/evidence/browser-expanded.json');
const base=process.env.QUALITY_PREVIEW_URL||'http://127.0.0.1:8769';
const files=Object.keys(inventory).filter(name=>{
 const s=fs.readFileSync(path.join(root,'site',name),'utf8');
 return /<body\b/i.test(s)&&!(/http-equiv=["']refresh/i.test(s)||name==='auth-callback.html'||name.startsWith('google-site-verification-'));
});
(async()=>{
 const b=await chromium.launch({headless:true});
 const page=await b.newPage({reducedMotion:'reduce'});
 await page.route('**/*',r=>new URL(r.request().url()).origin===base?r.continue():r.abort());
 const results=[];
 try{
  for(const width of [320,390,768,1440]){
   await page.setViewportSize({width,height:900});
   for(const name of files){
    const url=name==='index.html'?'/?locale=en':'/'+name;
    await page.goto(base+url,{waitUntil:'load',timeout:15000});
    await page.keyboard.press('Tab');
    // Focus rendering must settle before measuring; bypass transition is disabled.
    await page.evaluate(()=>new Promise(r=>requestAnimationFrame(r)));
    const state=await page.evaluate(()=>{
     const a=document.activeElement,rect=a.getBoundingClientRect();
     const main=document.querySelectorAll('main,[role="main"]');
     const point=document.elementFromPoint(Math.max(1,rect.left+4),Math.max(1,rect.top+4));
     return {mainCount:main.length,href:a.getAttribute('href'),skipClass:a.className,
      skipVisible:rect.top>=0&&rect.bottom<=innerHeight&&!!point&&(point===a||a.contains(point)),
      overflow:document.documentElement.scrollWidth-innerWidth,
      contentLength:main[0]?.innerText.trim().length||0};
    });
    if(state.skipVisible&&state.href?.includes('#')){
     await page.keyboard.press('Enter');
     await page.waitForTimeout(100);
     await page.waitForLoadState('load');
     await page.evaluate(()=>new Promise(r=>requestAnimationFrame(r)));
     state.mainFocused=await page.evaluate(()=>document.activeElement.matches('main,[role="main"]'));
    }else state.mainFocused=false;
    results.push({file:name,width,...state});
   }
   fs.writeFileSync(output,JSON.stringify({method:'Local static site; reduced-motion; external requests blocked; one Chromium; CSS viewport widths',results},null,2)+'\n');
   console.log('Checked',width,files.length,'documents');
  }
  // JavaScript-disabled coverage and a CSS zoom reflow proxy on changed templates.
  const nojs=await b.newPage({javaScriptEnabled:false,viewport:{width:390,height:900}});
  await nojs.route('**/*',r=>new URL(r.request().url()).origin===base?r.continue():r.abort());
  const nojsResults=[];
  for(const name of ['contact.html','old/contact.html','guides/claude-code.html','guides/en/claude-code.html','news/20261005.html','hp-management/law-firm.html']){
   await nojs.goto(base+'/'+name,{waitUntil:'load'});
   nojsResults.push({file:name,mainCount:await nojs.locator('main').count(),textLength:(await nojs.locator('main').innerText()).trim().length});
  }
  await nojs.close();
  const zoom=[];
  await page.setViewportSize({width:640,height:900});
  for(const name of ['contact.html','old/contact.html','guides/claude-code.html','guides/en/claude-code.html','news/20261005.html','hp-management/law-firm.html']){
   await page.goto(base+'/'+name,{waitUntil:'load'});
   zoom.push({file:name,method:'640 CSS-px viewport (1280px at 200% layout proxy); not a manual browser zoom test',overflow:await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)});
  }
  const summary={documents:files.length,viewportCases:results.length,failed:results.filter(r=>r.mainCount!==1||!r.skipVisible||!r.mainFocused||r.overflow>1||r.contentLength===0)};
  fs.writeFileSync(output,JSON.stringify({method:'Local static site; reduced-motion; external requests blocked; one Chromium; CSS viewport widths',summary,results,nojsResults,zoom},null,2)+'\n');
  // Current-code screenshots for edited copy and responsive layouts.
  await page.setViewportSize({width:390,height:900});
  for(const [name,label] of [['old/contact.html','contact-mobile'],['guides/claude-code.html','guide-ja-mobile']]){
   await page.goto(base+'/'+name,{waitUntil:'networkidle'});
   await page.screenshot({path:path.join(root,'docs/sitewide-quality/evidence/'+label+'.png')});
  }
  console.log(JSON.stringify({documents:summary.documents,cases:summary.viewportCases,failures:summary.failed.length,nojsResults,zoom},null,2));
 } finally{await b.close();}
})().catch(e=>{console.error(e);process.exit(1)});
