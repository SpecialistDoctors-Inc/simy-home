const{test}=require('node:test');const assert=require('node:assert/strict');const{validate,select}=require('../site/clinic-checkout.js');
const config=()=>({enabled:true,plans:Object.fromEntries(Object.entries({basic:19800,security:29800,basic_manager:69600,security_manager:79600}).map(([k,n],i)=>[k,{monthlyYen:n,taxInclusiveYen:Math.round(n*1.1),url:'https://buy.stripe.com/example'+i}]))});
test('checkout requires all four live links with current prices and tax',()=>{const c=config(),links=validate(c);assert.equal(select(links,'19800',false),c.plans.basic.url);assert.equal(select(links,'19800',true),c.plans.basic_manager.url);assert.equal(select(links,'29800',true),c.plans.security_manager.url);assert.equal(select(links,'29800',false),c.plans.security.url);c.plans.basic.monthlyYen=14800;assert.equal(validate(c),null)});
test('unconfigured, test, missing and foreign checkout links are never enabled',()=>{assert.equal(validate({enabled:false}),null);for(const url of ['https://buy.stripe.com/test_abc','https://evil.example/abc','http://buy.stripe.com/abc','https://buy.stripe.com/abc?amount=1']){const c=config();c.plans.basic.url=url;assert.equal(validate(c),null)}const c=config();delete c.plans.security;assert.equal(validate(c),null);assert.equal(select(null,'19800',true),null);assert.throws(()=>select({},'1',false))});

test('published configuration maps each current monthly total to a distinct live link',()=>{
 const c=require('../site/hp-management/clinic-checkout.json');
 if(!c.enabled)return;
 const links=validate(c);assert.ok(links,'enabled checkout configuration must validate');
 assert.equal(new Set(Object.values(links)).size,4,'each plan combination needs its own checkout');
 assert.deepEqual(Object.values(c.plans).map(p=>p.taxInclusiveYen),[21780,32780,76560,87560]);
});
