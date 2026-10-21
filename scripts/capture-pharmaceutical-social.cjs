// Render the localized Open Graph cards from the approved artwork and copy.
// NODE_PATH=<Playwright installation> node scripts/capture-pharmaceutical-social.cjs
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const copy=require('./pharmaceutical-social-copy.json');
const data=(file,mime)=>`data:${mime};base64,${fs.readFileSync(path.join(root,file)).toString('base64')}`;
const escape=s=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
(async()=>{const browser=await chromium.launch({channel:'chrome'});try{for(const [lang,c]of Object.entries(copy)){
 const page=await browser.newPage({viewport:{width:1200,height:630},deviceScaleFactor:1});
 await page.setContent(`<!doctype html><html lang="${lang}"><meta charset="utf-8"><style>
 @font-face{font-family:PharmaDevanagari;src:url('${data('site/assets/pharmaceutical-companies/noto-sans-devanagari-700.ttf','font/ttf')}');font-weight:700}
 *{box-sizing:border-box}html,body{margin:0;width:1200px;height:630px;background:#f6f5f4;color:#17233a;font-family:Arial,'Hiragino Sans',Meiryo,sans-serif}
 html[lang=hi] body{font-family:PharmaDevanagari,Arial,sans-serif}
 .card{display:grid;grid-template-columns:520px 680px;width:1200px;height:630px;border-bottom:10px solid #215ac7;overflow:hidden}
 .copy{padding:48px 36px 42px 46px;position:relative;min-width:0}
 .brand{display:flex;align-items:center;gap:12px;font:800 48px/1 Arial,sans-serif;letter-spacing:-2px}
 .brand img{width:54px;height:54px}.label{font-size:20px;font-weight:700;margin:34px 0 26px;letter-spacing:.02em;color:#385581}
 h1{font-size:58px;line-height:1.2;letter-spacing:-.04em;margin:0;font-weight:800}h1 span{display:block;white-space:nowrap}h1 span+span{color:#215ac7}
 html[lang=hi] h1{font-size:53px;line-height:1.45;letter-spacing:0}html[lang=fr] h1{font-size:56px}
 .url{position:absolute;left:46px;bottom:36px;font:700 22px/1 Arial,sans-serif;color:#385581;letter-spacing:.01em}
 .art{width:680px;height:620px;object-fit:cover;object-position:50% 48%;border-left:3px solid #17233a;display:block}
 </style><main class=card><div class=copy><div class=brand><img src="${data('site/simy-icon-56.png','image/png')}" alt="">SIMY</div><p class=label>${escape(c.label)}</p><h1>${c.lines.map(line=>`<span>${escape(line)}</span>`).join('')}</h1><div class=url>simy.one</div></div><img class=art src="${data('site/assets/pharmaceutical-companies/social/meeting-v1.webp','image/webp')}" alt=""></main></html>`);
 await page.evaluate(()=>document.fonts.ready);await page.locator('img').evaluateAll(es=>Promise.all(es.map(e=>e.decode())));
 const boxes=await page.locator('h1 span,.label').evaluateAll(es=>es.map(e=>({text:e.innerText,rect:e.getBoundingClientRect().toJSON(),scroll:e.scrollWidth,client:e.clientWidth})));
 for(const x of boxes){assert.ok(x.scroll<=x.client+1,`${lang}: clipped text ${x.text}`);assert.ok(x.rect.right<=484&&x.rect.bottom<550,`${lang}: copy collides with artwork or footer`)}
 const output=path.join(root,`site/assets/pharmaceutical-companies/social/next-meeting-${lang}-v1.png`);
 await page.screenshot({path:output});console.log(lang,output);await page.close();
}}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
