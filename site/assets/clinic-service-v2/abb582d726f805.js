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

 let previewSourceUrl='',editorReturn=openEditor;
 let busy=false,editBusy=false,objectUrl,currentHtml='',originalHtml='',history=[],chat=[],assets=[],context={goal:'',target:'',decisions:'',pending:''},assetSequence=0;
 // Use wall-clock time so background-tab throttling cannot undercount elapsed time.
 const makeElapsed=anchor=>{const output=document.createElement('p');output.className='small operation-elapsed';output.hidden=true;output.setAttribute('role','timer');output.setAttribute('aria-live','off');output.style.fontVariantNumeric='tabular-nums';anchor.after(output);let timer;
  return ()=>{clearInterval(timer);const started=Date.now();output.hidden=false;const tick=()=>{output.textContent='経過 '+Math.floor((Date.now()-started)/1000)+'秒';};tick();timer=setInterval(tick,1000);return ()=>{clearInterval(timer);tick();};};
 };
 const snapshot=()=>({html:currentHtml,context:{...context},chat:chat.map(x=>({...x})),assets:[...assets]});
 const restore=previous=>{context={...previous.context};chat=previous.chat.map(x=>({...x}));assets=[...previous.assets];photoInput.value='';photoStatus.textContent=assets.length?'添付：'+assets.map(a=>a.name).join('、'):'';updatePreview(previous.html);};
 // Chrome canvas JPEG may contain an ICC APP2 segment. Strip only that identified profile.
 const normalizeCanvasJpeg=dataUrl=>{try{
  const prefix='data:image/jpeg;base64,';if(typeof dataUrl!=='string'||!dataUrl.startsWith(prefix))return null;
  const encoded=dataUrl.slice(prefix.length);if(encoded.length>350000||encoded.length%4||!/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(encoded))return null;
  const raw=atob(encoded);if(btoa(raw)!==encoded||raw.length<32||raw.charCodeAt(0)!==255||raw.charCodeAt(1)!==216)return null;
  const byte=i=>raw.charCodeAt(i),word=i=>(byte(i)<<8)|byte(i+1),parts=[raw.slice(0,2)],chunks=new Set();let i=2,scan=false,ended=false,profileCount=0,profileBytes=0,segments=0;
  while(i<raw.length){const start=i;if(++segments>256||byte(i++)!==255)return null;while(byte(i)===255)i++;const marker=byte(i++);
   if(marker===217){if(i!==raw.length||!scan)return null;parts.push(raw.slice(start,i));ended=true;break;}
   if(![224,226,219,196,221,192,194,218].includes(marker)||i+2>raw.length)return null;
   const length=word(i),end=i+length;if(length<2||end>raw.length-2)return null;
   if(marker===226){const payload=i+2;if(scan||length<16||raw.slice(payload,payload+12)!=='ICC_PROFILE\0')return null;const sequence=byte(payload+12),count=byte(payload+13);if(!sequence||!count||count>16||sequence>count||(profileCount&&count!==profileCount)||chunks.has(sequence))return null;profileCount=count;chunks.add(sequence);profileBytes+=length;if(profileBytes>65536)return null;}
   else parts.push(raw.slice(start,end));i=end;
   if(marker===218){scan=true;const entropy=i;while(i<raw.length){if(byte(i)!==255){i++;continue;}const next=byte(i+1);if(next===0||(next>=208&&next<=215)){i+=2;continue;}break;}parts.push(raw.slice(entropy,i));}
  }
  if(!ended||(profileCount&&chunks.size!==profileCount))return null;return btoa(parts.join(''));
 }catch{return null;}};
 // Encode pixels locally; never send original files, EXIF or remote URLs to the image runner.
 const thumbnail=(source,width,height)=>{try{for(let edge=384;edge>=96;edge=Math.floor(edge*.75)){const canvas=document.createElement('canvas'),scale=Math.min(1,edge/Math.max(width,height));canvas.width=Math.max(1,Math.round(width*scale));canvas.height=Math.max(1,Math.round(height*scale));canvas.getContext('2d').drawImage(source,0,0,canvas.width,canvas.height);for(const quality of [.72,.5,.32]){const data=normalizeCanvasJpeg(canvas.toDataURL('image/jpeg',quality));if(data&&data.length<=16384)return data;}}}catch{}return null;};
 const editPayload=(message,base)=>{const nodes=window.SimyPreviewEdit.inventory(base,frame.contentDocument);let images=[];
  const asset=assets.at(-1);if(asset?.thumbnail)images=[{id:asset.id,mime:'image/jpeg',data:asset.thumbnail}];
  // Reuse already decoded browser pixels only. A tainted cross-origin canvas falls back to metadata.
  if(!asset){const candidates=nodes.filter(n=>n.kind==='image'&&n.tag==='img').map(n=>({n,live:frame.contentDocument?.querySelector('[data-simy-edit-id="'+n.id+'"]')})).filter(({live})=>live?.complete&&live.naturalWidth>1).sort((a,b)=>b.live.getBoundingClientRect().width*b.live.getBoundingClientRect().height-a.live.getBoundingClientRect().width*a.live.getBoundingClientRect().height);for(const {n,live} of candidates){const data=thumbnail(live,live.naturalWidth,live.naturalHeight);if(data){images=[{id:n.id,mime:'image/jpeg',data}];break;}}}
  const payload={request:message,context,nodes,history:chat.slice(-6),assets:assets.map(({id,name})=>({id,name})),images};
  // Preserve request, conversation state and images within the unchanged planner/queue budget.
  const retained=new Set(['e0',...images.map(image=>image.id)]);
  while(JSON.stringify(payload).length>46000&&payload.nodes.length>1){let index=payload.nodes.length-1;while(index>=0&&retained.has(payload.nodes[index].id))index--;if(index<0)break;payload.nodes.splice(index,1);}
  if(JSON.stringify(payload).length>46000)throw Error('会話と写真のデータ量が上限を超えました。依頼を短くしてください。');return payload;
 };
 const startRebuildElapsed=makeElapsed(status),startEditElapsed=makeElapsed(editForm);
 const photoInput=document.querySelector('#preview-photo'),photoStatus=document.querySelector('#preview-photo-status');
 photoInput.addEventListener('change',async()=>{const file=photoInput.files[0];if(!file)return;photoInput.disabled=true;
  try{if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>5*1024*1024)throw Error('写真はJPEG・PNG・WebP、5MB以内で選んでください。');
   const bitmap=await createImageBitmap(file),scale=Math.min(1,1600/Math.max(bitmap.width,bitmap.height));const canvas=document.createElement('canvas');canvas.width=Math.round(bitmap.width*scale);canvas.height=Math.round(bitmap.height*scale);canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close();
   assets=[...assets,{id:'a'+assetSequence++,name:file.name.slice(0,120),data:canvas.toDataURL('image/jpeg',.88),thumbnail:thumbnail(canvas,canvas.width,canvas.height)}].slice(-5);photoStatus.textContent='添付：'+file.name;chat.push({role:'user',text:'差し替え用の写真を添付しました：'+file.name.slice(0,120)});chat=chat.slice(-6);log('写真を添付しました。');if(context.goal&&!editBusy){editInput.value=editInput.value.trim()||'素材を追加しました。会話の内容に沿って続けてください。';editForm.requestSubmit();}
  }catch(e){photoStatus.textContent=e.message;photoInput.value='';}finally{photoInput.disabled=editBusy;}
 });
 for(const chip of document.querySelectorAll('[data-chat-prompt]'))chip.addEventListener('click',()=>{editInput.value=chip.dataset.chatPrompt;editInput.focus();});
 editInput.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();editForm.requestSubmit();}});
 const mobile=()=>matchMedia('(max-width:700px)').matches;
 const updatePreview=html=>{currentHtml=html;requestAnimationFrame(()=>{if(currentHtml===html)frame.srcdoc=html;});if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl=URL.createObjectURL(new Blob([html],{type:'text/html;charset=utf-8'}));download.href=objectUrl;undo.disabled=!history.length;};
 const log=(text,kind='')=>{document.querySelector('.preview-chat').classList.remove('is-empty');const p=document.createElement('p');p.textContent=text;if(kind)p.className=kind;conversation.append(p);conversation.scrollTop=conversation.scrollHeight;};
 const showEditor=()=>{if(!currentHtml)return;editor.showModal();document.body.classList.add('preview-editor-open');(mobile()?closeEditor:editInput).focus({preventScroll:true});};
 openEditor.addEventListener('click',showEditor);closeEditor.addEventListener('click',()=>editor.close());editor.addEventListener('close',()=>{document.body.classList.remove('preview-editor-open');editorReturn.focus({preventScroll:true});});
 const setEditBusy=value=>{editBusy=value;let pending=conversation.querySelector('.chat-thinking');if(value){pending=document.createElement('p');pending.className='chat-thinking';pending.setAttribute('role','status');pending.textContent='変更内容を考えています';conversation.append(pending);conversation.scrollTop=conversation.scrollHeight;}else pending?.remove();editForm.querySelector('[type=submit]').disabled=value;editForm.querySelector('[type=submit]').textContent=value?'…':'↑';undo.disabled=value||!history.length;reset.disabled=value;example.disabled=value;editInput.disabled=value;photoInput.disabled=value;editForm.setAttribute('aria-busy',String(value));};
 const pageOffer=document.querySelector('#preview-page-offer');
 document.querySelector('#page-offer-close').addEventListener('click',()=>pageOffer.close());
 document.querySelector('#page-offer-back').addEventListener('click',()=>pageOffer.close());
 document.querySelector('#page-offer-apply').addEventListener('click',()=>{pageOffer.close();document.querySelector('#preview-apply').click();});
 frame.addEventListener('load',()=>{try{const doc=frame.contentDocument;if(!doc)return;
  for(const link of doc.querySelectorAll('a,area,[role=button]')){link.removeAttribute('aria-disabled');link.setAttribute('tabindex','0');}
  const style=doc.createElement('style');style.textContent='a,area,button,[role=button],input[type=button],input[type=submit]{pointer-events:auto!important;cursor:pointer!important}';doc.head.append(style);
  for(const control of doc.querySelectorAll('button,input[type=button],input[type=submit]')){control.disabled=false;control.setAttribute('type','button');}
  doc.addEventListener('click',event=>{if(event.target.closest?.('a,area,button,[role=button],input[type=button],input[type=submit]')){event.preventDefault();event.stopImmediatePropagation();if(!pageOffer.open)pageOffer.showModal();}},true);
  doc.addEventListener('submit',event=>{event.preventDefault();event.stopImmediatePropagation();},true);
  doc.querySelector('[data-simy-changed]')?.scrollIntoView({block:'center',behavior:'instant'});
 }catch{}});
 editForm.addEventListener('submit',async event=>{event.preventDefault();if(editBusy||!editForm.reportValidity()||!currentHtml)return;const message=editInput.value.trim(),base=currentHtml;log(message,'preview-user-message');setEditBusy(true);const stopElapsed=startEditElapsed();
  try{
   const response=await fetch(new URL('/api/preview-edit',form.dataset.endpoint),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...editPayload(message,base),siteUrl:previewSourceUrl}),signal:AbortSignal.timeout(100000)});
   const plan=await response.json();if(!response.ok)throw Error(plan.error||'変更案を作成できませんでした。');
   if(currentHtml!==base)throw Error('ページの状態が変わりました。もう一度お試しください。');
   if(plan.status==='edit'){const changed=window.SimyPreviewEdit.applyPlan(base,plan,assets,frame.contentDocument);history.push(snapshot());if(history.length>10)history.shift();updatePreview(changed.html);log(changed.summary);}
   else if(['clarify','unsupported','answer'].includes(plan.status)){log(plan.question||plan.summary);}
   else throw Error('変更案の形式を確認できませんでした。');
   if(plan.context)context=plan.context;
   if(assets.length){const latest=assets.at(-1);photoStatus.textContent='添付：'+latest.name+(plan.visualInputs?.includes(latest.id)?'（画像の内容も回答に使用）':'（画像内容は未確認）');}
   chat.push({role:'user',text:message},{role:'assistant',text:(plan.question||plan.summary).slice(0,1500)});chat=chat.slice(-6);editInput.value='';
  }catch(error){log(error.name==='TimeoutError'?'変更案の作成に時間がかかっています。ページは変更していません。もう一度お試しください。':error.name==='TypeError'?'接続できませんでした。ページは変更していません。時間をおいて再度お試しください。':error.message,'preview-edit-error');}
  finally{stopElapsed();setEditBusy(false);if(!mobile()||editor.dataset.pane==='edit')editInput.focus({preventScroll:true});}
 });
 example.addEventListener('click',()=>{toolsMenu.hidePopover();editInput.value='明日は午後休診です。お知らせに追加してください。';editForm.requestSubmit();});
 const application=document.querySelector('#preview-application'),applicationForm=document.querySelector('#application-form');
 let applicationReturnToEditor=false,applicationTrigger=null,applicationSourceUrl='',applicationIntent='';
 const openApplication=({plan=null,assistance=false,sourceUrl='',returnToEditor=false,trigger=null,intent=''}={})=>{
  applicationIntent=String(intent).slice(0,500);window.SimyClinicCheckout?.configure?.(Boolean(applicationIntent));applicationReturnToEditor=returnToEditor;applicationTrigger=trigger;document.querySelector('#application-close').setAttribute('aria-label',returnToEditor?'編集体験に戻る':'閉じる');applicationSourceUrl=sourceUrl||document.querySelector('#diagnosis-url')?.value.trim()||previewSourceUrl;
  const selectedPlan=plan==='29800'?'29800':plan==='19800'?'19800':applicationForm.elements.plan.value||'19800';
  for(const radio of applicationForm.querySelectorAll('[name=plan]'))radio.checked=radio.value===selectedPlan;
  applicationForm.elements.assistance.checked=Boolean(assistance);applicationForm.dispatchEvent(new Event('change'));
  document.querySelector('#application-site').textContent=(applicationSourceUrl?'対象ホームページ：'+applicationSourceUrl:'')+(applicationIntent?' ／ ご相談内容：'+applicationIntent:'');
  document.querySelector('#application-enquiry').href=document.querySelector('#preview-enquiry').href;
  if(editor.open)editor.close();if(!application.open)application.showModal();application.scrollTop=0;
 };
 window.SimyClinicApplication={open:openApplication};
 document.querySelector('#preview-apply').addEventListener('click',event=>openApplication({sourceUrl:previewSourceUrl,returnToEditor:true,trigger:event.currentTarget}));
 document.querySelector('#application-close').addEventListener('click',()=>{application.close();if(applicationReturnToEditor)showEditor();else applicationTrigger?.focus({preventScroll:true});});
 applicationForm.addEventListener('change',()=>{const data=new FormData(applicationForm),total=Number(data.get('plan'))+(data.has('assistance')?49800:0);document.querySelector('#application-total').textContent=total.toLocaleString('ja-JP')+'円';document.querySelector('#application-tax').textContent='税込'+Math.round(total*1.1).toLocaleString('ja-JP')+'円';});
 applicationForm.addEventListener('submit',async event=>{event.preventDefault();await window.SimyClinicCheckout?.ready;if(!applicationForm.reportValidity())return;if(!applicationIntent&&await window.SimyClinicCheckout?.go(new FormData(applicationForm)))return;const data=new FormData(applicationForm),plan=data.get('plan')==='29800'?'セキュリティ強化':'基本保守';const body=['SIMY ご担当者様','HP管理の申し込みを希望します。','医療機関名：'+data.get('clinic'),'ご担当者名：'+data.get('contact'),'メールアドレス：'+data.get('email'),'対象URL：'+applicationSourceUrl,'プラン：'+plan,'更新代行：'+(data.has('assistance')?'追加する（月額＋49,800円・税別）':'追加しない'),'月額合計（税別）：'+document.querySelector('#application-total').textContent,...(applicationIntent?['ご相談内容：'+applicationIntent]:[]),'移管内容・費用のご案内をお願いします。'].join('\r\n');location.href='mailto:sales@simy.one?subject='+encodeURIComponent('SIMY HP管理のお申し込み')+'&body='+encodeURIComponent(body);});
 document.querySelector('#preview-show-pricing').addEventListener('click',()=>{editor.close();requestAnimationFrame(()=>document.querySelector('#pricing').scrollIntoView({block:'start',behavior:'instant'}));});
 undo.addEventListener('click',()=>{if(!editBusy&&history.length){restore(history.pop());log('ひとつ前の状態に戻しました。');}});reset.addEventListener('click',()=>{if(!editBusy&&originalHtml){history.push(snapshot());if(history.length>10)history.shift();context={goal:'',target:'',decisions:'',pending:''};chat=[];assets=[];photoInput.value='';photoStatus.textContent='';updatePreview(originalHtml);log('最初のプレビューに戻しました。');}});
 document.addEventListener('click',event=>{const link=event.target.closest('[data-rebuild-url]');if(!link)return;event.preventDefault();input.value=link.dataset.rebuildUrl;document.querySelector('#rebuild').scrollIntoView({block:'start',behavior:'instant'});input.focus({preventScroll:true});});
 input.addEventListener('input',()=>input.setCustomValidity(''));
 const runRebuild=async (activeForm)=>{
  const input=activeForm.querySelector('[name=url]'),button=activeForm.querySelector('[type=submit]'),status=activeForm.querySelector('.rebuild-status');
  if(busy){status.textContent='プレビューを作成中です。完了までお待ちください。';return;}
  if(!activeForm.reportValidity())return;
  const startElapsed=activeForm===form?startRebuildElapsed:(activeForm._startElapsed||(activeForm._startElapsed=makeElapsed(status)));
  let url;try{url=new URL(/^[a-z][a-z0-9+.-]*:/i.test(input.value.trim())?input.value.trim():'https://'+input.value.trim());if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.port||url.search)throw Error();url.hash='';url.pathname='/';}catch{input.setCustomValidity('http / https の公開URLを入力してください。認証情報や「?」以降は含めないでください。');input.reportValidity();return;}
  currentHtml='';originalHtml='';history=[];chat=[];assets=[];context={goal:'',target:'',decisions:'',pending:''};assetSequence=0;conversation.replaceChildren();frame.removeAttribute('srcdoc');if(objectUrl){URL.revokeObjectURL(objectUrl);objectUrl=null;}
  busy=true;button.disabled=true;button.textContent='作成中…';status.className='rebuild-status is-running';status.textContent='公開ページを読み込み、プレビューを作成しています…';result.hidden=true;const stopElapsed=startElapsed();
  try{
   const response=await fetch(form.dataset.endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url.href,rightsConfirmed:activeForm.elements.rights.checked}),signal:AbortSignal.timeout(80000)});
   const data=await response.json();if(!response.ok)throw Error(data.error||'プレビューを作成できませんでした。');
   if(data.mode!=='static-html5-preview'||typeof data.html!=='string'||data.html.length>2000000)throw Error('プレビューの形式を確認できませんでした。');
   originalHtml=window.SimyPreviewEdit.index(window.SimyPreviewEdit.prepare(data.html));history=[];chat=[];assets=[];context={goal:'',target:'',decisions:'',pending:''};assetSequence=0;photoInput.value='';photoStatus.textContent='';updatePreview(originalHtml);document.querySelector('#preview-source').textContent=url.hostname+' · 公開中のサイトは変更しません';conversation.replaceChildren();document.querySelector('.preview-chat').classList.add('is-empty');
   const enquiryBody='SIMY ご担当者様\r\n\r\n医療機関名：\r\nご担当者名：\r\nホームページURL：'+url.href+'\r\nご用件：ホームページの再現を体験しました。移管・保守について相談したいです。\r\n';document.querySelector('#preview-enquiry').href='mailto:sales@simy.one?subject='+encodeURIComponent('HP管理・移管の相談')+'&body='+encodeURIComponent(enquiryBody);
   status.className='rebuild-status';status.textContent='プレビューができました。もう一度開くには「編集画面を開く」を押してください。';previewSourceUrl=url.href;editorReturn=button;result.hidden=false;if(activeForm!==form){button.dataset.previewReady='true';button.dataset.sourceInput=input.value.trim();button.dataset.previewUrl=url.href;}showEditor();
  }catch(error){status.className='rebuild-status is-error';status.textContent=error.name==='TimeoutError'?'時間内に取得できませんでした。もう一度お試しください。':error.name==='TypeError'?'接続できませんでした。時間をおいて、もう一度お試しください。':error.message;}finally{stopElapsed();busy=false;button.disabled=false;button.innerHTML=button.dataset.previewReady?'編集画面を開く →':'作ってみる <span aria-hidden="true">→</span>';}
 };
 form.addEventListener('submit',event=>{event.preventDefault();runRebuild(form);});
 document.addEventListener('submit',event=>{const target=event.target;if(!target.matches('[data-report-rebuild]'))return;event.preventDefault();const trigger=target.querySelector('[type=submit]');if(trigger.dataset.previewReady&&currentHtml&&!busy&&target.querySelector('[name=url]').value.trim()===trigger.dataset.sourceInput&&previewSourceUrl===trigger.dataset.previewUrl){editorReturn=trigger;showEditor();return;}runRebuild(target);});
 document.addEventListener('input',event=>{const target=event.target.closest('[data-report-rebuild]');if(!target)return;target.querySelector('[name=url]').setCustomValidity('');delete target.querySelector('[type=submit]').dataset.previewReady;target.querySelector('[type=submit]').textContent='作ってみる →';});
window.dispatchEvent(new Event('simy-application-ready'));
})();
