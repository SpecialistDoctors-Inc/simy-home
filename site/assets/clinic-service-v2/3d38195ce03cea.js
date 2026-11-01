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
  const style=doc.createElement('style');style.textContent='a,area,button,input,select,textarea,[role=button]{pointer-events:none!important}.splide:not(.is-initialized){visibility:visible!important}.splide:not(.is-initialized) .splide__track{overflow-x:auto!important}.splide:not(.is-initialized) .splide__slide{flex:0 0 min(100%,360px)!important;min-width:0!important;white-space:normal!important}';doc.head.append(style);
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
 const datePattern=/\d{4}\s*[.\/年-]\s*\d{1,2}\s*[.\/月-]\s*\d{1,2}/;
 const dateOnly=value=>datePattern.test(value)&&!value.replace(datePattern,'').replace(/[日月火水木金土曜（）()\s]/g,'');
 function newsContext(e){let p=e;for(let depth=0;p&&p.tagName!=='BODY'&&depth<5;depth++,p=p.parentElement){const hints=[p.id,p.className,label(p),...[...p.children].map(c=>(c.className||'')+' '+(c.querySelector('[class*=news],[class*=notice]')?.className||'')),...[...p.querySelectorAll(':scope > h2,:scope > h3,:scope > header h2,:scope > header h3,:scope > div[class*=head] h2,:scope > div[class*=head] h3')].map(text)].join(' ');if(/お知らせ|休診|news|information|topics|notice/i.test(hints))return true;}return false;}
 function noticeRow(e){
  if(e.tagName==='DL'){
   const dt=e.querySelector(':scope > dt');
   if(dt?.nextElementSibling?.tagName==='DD'&&(datePattern.test(text(dt))||/news|notice/i.test(dt.className||'')))return dt;
  }
  if(!['DL','UL','OL','DIV','SECTION'].includes(e.tagName))return null;
  const rows=[...e.children].filter(c=>['LI','DIV','ARTICLE','A','DL'].includes(c.tagName)&&(text(c).match(new RegExp(datePattern.source,'g'))||[]).length===1&&text(c).length<2500&&text(c).replace(datePattern,'').trim().length>4);
  const contentChildren=[...e.children].filter(c=>!blocked(c)&&text(c));
  if(rows.length>=2&&rows.length/contentChildren.length>=0.5)return rows[0];
  if(contentChildren.length>2)return null;
  return rows.find(c=>['LI','ARTICLE','A'].includes(c.tagName)||/(?:^|[-_ ])(?:item|post|news|notice)(?:[-_ ]|$)/i.test(c.className||''))||null;
 }
 function isNews(e){return (e.tagName!=='DL'||!!e.querySelector(':scope > dt'))&&!e.closest('nav,footer')&&newsContext(e)&&!!noticeRow(e);}

 api.index=function(html){const doc=parse(html);let count=0;for(const e of [doc.body,...doc.body.querySelectorAll('*')]){if(!blocked(e))e.setAttribute('data-simy-edit-id','e'+count++);}return '<!doctype html>\n'+doc.documentElement.outerHTML;};
 api.inventory=function(html,liveDocument){
  const doc=parse(html),all=[doc.body,...doc.body.querySelectorAll('[data-simy-edit-id]')];
  const newsCandidates=all.filter(isNews);
  // Prefer the existing article list over an outer section containing several categories.
  const collections=newsCandidates.filter(e=>!newsCandidates.some(n=>n!==e&&e.contains(n)&&['DL','UL','OL'].includes(n.tagName)));
  const news=collections.filter(e=>!collections.some(n=>n!==e&&n.contains(e)&&[...n.children].filter(c=>datePattern.test(text(c))&&text(c).length<2500).length>=2));
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
  const doc=parse(html);doc.querySelector('#simy-edit-highlight')?.remove();for(const e of doc.querySelectorAll('[data-simy-changed]'))e.removeAttribute('data-simy-changed');
  const changed=[];
  // Deduplicate the same physical text range, not every descendant of a target.
  const starts=new Map();
  const matchStart=o=>{
   if(starts.has(o))return starts.get(o);
   const target=/^e\d+$/.test(o.target)&&doc.querySelector('[data-simy-edit-id="'+o.target+'"]');
   if(!target)return null;
   const walker=doc.createTreeWalker(target,NodeFilter.SHOW_TEXT),map=[];let n,normalized='',space=false;
   while(n=walker.nextNode()){if(blocked(n.parentElement))continue;for(let offset=0;offset<n.nodeValue.length;offset++){
    const char=n.nodeValue[offset];if(/\s/.test(char)){if(space)continue;space=true;normalized+=' ';}else{space=false;normalized+=char;}map.push({node:n,offset});
   }}
   const at=normalized.indexOf(o.oldText),start=at<0?null:map[at];starts.set(o,start);return start;
  };
  const operations=plan.operations.filter((o,i,all)=>o.type!=='replace_text'||!all.slice(0,i).some(other=>{
   if(other.type!=='replace_text'||o.oldText!==other.oldText||o.newText!==other.newText)return false;
   const a=matchStart(o),b=matchStart(other);return a&&b&&a.node===b.node&&a.offset===b.offset;
  }));
  for(const o of operations){if(!/^e\d+$/.test(o.target))throw Error('変更箇所を確認できませんでした。');const e=doc.querySelector('[data-simy-edit-id="'+o.target+'"]');if(!e||blocked(e))throw Error('変更箇所が見つかりません。');
   if(o.type==='insert_notice'){
    if(!isNews(e)||!o.title||!o.body||!/^\d{4}-\d{2}-\d{2}$/.test(o.date))throw Error('お知らせの追加先を確認できません。');
    const cleanClone=source=>{const clone=source.cloneNode(true);for(const n of [clone,...clone.querySelectorAll('*')]){n.removeAttribute('id');n.removeAttribute('data-simy-edit-id');n.removeAttribute('data-simy-changed');}return clone;};
    const writeText=(node,value)=>{const walker=doc.createTreeWalker(node,NodeFilter.SHOW_TEXT),nodes=[];let n;while(n=walker.nextNode())if(n.nodeValue.trim())nodes.push(n);if(nodes.length){nodes[0].nodeValue=value;for(const rest of nodes.slice(1))rest.nodeValue='';}else node.textContent=value;};
    let heading,body,item,dateElement;
    const metadata=node=>{for(let p=node;p&&p!==item;p=p.parentElement)if(/(?:^|[-_ ])(?:cat|cate|category|label|badge)(?:[-_ ]|$)/i.test(p.className||''))return true;return false;};
    if(e.tagName==='DL'&&e.querySelector(':scope > dt')){
     const template=noticeRow(e),bodyTemplate=template?.nextElementSibling;
     if(!template||bodyTemplate?.tagName!=='DD')throw Error('既存のお知らせの形式を確認できません。');
     const first=cleanClone(template),second=cleanClone(bodyTemplate);e.prepend(first,second);
     if(dateOnly(text(template))){
      dateElement=first;heading=second.querySelector('h2,h3,h4,h5,[class*=title],[class*=ttl]')||second;
      body=[...second.querySelectorAll('p,[class*=excerpt],[class*=description]')].find(n=>n!==heading&&!heading.contains(n)&&!n.contains(heading));
     }else{heading=first;body=second;dateElement=first.querySelector('time')||[...first.querySelectorAll('[class*=date]')].find(n=>dateOnly(text(n)));}
    }else{
     const template=noticeRow(e);if(!template)throw Error('既存のお知らせの形式を確認できません。');item=cleanClone(template);
     dateElement=item.querySelector('time')||[...item.querySelectorAll('dt,[class*=date]')].find(n=>datePattern.test(text(n)))||[...item.querySelectorAll('*')].find(n=>dateOnly(text(n)));
     heading=item.querySelector('h2,h3,h4,h5,dd,[class*=title],[class*=ttl]');
     if(!heading){const candidates=[item,...item.querySelectorAll('a,span,p,div')].filter(n=>n!==dateElement&&!n.contains(dateElement)&&!metadata(n)&&text(n)&&!datePattern.test(text(n))&&!/^(お知らせ|新着|NEWS|NEW|診療時間|休診情報)$/i.test(text(n)));heading=candidates.find(n=>![...n.children].some(c=>text(c)))||candidates[0];}
     if(!heading){if(dateElement)throw Error('既存のお知らせの見出しを確認できません。');heading=item;}
     body=[...item.querySelectorAll('p,[class*=excerpt],[class*=description],[class*=body]')].find(n=>n!==heading&&!heading.contains(n)&&!n.contains(heading)&&n!==dateElement&&!n.contains(dateElement)&&!metadata(n)&&!/^(お知らせ|新着|NEWS|NEW|診療案内|休診情報)$/i.test(text(n)));
     e.prepend(item);
    }
    const formatDate=before=>{const source=before.match(datePattern)?.[0]||before,parts=o.date.split('-');return source.includes('年')?parts[0]+'年'+parts[1]+'月'+parts[2]+'日':parts.join(source.includes('/')?'/':source.includes('-')?'-':'.');};
    const date=formatDate(text(heading));
    if(dateElement){writeText(dateElement,formatDate(text(dateElement)));if(dateElement.tagName==='TIME')dateElement.setAttribute('datetime',o.date);if(heading.contains(dateElement)){const tw=doc.createTreeWalker(heading,NodeFilter.SHOW_TEXT),nodes=[];let n;while(n=tw.nextNode())if(!dateElement.contains(n)&&n.nodeValue.trim())nodes.push(n);if(!nodes.length)heading.append(doc.createTextNode(o.title+(body?'':' — '+o.body)));else{nodes[0].nodeValue=o.title+(body?'':' — '+o.body);for(const rest of nodes.slice(1))rest.nodeValue='';}}else writeText(heading,o.title+(body?'':' — '+o.body));}
    else{const walker=doc.createTreeWalker(heading,NodeFilter.SHOW_TEXT);let n,dateNode;while(n=walker.nextNode())if(/^\s*\d{4}[.\/-]\d{1,2}[.\/-]\d{1,2}\s*$/.test(n.nodeValue)){dateNode=n;break;}
     if(dateNode){dateNode.nodeValue=date+'　';const titleNodes=[];const tw=doc.createTreeWalker(heading,NodeFilter.SHOW_TEXT);while(n=tw.nextNode())if(n!==dateNode&&n.nodeValue.trim())titleNodes.push(n);if(titleNodes.length){titleNodes[0].nodeValue=o.title+(body?'':' — '+o.body);for(const rest of titleNodes.slice(1))rest.nodeValue='';}else heading.append(doc.createTextNode(o.title+(body?'':' — '+o.body)));}
     else writeText(heading,(datePattern.test(text(heading))?date+'　':'')+o.title+(body?'':' — '+o.body));
    }
    if(body)writeText(body,o.body);
    heading.setAttribute('data-simy-changed','true');body?.setAttribute('data-simy-changed','true');changed.push(o.target);
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

  return {html:api.index('<!doctype html>\n'+doc.documentElement.outerHTML),summary:plan.summary,targets:changed};
 };
})(typeof window==='undefined'?globalThis:window);
