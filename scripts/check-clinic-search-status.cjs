// Synthetic browser regression; this is separate from real production acceptance.
const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{const b=await chromium.launch({channel:'chrome',headless:true});try{const p=await b.newPage();
const asset=path.resolve(__dirname,'../site/assets/clinic-service-v2/cd840cc17fa055.js');
await p.route('**/33a5d8e6590c1d.js',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(asset,'utf8')}));
await p.route('**/api/report-registration',r=>r.fulfill({status:202,json:{status:'registered',receiptId:r.request().postDataJSON().id}}));
for(const width of [1440,390]){await p.setViewportSize({width,height:1000});for(const measured of [false,true]){
 await p.goto(process.env.CLINIC_URL||'http://127.0.0.1:18972/hp-management/clinic-service-v2.html');
 const report={url:'https://example.com/',checkedAt:new Date().toISOString(),completion:'partial',completionReason:'追加取得は未完了',technologies:[],scripts:{libraries:[],resources:[]},findings:measured?[{id:'seo-title',title:'SEO / 検索結果の見出し',state:'observed',summary:'記載を確認しました。',evidence:'テスト医院',fix:'',reference:''},{id:'sem-performance',title:'SEM / 検索広告の成果',state:'unknown',summary:'広告データは未確認です。',evidence:'管理画面未接続',fix:'',reference:''}]:[]};
 await p.evaluate(r=>{renderReport(r);document.querySelector('#diagnosis-state').hidden=false},report);
 await p.locator('#report-email-address').fill('test@example.com');await p.locator('#report-clinic-name').fill('架空医院');await p.locator('#report-contact-name').fill('テスト');await p.locator('.report-email-consent input').check();await p.locator('.report-email-form button').click();await p.locator('.report-unlocked').waitFor();
 const section=p.locator('.report-search-checks');assert(await section.isVisible());const text=await section.innerText();assert(text.includes(measured?'テスト医院':'この診断では未確認'));assert(text.includes('未確認'));assert.match(await p.locator('#diagnosis-state-title').innerText(),/一部/);assert.match(await p.locator('.report-counts strong').first().innerText(),/未確認/);
 assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 if(measured){const boxes=await section.locator('article').evaluateAll(es=>es.map(e=>({left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right})));assert(Math.abs(boxes[0].left-boxes[1].left)<=1);assert(Math.abs(boxes[0].right-boxes[1].right)<=1);}
 if(width===1440&&!measured){const d=p.waitForEvent('download',{timeout:120000});await p.locator('.report-download-dock button').click();await(await d).saveAs('/tmp/clinic-search-status.pdf');}
 await section.screenshot({path:`/tmp/clinic-search-status-${width}-${measured}.png`});
 console.log(`${width}: measured=${measured}; unverified scope, partial title, zero safety and overflow passed`);
}}
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
