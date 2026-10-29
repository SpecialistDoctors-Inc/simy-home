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
 api.index=function(html){const doc=parse(html);let count=0;for(const e of doc.body.querySelectorAll('*')){if(!blocked(e))e.setAttribute('data-simy-edit-id','e'+count++);}return '<!doctype html>\n'+doc.documentElement.outerHTML;};
 api.inventory=function(html){
  const doc=parse(html),all=[...doc.body.querySelectorAll('[data-simy-edit-id]')],news=all.filter(isNews);
  const out=[],seen=new Set();let size=0;
  function add(e,kind){const id=e.getAttribute('data-simy-edit-id');if(seen.has(id)||out.length>=220)return;let t=text(e);if(!t)return;if(kind==='text'&&t.length>1800)return;t=t.slice(0,1800);const n={id,kind,tag:e.tagName.toLowerCase(),text:t,context:label(e)};const len=JSON.stringify(n).length;if(size+len>35000)return;size+=len;seen.add(id);out.push(n);}
  news.forEach(e=>add(e,'news'));
  // Semantic headings and buttons first; then editable leaf paragraphs, avoiding nested duplicates.
  all.filter(e=>/^H[1-6]$/.test(e.tagName)||['A','BUTTON'].includes(e.tagName)).forEach(e=>add(e,'text'));
  all.filter(e=>!['DL','UL','OL','TABLE','TR','TBODY'].includes(e.tagName)&&text(e)&&![...e.children].some(c=>text(c)&&!['SPAN','BR','B','STRONG','EM','I','SMALL'].includes(c.tagName))).forEach(e=>add(e,'text'));
  return out;
 };
 api.applyPlan=function(html,plan){
  if(plan.status!=='edit'||!Array.isArray(plan.operations)||!plan.operations.length||plan.operations.length>6)throw Error('変更案を確認できませんでした。');
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
   }else throw Error('対応していない変更です。');
  }
  if(!doc.querySelector('#simy-edit-highlight')){const style=doc.createElement('style');style.id='simy-edit-highlight';style.textContent='[data-simy-changed]{outline:3px solid #248c83!important;outline-offset:4px;scroll-margin:30px}';doc.head.append(style);}
  return {html:api.index('<!doctype html>\n'+doc.documentElement.outerHTML),summary:plan.summary,targets:changed};
 };
})(typeof window==='undefined'?globalThis:window);
