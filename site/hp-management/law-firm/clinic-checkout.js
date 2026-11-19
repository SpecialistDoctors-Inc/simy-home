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
function sandboxCheckoutUrl(modes,plan,assistance){
 if(modes.length!==1||modes[0]!=='sandbox')return null;
 const key=plan==='19800'?'basic':plan==='29800'?'security':null;
 if(!key)return null;
 const url=new URL('https://app.simy.one/signup/sandbox/');
 url.search=new URLSearchParams({product:'law-firm',plan:key+(assistance?'_manager':'')}).toString();
 return url.href;
}
if(typeof module!=='undefined'&&module.exports){module.exports={validate,select,sandboxCheckoutUrl};return;}
let links=null;
const modes=new URLSearchParams(location.search).getAll('checkout_mode');
const applicationForm=document.querySelector('#application-form');
const initialCopy={submit:applicationForm.querySelector('[type=submit]').textContent,next:applicationForm.querySelector('.application-next').textContent,note:applicationForm.querySelector('.application-note').textContent};
function presentation(consultation=false){
 const form=applicationForm,fields=form.querySelectorAll('fieldset')[1];
 if(modes.length){
  const submit=form.querySelector('[type=submit]');
  const valid=modes.length===1&&modes[0]==='sandbox';
  fields.disabled=true;
  fields.hidden=true;
  submit.disabled=!valid||consultation;
  submit.textContent=consultation?'相談（テストモード）':'テスト決済に進む →';
  form.querySelector('.application-next').textContent=consultation?'テストモードでは相談メールは送信されません。':valid?'検証用アカウントでログインして、Stripeのテスト決済に進みます。':'テスト申込リンクを確認してください。';
  form.querySelector('.application-note').textContent='テストモードです。架空の情報とStripeのテストカードを使用してください。実際の請求はありません。';
  return;
 }
 fields.disabled=Boolean(links)&&!consultation;fields.hidden=Boolean(links)&&!consultation;
 form.querySelector('[type=submit]').textContent=consultation?'相談メールを作成する →':links?'Stripeの決済画面へ →':initialCopy.submit;
 form.querySelector('.application-next').textContent=consultation?'ご希望の仕組みと対象事務所を確認して、SIMYへの相談メールを作成します。':links?'お申し込み内容と月額料金を、Stripeの画面でご確認ください。':initialCopy.next;
 form.querySelector('.application-note').textContent=consultation?'表示料金はHP管理・更新代行プランの参考額です。ご希望の機能と対象サイトを確認し、対応範囲と費用をご案内します。':links?'事務所情報・お支払い情報はStripeの画面で入力します。ドメインの取得・更新費用は別途です。':initialCopy.note;
}
const ready=modes.length?Promise.resolve().then(()=>presentation()):fetch('/hp-management/law-firm/hp-management/clinic-checkout.json',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(config=>{links=validate(config);presentation();}).catch(()=>{});
global.SimyClinicCheckout={ready,sandboxCheckoutUrl,configure:async consultation=>{await ready;presentation(consultation);},go:async data=>{await ready;if(modes.length)return false;const url=select(links,data.get('plan'),data.has('assistance'));if(!url)return false;const destination=new URL(url);destination.searchParams.set('client_reference_id','hp_'+crypto.randomUUID().replaceAll('-',''));location.assign(destination.href);return true;}};
})(typeof window==='undefined'?globalThis:window);
