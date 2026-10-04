// Local synthetic browsing only. Evidence is written outside the repository.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {chromium} = require('playwright');
const site = path.resolve(__dirname,'../site');
const output = process.env.HEADER_EVIDENCE_DIR;
if (!output) throw new Error('Set HEADER_EVIDENCE_DIR outside the repository');
fs.mkdirSync(output,{recursive:true});
const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.png':'image/png','.svg':'image/svg+xml','.webp':'image/webp'};
const server=http.createServer((req,res)=>{
 const u=new URL(req.url,'http://localhost');let decoded;try{decoded=decodeURIComponent(u.pathname);}catch{res.writeHead(400).end();return;}const file=path.resolve(site,'.'+decoded+(u.pathname.endsWith('/')?'index.html':''));
 if(!file.startsWith(site+path.sep)){res.writeHead(403).end();return;}
 fs.readFile(file,(err,data)=>{if(err){res.writeHead(404).end();return;}res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream'}).end(data);});
});
const report={views:[],operations:[],screenshots:[],consoleErrors:[],pageErrors:[],networkFailures:[],externalRequests:[],fixtureRequests:[],environment:{releaseManifests:'synthetic null response; installer publication is a separate publisher',externalServices:'inert 204; no third-party execution or live account writes'},cleanupResidualCount:null};
const widths=[360,390,768,1024,1280,1440,1920];
const locales=['en','ja','hi','es','fr','zh-Hans'];
const home=l=>l==='en'?'/':`/${l}.html`;
const guide=l=>`/guides/${l==='ja'?'':l.toLowerCase()+'/'}codex.html`;
const download=l=>l==='ja'?'/download.html':`/download/${l.toLowerCase()}.html`;
const routes=[...locales.flatMap(l=>[home(l),guide(l),download(l)]),'/for/engineers/','/for/en/engineers/','/for/','/for/en/sales/','/guides/simy-getting-started.html','/about.html','/contact.html','/privacy.html','/legal.html','/seller-info.html','/old/about.html','/old/index.html','/error.html','/404.html'];
function geometry(){
 const header=document.querySelector('.simy-header'),row=header.querySelector('.sh-row');
 const r=row.getBoundingClientRect();
 const controls=[...header.querySelectorAll('a,summary')].filter(el=>el.checkVisibility() && el.getBoundingClientRect().width);
 const clipped=controls.filter(el=>{const b=el.getBoundingClientRect();return b.left < -1 || b.right>innerWidth+1;}).map(el=>el.textContent.trim());
 const top=[header.querySelector('.sh-brand'),...header.querySelectorAll('.sh-desktop > *, .sh-actions > *')].filter(el=>el.checkVisibility()&&el.getBoundingClientRect().width).map(el=>({text:el.textContent.trim().slice(0,40),r:el.getBoundingClientRect().toJSON()}));
 const overlap=top.filter((el,i)=>i&&el.r.left<top[i-1].r.right-1).map(el=>el.text);
 const wrapped=[...header.querySelectorAll('.sh-desktop > a > span,.sh-desktop > details > summary > [data-sh-label],.sh-actions > a > span,.sh-language > summary > [data-sh-label]')].filter(el=>el.checkVisibility()&&el.getBoundingClientRect().width).filter(el=>{const range=document.createRange();range.selectNodeContents(el);return range.getClientRects().length>1;}).map(el=>el.textContent);
 const main=document.querySelector('main.page-frame,main.site-shell');const rail=main?Math.max(Math.abs(main.getBoundingClientRect().left-r.left),Math.abs(main.getBoundingClientRect().right-r.right)):null;
 return {width:innerWidth,header:header.getBoundingClientRect().toJSON(),row:r.toJSON(),clipped,overlap,wrapped,rail,documentOverflow:document.documentElement.scrollWidth-innerWidth};
}
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const origin=`http://127.0.0.1:${server.address().port}`;
 const browser=await chromium.launch({channel:process.env.PLAYWRIGHT_CHANNEL||'chrome',headless:true});
 try{
 const context=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce'});
 await context.addInitScript(()=>{localStorage.setItem('simy-cookies','0');});
 await context.route('**/*',route=>{const u=new URL(route.request().url());if(['/downloads/simy-cli/latest.json','/downloads/simy-cli/windows/latest.json'].includes(u.pathname)){report.fixtureRequests.push(u.pathname);return route.fulfill({status:200,contentType:'application/json',body:'null'});}if(u.pathname.includes('VITE_ANALYTICS_ENDPOINT')){report.fixtureRequests.push('unconfigured legacy analytics placeholder');return route.fulfill({status:204,body:''});}if(u.origin!==origin){report.externalRequests.push(u.origin+u.pathname);return route.fulfill({status:204,body:''});}return route.continue();});
 const page=await context.newPage();
 page.on('pageerror',err=>report.pageErrors.push({url:page.url(),message:err.message}));
 page.on('console',msg=>{if(msg.type()==='error')report.consoleErrors.push({url:page.url(),message:msg.text()});});
 page.on('requestfailed',req=>report.networkFailures.push({url:req.url(),error:req.failure()}));
 for(const route of routes){
  await page.goto(origin+route,{waitUntil:'networkidle'});
  assert.equal(await page.locator('.simy-header').count(),1,route);
  for(const width of widths){
   await page.setViewportSize({width,height:900});
   await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
   const g=await page.evaluate(geometry);report.views.push({route,...g});
   assert.deepEqual(g.clipped,[],`${route} ${width} clipped`);assert.deepEqual(g.overlap,[],`${route} ${width} overlap`);assert.deepEqual(g.wrapped,[],`${route} ${width} wrapped`);
   if(g.rail!==null)assert.ok(g.rail<=1,`${route} ${width} rail ${g.rail}`);
   assert.ok(g.header.top>=-1&&g.header.top<=2,`${route} ${width} header top ${g.header.top}`);
   for(const selector of ['.sh-brand','.sh-language > summary','.sh-signup'])assert.ok(await page.locator(selector).isVisible());
   if(width<1400){
    await page.locator('.sh-mobile > summary').click();
    assert.ok(await page.locator('.sh-mobile-panel [data-sh-link="login"]').isVisible());
    for(const group of ['product','work']){
     const summary=page.locator(`.sh-mobile-panel summary:has([data-sh-label="${group}"])`);await summary.click();
     const open=await page.evaluate(geometry);assert.deepEqual(open.clipped,[],`${route} ${width} mobile ${group}`);
     await summary.press('Escape');assert.equal(await summary.evaluate(el=>el.parentElement.open),false);
    }
    await page.locator('.sh-mobile > summary').press('Escape');
   }else{
    for(const group of ['product','work']){
     const summary=page.locator(`.sh-desktop summary:has([data-sh-label="${group}"])`);await summary.click();
     const open=await page.evaluate(geometry);assert.deepEqual(open.clipped,[],`${route} ${width} desktop ${group}`);
     await summary.press('Escape');assert.equal(await summary.evaluate(el=>el.parentElement.open),false);
     assert.equal(await summary.evaluate(el=>document.activeElement===el),true);
    }
   }
   await page.locator('.sh-language > summary').click();assert.equal(await page.locator('.sh-language a:visible').count(),6);
   assert.deepEqual((await page.evaluate(geometry)).clipped,[],`${route} ${width} language`);
   await page.mouse.click(1,500);assert.equal(await page.locator('.sh-language').getAttribute('open'),null);
   if([390,1440].includes(width)){
    const file=path.join(output,`${route.replace(/[^a-z0-9]/gi,'_')||'home'}-${width}.png`);await page.screenshot({path:file});report.screenshots.push(file);
   }
  }
 }
 // Actual navigations across every home/guide/download locale, not just hrefs.
 for(const make of [home,guide,download])for(const lang of locales){
  await page.goto(origin+make('en'),{waitUntil:'networkidle'});await page.locator('.sh-language > summary').click();
  await page.locator(`[data-sh-link="locale-${lang}"]`).click();await page.waitForURL(origin+make(lang),{waitUntil:'networkidle'});
  assert.equal(await page.locator('html').getAttribute('lang'),lang);
  report.operations.push({operation:'equivalent-language',source:make('en'),locale:lang,destination:new URL(page.url()).pathname});
 }
 // Route through the actual desktop groups/direct links, verifying destination fragment.
 await page.setViewportSize({width:1440,height:900});
 for(const key of ['overview','ai','how','apps','why','hub','engineers','sales','cases','pricing','guides','download']){
  await page.goto(origin+'/ja.html',{waitUntil:'networkidle'});
  const link=page.locator(`.sh-desktop [data-sh-link="${key}"]`);const href=await link.getAttribute('href');
  const group=link.locator('xpath=ancestor::details');if(await group.count())await group.locator('summary').click();
  await link.click();await page.waitForURL(origin+href,{waitUntil:"networkidle"});const u=new URL(page.url());
  if(u.hash)assert.equal(await page.locator(u.hash).count(),1);
  else assert.equal(await page.locator('.simy-header').count(),1);
  report.operations.push({operation:'destination',key,destination:u.pathname+u.hash});
 }
 // Legacy query translations, explicit account region, and missing-topic fallback.
 for(const route of ['/about.html','/privacy.html','/404.html','/old/about.html'])for(const lang of locales){
  await page.goto(origin+route+'?lang='+lang+'&region=gb',{waitUntil:'networkidle'});
  await page.waitForFunction(l=>document.documentElement.lang===l&&document.querySelector('.simy-header').dataset.shLocale===l,lang);
  assert.equal(await page.locator('#langBtn').count(),0);
  assert.equal(await page.locator('.sh-language [aria-current]').getAttribute('data-sh-link'),'locale-'+lang);
  for(const key of ['login','signup']){
   const a=page.locator(`.sh-actions > [data-sh-link="${key}"]`);const url=new URL(await a.getAttribute('href'));
   assert.equal(url.searchParams.get('region'),'gb');assert.equal(url.searchParams.get('lang'),lang);
  }
  report.operations.push({operation:'legacy-query',route,lang,region:'gb'});
 }
 await page.goto(origin+'/guides/simy-getting-started.html',{waitUntil:'networkidle'});await page.locator('.sh-language > summary').click();
 const fallback=page.locator('[data-sh-link="locale-fr"]');assert.match(await fallback.innerText(),/英語/);await fallback.click();await page.waitForURL(origin+'/guides/en/simy-getting-started.html',{waitUntil:'networkidle'});
 assert.equal(await page.locator('html').getAttribute('lang'),'en');report.operations.push({operation:'missing-topic-fallback',destination:'/guides/en/simy-getting-started.html'});
 // Keyboard, native disclosure recovery, focus leaving, and 200% text scaling.
 await page.goto(origin+'/ja.html',{waitUntil:'networkidle'});const language=page.locator('.sh-language > summary');await language.focus();await language.press('Enter');await page.locator('.sh-language a').first().focus();await page.keyboard.press('Escape');assert.ok(await language.evaluate(el=>el===document.activeElement));
 await language.press('Space');await page.locator('.sh-signup').focus();await page.waitForTimeout(50);assert.equal(await page.locator('.sh-language').getAttribute('open'),null);
 await page.setViewportSize({width:720,height:450});assert.deepEqual((await page.evaluate(geometry)).clipped,[]);report.operations.push({operation:'200-percent-equivalent-viewport',width:720});
 await context.close();
 const nojs=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:900}});const np=await nojs.newPage();
 for(const route of ['/ja.html','/guides/en/codex.html','/download/fr.html','/for/engineers/','/privacy.html','/error.html']){
  await np.goto(origin+route);await np.locator('.sh-mobile > summary').click();await np.locator('.sh-mobile-panel summary').first().click();
  assert.ok(await np.locator('.sh-mobile-panel [data-sh-link="overview"]').isVisible());
  await np.locator('.sh-mobile-panel [data-sh-link="guides"]').click();assert.ok(new URL(np.url()).pathname.startsWith('/guides/'));
  await np.locator('.sh-language > summary').click();await np.locator('[data-sh-link="locale-en"]').click();
  assert.equal(await np.locator('html').getAttribute('lang'),'en');report.operations.push({operation:'no-js',source:route,destination:new URL(np.url()).pathname});
 }
 await nojs.close();report.cleanupResidualCount=0;
 assert.deepEqual(report.pageErrors,[]);assert.deepEqual(report.consoleErrors,[]);assert.deepEqual(report.networkFailures,[]);
 report.status='passed';
 }catch(e){report.status='failed';report.failure=e.stack;throw e;}finally{await browser.close();server.close();fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));}
 console.log(JSON.stringify({status:report.status,views:report.views.length,operations:report.operations.length,screenshots:report.screenshots.length}));
})().catch(e=>{console.error(e.message);process.exitCode=1;});
