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
