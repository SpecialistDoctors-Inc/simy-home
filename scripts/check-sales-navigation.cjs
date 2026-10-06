// Bundled header navigation only; external services are inert, no account writes.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
(async()=>{
 const site=path.resolve(__dirname,'../site');
 const out=process.env.HEADER_REPORT_DIR;
 const server=http.createServer((req,res)=>{
  const u=new URL(req.url,'http://localhost');
  const file=path.resolve(site,'.'+u.pathname+(u.pathname.endsWith('/')?'index.html':''));
  if(!file.startsWith(site+path.sep))return res.writeHead(403).end();
  fs.readFile(file,(err,data)=>{
   if(err)return res.writeHead(404).end();
   res.setHeader('Content-Type',({'.html':'text/html; charset=utf-8','.js':'text/javascript','.css':'text/css','.png':'image/png','.svg':'image/svg+xml'})[path.extname(file)]||'application/octet-stream');res.end(data);
  });
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const base=`http://127.0.0.1:${server.address().port}`;
 let browser;const errors=[],checks=[];
 try{
  browser=await chromium.launch({channel:'chrome'});
  for(const js of [true,false])for(const width of [390,1440]){
   const page=await browser.newPage({javaScriptEnabled:js,viewport:{width,height:900}});
   page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/*',r=>new URL(r.request().url()).origin===base?r.continue():r.fulfill({status:204,body:''}));
   for(const locale of ['ja','en','fr','es','hi','zh-Hans']){
    await page.goto(base+(locale==='en'?'/':`/${locale}.html`));
    if(await page.locator('.sh-menu-toggle').isVisible())await page.locator('.sh-menu-toggle').click();
    await page.locator('.sh-navigation summary').nth(1).click();
    const sales=page.locator('.sh-navigation').getByRole('link',{name:/^For sales/});
    assert.ok(await sales.isVisible());
    const box=await sales.boundingBox();assert.ok(box.x>=0&&box.x+box.width<=width);
    if(out&&locale==='ja'){fs.mkdirSync(out,{recursive:true});await page.screenshot({path:path.join(out,`sales-ja-${width}-${js?'js':'nojs'}.png`)});}
    const expected=locale==='ja'?'/for/sales/':'/for/en/sales/';
    assert.equal(await sales.getAttribute('href'),expected);
    await sales.click();await page.waitForLoadState();assert.equal(new URL(page.url()).pathname,expected);assert.ok(await page.locator('h1').isVisible());
    checks.push({locale,width,js,destination:expected});
   }
   if(js){
    await page.goto(base+'/about.html?lang=fr');
    for(const locale of ['fr','ja','en']){
     if(await page.locator('html').getAttribute('lang')!==locale){await page.locator('.sh-language summary').click();await page.locator(`[data-locale-option="${locale}"]`).click();}
     await page.waitForFunction(l=>document.documentElement.lang===l,locale);
     const link=page.locator('.sh-navigation a[href*="/sales/"]');assert.equal(await link.count(),1);
     assert.equal(new URL(await link.getAttribute('href'),base).pathname,locale==='ja'?'/for/sales/':'/for/en/sales/');
     assert.equal(await link.textContent(),['ja','en'].includes(locale)?'For sales':'For sales (English)');
    }
   }
   await page.close();
  }
  assert.deepEqual(errors,[]);
  if(out)fs.writeFileSync(path.join(out,'sales-navigation.json'),JSON.stringify({checks,errors},null,2));
  console.log(`PASS ${checks.length} sales navigation flows; JS/no-JS, six locales, desktop/mobile, legacy language switching`);
 }finally{if(browser)await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
