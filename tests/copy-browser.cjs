// NODE_PATH=<existing Playwright runtime> node tests/copy-browser.cjs
// Uses only a private loopback preview and synthetic input; never sends enquiries.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
const site = path.join(root, 'site');
const output = path.join(root, 'docs/pr-evidence/copy-clarity');
const dicts = Object.fromEntries(fs.readdirSync(path.join(site, 'lang/home-dom')).filter(f=>f.endsWith('.json'))
  .map(f=>[f.slice(0,-5),JSON.parse(fs.readFileSync(path.join(site,'lang/home-dom',f)))]));
const types = {'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.png':'image/png','.svg':'image/svg+xml'};
const server = http.createServer((req,res)=>{
  const url = new URL(req.url,'http://localhost');
  let pathname;
  try { pathname = decodeURIComponent(url.pathname); }
  catch { res.writeHead(400).end(); return; }
  const file = path.resolve(site,'.'+pathname+(pathname.endsWith('/')?'index.html':''));
  if (!file.startsWith(site+path.sep)) return res.writeHead(403).end();
  fs.readFile(file,(error,data)=>error?res.writeHead(404).end():res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream'}).end(data));
});
const report = {locales:Object.keys(dicts),contactStates:[],demoStates:[],aboutStates:[],errors:[],checks:[]};
(async()=>{
  fs.mkdirSync(output,{recursive:true});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({channel:'chrome'});
  try {
    const page = await browser.newPage();
    page.on('pageerror',error=>report.errors.push(error.message));
    await page.route('**/*',route=>{
      const url = route.request().url();
      if(url.startsWith(origin)||url.startsWith('data:')||/\.woff2?(\?|$)/.test(url)) return route.continue();
      return route.abort();
    });
    for (const width of [1440,390,320]) {
      await page.setViewportSize({width,height:1000});
      for(const [locale,dict] of Object.entries(dicts)) {
        await page.goto(`${origin}/contact.html?lang=${locale}`);
        await page.waitForFunction(value=>document.querySelector('#root h1')?.textContent===value,dict['Tell us what you need.']);
        const hints=['Your name','Company name',"Tell us about your team, your workflows, and what you're hoping to achieve with SIMY."];
        for(const [id,key] of [['name',hints[0]],['company',hints[1]],['message',hints[2]]]) {
          await page.waitForFunction(({id,value})=>document.getElementById('contact-'+id)?.getAttribute('placeholder')===value,{id,value:dict[key]||key});
        }
        assert.equal(await page.locator('html').getAttribute('dir'),locale==='ar'?'rtl':'ltr');
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Contact overflow: ${locale} ${width}`);
        const fields = await page.locator('#root label').evaluateAll(labels=>labels.map(l=>({for:l.htmlFor,found:!!document.getElementById(l.htmlFor)})));
        assert.equal(fields.length,5);assert.ok(fields.every(f=>f.for&&f.found));
        report.contactStates.push({locale,width,heading:dict['Tell us what you need.'],labels:fields.length});
        if((locale==='ja'&&width===1440)||(locale==='en'&&width===390)||(locale==='ar'&&width===390)) {
          await page.screenshot({path:path.join(output,`contact-${locale}-${width}.png`),fullPage:true});
        }
      }
    }
    await page.setViewportSize({width:1440,height:1000});
    await page.goto(`${origin}/contact.html?lang=ja`);
    await page.locator('#contact-name').fill('Synthetic visitor');
    await page.locator('#contact-message').fill('Synthetic enquiry; do not send.');
    for(const locale of ['fr','en','ar','ja']) {
      await page.evaluate(lang=>window.simyI18n.setLang(lang),locale);
      await page.waitForFunction(value=>document.querySelector('#root h1')?.textContent===value,dicts[locale]['Tell us what you need.']);
      await page.waitForFunction(value=>document.querySelector('#contact-name').placeholder===value,dicts[locale]['Your name']||'Your name');
      assert.equal(await page.locator('#contact-name').inputValue(),'Synthetic visitor');
      assert.equal(await page.locator('#contact-message').inputValue(),'Synthetic enquiry; do not send.');
    }
    await page.locator('label[for="contact-name"]').click();
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(()=>document.activeElement.id),'contact-company');
    report.checks.push('JA→FR→EN→AR→JA preserves typed input and translated hints; labels and keyboard focus work');
    // A failed translation request must leave readable English hints, and reload can recover.
    await page.route('**/lang/home-dom/fr.json*',route=>route.fulfill({status:503,body:''}));
    await page.goto(`${origin}/contact.html?lang=fr`);
    await page.waitForFunction(()=>document.querySelector('#contact-name')?.placeholder==='Your name');
    assert.equal(await page.locator('#root h1').innerText(),'Tell us what you need.');
    await page.unroute('**/lang/home-dom/fr.json*');
    await page.reload();
    await page.waitForFunction(value=>document.querySelector('#root h1')?.textContent===value,dicts.fr['Tell us what you need.']);
    report.checks.push('HTTP 503 dictionary failure shows English fallback; reload restores French');
    const demoKey='Meet a product manager at a 150-person tech company.';
    for(const width of [1440,390]) {
      await page.setViewportSize({width,height:1000});
      for(const [locale,dict] of Object.entries(dicts)) {
        await page.goto(`${origin}/demo.html?lang=${locale}`);
        await page.waitForFunction(value=>document.querySelector('h1')?.textContent.includes(value),dict[demoKey]);
        await page.waitForFunction(value=>document.body.textContent.includes(value),dict['Meeting ends. Roadmap ready.']);
        await page.waitForFunction(value=>document.body.textContent.includes(value),dict['Before standup']);
        await page.waitForFunction(value=>document.querySelector('h1 .accent')?.textContent===value,dict['See how she uses SIMY.']);
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Demo overflow ${locale} ${width}`);
        const copy=JSON.parse(fs.readFileSync(path.join(site,'lang',locale+'.json')));
        await page.waitForFunction(value=>document.querySelector('[data-i18n="footer.tagline"]')?.textContent===value,copy['footer.tagline']);
        report.demoStates.push({locale,width});
        if(locale==='ja'&&width===1440) await page.screenshot({path:path.join(output,'demo-ja-1440.png'),fullPage:true});
      }
    }
    for(const width of [1440,390]) {
      await page.setViewportSize({width,height:1000});
      for(const locale of Object.keys(dicts)) {
        const copy=JSON.parse(fs.readFileSync(path.join(site,'lang',locale+'.json')));
        await page.goto(`${origin}/about.html?lang=${locale}`);
        for(const key of ['about.challenge.p2','about.solution.p3','about.valB.h','about.valB.p2']) {
          await page.waitForFunction(({key,value})=>document.querySelector(`[data-i18n="${key}"]`)?.textContent===value,{key,value:copy[key]});
        }
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`About overflow ${locale} ${width}`);
        report.aboutStates.push({locale,width});
        if(locale==='ja'&&width===390) await page.screenshot({path:path.join(output,'about-ja-390.png'),fullPage:true});
      }
    }
    for(const [file,key] of [['about.html','about.valB.h'],['careers.html','careers.perk3H'],['how-it-works.html','how.step4H']]) {
      await page.goto(`${origin}/${file}?lang=ja`);
      const dict=JSON.parse(fs.readFileSync(path.join(site,'lang/ja.json')));
      await page.waitForFunction(({key,value})=>document.querySelector(`[data-i18n="${key}"]`)?.textContent===value,{key,value:dict[key]});
      report.checks.push(`${file}: Japanese editorial copy rendered`);
    }
    for(const locale of ['en','ja']) {
      await page.goto(`${origin}/old/demo.html?lang=${locale}`);
      const copy=JSON.parse(fs.readFileSync(path.join(site,'lang',locale+'.json')));
      await page.waitForFunction(value=>document.querySelector('[data-i18n="footer.tagline"]')?.textContent===value,copy['footer.tagline']);
      report.checks.push(`old/demo.html: ${locale} shared footer rendered`);
      await page.screenshot({path:path.join(output,`old-demo-${locale}.png`),fullPage:true});
    }
    assert.deepEqual(report.errors,[]);
    fs.writeFileSync(path.join(output,'browser-results.json'),JSON.stringify(report,null,2)+'\n');
    console.log(`PASS: ${report.contactStates.length} contact and ${report.demoStates.length} demo and ${report.aboutStates.length} about states; locale switching, keyboard labels and failure/reload recovery; no page errors`);
  } finally {await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);server.close();process.exitCode=1});
