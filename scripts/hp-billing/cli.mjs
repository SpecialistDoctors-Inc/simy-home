import {readFile,mkdir,writeFile,appendFile,rm} from 'node:fs/promises';
import {resolve} from 'node:path';
import {validate,quoteHash,checkoutParams,renewalParams,paidSession,stripeClient} from './stripe.mjs';
const [action,file,resource]=process.argv.slice(2);
if(!['preview','checkout','verify','renewal'].includes(action)||!file) throw Error('Usage: node scripts/hp-billing/cli.mjs preview|checkout|verify|renewal quote.json [session/subscription ID]');
const q=validate(JSON.parse(await readFile(file,'utf8')),action==='verify'?0:Date.now());
if(action==='preview') {console.log(checkoutParams(q).toString());process.exit(0);}
const key=process.env.STRIPE_SECRET_KEY;
if(key?.includes('_live_') && process.env.HP_BILLING_ALLOW_LIVE!=='1') throw Error('Live writes disabled: confirm approved quote before enabling HP_BILLING_ALLOW_LIVE');
const stripe=stripeClient(key);
const tax=await stripe(`tax_rates/${q.taxRate}`);
if(!tax.active||tax.inclusive||tax.percentage!==10) throw Error('Expected active, exclusive 10% tax rate');
const customer=await stripe(`customers/${q.customer}`);
if(customer.deleted) throw Error('Customer is deleted');
if(action==='verify') {
  if(!/^cs_(test_|live_)?[A-Za-z0-9]+$/.test(resource||''))throw Error('Session ID required');
  const session=await stripe(`checkout/sessions/${resource}`);
  if(!paidSession(session,q))throw Error('Payment not confirmed; do not transfer/register domain');
  console.log(JSON.stringify({id:session.id,subscription:session.subscription,paid:true,domainProvisioned:false}));
  process.exit(0);
}
// Durable operator ledger: do not put it under site/ or commit it to Git.
const root=resolve(process.env.HP_BILLING_LEDGER || `${process.env.HOME}/.simy-hp-billing`);
await mkdir(root,{recursive:true,mode:0o700});
const lock=`${root}/billing.lock`; await mkdir(lock,{mode:0o700});
try {
  const token=action==='renewal'?`${q.customer}-${q.domain}-${q.periodStart}-${q.periodEnd}`:q.id;
  const receipt=`${root}/${action}-${token}.json`;
  let existing;try{existing=JSON.parse(await readFile(receipt,'utf8'));}catch(e){if(e.code!=='ENOENT')throw e;}
  if(existing) {
    if(existing.hash!==quoteHash(q)) throw Error('Quote changed after recording: reconcile existing Stripe operation');
    if(existing.state==='complete'){console.log(JSON.stringify(existing.result));process.exitCode=0;}
    else throw Error('Uncertain previous attempt: reconcile in Stripe before retrying. Do not delete the receipt.');
  } else {
    if(action==='verify'&&!/^cs_(test_|live_)?[A-Za-z0-9]+$/.test(resource||''))throw Error('Session ID required');
    if(action==='renewal'&&!/^sub_[A-Za-z0-9]+$/.test(resource||''))throw Error('Subscription ID required');
    await writeFile(receipt,JSON.stringify({hash:quoteHash(q),state:'pending',at:new Date().toISOString()}),{flag:'wx',mode:0o600});
    let result;
    if(action==='checkout') {const s=await stripe('checkout/sessions',checkoutParams(q),`hp-checkout-${q.id}`);result={id:s.id,url:s.url};}
    if(action==='renewal') {const sub=await stripe(`subscriptions/${resource}`);const item=await stripe('invoiceitems',renewalParams(q,sub),`hp-renew-${token}`);result={id:item.id,status:'queued_for_next_subscription_invoice',paid:false};}
    if(action==='verify') {const s=await stripe(`checkout/sessions/${resource}`);if(!paidSession(s,q))throw Error('Payment not confirmed; do not transfer/register domain');result={id:s.id,subscription:s.subscription,paid:true,domainProvisioned:false};}
    await writeFile(receipt,JSON.stringify({hash:quoteHash(q),state:'complete',result,at:new Date().toISOString()}),{mode:0o600});
    await appendFile(`${root}/audit.jsonl`,JSON.stringify({at:new Date().toISOString(),action,quoteId:q.id,stripeId:result.id})+'\n',{mode:0o600});
    console.log(JSON.stringify(result));
  }
} finally {await rm(lock,{recursive:true});}
