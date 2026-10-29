(function(global){
 'use strict';
 function parse(message){
  const text=String(message||'').trim();
  const replace=text.match(/^[「『]([^」』]+)[」』]を[「『]([^」』]*)[」』](?:に変更(?:して(?:ください)?)?[。！!]?|に差し替え(?:て(?:ください)?)?[。！!]?)$/);
  if(replace)return {type:'replace',from:replace[1],to:replace[2]};
  const notice=text.match(/^(?:お知らせ|告知)[：:]\s*([\s\S]+)$/);
  if(notice&&notice[1].trim())return {type:'notice',text:notice[1].trim()};
  throw Error('お知らせは「お知らせ：内容」、差し替えは「変更前」を「変更後」に変更、と入力してください。');
 }
 function prepare(html){
  const doc=new DOMParser().parseFromString(html,'text/html');
  for(const a of doc.querySelectorAll('a,area')){a.removeAttribute('href');a.removeAttribute('target');a.setAttribute('aria-disabled','true');}
  for(const control of doc.querySelectorAll('button,input,select,textarea'))control.disabled=true;
  const style=doc.createElement('style');style.textContent='a,area,button,input,select,textarea,[role=button]{pointer-events:none!important}';doc.head.append(style);
  return '<!doctype html>\n'+doc.documentElement.outerHTML;
 }
 function normalize(change){
  if(change?.type==='notice'&&typeof change.text==='string'&&change.text.trim()&&change.text.length<=500)return {type:'notice',text:change.text.trim()};
  if(change?.type==='replace'&&typeof change.from==='string'&&change.from.trim()&&typeof change.to==='string'&&change.from.length<=500&&change.to.length<=500)return {type:'replace',from:change.from,to:change.to};
  throw Error('変更する文章を入力してください。');
 }
 function applyChange(html,input){
  const change=normalize(input),doc=new DOMParser().parseFromString(html,'text/html');
  if(change.type==='notice'){
   let notice=doc.querySelector('#simy-preview-notice');if(!notice){notice=doc.createElement('aside');notice.id='simy-preview-notice';notice.setAttribute('role','note');notice.style.cssText='position:relative!important;display:block!important;visibility:visible!important;opacity:1!important;padding:20px 24px!important;background:#fff3d5!important;color:#442f12!important;font:700 18px/1.7 sans-serif!important;text-align:center!important;border-bottom:2px solid #e7bc5c!important;z-index:2147483647!important;';doc.body.prepend(notice);}notice.textContent=change.text;
   return {html:'<!doctype html>\n'+doc.documentElement.outerHTML,summary:'ページの先頭にお知らせを追加しました。'};
  }
  const walker=doc.createTreeWalker(doc.body,NodeFilter.SHOW_TEXT);let node,count=0;
  while((node=walker.nextNode())){if(node.parentElement?.closest('style,script,noscript,template'))continue;if(node.nodeValue.includes(change.from)){node.nodeValue=node.nodeValue.split(change.from).join(change.to);count++;}}
  if(!count)throw Error('変更前の文章が見つかりませんでした。プレビューにある文章をそのまま指定してください。');
  return {html:'<!doctype html>\n'+doc.documentElement.outerHTML,summary:count+'か所の文章を差し替えました。'};
 }
 const apply=(html,message)=>applyChange(html,parse(message));
 global.SimyPreviewEdit={parse,prepare,apply,applyChange,normalize};
})(typeof window==='undefined'?globalThis:window);

/* AI plans edit only explicit, bounded targets extracted from the current DOM. */
(function(global){
 'use strict';
 const api=global.SimyPreviewEdit;
 const parse=html=>new DOMParser().parseFromString(html,'text/html');
 const text=e=>(e.textContent||'').replace(/\s+/g,' ').trim();
 const blocked=e=>!!e.closest('script,style,noscript,template,head');
 function label(e){
  let p=e.parentElement;for(let depth=0;p&&depth<4;depth++,p=p.parentElement){
   if(['DL','UL','OL'].includes(p.tagName))continue;
   const headings=[...p.children].filter(n=>/^H[1-6]$/.test(n.tagName)||/title|heading|caption/i.test(n.className||''));
   const value=headings.map(text).filter(Boolean).join(' / ');if(value)return value.slice(0,300);
  }
  return '';
 }
 function isNews(e){return ['DL','UL','OL'].includes(e.tagName)&&/お知らせ|休診|診療.*変更|担当医|感染症|news|information/i.test(label(e));}
 api.index=function(html){const doc=parse(html);let count=0;for(const e of [doc.body,...doc.body.querySelectorAll('*')]){if(!blocked(e))e.setAttribute('data-simy-edit-id','e'+count++);}return '<!doctype html>\n'+doc.documentElement.outerHTML;};
 api.inventory=function(html,liveDocument){
  const doc=parse(html),all=[doc.body,...doc.body.querySelectorAll('[data-simy-edit-id]')],news=all.filter(isNews);
  const out=[],seen=new Set();let size=0;
  function add(e,kind){const id=e.getAttribute('data-simy-edit-id');if(seen.has(id)||out.length>=220)return;let t=kind==='image'?(e.getAttribute('alt')||'画像'):(e.tagName==='BODY'?'ページ全体':text(e));if(!t)return;if(kind==='text'&&t.length>1800)return;t=t.slice(0,1800);let context=label(e);try{const live=liveDocument?.querySelector('[data-simy-edit-id="'+id+'"]');if(live){const css=liveDocument.defaultView.getComputedStyle(live);context+=' / 現在の文字サイズ:'+css.fontSize+'、文字色:'+css.color+'、背景:'+css.backgroundColor;}}catch{}const n={id,kind,tag:e.tagName.toLowerCase(),text:t,context:context.slice(0,300)};const len=JSON.stringify(n).length;if(size+len>35000)return;size+=len;seen.add(id);out.push(n);}
  add(doc.body,'element');
  all.filter(e=>e.tagName==='IMG').slice(0,50).forEach(e=>add(e,'image'));
  if(liveDocument)all.filter(e=>e.tagName!=='IMG').forEach(e=>{try{const live=liveDocument.querySelector('[data-simy-edit-id="'+e.getAttribute('data-simy-edit-id')+'"]');if(live&&/^url\(/.test(liveDocument.defaultView.getComputedStyle(live).backgroundImage))add(e,'image');}catch{}});
  all.filter(e=>['SECTION','ARTICLE','HEADER','FOOTER','NAV'].includes(e.tagName)).slice(0,35).forEach(e=>add(e,'element'));
  news.forEach(e=>add(e,'news'));
  // Semantic headings and buttons first; then editable leaf paragraphs, avoiding nested duplicates.
  all.filter(e=>/^H[1-6]$/.test(e.tagName)||['A','BUTTON'].includes(e.tagName)).forEach(e=>add(e,'text'));
  all.filter(e=>!['DL','UL','OL','TABLE','TR','TBODY'].includes(e.tagName)&&text(e)&&![...e.children].some(c=>text(c)&&!['SPAN','BR','B','STRONG','EM','I','SMALL'].includes(c.tagName))).forEach(e=>add(e,'text'));
  return out;
 };
 api.redesign=function(doc,theme,accent,liveDocument){
  // Keep visible CSS background photography when replacing the old design system.
  if(liveDocument)for(const n of doc.body.querySelectorAll('[data-simy-edit-id]')){try{const live=liveDocument.querySelector('[data-simy-edit-id="'+n.getAttribute('data-simy-edit-id')+'"]');const bg=live&&liveDocument.defaultView.getComputedStyle(live).backgroundImage;const match=bg?.match(/^url\(["']?(https?:\/\/[^"')]+)["']?\)$/);if(match&&!n.children.length){const img=doc.createElement('img');img.src=match[1];img.alt='';n.append(img);}}catch{}}
  for(const n of doc.querySelectorAll('link[rel="stylesheet"],style'))n.remove();
  for(const n of doc.body.querySelectorAll('*')){n.removeAttribute('style');n.removeAttribute('width');n.removeAttribute('height');}
  doc.body.removeAttribute('style');doc.body.setAttribute('data-simy-theme',theme);
  for(const list of doc.querySelectorAll('ul,ol')){if(!isNews(list)&&list.children.length>=2&&[...list.children].every(li=>li.querySelector('img')))list.setAttribute('data-simy-grid','true');}
  const style=doc.createElement('style');style.textContent=`
  *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:${theme==='warm'?'#faf6ef':'#f5f7fa'};color:#172b3a;font:17px/1.85 ${theme==='editorial'?"Georgia, 'Yu Mincho', serif":"'Noto Sans JP', sans-serif"};overflow-wrap:anywhere}
  body>*,main>*,header,footer{max-width:1120px;margin:0 auto}body>div,main,section,article{padding:clamp(16px,4vw,48px)}header,nav,footer{padding:24px;background:#fff}section,article{margin:24px auto;background:#fff;border-radius:${theme==='warm'?'28':'8'}px}
  img{max-width:100%;height:auto;display:block;margin:16px auto;border-radius:${theme==='warm'?'20':'4'}px}picture{display:block}iframe,video{max-width:100%}h1,h2,h3{line-height:1.45;color:${accent};letter-spacing:.03em}h1{font-size:clamp(28px,4vw,48px)}h2{font-size:clamp(23px,3vw,32px);border-bottom:2px solid ${accent};padding-bottom:16px}p{margin:16px 0}a{color:${accent};pointer-events:none}ul,ol{padding-left:24px}nav ul{display:flex;flex-wrap:wrap;gap:16px;list-style:none;padding:0}dt{font-weight:700;color:${accent};margin-top:24px}dd{margin:8px 0 24px;border-bottom:1px solid #dce3e9;padding-bottom:16px}table{border-collapse:collapse;width:100%}td,th{padding:12px;border:1px solid #dce3e9}button,input,textarea,select{pointer-events:none}svg{max-width:100%;max-height:120px}[hidden]{display:none!important}
  [class*="nav_sp"],[class*="logo_sp"],.toggle,.toggle-label{display:none!important}nav ul,.main_nav{display:flex;flex-wrap:wrap;gap:12px;list-style:none;padding:0}nav li{padding:8px 12px;background:#edf3f1;border-radius:8px}nav ul ul{font-size:13px}.key_visual{display:grid;grid-template-columns:1fr 1.4fr;gap:32px;align-items:center}.key_visual h1 img{max-width:320px}.key_visual section{padding:24px}.key_visual nav{font-size:14px}.key_visual .slider>div:not(:first-child){display:none}.key_visual .slider img{width:100%;max-height:500px;object-fit:cover}.top_access_text{text-align:center;background:${accent};color:white;padding:16px}.notice_area{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px}[data-simy-grid]{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px;list-style:none;padding:0}[data-simy-grid] img{width:100%}.side_web_link{display:inline-block;padding:12px 24px;border:2px solid ${accent};border-radius:30px}.demo-icon{display:none}
  @media(max-width:799px){.key_visual,.notice_area,[data-simy-grid]{grid-template-columns:1fr}.key_visual{gap:16px}}
  @media(min-width:800px){body[data-simy-theme="editorial"] section{border-radius:0;border-left:5px solid ${accent}}} @media(max-width:600px){body>div,main,section,article{padding:16px}img{max-height:65vh;object-fit:contain}}
  `;doc.head.append(style);
 };
 api.applyPlan=function(html,plan,assets=[],liveDocument){
  if(plan.status!=='edit'||!Array.isArray(plan.operations)||!plan.operations.length||plan.operations.length>24)throw Error('変更案を確認できませんでした。');
  const doc=parse(html);for(const e of doc.querySelectorAll('[data-simy-changed]'))e.removeAttribute('data-simy-changed');
  const changed=[];
  for(const o of plan.operations){if(!/^e\d+$/.test(o.target))throw Error('変更箇所を確認できませんでした。');const e=doc.querySelector('[data-simy-edit-id="'+o.target+'"]');if(!e||blocked(e))throw Error('変更箇所が見つかりません。');
   if(o.type==='insert_notice'){
    if(!isNews(e)||!o.title||!o.body||!/^\d{4}-\d{2}-\d{2}$/.test(o.date))throw Error('お知らせの追加先を確認できません。');
    const heading=doc.createElement(e.tagName==='DL'?'dt':'strong'),body=doc.createElement(e.tagName==='DL'?'dd':'p');
    const template=e.querySelector(e.tagName==='DL'?'dt':'strong');if(template)heading.className=template.className;
    const bodyTemplate=e.querySelector(e.tagName==='DL'?'dd':'p');if(bodyTemplate)body.className=bodyTemplate.className;
    heading.textContent=o.date.replace(/-/g,'.')+'　'+o.title;body.textContent=o.body;
    if(e.tagName==='DL'){e.prepend(heading,body);}else{const li=doc.createElement('li');li.className=e.querySelector('li')?.className||'';li.append(heading,body);e.prepend(li);}
    heading.setAttribute('data-simy-changed','true');body.setAttribute('data-simy-changed','true');changed.push(o.target);
   }else if(o.type==='replace_text'){
    if(!o.oldText||typeof o.newText!=='string'||!o.newText.trim())throw Error('変更文を確認できません。');
    // Locate text across inline elements without destroying links, icons or layout.
    const walker=doc.createTreeWalker(e,NodeFilter.SHOW_TEXT),nodes=[];let n,full='';while(n=walker.nextNode()){if(blocked(n.parentElement))continue;nodes.push({n,start:full.length,end:full.length+n.nodeValue.length});full+=n.nodeValue;}
    let start=full.indexOf(o.oldText),end=start+o.oldText.length;
    if(start<0){ // Model inventory normalizes whitespace; map normalized characters back to original offsets.
     let normalized='',map=[],space=false;for(let i=0;i<full.length;i++){if(/\s/.test(full[i])){if(!space){normalized+=' ';map.push(i);}space=true;}else{normalized+=full[i];map.push(i);space=false;}}
     const at=normalized.indexOf(o.oldText);if(at<0)throw Error('変更前の文章と一致しません。ページは変更していません。');start=map[at];end=map[at+o.oldText.length-1]+1;
    }
    let inserted=false;for(const x of nodes){if(x.end<=start||x.start>=end)continue;const left=Math.max(0,start-x.start),right=Math.min(x.n.nodeValue.length,end-x.start);x.n.nodeValue=x.n.nodeValue.slice(0,left)+(inserted?'':o.newText)+x.n.nodeValue.slice(right);inserted=true;}
    if(!inserted)throw Error('文章を変更できませんでした。');e.setAttribute('data-simy-changed','true');changed.push(o.target);
   }else if(o.type==='set_style'){
    const valid=(['color','background-color'].includes(o.property)&&/^#[0-9a-f]{6}$/i.test(o.value))||(o.property==='font-size'&&/^(1[4-9]|[23]\d|40)px$/.test(o.value))||(o.property==='font-weight'&&/^(400|600|700)$/.test(o.value));if(!valid)throw Error('対応していない見た目の変更です。');e.style.setProperty(o.property,o.value,'important');e.setAttribute('data-simy-changed','true');changed.push(o.target);
   }else if(o.type==='replace_image'){
    const asset=assets.find(a=>a.id===o.value);if(!asset||!/^data:image\/(jpeg|png|webp);base64,[a-z0-9+/=]+$/i.test(asset.data))throw Error('差し替える写真を添付してください。');
    if(e.tagName==='IMG'){e.src=asset.data;}else{e.style.setProperty('background-image','url("'+asset.data+'")','important');}e.removeAttribute('srcset');e.removeAttribute('sizes');e.removeAttribute('loading');for(const source of e.closest('picture')?.querySelectorAll('source')||[])source.remove();e.setAttribute('data-simy-changed','true');changed.push(o.target);
   }else if(o.type==='redesign'){
    if(e!==doc.body||!['modern','editorial','warm'].includes(o.property)||!/^#[0-9a-f]{6}$/i.test(o.value))throw Error('デザイン指定を確認できません。');
    api.redesign(doc,o.property,o.value,liveDocument);changed.push(o.target);
   }else if(o.type==='add_section'){
    if(e===doc.body||!o.title?.trim()||!o.body?.trim())throw Error('追加先を確認できません。');const section=doc.createElement('section'),h=doc.createElement('h2'),p=doc.createElement('p');h.textContent=o.title;p.textContent=o.body;section.append(h,p);section.style.cssText='padding:32px;max-width:1100px;margin:24px auto;';section.setAttribute('data-simy-changed','true');e.after(section);changed.push(o.target);
   }else if(o.type==='remove_element'){
    if(e===doc.body)throw Error('ページ全体は削除できません。');e.remove();changed.push(o.target);
   }else if(o.type==='move_before'){
    if(!/^e\d+$/.test(o.value))throw Error('移動先を確認できません。');const dest=doc.querySelector('[data-simy-edit-id="'+o.value+'"]');if(!dest||dest===e||dest===doc.body||e===doc.body||e.contains(dest))throw Error('この位置には移動できません。');dest.before(e);e.setAttribute('data-simy-changed','true');changed.push(o.target);
   }else throw Error('対応していない変更です。');
  }
  if(!doc.querySelector('#simy-edit-highlight')){const style=doc.createElement('style');style.id='simy-edit-highlight';style.textContent='[data-simy-changed]{outline:3px solid #248c83!important;outline-offset:4px;scroll-margin:30px}';doc.head.append(style);}
  return {html:api.index('<!doctype html>\n'+doc.documentElement.outerHTML),summary:plan.summary,targets:changed};
 };
})(typeof window==='undefined'?globalThis:window);
