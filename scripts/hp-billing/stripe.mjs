// Operator-only billing integration. Never import this module into the public site.
import { createHash } from 'node:crypto';
import { domainToASCII } from 'node:url';
export const plans = Object.freeze({basic:14800,security:29800,basic_manager:49800,security_manager:64800});
const names = {basic:'HP管理・基本保守',security:'HP管理・セキュリティ強化',basic_manager:'HP管理・基本保守（担当者付き）',security_manager:'HP管理・セキュリティ強化（担当者付き）'};
export function validate(q, now=Date.now()) {
  if (!q || !/^[a-zA-Z0-9_-]{8,80}$/.test(q.id)) throw Error('Invalid quote ID');
  if (!Object.hasOwn(plans,q.plan)) throw Error('Invalid plan');
  if (!/^cus_[a-zA-Z0-9]+$/.test(q.customer)) throw Error('Stripe customer required');
  if (!Number.isFinite(Date.parse(q.expiresAt)) || Date.parse(q.expiresAt)<=now) throw Error('Quote expired');
  if (!q.approvalReference || typeof q.approvalReference!=='string') throw Error('Customer-approved quote reference required');
  const domain=domainToASCII(q.domain || '').toLowerCase();
  if (!/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/.test(domain)) throw Error('Domain required, without URL path');
  if (!Number.isSafeInteger(q.domainYen) || q.domainYen<=0 || q.domainYen>1000000) throw Error('Domain price must be positive JPY, excluding tax');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(q.periodStart) || !/^\d{4}-\d{2}-\d{2}$/.test(q.periodEnd) || !(Date.parse(q.periodStart)<Date.parse(q.periodEnd))) throw Error('Domain coverage dates required');
  if (!/^txr_[a-zA-Z0-9]+$/.test(q.taxRate)) throw Error('Configured Japanese tax rate required');
  return {...q,domain};
}
export function quoteHash(q) { return createHash('sha256').update(JSON.stringify(q)).digest('hex'); }
export function checkoutParams(input) {
  const q=validate(input), p=new URLSearchParams({mode:'subscription',customer:q.customer,locale:'ja',client_reference_id:q.id,
    success_url:'https://simy.one/hp-management/clinic/?payment=returned',cancel_url:'https://simy.one/hp-management/clinic/#pricing'});
  p.set('metadata[service]','hp_management'); p.set('metadata[quote_id]',q.id); p.set('metadata[quote_hash]',quoteHash(q));
  p.set('subscription_data[metadata][service]','hp_management'); p.set('subscription_data[metadata][domain]',q.domain);
  p.set('subscription_data[metadata][quote_id]',q.id);
  const items=[{name:`SIMY ${names[q.plan]}`,amount:plans[q.plan],monthly:true},
    {name:`ドメイン費用 ${q.domain}（${q.periodStart}〜${q.periodEnd}）`,amount:q.domainYen}];
  items.forEach((item,i)=>{
    const root=`line_items[${i}]`; p.set(`${root}[quantity]`,'1'); p.set(`${root}[tax_rates][0]`,q.taxRate);
    p.set(`${root}[price_data][currency]`,'jpy'); p.set(`${root}[price_data][unit_amount]`,String(item.amount));
    p.set(`${root}[price_data][tax_behavior]`,'exclusive');p.set(`${root}[price_data][product_data][name]`,item.name);
    if(item.monthly) p.set(`${root}[price_data][recurring][interval]`,'month');
  });
  p.set('custom_text[submit][message]','HP管理料は毎月、今回のドメイン費用は初回のみ請求します。次回のドメイン更新料は事前にご案内します。');
  return p;
}
export function renewalParams(input,subscription) {
  const q=validate(input);
  if(subscription.customer!==q.customer || subscription.metadata?.service!=='hp_management' || subscription.metadata?.domain!==q.domain || subscription.status!=='active' || !/^sub_[a-zA-Z0-9]+$/.test(subscription.id)) throw Error('Subscription/customer/domain mismatch or inactive subscription');
  return new URLSearchParams({customer:q.customer,subscription:subscription.id,currency:'jpy',amount:String(q.domainYen),
    description:`ドメイン更新料 ${q.domain}（${q.periodStart}〜${q.periodEnd}）`,
    'tax_rates[0]':q.taxRate,'metadata[quote_id]':q.id,'metadata[service]':'hp_management',
    'period[start]':String(Date.parse(q.periodStart)/1000),'period[end]':String(Date.parse(q.periodEnd)/1000)});
}
export function paidSession(session,q) {
  return session.status==='complete' && session.payment_status==='paid' && session.customer===q.customer &&
    session.client_reference_id===q.id && session.metadata?.quote_hash===quoteHash(validate(q,0)) && session.mode==='subscription' && !!session.subscription;
}
export function stripeClient(key,{fetcher=fetch}={}) {
  if(!/^(sk|rk)_(test|live)_/.test(key||'')) throw Error('STRIPE_SECRET_KEY is not configured');
  return async (path,params,idempotencyKey)=>{
    const response=await fetcher(`https://api.stripe.com/v1/${path}`,{method:params?'POST':'GET',
      headers:{Authorization:`Bearer ${key}`,'Stripe-Version':'2025-06-30.basil',...(params?{'Content-Type':'application/x-www-form-urlencoded','Idempotency-Key':idempotencyKey}: {})},body:params?.toString(),signal:AbortSignal.timeout(30000)});
    const data=await response.json();
    if(!response.ok) throw Error(`Stripe request failed (${response.status}; ${data.error?.code || 'unknown'}). Reconcile before retrying.`);
    return data;
  };
}
