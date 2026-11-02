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
const ready=fetch('/hp-management/clinic-checkout.json',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(config=>{
 links=validate(config);if(!links)return;
 const form=document.querySelector('#application-form'),fields=form.querySelectorAll('fieldset')[1];fields.disabled=true;fields.hidden=true;
 form.querySelector('[type=submit]').textContent='Stripeの決済画面へ →';
 form.querySelector('.application-next').textContent='お申し込み内容と月額料金を、Stripeの画面でご確認ください。';
 form.querySelector('.application-note').textContent='医院情報・お支払い情報はStripeの画面で入力します。ドメインの取得・更新費用は別途です。';
}).catch(()=>{});
global.SimyClinicCheckout={ready,go:async data=>{await ready;const url=select(links,data.get('plan'),data.has('assistance'));if(!url)return false;const destination=new URL(url);destination.searchParams.set('client_reference_id','hp_'+crypto.randomUUID().replaceAll('-',''));location.assign(destination.href);return true;}};
})(typeof window==='undefined'?globalThis:window);
