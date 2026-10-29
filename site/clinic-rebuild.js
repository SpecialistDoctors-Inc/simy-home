(() => {
 'use strict';
 const form=document.querySelector('#rebuild-form');if(!form)return;
 const input=form.querySelector('[name="url"]'),button=form.querySelector('button'),status=document.querySelector('#rebuild-status'),result=document.querySelector('#rebuild-result'),frame=document.querySelector('#rebuild-preview'),download=document.querySelector('#rebuild-download');
 let busy=false,objectUrl;
 document.addEventListener('click',event=>{const link=event.target.closest('[data-rebuild-url]');if(!link)return;event.preventDefault();input.value=link.dataset.rebuildUrl;document.querySelector('#rebuild').scrollIntoView({block:'start',behavior:'instant'});input.focus({preventScroll:true});});
 input.addEventListener('input',()=>input.setCustomValidity(''));
 form.addEventListener('submit',async event=>{
  event.preventDefault();if(busy||!form.reportValidity())return;
  let url;try{url=new URL(/^[a-z][a-z0-9+.-]*:/i.test(input.value.trim())?input.value.trim():'https://'+input.value.trim());if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.port||url.search)throw Error();url.hash='';url.pathname='/';}catch{input.setCustomValidity('http / https の公開URLを入力してください。認証情報や「?」以降は含めないでください。');input.reportValidity();return;}
  busy=true;button.disabled=true;button.textContent='作成中…';status.className='rebuild-status is-running';status.textContent='公開ページを読み込み、プレビューを作成しています…';result.hidden=true;
  try{
   const response=await fetch(form.dataset.endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url.href,rightsConfirmed:form.elements.rights.checked}),signal:AbortSignal.timeout(80000)});
   const data=await response.json();if(!response.ok)throw Error(data.error||'プレビューを作成できませんでした。');
   if(data.mode!=='static-html5-preview'||typeof data.html!=='string'||data.html.length>2000000)throw Error('プレビューの形式を確認できませんでした。');
   frame.srcdoc=data.html;
   const versions=document.querySelector('#rebuild-versions');versions.replaceChildren();
   const table=document.createElement('table');const caption=document.createElement('caption');caption.textContent='再現したトップページの構成・更新状況';table.append(caption);
   const head=document.createElement('thead'),headRow=document.createElement('tr');for(const label of ['項目','再現したページ']){const th=document.createElement('th');th.textContent=label;headRow.append(th);}head.append(headRow);table.append(head);const body=document.createElement('tbody');
   const rows=[['生成日時',new Date(data.generatedAt||Date.now()).toLocaleString('ja-JP')],['HTML・CSS','ブラウザーの標準仕様で生成'],['JavaScriptライブラリ','0件。旧サイトのJavaScriptは引き継いでいません。'],['PHP・WordPressの実行','なし。静的HTMLとして生成しています。'],['元サイトのCSS参照',String(data.externalStylesheets??0)+'件。外部CSSの版・更新状況は未確認です。']];
   for(const [label,value]of rows){const tr=document.createElement('tr'),th=document.createElement('th'),td=document.createElement('td');th.scope='row';th.textContent=label;td.textContent=value;tr.append(th,td);body.append(tr);}table.append(body);versions.append(table);
   if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl=URL.createObjectURL(new Blob([data.html],{type:'text/html;charset=utf-8'}));download.href=objectUrl;
   status.className='rebuild-status';status.textContent='プレビューができました。';result.hidden=false;result.scrollIntoView({block:'start',behavior:'instant'});
  }catch(error){status.className='rebuild-status is-error';status.textContent=error.name==='TimeoutError'?'時間内に取得できませんでした。もう一度お試しください。':error.message;}finally{busy=false;button.disabled=false;button.innerHTML='作ってみる <span aria-hidden="true">→</span>';}
 });
})();
