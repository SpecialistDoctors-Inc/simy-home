(() => {
 'use strict';
 const form=document.querySelector('#rebuild-form');if(!form)return;
 const input=form.querySelector('[name="url"]'),button=form.querySelector('button'),status=document.querySelector('#rebuild-status'),result=document.querySelector('#rebuild-result'),frame=document.querySelector('#rebuild-preview'),download=document.querySelector('#rebuild-download');
 const editor=document.querySelector('#rebuild-editor'),openEditor=document.querySelector('#rebuild-editor-open'),closeEditor=document.querySelector('#rebuild-editor-close'),editForm=document.querySelector('#preview-edit-form'),editInput=document.querySelector('#preview-edit-message'),conversation=document.querySelector('#preview-conversation'),undo=document.querySelector('#preview-edit-undo'),reset=document.querySelector('#preview-edit-reset');
 const example=document.querySelector('#preview-edit-example');
 const toolsMenu=document.querySelector('#preview-tools');
 document.querySelector('#preview-attach').addEventListener('click',()=>{toolsMenu.hidePopover();document.querySelector('#preview-photo').click();});
 for(const option of toolsMenu.querySelectorAll('[data-edit-prompt]'))option.addEventListener('click',()=>{toolsMenu.hidePopover();editInput.value=option.dataset.editPrompt;editInput.focus();});
 toolsMenu.addEventListener('toggle',event=>{if(event.newState==='open'){const trigger=editForm.querySelector('[popovertarget]'),box=trigger.getBoundingClientRect();toolsMenu.style.left=Math.max(8,Math.min(box.left,innerWidth-toolsMenu.offsetWidth-8))+'px';toolsMenu.style.top=Math.max(8,box.top-toolsMenu.offsetHeight-8)+'px';}});

 let busy=false,editBusy=false,objectUrl,currentHtml='',originalHtml='',history=[],chat=[],assets=[];
 // Use wall-clock time so background-tab throttling cannot undercount elapsed time.
 const makeElapsed=anchor=>{const output=document.createElement('p');output.className='small operation-elapsed';output.hidden=true;output.setAttribute('role','timer');output.setAttribute('aria-live','off');output.style.fontVariantNumeric='tabular-nums';anchor.after(output);let timer;
  return ()=>{clearInterval(timer);const started=Date.now();output.hidden=false;const tick=()=>{output.textContent='経過 '+Math.floor((Date.now()-started)/1000)+'秒';};tick();timer=setInterval(tick,1000);return ()=>{clearInterval(timer);tick();};};
 };
 const startRebuildElapsed=makeElapsed(status),startEditElapsed=makeElapsed(editForm);
 const photoInput=document.querySelector('#preview-photo'),photoStatus=document.querySelector('#preview-photo-status');
 photoInput.addEventListener('change',async()=>{const file=photoInput.files[0];if(!file)return;photoInput.disabled=true;
  try{if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>5*1024*1024)throw Error('写真はJPEG・PNG・WebP、5MB以内で選んでください。');
   const bitmap=await createImageBitmap(file),scale=Math.min(1,1600/Math.max(bitmap.width,bitmap.height));const canvas=document.createElement('canvas');canvas.width=Math.round(bitmap.width*scale);canvas.height=Math.round(bitmap.height*scale);canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close();
   assets=[{id:'a0',name:file.name.slice(0,120),data:canvas.toDataURL('image/jpeg',.88)}];photoStatus.textContent='添付：'+file.name;log('写真を添付しました。差し替えたい写真の場所を入力してください。');
  }catch(e){photoStatus.textContent=e.message;photoInput.value='';}finally{photoInput.disabled=false;}
 });
 const mobile=()=>matchMedia('(max-width:700px)').matches;
 const setPane=pane=>{editor.dataset.pane=pane;for(const tab of editor.querySelectorAll('[data-preview-pane]'))tab.setAttribute('aria-pressed',String(tab.dataset.previewPane===pane));};
 for(const tab of editor.querySelectorAll('[data-preview-pane]'))tab.addEventListener('click',()=>{setPane(tab.dataset.previewPane);if(tab.dataset.previewPane==='edit')editInput.focus({preventScroll:true});});
 const updatePreview=html=>{currentHtml=html;if(editor.open&&mobile())setPane('canvas');requestAnimationFrame(()=>{if(currentHtml===html)frame.srcdoc=html;});if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl=URL.createObjectURL(new Blob([html],{type:'text/html;charset=utf-8'}));download.href=objectUrl;undo.disabled=!history.length;};
 const log=(text,kind='')=>{const p=document.createElement('p');p.textContent=text;if(kind)p.className=kind;conversation.append(p);conversation.scrollTop=conversation.scrollHeight;};
 const showEditor=()=>{if(!currentHtml)return;setPane(mobile()?'canvas':'edit');editor.showModal();document.body.classList.add('preview-editor-open');(mobile()?closeEditor:editInput).focus({preventScroll:true});};
 openEditor.addEventListener('click',showEditor);closeEditor.addEventListener('click',()=>editor.close());editor.addEventListener('close',()=>{document.body.classList.remove('preview-editor-open');openEditor.focus({preventScroll:true});});
 const setEditBusy=value=>{editBusy=value;editForm.querySelector('[type=submit]').disabled=value;editForm.querySelector('[type=submit]').textContent=value?'…':'↑';undo.disabled=value||!history.length;reset.disabled=value;example.disabled=value;editInput.disabled=value;photoInput.disabled=value;editForm.setAttribute('aria-busy',String(value));};
 frame.addEventListener('load',()=>{try{const mark=frame.contentDocument?.querySelector('[data-simy-changed]');mark?.scrollIntoView({block:'center',behavior:'instant'});}catch{}});
 editForm.addEventListener('submit',async event=>{event.preventDefault();if(editBusy||!editForm.reportValidity()||!currentHtml)return;const message=editInput.value.trim(),base=currentHtml;log(message,'preview-user-message');setEditBusy(true);const stopElapsed=startEditElapsed();
  try{
   const response=await fetch(new URL('/api/preview-edit',form.dataset.endpoint),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request:message,nodes:window.SimyPreviewEdit.inventory(base,frame.contentDocument),history:chat.slice(-6),assets:assets.map(({id,name})=>({id,name}))}),signal:AbortSignal.timeout(100000)});
   const plan=await response.json();if(!response.ok)throw Error(plan.error||'変更案を作成できませんでした。');
   if(currentHtml!==base)throw Error('ページの状態が変わりました。もう一度お試しください。');
   if(plan.status==='edit'){const changed=window.SimyPreviewEdit.applyPlan(base,plan,assets,frame.contentDocument);history.push(base);if(history.length>10)history.shift();updatePreview(changed.html);log(changed.summary);}
   else if(['clarify','unsupported'].includes(plan.status)){log(plan.question||plan.summary);if(mobile())setPane('edit');}
   else throw Error('変更案の形式を確認できませんでした。');
   chat.push({role:'user',text:message},{role:'assistant',text:(plan.question||plan.summary).slice(0,1500)});chat=chat.slice(-6);editInput.value='';
  }catch(error){log(error.name==='TimeoutError'?'変更案の作成に時間がかかっています。ページは変更していません。もう一度お試しください。':error.name==='TypeError'?'接続できませんでした。ページは変更していません。時間をおいて再度お試しください。':error.message,'preview-edit-error');}
  finally{stopElapsed();setEditBusy(false);if(!mobile()||editor.dataset.pane==='edit')editInput.focus({preventScroll:true});}
 });
 example.addEventListener('click',()=>{toolsMenu.hidePopover();editInput.value='明日は午後休診です。お知らせに追加してください。';editForm.requestSubmit();});
 document.querySelector('#preview-show-pricing').addEventListener('click',()=>{editor.close();requestAnimationFrame(()=>document.querySelector('#pricing').scrollIntoView({block:'start',behavior:'instant'}));});
 undo.addEventListener('click',()=>{if(!editBusy&&history.length){chat=[];updatePreview(history.pop());log('ひとつ前の状態に戻しました。');}});reset.addEventListener('click',()=>{if(!editBusy&&currentHtml!==originalHtml){chat=[];history.push(currentHtml);if(history.length>10)history.shift();updatePreview(originalHtml);log('最初のプレビューに戻しました。');}});
 document.addEventListener('click',event=>{const link=event.target.closest('[data-rebuild-url]');if(!link)return;event.preventDefault();input.value=link.dataset.rebuildUrl;document.querySelector('#rebuild').scrollIntoView({block:'start',behavior:'instant'});input.focus({preventScroll:true});});
 input.addEventListener('input',()=>input.setCustomValidity(''));
 form.addEventListener('submit',async event=>{
  event.preventDefault();if(busy||!form.reportValidity())return;
  let url;try{url=new URL(/^[a-z][a-z0-9+.-]*:/i.test(input.value.trim())?input.value.trim():'https://'+input.value.trim());if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.port||url.search)throw Error();url.hash='';url.pathname='/';}catch{input.setCustomValidity('http / https の公開URLを入力してください。認証情報や「?」以降は含めないでください。');input.reportValidity();return;}
  busy=true;button.disabled=true;button.textContent='作成中…';status.className='rebuild-status is-running';status.textContent='公開ページを読み込み、プレビューを作成しています…';result.hidden=true;const stopElapsed=startRebuildElapsed();
  try{
   const response=await fetch(form.dataset.endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url.href,rightsConfirmed:form.elements.rights.checked}),signal:AbortSignal.timeout(80000)});
   const data=await response.json();if(!response.ok)throw Error(data.error||'プレビューを作成できませんでした。');
   if(data.mode!=='static-html5-preview'||typeof data.html!=='string'||data.html.length>2000000)throw Error('プレビューの形式を確認できませんでした。');
   originalHtml=window.SimyPreviewEdit.index(window.SimyPreviewEdit.prepare(data.html));history=[];chat=[];assets=[];photoInput.value='';photoStatus.textContent='';updatePreview(originalHtml);document.querySelector('#preview-source').textContent=url.hostname+' · 公開中のサイトは変更しません';conversation.replaceChildren();log('今日は、どこを変えましょうか。');
   const enquiryBody='SIMY ご担当者様\r\n\r\n医療機関名：\r\nご担当者名：\r\nホームページURL：'+url.href+'\r\nご用件：ホームページの再現を体験しました。移管・保守について相談したいです。\r\n';document.querySelector('#preview-enquiry').href='mailto:sales@simy.one?subject='+encodeURIComponent('HP管理・移管の相談')+'&body='+encodeURIComponent(enquiryBody);
   status.className='rebuild-status';status.textContent='プレビューができました。';result.hidden=false;result.scrollIntoView({block:'start',behavior:'instant'});showEditor();
  }catch(error){status.className='rebuild-status is-error';status.textContent=error.name==='TimeoutError'?'時間内に取得できませんでした。もう一度お試しください。':error.name==='TypeError'?'接続できませんでした。時間をおいて、もう一度お試しください。':error.message;}finally{stopElapsed();busy=false;button.disabled=false;button.innerHTML='作ってみる <span aria-hidden="true">→</span>';}
 });
})();
