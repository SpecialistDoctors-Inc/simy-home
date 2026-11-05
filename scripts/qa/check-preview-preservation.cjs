// Run with SIMY_BROWSER_PACKAGE pointing to an existing Playwright installation.
const {chromium}=require(process.env.SIMY_BROWSER_PACKAGE||'playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.env.SIMY_EDITOR_SOURCE||'site/preview-edit.js','utf8');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage();
 page.setDefaultTimeout(3000);
 // Serve a real local pixel for geometry assertions; aborted images render fallback alt text.
 await page.route('https://fixture.test/**',route=>route.request().url().endsWith('/clinic-hero.jpg')?route.fulfill({contentType:'image/png',body:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aP1UAAAAASUVORK5CYII=','base64')}):route.abort());
 const results=[];
 async function check(name,html,verify){
  try{
   await page.setContent(html);await page.addScriptTag({content:source});
   const indexed=await page.evaluate(()=>SimyPreviewEdit.index(document.documentElement.outerHTML));
   await page.setContent(indexed);await verify(indexed);results.push({name,passed:true});
  }catch(error){results.push({name,passed:false,error:error.message});}
 }
 try{
  await check('long page keeps news and late editable text within the existing budget',
   '<html><body>'+Array.from({length:25},(_,i)=>`<section><h2>Section ${i}</h2><p>${'x'.repeat(1800)}</p></section>`).join('')+'<section><h2>お知らせ</h2><ul><li>2026年10月30日 '+ '診療時間は通常どおりです'.repeat(150)+' </li></ul><p>末尾の予約案内</p></section></body></html>',
   async indexed=>{
    const result=await page.evaluate(indexed=>{
     const api=SimyPreviewEdit,nodes=api.inventory(indexed,document),news=nodes.find(n=>n.kind==='news');
     let edited='';if(news)edited=api.applyPlan(indexed,{status:'edit',operations:[{type:'insert_notice',target:news.id,title:'午後休診',body:'明日は午後休診です',date:'2026-10-31'}]}).html;
     return {nodes,edited};
    },indexed);
    assert(result.nodes.some(n=>n.kind==='news'),'news target missing');
    assert(result.nodes.some(n=>n.kind==='text'&&n.text==='末尾の予約案内'),'late leaf text missing');
    assert.equal(result.nodes.filter(n=>n.tag==='p'&&n.text.startsWith('xxx')).length,25,'long paragraphs must remain targetable');
    assert(result.nodes.filter(n=>n.kind==='text').every(n=>n.text.length<=600));
    assert(result.nodes.filter(n=>n.kind==='element').every(n=>n.text.length<=120));
    assert(result.edited.includes('明日は午後休診です'),'notice cannot be applied');
    assert(result.nodes.length<=220);assert(result.nodes.reduce((n,x)=>n+JSON.stringify(x).length,0)<=35000);
   });
  await check('redesign preserves nested hero photography and repeated redesign stays idempotent',
   '<html><head><style>.hero{background-image:url("https://fixture.test/hero.jpg")}</style></head><body><section class="hero"><h1>診療案内</h1><p>予約について</p></section></body></html>',
   async indexed=>{
    // Both operations see the original live CSS; the duplicate marker must do the work.
    const changed=await page.evaluate(indexed=>{
     const operation={type:'redesign',target:'e0',property:'warm',value:'#146854'};
     return SimyPreviewEdit.applyPlan(indexed,{status:'edit',operations:[operation,operation]},[],document).html;
    },indexed);
    await page.setContent(changed);
    assert.equal(await page.locator('.hero img').count(),1);
    assert.equal(await page.locator('.hero img').getAttribute('src'),'https://fixture.test/hero.jpg');
    assert.equal(await page.locator('.hero h1').textContent(),'診療案内');
    assert.equal(await page.locator('.hero p').textContent(),'予約について');
    const again=await page.evaluate(changed=>SimyPreviewEdit.applyPlan(changed,{status:'edit',operations:[{type:'redesign',target:'e0',property:'editorial',value:'#146854'}]},[],document).html,changed);
    await page.setContent(again);assert.equal(await page.locator('.hero img').count(),1);
    // Undo restores the saved original HTML, including its stylesheet and heading.
    await page.setContent(indexed);assert.equal(await page.locator('.hero img').count(),0);
    assert((await page.locator('.hero').evaluate(e=>getComputedStyle(e).backgroundImage)).includes('hero.jpg'));
   });
  await check('image inventory keeps usage, source, dimensions and position with bounded text',
   '<html><body><section class="hero"><img id="clinic-hero" class="photo" src="https://fixture.test/clinic-hero.jpg" alt="院内写真" style="width:240px;height:120px"></section></body></html>',
   async indexed=>{
    const image=await page.evaluate(indexed=>SimyPreviewEdit.inventory(indexed,document).find(n=>n.kind==='image'),indexed);
    assert(image,'image target missing');
    for(const expected of ['画像の表示サイズ:240×120px','元寸法:1x1','ページ上端から:','用途:clinic-hero photo hero','素材:clinic-hero.jpg'])assert(image.context.includes(expected),expected+' missing');
    assert(image.context.length<=300);
   });
  await check('existing image reuse and insertion survive preview preservation refresh',
   '<html><body><section><article class="feature"><h2>診療案内</h2><img src="https://fixture.test/original.jpg" alt="院内"></article><article class="feature"><h2>予約案内</h2><p>予約方法はこちらです。</p></article></section></body></html>',
   async indexed=>{
    const result=await page.evaluate(indexed=>{
     const api=SimyPreviewEdit,doc=new DOMParser().parseFromString(indexed,'text/html'),image=doc.querySelector('img'),card=doc.querySelectorAll('article')[1];
     const nodes=api.inventory(indexed,document),source=image.getAttribute('data-simy-edit-id'),target=card.getAttribute('data-simy-edit-id');
     const inserted=api.applyPlan(indexed,{status:'edit',operations:[{type:'insert_image',target,value:source,title:'予約案内の院内写真'}]},[],document).html;
     const insertedDoc=new DOMParser().parseFromString(inserted,'text/html'),newImage=insertedDoc.querySelectorAll('article')[1].querySelector('img');
     return {hasCard:nodes.some(n=>n.id===target&&n.kind==='element'),insertedSource:newImage?.getAttribute('src'),insertedAlt:newImage?.getAttribute('alt'),originalText:insertedDoc.querySelectorAll('article')[1].textContent};
    },indexed);
    assert(result.hasCard,'card target missing');
    assert.equal(result.insertedSource,'https://fixture.test/original.jpg');
    assert.equal(result.insertedAlt,'予約案内の院内写真');
    assert(result.originalText.includes('予約方法はこちらです。'));
   });
 }finally{await browser.close();}
 console.log(JSON.stringify(results,null,2));if(results.some(r=>!r.passed))process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
