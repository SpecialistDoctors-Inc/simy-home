// NODE_PATH may point to the workspace's bundled Playwright runtime.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path');
(async()=>{const browser=await chromium.launch({headless:true,channel:'chrome'});const page=await browser.newPage();
for(const tag of ['dl','ul','ol']){
 await page.setContent('<style>.notice-heading{font:700 21px/1.5 serif;color:#426a38;padding:8px 0}.notice-body{font:16px/1.7 serif;color:#333;border-bottom:1px dashed #ccc;padding:12px 0}.date{font-size:18px}</style><h2>お知らせ</h2><'+tag+'>'+(tag==='dl'?'<dt class="notice-heading"><span class="date">2026.10.29</span><span class="title">以前のお知らせ</span></dt><dd class="notice-body"><p>以前の本文</p></dd>':'<li class="notice-item"><h3 class="notice-heading"><span class="date">2026.10.29</span><span class="title">以前のお知らせ</span></h3><p class="notice-body">以前の本文</p></li>')+'</'+tag+'>');
 await page.addScriptTag({path:path.resolve('site/preview-edit.js')});
 const checked=await page.evaluate(tag=>{const html=SimyPreviewEdit.index(document.documentElement.outerHTML),inventory=SimyPreviewEdit.inventory(html),target=inventory.find(x=>x.kind==='news');if(!target)throw Error('No news');const result=SimyPreviewEdit.applyPlan(html,{status:'edit',summary:'休診案内を追加しました',operations:[{type:'insert_notice',target:target.id,title:'休診のお知らせ',body:'明日は休診です。',date:'2026-11-01'}]});document.open();document.write(result.html);document.close();const nodes=document.querySelectorAll('.notice-heading'),bodies=document.querySelectorAll('.notice-body'),keys=['fontSize','fontFamily','lineHeight','paddingTop','paddingBottom','borderBottomStyle','color'];const compare=(a,b)=>keys.every(k=>getComputedStyle(a)[k]===getComputedStyle(b)[k]);return{sameHeading:compare(nodes[0],nodes[1]),sameBody:compare(bodies[0],bodies[1]),nestedDate:!!nodes[0].querySelector('.date'),title:nodes[0].querySelector('.title').textContent,date:nodes[0].querySelector('.date').textContent.trim(),highlight:!!document.querySelector('#simy-edit-highlight'),outline:getComputedStyle(nodes[0]).outlineStyle};},tag);
 assert(checked.sameHeading&&checked.sameBody&&checked.nestedDate,JSON.stringify(checked));assert.equal(checked.title,'休診のお知らせ');assert.equal(checked.date,'2026.11.01');assert.equal(checked.highlight,false);assert.equal(checked.outline,'none');console.log(tag,'existing structure and computed styles retained');
}
await browser.close();})().catch(e=>{console.error(e);process.exit(1)});

(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'}),page=await browser.newPage();
 const cases=[
  ['category-badge','<ul class="info-list"><li><span class="info-list-date">2026.10.29</span><p class="info-list-cat"><a><span>診療時間</span></a></p><span class="info-list-text"><a>以前のタイトル</a></span></li><li><span>2026.10.28</span><p class="info-list-cat">お知らせ</p><span>以前のタイトル2</span></li></ul>'],
  ['japanese-date-span','<dl><dt><span class="date">2026年10月1日</span><span class="title">以前のタイトル</span></dt><dd>以前の本文</dd></dl>'],
  ['japanese-date-column','<dl><dt>2026年10月1日</dt><dd><a>以前のタイトル</a></dd></dl>'],
  ['date-column','<dl><dt>2026/10/29</dt><dd><h4><a>以前のタイトル</a></h4></dd></dl>'],
  ['cards','<div class="news-list"><article class="card"><time>2026/10/29</time><h3>以前のタイトル</h3><p>以前の本文</p></article><article class="card"><time>2026/10/28</time><h3>その前のタイトル</h3><p>その前の本文</p></article></div>'],
  ['wrapped-dl','<div id="topicsIn"><dl><a><dt>2026.10.29</dt><dd>以前のタイトル</dd></a></dl><dl><a><dt>2026.10.28</dt><dd>以前のタイトル2</dd></a></dl></div>'],
  ['single-card','<div class="news"><div class="inner-news"><p>2026年10月29日</p><p>以前のお知らせ</p></div></div>'],
  ['undated-dl','<dl><dt class="news_title">休診のお知らせ</dt><dd class="news_body">明日は休診です</dd></dl>'],
  ['builder','<div class="news-list"><div class="post"><div class="news__wrapper"><div><time>2026/10/29</time><h4>以前のタイトル</h4></div></div></div><div class="post"><div class="news__wrapper"><div><time>2026/10/28</time><h4>以前のタイトル2</h4></div></div></div></div>']
 ];
 for(const[name,markup]of cases){
  await page.setContent('<style>h3,h4,dt{font:700 20px/1.6 serif;color:#53722a}p,dd{font:16px/1.8 serif;border-bottom:1px dashed #ccc}article{padding:12px}</style><section><h2>今週の伝言</h2>'+markup+'</section><section><h2>医院概要</h2><dl><dt>所在地</dt><dd>東京都</dd></dl></section>');
  await page.addScriptTag({path:path.resolve('site/preview-edit.js')});
  const result=await page.evaluate(()=>{const html=SimyPreviewEdit.index(document.documentElement.outerHTML),nodes=SimyPreviewEdit.inventory(html),news=nodes.filter(n=>n.kind==='news');if(news.length!==1)return{error:'Expected one collection',news};const plan={status:'edit',operations:[{type:'insert_notice',target:news[0].id,title:'午後休診のご案内',body:'11月1日は午後休診です。',date:'2026-10-31'}]},final=SimyPreviewEdit.applyPlan(html,plan).html,doc=new DOMParser().parseFromString(final,'text/html');return{news:news[0],title:doc.body.textContent.includes('午後休診のご案内'),body:doc.body.textContent.includes('11月1日は午後休診です。'),outline:!!doc.querySelector('#simy-edit-highlight'),nestedDate:doc.querySelector('.date')?.textContent,dateColumn:doc.querySelector('dt')?.textContent,badge:doc.querySelector('li:first-child .info-list-cat')?.textContent,profile:doc.querySelector('section:last-child').textContent};});
  assert(!result.error,JSON.stringify(result));assert(result.title&&result.body&&!result.outline,JSON.stringify(result));assert.equal(result.profile,'医院概要所在地東京都');if(name==='category-badge')assert.equal(result.badge,undefined);if(name==='japanese-date-span')assert.equal(result.nestedDate,'2026年10月31日');if(name==='japanese-date-column')assert.equal(result.dateColumn,'2026年10月31日');console.log(name,'retains collection and does not edit clinic profile');
 }
 await page.setContent('<div class="notice_area">'+['お知らせ','担当医のお知らせ','感染症流行状況'].map(title=>'<div class="notice_box"><h3>'+title+'</h3><dl><dt class="news_title">2026.10.29 以前のタイトル</dt><dd>以前の本文</dd></dl></div>').join('')+'</div>');
 await page.addScriptTag({path:path.resolve('site/preview-edit.js')});
 const categories=await page.evaluate(()=>{const html=SimyPreviewEdit.index(document.documentElement.outerHTML),news=SimyPreviewEdit.inventory(html).filter(n=>n.kind==='news');if(news.length!==3||news.some(n=>n.tag!=='dl'))throw Error('Category wrapper was mistaken for an article list');const result=SimyPreviewEdit.applyPlan(html,{status:'edit',operations:[{type:'insert_notice',target:news[0].id,title:'午後休診のご案内',body:'明日は午後休診です。',date:'2026-10-31'}]});return [...new DOMParser().parseFromString(result.html,'text/html').querySelectorAll('.notice_box h3')].map(e=>e.textContent);});
 assert.deepEqual(categories,['お知らせ','担当医のお知らせ','感染症流行状況']);
 await page.setContent('<style>.deck{width:200px;visibility:hidden}.crop{overflow:hidden}.cards{display:flex;margin:0;padding:0}.cards li{flex:0 0 180px}.unrelated{visibility:hidden}</style><section class="deck"><div class="crop"><ul class="cards"><li>カード A</li><li>カード B</li></ul></div></section><section class="deck" aria-hidden="true"><div class="crop"><ul class="cards"><li>カード C</li><li>カード D</li></ul></div></section><div class="unrelated">別のナビゲーション</div>');await page.addScriptTag({path:path.resolve('site/preview-edit.js')});
 await page.evaluate(()=>SimyPreviewEdit.repairStaticLayout(document));
 assert.equal(await page.locator('.deck').first().evaluate(e=>getComputedStyle(e).visibility),'visible');
 assert.equal(await page.locator('.crop').first().evaluate(e=>getComputedStyle(e).overflowX),'auto');
 assert.equal(await page.locator('.deck').last().evaluate(e=>getComputedStyle(e).visibility),'hidden');
 assert.equal(await page.locator('.unrelated').evaluate(e=>getComputedStyle(e).visibility),'hidden');
 await page.setContent('<h2><span>診療案内</span></h2>');await page.addScriptTag({path:path.resolve('site/preview-edit.js')});
 const text=await page.evaluate(()=>{const html=SimyPreviewEdit.index(document.documentElement.outerHTML),doc=new DOMParser().parseFromString(html,'text/html'),targets=[doc.querySelector('h2'),doc.querySelector('span')].map(e=>e.getAttribute('data-simy-edit-id'));return SimyPreviewEdit.applyPlan(html,{status:'edit',operations:targets.map(target=>({type:'replace_text',target,oldText:'診療案内',newText:'診療案内について'}))}).html;});assert(!text.includes('についてについて'));assert(text.includes('診療案内について'));
 await page.setContent('<p><span>診療案内</span><span>診療案内</span></p>');await page.addScriptTag({path:path.resolve('site/preview-edit.js')});
 const distinct=await page.evaluate(()=>{const html=SimyPreviewEdit.index(document.documentElement.outerHTML),doc=new DOMParser().parseFromString(html,'text/html'),targets=[doc.querySelector('p'),doc.querySelectorAll('span')[1]].map(e=>e.getAttribute('data-simy-edit-id'));const result=SimyPreviewEdit.applyPlan(html,{status:'edit',operations:targets.map(target=>({type:'replace_text',target,oldText:'診療案内',newText:'診療案内について'}))});return new DOMParser().parseFromString(result.html,'text/html').body.textContent;});assert.equal(distinct,'診療案内について診療案内について');
 await page.setViewportSize({width:1000,height:800});
 await page.setContent('<style>.site-columns{display:grid;grid-template-columns:1fr 2fr;background-image:url("https://example.com/hero.png")} h1{background:white;color:black;font-family:serif;border-bottom:2px solid gray}section{border-radius:19px}@media(max-width:600px){.site-columns{grid-template-columns:1fr}h1{background:#234567;color:white;font-family:monospace}section{border-radius:2px}}</style><main class="site-columns"><h1>既存の見出し</h1><section style="padding:12px;background:#234567;color:white"><h2>暗い背景の見出し</h2><p>既存の本文</p><img src="photo.jpg" alt="既存の写真"></section></main>');
 await page.addScriptTag({path:path.resolve('site/preview-edit.js')});
 const theme=await page.evaluate(()=>{
  const original=SimyPreviewEdit.index(document.documentElement.outerHTML);
  const indexed=new DOMParser().parseFromString(original,'text/html');
  for(const [i,node] of [...document.querySelectorAll('h1,h2')].entries())node.dataset.simyEditId=indexed.querySelectorAll('h1,h2')[i].dataset.simyEditId;
  return SimyPreviewEdit.applyPlan(original,{status:'edit',operations:[
   {type:'redesign',target:'e0',property:'editorial',value:'#234567'},
  ]},[],document).html;
 });
 await page.setContent(theme);
 assert.equal(await page.locator('.site-columns').evaluate(node=>getComputedStyle(node).display),'grid');
 assert.match(await page.locator('.site-columns').evaluate(node=>getComputedStyle(node).backgroundImage),/hero\.png/);
 assert.equal(await page.locator('section').evaluate(node=>getComputedStyle(node).paddingTop),'12px');
 assert.deepEqual(await page.locator('h1').evaluate(node=>[getComputedStyle(node).borderBottomColor,getComputedStyle(node).fontFamily]),['rgb(35, 69, 103)','serif']);
 assert.equal(await page.locator('section').evaluate(node=>getComputedStyle(node).borderRadius),'19px');
 assert.equal(await page.locator('h2').evaluate(node=>getComputedStyle(node).color),'rgb(255, 255, 255)');
 await page.setViewportSize({width:500,height:800});
 assert.deepEqual(await page.locator('h1').evaluate(node=>[getComputedStyle(node).color,getComputedStyle(node).backgroundColor]),['rgb(255, 255, 255)','rgb(35, 69, 103)']);
 assert.deepEqual(await page.locator('h1').evaluate(node=>[getComputedStyle(node).fontFamily,getComputedStyle(node).borderBottomWidth]),['monospace','2px']);
 assert.equal(await page.locator('section').evaluate(node=>getComputedStyle(node).borderRadius),'2px');
 assert.equal(await page.locator('img').getAttribute('src'),'photo.jpg');
 console.log('The requested theme preserves the original media, responsive layout and readable heading colors.');
 await page.setContent('<style>.waiting-for-script{opacity:0;transition:opacity 1s}</style><section id="edited" class="waiting-for-script"><img data-simy-changed alt="差し替えた写真"></section><section id="untouched" class="waiting-for-script">他の内容</section><section id="hidden" class="waiting-for-script" hidden><p data-simy-changed>非表示</p></section>');
 await page.addScriptTag({path:path.resolve('site/preview-edit.js')});
 const visible=await page.evaluate(()=>{
  const focused=SimyPreviewEdit.revealChanges(document);
  return {focus:focused?.getAttribute('alt'), edited:getComputedStyle(document.querySelector('#edited')).opacity,
   untouched:getComputedStyle(document.querySelector('#untouched')).opacity, hidden:getComputedStyle(document.querySelector('#hidden')).opacity};
 });
 assert.deepEqual(visible,{focus:'差し替えた写真',edited:'1',untouched:'0',hidden:'0'});
 console.log('A changed photo behind a script-dependent fade becomes visible without revealing unrelated or hidden sections.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});

async function checkStaticScrollAreas() {
 const fs = require('node:fs');
 const pageHtml = fs.readFileSync('site/hp-management/clinic/index.html', 'utf8');
 const scripts = [...pageHtml.matchAll(/<script src="(\/assets\/clinic-service-v2\/[a-f0-9]+\.js)"/g)];
 const editorPath = scripts.map(match => path.resolve('site' + match[1]))
  .find(file => fs.readFileSync(file, 'utf8').includes('global.SimyPreviewEdit='));
 const browser = await chromium.launch({ headless: true, channel: 'chrome' });
 try {
  const page = await browser.newPage();
  const entries = Array.from({length: 10}, (_, i) =>
   '<li><dl><dt>2026.10.01</dt><dd>以前のお知らせ' + i + '</dd></dl></li>').join('');
  const source = '<style>.topics .article-window{height:120px}li{min-height:60px}</style>' +
   '<div class="publisher"><div class="topics"><h2>お知らせ</h2><div class="article-window">' +
   '<ul class="item_list">' + entries + '</ul></div></div></div><section>予約・動画案内</section>';
  await page.addScriptTag({path: editorPath});
  const updated = await page.evaluate(source => {
   const html = SimyPreviewEdit.index(SimyPreviewEdit.prepare(source));
   const target = SimyPreviewEdit.inventory(html).find(node => node.kind === 'news').id;
   return SimyPreviewEdit.applyPlan(html, {status:'edit', operations:[{
    type:'insert_notice', target, title:'休診のお知らせ', body:'明日は休診です。', date:'2026-11-04'
   }]}).html;
  }, source);
  await page.setContent(updated);
  await page.addScriptTag({path: editorPath});
  await page.evaluate(()=>SimyPreviewEdit.repairStaticLayout(document));
  const exported=await page.evaluate(html=>SimyPreviewEdit.exportStaticLayout(html,document),updated);
  assert(!updated.includes('data-simy-static-layout'));
  assert.match(exported,/data-simy-static-layout/);
  await page.setContent(exported);
  const list = page.locator('.article-window');
  assert.match(await list.locator('li').first().innerText(), /明日は休診です/);
  assert.equal(await list.locator('dt').count(), 11);
  const clipped = await list.evaluate(box => {
   const section = document.querySelector('section').getBoundingClientRect();
   const overSection = document.elementsFromPoint(section.left + 60, section.top + 5);
   return !overSection.some(element => box.contains(element));
  });
  assert(clipped, 'Notices must not paint over the next section');
  assert(await list.evaluate(box => {
   box.scrollTop = box.scrollHeight;
   return box.scrollTop > 0 && box.querySelector('li:last-child').getBoundingClientRect().bottom <= box.getBoundingClientRect().bottom + 1;
  }), 'The final notice must be reachable by scrolling inside the list');
 } finally {
  await browser.close();
 }
}
checkStaticScrollAreas().catch(error => { console.error(error); process.exit(1); });
