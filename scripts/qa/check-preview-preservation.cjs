// Run with SIMY_BROWSER_PACKAGE pointing to an existing Playwright installation.
const {chromium}=require(process.env.SIMY_BROWSER_PACKAGE||'playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.env.SIMY_EDITOR_SOURCE||'site/preview-edit.js','utf8');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage();
 page.setDefaultTimeout(3000);
 await page.route('https://fixture.test/**',route=>route.abort());
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
   '<html><body>'+Array.from({length:25},(_,i)=>`<section><h2>Section ${i}</h2><p>${'x'.repeat(1800)}</p></section>`).join('')+'<section><h2>お知らせ</h2><ul><li>'+ '診療時間は通常どおりです'.repeat(150)+' </li></ul><p>末尾の予約案内</p></section></body></html>',
   async indexed=>{
    const result=await page.evaluate(indexed=>{
     const api=SimyPreviewEdit,nodes=api.inventory(indexed,document),news=nodes.find(n=>n.kind==='news');
     let edited='';if(news)edited=api.applyPlan(indexed,{status:'edit',operations:[{type:'insert_notice',target:news.id,title:'午後休診',body:'明日は午後休診です',date:'2026-10-31'}]}).html;
     return {nodes,edited};
    },indexed);
    assert(result.nodes.some(n=>n.kind==='news'),'news target missing');
    assert(result.nodes.some(n=>n.kind==='text'&&n.text==='末尾の予約案内'),'late leaf text missing');
    assert.equal(result.nodes.filter(n=>n.tag==='p'&&n.text.startsWith('xxx')).length,25,'long paragraphs must remain targetable');
    assert(result.edited.includes('明日は午後休診です'),'notice cannot be applied');
    assert(result.nodes.length<=220);assert(result.nodes.reduce((n,x)=>n+JSON.stringify(x).length,0)<=35000);
   });
  await check('redesign preserves nested hero photography and repeated redesign stays idempotent',
   '<html><head><style>.hero{background-image:url("https://fixture.test/hero.jpg")}</style></head><body><section class="hero"><h1>診療案内</h1><p>予約について</p></section></body></html>',
   async indexed=>{
    const changed=await page.evaluate(indexed=>SimyPreviewEdit.applyPlan(indexed,{status:'edit',operations:[{type:'redesign',target:'e0',property:'warm',value:'#146854'}]},[],document).html,indexed);
    await page.setContent(changed);
    assert.equal(await page.locator('.hero img').getAttribute('src'),'https://fixture.test/hero.jpg');
    assert.equal(await page.locator('.hero h1').textContent(),'診療案内');
    assert.equal(await page.locator('.hero p').textContent(),'予約について');
    const again=await page.evaluate(changed=>SimyPreviewEdit.applyPlan(changed,{status:'edit',operations:[{type:'redesign',target:'e0',property:'editorial',value:'#146854'}]},[],document).html,changed);
    await page.setContent(again);assert.equal(await page.locator('.hero img').count(),1);
    // Undo restores the saved original HTML, including its stylesheet and heading.
    await page.setContent(indexed);assert.equal(await page.locator('.hero img').count(),0);
    assert((await page.locator('.hero').evaluate(e=>getComputedStyle(e).backgroundImage)).includes('hero.jpg'));
   });
 }finally{await browser.close();}
 console.log(JSON.stringify(results,null,2));if(results.some(r=>!r.passed))process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
