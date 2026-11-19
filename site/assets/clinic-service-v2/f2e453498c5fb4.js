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
 api.selectAttachment=function(assets,request,inspection){
  if(/^a\d+$/.test(inspection||''))return assets.find(asset=>asset.id===inspection);
  if(assets.length===1)return assets[0];
  const normalize=value=>String(value||'').normalize('NFKC').toLowerCase();
  const phrase=normalize(request);
  const candidates=assets.filter(asset=>normalize(asset.name)&&phrase.includes(normalize(asset.name)));
  return candidates.length===1?candidates[0]:undefined;
 };
 const parse=html=>new DOMParser().parseFromString(html,'text/html');
 const text=e=>(e.textContent||'').replace(/\s+/g,' ').trim();
 const blocked=e=>!!e.closest('script,style,noscript,template,head');
 function label(e){
  let p=e.parentElement;for(let depth=0;p&&depth<4;depth++,p=p.parentElement){
   if(['DL','UL','OL'].includes(p.tagName))continue;
   const headings=[...p.children].filter(n=>/^H[1-6]$/.test(n.tagName)||/title|heading|caption|(?:^|[-_])header(?:$|[-_])/i.test(n.className||''));
   const value=headings.map(text).filter(Boolean).join(' / ');if(value)return value.slice(0,300);
  }
  return '';
 }
 const datePattern=/\d{4}\s*[.\/年-]\s*\d{1,2}\s*[.\/月-]\s*\d{1,2}/;
 const dateOnly=value=>datePattern.test(value)&&!value.replace(datePattern,'').replace(/[日月火水木金土曜（）()\s]/g,'');
 const isoDate=/^\d{4}-\d{2}-\d{2}(?:T|$)/;
 const timeDate=e=>[...e.querySelectorAll('time[datetime]')].some(t=>isoDate.test(t.getAttribute('datetime')));
 const dated=e=>datePattern.test(text(e))||timeDate(e);
 const interactive='form,input,select,textarea,button,[role=button],[role=tablist],[role=grid]';
 function repeatedClasses(a,b){
  const prefixes=e=>[...e.classList].flatMap(name=>name.match(/^(.+)[-_][^-_]+$/)?.[1]||[]);
  const right=prefixes(b);
  return prefixes(a).some(prefix=>right.includes(prefix));
 }
 function rowHasDate(e){
  const value=text(e);
  return value.length<2500&&(value.match(new RegExp(datePattern.source,'g'))||[]).length<=1&&
   dated(e)&&value.replace(datePattern,'').trim().length>4&&!e.querySelector(interactive);
 }
 function noticeRow(e){
  if(e.tagName==='DL'){
   const pairs=[...e.querySelectorAll(':scope > dt')].filter(dt=>dt.nextElementSibling?.tagName==='DD');
   return pairs.find(dt=>dated(dt)&&!dt.nextElementSibling.querySelector(interactive))||
    pairs.find(dt=>repeatedClasses(dt,dt.nextElementSibling)&&!dt.nextElementSibling.querySelector(interactive))||null;
  }
  if(!['UL','OL','DIV','SECTION'].includes(e.tagName))return null;
  const contents=[...e.children].filter(c=>!blocked(c)&&text(c));
  const rows=contents.filter(c=>['LI','DIV','ARTICLE','A','DL'].includes(c.tagName)&&rowHasDate(c));
  if(rows.length>=2&&rows.length/contents.length>=0.5)return rows[0];
  if(contents.length>2)return null;
  return rows.find(c=>['LI','ARTICLE','A'].includes(c.tagName)||
   (c.tagName==='DIV'&&c.children.length>=2&&[...c.children].some(child=>dateOnly(text(child))||child.tagName==='TIME')))||null;
 }
 function isNews(e){return !e.closest('nav,footer,'+interactive)&&!!noticeRow(e);}

 api.index=function(html){const doc=parse(html);let count=0;for(const e of [doc.body,...doc.body.querySelectorAll('*')]){if(!blocked(e))e.setAttribute('data-simy-edit-id','e'+count++);}return '<!doctype html>\n'+doc.documentElement.outerHTML;};
 api.inventory=function(html,liveDocument,query=''){
  const doc=parse(html),all=[doc.body,...doc.body.querySelectorAll('[data-simy-edit-id]')];
  const siteName=doc.querySelector('meta[property="og:site_name"]')?.content.trim();
  const heading=doc.querySelector('main h1')||doc.querySelector('body h1');
  const headings=[...new Set([siteName,doc.title.trim(),heading&&text(heading)].filter(Boolean))];
  const pageContext=headings.map(value=>value.slice(0,80)).join(' / ');
  const newsCandidates=all.filter(isNews);
  // Prefer the existing article list over an outer section containing several categories.
  const collections=newsCandidates.filter(e=>{
   const row=noticeRow(e);
   const singleDatedRow=[...e.children].filter(child=>dated(child)).length===1;
   return !newsCandidates.some(n=>n!==e&&e.contains(n)&&((singleDatedRow&&n===row)||['DL','UL','OL'].includes(n.tagName)));
  });
  const news=collections.filter(e=>!collections.some(n=>n!==e&&n.contains(e)&&[...n.children].filter(c=>dated(c)&&text(c).length<2500).length>=2));
  const out=[],seen=new Set();let size=0;
  const term=query.trim().normalize('NFKC').toLowerCase();
  const matches=term?all.filter(element=>{
   if(element===doc.body||blocked(element))return false;
   const alt=element.getAttribute('alt')||'';
   const title=element.getAttribute('title')||'';
   const content=text(element);
   return [alt,title,element.id,typeof element.className==='string'?element.className:'',content.length<=1800?content:''].some(value=>value.normalize('NFKC').toLowerCase().includes(term));
  }).sort((a,b)=>text(a).length-text(b).length).slice(0,25):[];

  function add(e,kind){
   const id=e.getAttribute('data-simy-edit-id');
   if(seen.has(id)||out.length>=220)return;
   const value=kind==='image'?(e.getAttribute('alt')||'画像'):(e.tagName==='BODY'?'ページ全体':text(e));
   if(!value||(kind==='text'&&value.length>1800))return;
   let context=e===doc.body?pageContext:label(e);
   if(kind==='image'){
    const purpose=[e.id,e.getAttribute('class'),e.parentElement?.getAttribute('class'),e.parentElement?.parentElement?.getAttribute('class')].filter(Boolean).join(' ');
    context=context.slice(0,75)+' / 用途:'+purpose.slice(0,72)+' / 素材:'+(e.getAttribute('src')||'').split('/').pop().slice(0,48);
   }
   try{
    const live=liveDocument?.querySelector('[data-simy-edit-id="'+id+'"]');
    if(live){
     const css=liveDocument.defaultView.getComputedStyle(live);
     if(kind==='image'){
      const rect=live.getBoundingClientRect();
      context+=' / 表示:'+Math.round(rect.width)+'x'+Math.round(rect.height)+' / 元寸法:'+(live.naturalWidth||0)+'x'+(live.naturalHeight||0);
     }else{
      context=context.slice(0,125)+' / 文字:'+css.fontSize+' '+css.fontWeight+' '+css.fontFamily.slice(0,38)+' / 色:'+css.color+' / 背景:'+css.backgroundColor+' / 角:'+css.borderRadius;
     }
    }
   }catch{}
   const n={id,kind,tag:e.tagName.toLowerCase(),text:value.slice(0,1800),context:context.slice(0,300)};
   const len=JSON.stringify(n).length;
   if(size+len>35000)return;
   size+=len;seen.add(id);out.push(n);
  }
  add(doc.body,'element');
  for(const element of matches){
   const id=element.getAttribute('data-simy-edit-id');
   const background=/^e\d+$/.test(id)?liveDocument?.querySelector('[data-simy-edit-id="'+id+'"]'):null;
   let isBackground=false;
   if(background)try{isBackground=/^url\(/.test(liveDocument.defaultView.getComputedStyle(background).backgroundImage);}catch{}
   add(element,element.tagName==='IMG'||isBackground?'image':news.includes(element)?'news':text(element)?'text':'element');
  }

  // Keep notice targets before optional structure summaries spend the shared budget.
  news.forEach(e=>add(e,'news'));
  all.filter(e=>e.tagName==='IMG').slice(0,50).forEach(e=>add(e,'image'));
  if(liveDocument)all.filter(e=>e.tagName!=='IMG').forEach(e=>{try{const live=liveDocument.querySelector('[data-simy-edit-id="'+e.getAttribute('data-simy-edit-id')+'"]');if(live&&/^url\(/.test(liveDocument.defaultView.getComputedStyle(live).backgroundImage))add(e,'image');}catch{}});
  all.filter(e=>['SECTION','ARTICLE','HEADER','FOOTER','NAV'].includes(e.tagName)).slice(0,35).forEach(e=>add(e,'element'));
  all.filter(e=>['DIV','LI','FIGURE'].includes(e.tagName)&&/card|feature|reason/i.test(e.className||'')&&text(e).length<=1800).slice(0,35).forEach(e=>add(e,'element'));
  // Semantic headings and buttons first; then editable leaf paragraphs, avoiding nested duplicates.
  all.filter(e=>/^H[1-6]$/.test(e.tagName)||['A','BUTTON'].includes(e.tagName)).forEach(e=>add(e,'text'));
  all.filter(e=>!['DL','UL','OL','TABLE','TR','TBODY'].includes(e.tagName)&&text(e)&&![...e.children].some(c=>text(c)&&!['SPAN','BR','B','STRONG','EM','I','SMALL'].includes(c.tagName))).forEach(e=>add(e,'text'));
  return out;
 };
 api.revealChanges=function(doc){
  const view=doc.defaultView;
  if(!view)return null;
  let first=null;
  for(const target of doc.querySelectorAll('[data-simy-changed]')){
   const ancestors=[];
   for(let node=target;node;node=node.parentElement)ancestors.push(node);
   const chain=ancestors.map(node=>[node,view.getComputedStyle(node)]);
   // Keep intentionally hidden or breakpoint-specific branches in their original state.
   if(chain.some(([node,style])=>node.hidden||node.getAttribute('aria-hidden')==='true'||style.display==='none'||style.visibility!=='visible'))continue;
   for(const [node,style] of chain){
    if(Number(style.opacity)!==0)continue;
    // The preview blocks source scripts, including any script that ends a reveal animation.
    node.style.setProperty('transition-property','none','important');
    node.style.setProperty('opacity','1','important');
   }
   first??=target;
  }
  return first;
 };
 // This runs only against the live sandbox, so layout repairs never enter downloaded HTML.
 const staticRepairs=new WeakMap();
 api.repairStaticLayout=function(doc){
  const view=doc.defaultView;
  if(!view)return;
  staticRepairs.get(doc)?.remove();
  const style=doc.createElement('style'),rules=new Map(),marked=[];
  const mark=(node,rule)=>{
   let id=marked.indexOf(node);
   if(id<0){id=marked.length;marked.push(node);node.setAttribute('data-simy-static-layout',id);}
   rules.set(id,(rules.get(id)||'')+rule);
  };
  const chain=node=>{
   const path=[];
   for(let e=node;e&&e!==doc.body;e=e.parentElement)path.push(e);
   return path;
  };
  const excluded=path=>path.some(e=>e.hidden||e.getAttribute('aria-hidden')==='true'||view.getComputedStyle(e).display==='none');
  const visited=new Set();
  const lists=doc.querySelectorAll('ul,ol,dl,[role=list]');
  for(const list of [...lists].slice(0,160)){
   const elements=chain(list);
   if(excluded(elements)||list.closest('nav,footer,form'))continue;
   const css=view.getComputedStyle(list);
   if(css.display.includes('flex')&&css.flexDirection.startsWith('row')&&css.flexWrap==='nowrap'&&list.children.length>=2){
    const track=elements.slice(0,4).find(e=>{
     const overflow=view.getComputedStyle(e).overflowX;
     return ['hidden','clip'].includes(overflow)&&e.clientWidth>0&&list.scrollWidth>e.clientWidth+1;
    });
    if(track){
     const scope=elements.slice(0,4);
     // A clipped horizontal strip can be rendered as a native scroll area when its script is blocked.
     if(!scope.slice(1).some(e=>e.getAttribute('aria-expanded')==='false')){
      mark(track,'overflow-x:auto!important;');
      const hiddenScope=scope.filter(e=>view.getComputedStyle(e).visibility==='hidden');
      if(hiddenScope.length){
       const outer=hiddenScope.at(-1);
       if(view.getComputedStyle(outer.parentElement).visibility==='visible')mark(outer,'visibility:visible!important;');
      }
     }
    }
   }
   if(!isNews(list))continue;
   for(const box of elements.slice(0,5)){
    if(visited.has(box))continue;
    visited.add(box);
    const css=view.getComputedStyle(box);
    const authoredHeight=box.computedStyleMap?.().get('height')?.toString();
    const constrained=(authoredHeight&&authoredHeight!=='auto')||css.maxHeight!=='none';
    const clipped=['hidden','clip'].includes(css.overflowY);
    if(css.visibility==='visible'&&box.clientHeight>0&&box.scrollHeight>box.clientHeight+2&&
     (clipped||(css.overflowY==='visible'&&constrained))){
     mark(box,'overflow-y:auto!important;');break;
    }
   }
  }
  style.textContent=[...rules].map(([id,rule])=>'[data-simy-static-layout="'+id+'"]{'+rule+'}').join('\n');
  doc.head.append(style);
  staticRepairs.set(doc,{remove:()=>{style.remove();for(const node of marked)node.removeAttribute('data-simy-static-layout');}});
 };
 api.redesign=function(doc,accent,liveDocument){
  doc.body.setAttribute('data-simy-theme','accent');
  doc.querySelector('style[data-simy-preview-theme]')?.remove();
  const style=doc.createElement('style');
  style.dataset.simyPreviewTheme='';
  for(const node of doc.querySelectorAll('[data-simy-accent-decoration]'))node.removeAttribute('data-simy-accent-decoration');
  for(const heading of [...doc.querySelectorAll('h1,h2,h3,[role="heading"]')].slice(0,100)){
   const id=heading.getAttribute('data-simy-edit-id');
   if(!/^e\d+$/.test(id))continue;
   const selector='[data-simy-edit-id="'+id+'"]';
   const live=liveDocument?.querySelector(selector);
   const css=live&&liveDocument.defaultView.getComputedStyle(live);
   const decoration=css&&parseFloat(css.borderBottomWidth)>0?'border':css&&css.textDecorationLine!=='none'?'existing':'underline';
   heading.setAttribute('data-simy-accent-decoration',decoration);
  }
  style.textContent=`
   [data-simy-accent-decoration]{text-decoration-color:${accent}}
   [data-simy-accent-decoration="border"]{border-bottom-color:${accent}}
   [data-simy-accent-decoration="underline"]{text-decoration-line:underline}
  `;
  doc.head.append(style);
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
  for(const o of operations){if(!/^e\d+$/.test(o.target))throw Error('変更箇所を確認できませんでした。');let e=doc.querySelector('[data-simy-edit-id="'+o.target+'"]');if(!e||blocked(e))throw Error('変更箇所が見つかりません。');
   if(o.type==='insert_notice'){
    if(!isNews(e)||!o.title||!o.body||!/^\d{4}-\d{2}-\d{2}$/.test(o.date))throw Error('お知らせの追加先を確認できません。');
    const cleanClone=source=>{
     const clone=source.cloneNode(true);
     for(const n of clone.querySelectorAll('picture,img,video,audio,iframe,object,embed,source'))n.remove();
     for(const n of [clone,...clone.querySelectorAll('*')]){
      for(const name of ['id','data-simy-edit-id','data-simy-changed','data-simy-accent-decoration'])n.removeAttribute(name);
     }
     return clone;
    };
    const writeText=(node,value)=>{const walker=doc.createTreeWalker(node,NodeFilter.SHOW_TEXT),nodes=[];let n;while(n=walker.nextNode())if(n.nodeValue.trim())nodes.push(n);if(nodes.length){nodes[0].nodeValue=value;for(const rest of nodes.slice(1))rest.nodeValue='';}else node.textContent=value;};
    let heading,body,item,dateElement,inserted;
    const metadata=node=>{for(let p=node;p&&p!==item;p=p.parentElement)if(/(?:^|[-_ ])(?:cat|cate|category|label|badge)(?:[-_ ]|$)/i.test(p.className||''))return true;return false;};
    if(e.tagName==='DL'&&e.querySelector(':scope > dt')){
     const template=noticeRow(e),bodyTemplate=template?.nextElementSibling;
     if(!template||bodyTemplate?.tagName!=='DD')throw Error('既存のお知らせの形式を確認できません。');
     const first=cleanClone(template),second=cleanClone(bodyTemplate);e.prepend(first,second);inserted=[first,second];
     if(dateOnly(text(template))||(timeDate(template)&&text(template)===text(template.querySelector('time[datetime]')))){
      dateElement=first.querySelector('time')||first;heading=second.querySelector('h2,h3,h4,h5,[class*=title],[class*=ttl]')||second;
      body=[...second.querySelectorAll('p,[class*=excerpt],[class*=description]')].find(n=>n!==heading&&!heading.contains(n)&&!n.contains(heading));
     }else{heading=first;body=second;dateElement=first.querySelector('time')||[...first.querySelectorAll('[class*=date]')].find(n=>dateOnly(text(n)));}
    }else{
     const template=noticeRow(e);if(!template)throw Error('既存のお知らせの形式を確認できません。');item=cleanClone(template);
     dateElement=item.querySelector('time')||[...item.querySelectorAll('dt,[class*=date]')].find(n=>datePattern.test(text(n)))||[...item.querySelectorAll('*')].find(n=>dateOnly(text(n)));
     heading=item.querySelector('h2,h3,h4,h5,dd,[class*=title],[class*=ttl]');
     if(!heading){const candidates=[item,...item.querySelectorAll('a,span,p,div')].filter(n=>n!==dateElement&&!n.contains(dateElement)&&!metadata(n)&&text(n)&&!datePattern.test(text(n)));heading=candidates.find(n=>![...n.children].some(c=>text(c)))||candidates[0];}
     if(!heading){if(dateElement)throw Error('既存のお知らせの見出しを確認できません。');heading=item;}
     body=[...item.querySelectorAll('p,[class*=excerpt],[class*=description],[class*=body]')].find(n=>n!==heading&&!heading.contains(n)&&!n.contains(heading)&&n!==dateElement&&!n.contains(dateElement)&&!metadata(n));
     e.prepend(item);inserted=[item];
    }
    const formatDate=before=>{const source=before.match(datePattern)?.[0]||before,parts=o.date.split('-');return source.includes('年')?parts[0]+'年'+parts[1]+'月'+parts[2]+'日':parts.join(source.includes('/')?'/':source.includes('-')?'-':'.');};
    const date=formatDate(text(heading));
    if(dateElement){writeText(dateElement,formatDate(text(dateElement)));if(dateElement.tagName==='TIME')dateElement.setAttribute('datetime',o.date);if(heading.contains(dateElement)){const tw=doc.createTreeWalker(heading,NodeFilter.SHOW_TEXT),nodes=[];let n;while(n=tw.nextNode())if(!dateElement.contains(n)&&n.nodeValue.trim())nodes.push(n);if(!nodes.length)heading.append(doc.createTextNode(o.title+(body?'':' — '+o.body)));else{nodes[0].nodeValue=o.title+(body?'':' — '+o.body);for(const rest of nodes.slice(1))rest.nodeValue='';}}else writeText(heading,o.title+(body?'':' — '+o.body));}
    else{const walker=doc.createTreeWalker(heading,NodeFilter.SHOW_TEXT);let n,dateNode;while(n=walker.nextNode())if(/^\s*\d{4}[.\/-]\d{1,2}[.\/-]\d{1,2}\s*$/.test(n.nodeValue)){dateNode=n;break;}
     if(dateNode){dateNode.nodeValue=date+'　';const titleNodes=[];const tw=doc.createTreeWalker(heading,NodeFilter.SHOW_TEXT);while(n=tw.nextNode())if(n!==dateNode&&n.nodeValue.trim())titleNodes.push(n);if(titleNodes.length){titleNodes[0].nodeValue=o.title+(body?'':' — '+o.body);for(const rest of titleNodes.slice(1))rest.nodeValue='';}else heading.append(doc.createTextNode(o.title+(body?'':' — '+o.body)));}
     else writeText(heading,(datePattern.test(text(heading))?date+'　':'')+o.title+(body?'':' — '+o.body));
    }
    if(body){
     writeText(body,o.body);
     for(const br of body.querySelectorAll('br'))br.remove();
    }
    for(const root of inserted){
     for(const blank of [...root.querySelectorAll('a,p')].reverse()){
      if(!text(blank)&&!blank.querySelector('svg,time'))blank.remove();
     }
    }
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
   }else if(o.type==='replace_image'||o.type==='insert_image'){
    const asset=assets.find(a=>a.id===o.value);let source;
    if(asset){if(!/^data:image\/(jpeg|png|webp);base64,[a-z0-9+/=]+$/i.test(asset.data))throw Error('写真の形式を確認できません。');source=asset.data;}
    else if(/^e\d+$/.test(o.value)&&o.value!==o.target){const other=doc.querySelector('[data-simy-edit-id="'+o.value+'"]');if(other&&!blocked(other)){if(other.tagName==='IMG'){source=other.getAttribute('src');if(source){try{source=new URL(source,doc.querySelector('base[href]')?.href||liveDocument?.baseURI).href;}catch{source=null;}}if(e.tagName==='IMG')e.alt=other.getAttribute('alt')||'';}else{const live=liveDocument?.querySelector('[data-simy-edit-id="'+o.value+'"]');const bg=live&&liveDocument.defaultView.getComputedStyle(live).backgroundImage;source=bg?.match(/^url\(["']?(https?:\/\/[^"')]+)["']?\)$/)?.[1];}}if(!source||!(/^https?:\/\//i.test(source)||/^data:image\/(jpeg|png|webp);base64,[a-z0-9+/=]+$/i.test(source)))throw Error('選んだ既存画像を読み込めません。');}
    else throw Error('差し替え元の写真を確認できません。');
    if(o.type==='insert_image'){
     let card=e;
     if(!['DIV','ARTICLE','LI','SECTION','FIGURE'].includes(card.tagName)){
      card=e.closest('article,li,figure,[data-simy-card],.card,[class*=card],[class*=feature],[class*=reason]');
      if(!card){const parent=e.parentElement;if(parent&&['DIV','SECTION'].includes(parent.tagName)&&parent!==doc.body&&[...parent.parentElement.children].some(s=>s!==parent&&s.tagName===parent.tagName&&s.querySelector('img')))card=parent;}
     }
     if(!card||card===doc.body||!['DIV','ARTICLE','LI','SECTION','FIGURE'].includes(card.tagName)||card.querySelector('img')||card.querySelectorAll('h1,h2,h3,h4').length>1)throw Error('画像の追加先を確認できません。');
     e=card;
     const img=doc.createElement('img');img.src=source;img.alt=o.title||'';img.setAttribute('data-simy-inserted-image','true');
     const siblings=[...e.parentElement.children].filter(n=>n!==e);const example=siblings.map(n=>n.querySelector('img')).find(Boolean);
     if(example){img.className=example.className;img.style.cssText=example.style.cssText;}
     img.style.setProperty('width','100%');img.style.setProperty('height','auto');img.style.setProperty('display','block');if(example?.getAttribute('width')&&example?.getAttribute('height'))img.style.setProperty('aspect-ratio',example.getAttribute('width')+'/'+example.getAttribute('height'));
     const sampleHeading=example?.parentElement?.querySelector('h1,h2,h3,h4');
     if(example&&sampleHeading&&(example.compareDocumentPosition(sampleHeading)&4))e.prepend(img);else e.append(img);e.setAttribute('data-simy-changed','true');changed.push(o.target);continue;
    }
    if(e.tagName==='IMG'){e.src=source;if(typeof o.title==='string'&&o.title.trim())e.alt=o.title.trim().slice(0,300);}else{e.style.setProperty('background-image','url("'+source.replace(/["\\\n\r]/g,'')+'")','important');}e.removeAttribute('srcset');e.removeAttribute('sizes');e.removeAttribute('loading');for(const source of e.closest('picture')?.querySelectorAll('source')||[])source.remove();e.setAttribute('data-simy-changed','true');changed.push(o.target);
   }else if(o.type==='redesign'){
    if(e!==doc.body||!['modern','editorial','warm'].includes(o.property)||!/^#[0-9a-f]{6}$/i.test(o.value))throw Error('デザイン指定を確認できません。');
    api.redesign(doc,o.value,liveDocument);e.setAttribute('data-simy-changed','true');changed.push(o.target);
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
