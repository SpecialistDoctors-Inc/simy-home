const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
// NODE_PATH=<Playwright installation> node scripts/check-unified-header.cjs
// Optional SITE_URL checks the published site; no account actions are submitted.
const root=path.resolve(__dirname,'..'),site=path.join(root,'site');
const out=process.env.HEADER_REPORT_DIR||path.join(root,'docs/shared-header/screenshots');
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const server=http.createServer((req,res)=>{const url=new URL(req.url,'http://localhost');let file=path.join(site,url.pathname);if(url.pathname.endsWith('/'))file=path.join(file,'index.html');fs.readFile(file,(err,data)=>{if(err){res.writeHead(404).end();return;}res.setHeader('content-type',({'.html':'text/html','.css':'text/css','.js':'text/javascript','.svg':'image/svg+xml','.png':'image/png'})[path.extname(file)]||'application/octet-stream');res.end(data);});});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const base=process.env.SITE_URL||`http://127.0.0.1:${server.address().port}`;
 let browser;
 try {
 browser=await chromium.launch({channel:'chrome'});
 const page=await browser.newPage({reducedMotion:'reduce'});
 // The header uses bundled assets and system fonts. Third-party analytics and
 // status widgets do not belong to this geometry audit and may be unavailable.
 await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());const report={base,checks:[],errors:[],pageErrors:[]};
 page.on('pageerror',e=>report.pageErrors.push({url:page.url(),message:e.message}));
 const files=fs.readdirSync(site,{recursive:true}).filter(f=>f.endsWith('.html')&&fs.readFileSync(path.join(site,f),'utf8').includes('class="simy-header"')).sort();
 for(const width of [320,390,960,1440]){
 await page.setViewportSize({width,height:900});const references={};
 for(const locale of ['en','ja','hi','es','fr','zh-Hans']){await page.goto(base+(locale==='en'?'/':'/'+locale+'.html'));await page.evaluate(()=>document.fonts.ready);references[locale]=await page.locator('.simy-header').evaluate(h=>{const rect=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {left:r.left,right:r.right,top:r.top,height:r.height,font:s.font,color:s.color,background:s.backgroundColor,border:s.borderBottom,textAlign:s.textAlign,letterSpacing:s.letterSpacing,textTransform:s.textTransform};};return {header:rect(h),items:[...h.querySelectorAll('.sh-brand,.sh-navigation>*,.sh-account>*,.sh-stores>*')].map(rect),count:document.querySelectorAll('.simy-header').length};});}
 for(const file of ['index.html',...files.filter(f=>f!=='index.html')]){
 await page.goto(base+'/'+(file==='index.html'?'':file));await page.evaluate(()=>document.fonts.ready);
 const state=await page.locator('.simy-header').evaluate(h=>{
 const rect=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {left:r.left,right:r.right,top:r.top,height:r.height,font:s.font,color:s.color,background:s.backgroundColor,border:s.borderBottom,textAlign:s.textAlign,letterSpacing:s.letterSpacing,textTransform:s.textTransform};};
 return {header:rect(h),items:[...h.querySelectorAll('.sh-brand,.sh-navigation>*,.sh-account>*,.sh-stores>*')].map(rect),count:document.querySelectorAll('.simy-header').length};});
 const locale=await page.locator('html').getAttribute('lang');const reference=references[locale]||references.en;
 try{assert.equal(state.count,1);assert.equal(state.header.left,0);assert.equal(state.header.right,width);assert.deepEqual(state,reference);}catch(e){report.errors.push({file,width,state,expected:reference,message:e.message.slice(0,200)});}
 if(['index.html','old/about.html','old/404.html','for/en/financial-planners/index.html'].includes(file)&&[390,1440].includes(width))await page.screenshot({path:path.join(out,file.replaceAll('/','-')+'-'+width+'.png')});
 await page.locator('.sh-navigation summary').first().click();assert.ok(await page.locator('.simy-header').getByRole('link',{name:'Overview',exact:true}).isVisible());await page.keyboard.press('Escape');assert.ok(!await page.locator('.simy-header').getByRole('link',{name:'Overview',exact:true}).isVisible(),'Escape closes the menu');
 await page.evaluate(()=>window.scrollTo(0,600));
 report.checks.push({file,width});
 }
 }
 fs.writeFileSync(path.join(out,process.env.SITE_URL?'production.json':'local.json'),JSON.stringify(report,null,2));
 console.log(JSON.stringify({checks:report.checks.length,errors:report.errors.length,pageErrors:report.pageErrors},null,2));
 assert.equal(report.errors.length,0,'Header differences: see the saved report');
 assert.deepEqual(report.pageErrors,[]);
 }finally{if(browser)await browser.close();server.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
