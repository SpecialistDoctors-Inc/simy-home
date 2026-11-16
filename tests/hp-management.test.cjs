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
 for(const asset of ['clinic-hero-phone.png','予約先の改ざん','危険サイト','復旧対応'])assert.ok(page.includes(asset));
 assert.doesNotMatch(page,/<section[^>]*class="[^"]*clinic-manga-journey/);
 assert.match(page,/id="rebuild-form"/);
 assert.match(fs.readFileSync('site/for/clinic/index.html','utf8'),/location.search\+location.hash/);
});
test('ISMS mark loads before scrolling and stays within the web image budget',()=>{
 const page=fs.readFileSync('site/hp-management/clinic/index.html','utf8');
 const section=page.match(/<section[^>]*id="isms"[\s\S]*?<\/section>/)[0];
 const img=section.match(/<img\b[^>]*>/)[0];
 assert.match(img,/loading="eager"/);
 assert.match(img,/decoding="async"/);
 assert.match(img,/width="640"/);assert.match(img,/height="403"/);
 const src=img.match(/src="([^"]+)"/)[1];
 assert.ok(fs.statSync('site'+src).size<50000,'Certification mark must stay under 50 KB');
});

test('HP entry pricing stays within HP management and matches the current clinic plans',()=>{
 const entry=fs.readFileSync('site/hp-management/index.html','utf8');
 const clinic=fs.readFileSync('site/hp-management/clinic/index.html','utf8');
 assert.match(entry,/<a class="sh-pricing" data-service-pricing href="#pricing">/);
 assert.match(entry,/<section[^>]*id="pricing"/);
 assert.match(entry,/href="\/hp-management\/clinic\/#pricing"/);
 for(const price of ['19,800','21,780','29,800','32,780','49,800','54,780']){
  assert.ok(entry.includes(price),`HP entry price ${price}`);
  assert.ok(clinic.includes(price),`clinic price ${price}`);
 }
 assert.match(entry,/既存ホームページの再制作/);
 assert.match(entry,/HP管理のご契約と、権利・対象範囲の確認が条件/);
});

test('Clinic service keeps pre-migration rights and FAQ disclosures available',()=>{
 const clinic=fs.readFileSync('site/hp-management/clinic/index.html','utf8');
 for(const anchor of ['faq','migration-rights'])assert.match(clinic,new RegExp(`id="${anchor}"`));
 for(const text of ['移管実費や追加機能の費用は事前に提示','写真・フォント・テンプレートの利用条件','許可の対象と範囲を記録','無料診断だけでも利用できますか？'])assert.ok(clinic.includes(text));
 assert.ok(!clinic.includes('保険商品の説明・見積もり・加入手続きは'),'paused insurance referral stays paused');
});
