// Content-specific, localized editorial cards. No screenshots of product UI.
// NODE_PATH=<Playwright installation> node scripts/capture-site-social.cjs
const {chromium}=require('playwright');
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');const cards=require('./social-preview-pages.json');
const data=(file,mime)=>`data:${mime};base64,${fs.readFileSync(path.join(root,file)).toString('base64')}`;
const esc=s=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
const icon=data('site/simy-icon-56.png','image/png');const font=data('site/assets/pharmaceutical-companies/noto-sans-devanagari-700.ttf','font/ttf');
const palettes={guide:['#f3f6fc','#2257b8'],home:['#eef9f5','#146653'],engineer:['#eef3fc','#2459ba'],fp:['#f8f4ee','#8b5530'],download:['#eff8fc','#1c647d'],news:['#fbf3ed','#9d4c24'],sales:['#f1f5fc','#2459ba'],solutions:['#f1f5fc','#2459ba'],company:['#f3f5f5','#344a57']};
(async()=>{const browser=await chromium.launch({channel:'chrome'});const report=[];try{
 const page=await browser.newPage({viewport:{width:1200,height:630},deviceScaleFactor:1});
 for(const c of cards){const [bg,accent]=palettes[c.kind];
 await page.setContent(`<!doctype html><html lang="${c.lang}"><meta charset="utf-8"><style>
 @font-face{font-family:Devanagari;src:url('${font}');font-weight:700}
 *{box-sizing:border-box}html,body{margin:0;width:1200px;height:630px}body{font-family:Arial,'Hiragino Sans',Meiryo,sans-serif;color:#17233a;background:${bg};border-bottom:12px solid ${accent}}
 html[lang=hi] body{font-family:Devanagari,Arial,sans-serif}main{padding:44px 58px;height:618px;position:relative;overflow:hidden}
 header{display:flex;align-items:center;justify-content:space-between;gap:28px} .brand{display:flex;gap:13px;align-items:center;font:800 44px/1 Arial;letter-spacing:-2px}.brand img{width:52px;height:52px}.label{font-size:23px;font-weight:700;color:${accent};text-align:right;max-width:660px}
 .content{height:424px;display:flex;flex-direction:column;justify-content:center}.topic:empty{display:none}.topic{margin:0 0 20px;font-size:28px;line-height:1.3;font-weight:700;color:${accent};letter-spacing:.01em}
 h1{margin:0;font-size:88px;line-height:1.3;letter-spacing:-.025em;font-weight:800;overflow-wrap:normal;text-wrap:balance;word-break:auto-phrase;max-width:1084px}
 h1 span{display:block;white-space:nowrap}
 html[lang=hi] h1{line-height:1.5;letter-spacing:0}
 footer{position:absolute;bottom:35px;left:58px;right:58px;display:flex;align-items:center;justify-content:space-between;color:${accent};font:700 22px/1 Arial}.rule{height:5px;width:70px;background:${accent}}
 </style><main><header><div class=brand><img src="${icon}" alt="">SIMY</div><div class=label>${esc(c.label==='SIMY'?'':c.label)}</div></header><div class=content><div class=topic>${esc(c.topic==='SIMY'||c.topic===c.label?'':c.topic)}</div><h1>${c.lines?c.lines.map(s=>`<span>${esc(s)}</span>`).join(''):esc(c.headline)}</h1></div><footer><span>simy.one</span><span class=rule></span></footer></main></html>`);
 await page.evaluate(()=>document.fonts.ready);await page.locator('img').evaluateAll(es=>Promise.all(es.map(e=>e.decode())));
 const fit=await page.evaluate(()=>{const h=document.querySelector('h1');let size=88;while((document.querySelector('.content').scrollHeight>424||h.getBoundingClientRect().bottom>520||h.scrollWidth>h.clientWidth)&&size>42){h.style.fontSize=`${--size}px`}return {size,bottom:h.getBoundingClientRect().bottom,width:h.scrollWidth,client:h.clientWidth,label:document.querySelector('.label').getBoundingClientRect().bottom}});
 assert.ok(fit.bottom<=531&&fit.width<=fit.client&&fit.label<110,`${c.page}: headline overflow ${JSON.stringify(fit)}`);
 const output=path.join(root,'site',c.image);fs.mkdirSync(path.dirname(output),{recursive:true});await page.screenshot({path:output});report.push({...c,...fit});
 }fs.mkdirSync(path.join(root,'output/site-social-review'),{recursive:true});fs.writeFileSync(path.join(root,'output/site-social-review/render.json'),JSON.stringify(report,null,2));console.log(`Rendered and checked ${report.length} cards`);
 }finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
