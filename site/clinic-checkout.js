(function(global){
'use strict';
const amounts={basic:19800,security:29800,basic_manager:69600,security_manager:79600};
function validate(config){
 if(config?.enabled!==true)return null;
 const links={};
 for(const [plan,amount] of Object.entries(amounts)){
  const item=config.plans?.[plan];if(item?.monthlyYen!==amount||item?.taxInclusiveYen!==Math.round(amount*1.1))return null;
  let url;try{url=new URL(item.url);}catch{return null;}
  if(url.protocol!=='https:'||url.hostname!=='buy.stripe.com'||url.port||url.username||url.password||url.search||url.hash||!/^\/[a-zA-Z0-9]+$/.test(url.pathname)||url.pathname.startsWith('/test'))return null;
  links[plan]=url.href;
 }
 return links;
}
function select(links,plan,assistance){const key=plan==='19800'?'basic':plan==='29800'?'security':null;if(!key)throw Error('プランを選択してください。');return links?.[key+(assistance?'_manager':'')]||null;}
if(typeof module!=='undefined'&&module.exports){module.exports={validate,select};return;}
let links=null;
const applicationForm=document.querySelector('#application-form');
const initialCopy={submit:applicationForm.querySelector('[type=submit]').textContent,next:applicationForm.querySelector('.application-next').textContent,note:applicationForm.querySelector('.application-note').textContent};
function presentation(consultation=false){
 const form=applicationForm,fields=form.querySelectorAll('fieldset')[1];fields.disabled=Boolean(links)&&!consultation;fields.hidden=Boolean(links)&&!consultation;
 form.querySelector('[type=submit]').textContent=consultation?'相談メールを作成する →':links?'Stripeの決済画面へ →':initialCopy.submit;
 form.querySelector('.application-next').textContent=consultation?'ご希望の仕組みと対象医院を確認して、SIMYへの相談メールを作成します。':links?'お申し込み内容と月額料金を、Stripeの画面でご確認ください。':initialCopy.next;
 form.querySelector('.application-note').textContent=consultation?'表示料金はHP管理・更新代行プランの参考額です。録音・記事化・近隣医院の変化確認の実施範囲と費用は、別途ご相談のうえで決めます。':links?'医院情報・お支払い情報はStripeの画面で入力します。ドメインの取得・更新費用は別途です。':initialCopy.note;
}
const ready=fetch('/hp-management/clinic-checkout.json',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(config=>{links=validate(config);presentation();}).catch(()=>{});
global.SimyClinicCheckout={ready,configure:async consultation=>{await ready;presentation(consultation);},go:async data=>{await ready;const url=select(links,data.get('plan'),data.has('assistance'));if(!url)return false;const destination=new URL(url);destination.searchParams.set('client_reference_id','hp_'+crypto.randomUUID().replaceAll('-',''));location.assign(destination.href);return true;}};
})(typeof window==='undefined'?globalThis:window);
