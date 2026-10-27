const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');
const production=fs.readFileSync('infra/cloudfront-functions/redirect-prod.js','utf8');
const terraform=fs.readFileSync('infra/terraform/main.tf','utf8').split('code    = <<-EOF\n')[1].split('\n  EOF')[0].replace('${local.basic_auth_enabled ? "true" : "false"}','false').replace('${local.basic_auth_token}','');
for(const [name,code] of [['production',production],['terraform',terraform]]){
 const ctx={};vm.runInNewContext(code,ctx);
 for(const base of ['/hp-management','/hp-management/clinic','/for/clinic']){
  for(const suffix of ['', '/', '.html','/index.html'])test(`${name} HP routing ${base+suffix}`,()=>{
   const canonical=base==='/for/clinic'?'/hp-management/clinic/':base+'/';
   const req={uri:base+suffix,headers:{host:{value:'simy.one'}},querystring:{utm_source:{value:'email'}}};
   const result=ctx.handler({request:req});
   if(base+suffix===canonical)assert.equal(result.uri,canonical+'index.html');
   else {assert.equal(result.statusCode,301);assert.equal(result.headers.location.value,'https://simy.one'+canonical+'?utm_source=email');}
  });
 }
}
test('Clinic service migration preserves the actual form, manga and script',()=>{
 const page=fs.readFileSync('site/hp-management/clinic/index.html','utf8');
 assert.match(page,/id="diagnosis-form"/);assert.match(page,/最大30ページ/);
 for(const asset of ['clinic-doctor-cybersecurity-v1','clinic-update-review-v2','clinic-incident-response-v2','clinic-provider-review-v2'])assert.ok(page.includes(asset));
 assert.match(page,/href="\/hp-management\/"/);
 assert.match(fs.readFileSync('site/for/clinic/index.html','utf8'),/location.search\+location.hash/);
});
