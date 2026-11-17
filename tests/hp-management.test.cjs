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

test('HP entry offers published industries and preserves clinic detail pricing',()=>{
 const entry=fs.readFileSync('site/hp-management/index.html','utf8');
 const clinic=fs.readFileSync('site/hp-management/clinic/index.html','utf8');
 assert.match(entry,/<link rel="canonical" href="https:\/\/simy.one\/hp-management\/">/);
 assert.doesNotMatch(entry,/location.replace|http-equiv="refresh"/);
 for(const url of ['/hp-management/clinic.html','/hp-management/law-firm.html'])assert.ok(entry.includes(`href="${url}#diagnosis"`));
 assert.match(clinic,/class="sp-hero-art"/);
 assert.match(clinic,/clinic-hero-phone.png/);
 assert.match(clinic,/<section[^>]*id="pricing"/);
 for(const price of ['19,800','21,780','29,800','32,780','49,800','54,780'])assert.ok(clinic.includes(price));
});

test('Clinic service keeps pre-migration rights and FAQ disclosures available',()=>{
 const clinic=fs.readFileSync('site/hp-management/clinic/index.html','utf8');
 for(const anchor of ['faq','migration-rights'])assert.match(clinic,new RegExp(`id="${anchor}"`));
 for(const text of ['移管実費や追加機能の費用は事前に提示','写真・フォント・テンプレートの利用条件','許可の対象と範囲を記録','無料診断だけでも利用できますか？'])assert.ok(clinic.includes(text));
 assert.ok(!clinic.includes('保険商品の説明・見積もり・加入手続きは'),'paused insurance referral stays paused');
});


test('Update assistance shows AI updates with optional human support',()=>{
 const clinic=fs.readFileSync('site/hp-management/clinic/index.html','utf8');
 assert.doesNotMatch(clinic,/support-portrait|support-advisor|clinic-support-advisor-portrait/);
 assert.ok(clinic.includes('使い方や運用で困ったときに、<br/>担当者へ相談できます。'));
 assert.match(clinic,/<figure class="support-scene"><img[^>]+clinic-ai-with-secretary-support-v2\.webp/);
 assert.ok(fs.statSync('site/assets/website-check/clinic-ai-with-secretary-support-v2.webp').size<400000);
 assert.ok(clinic.includes('AI・HP運用サポートを追加'));
 assert.ok(clinic.includes('税込＋54,780円／月'));
});


test('Pricing leads with AI information sharing and distinguishes managed growth support',()=>{
 const clinic=fs.readFileSync('site/hp-management/clinic/index.html','utf8');
 const basic=clinic.match(/<article class="plan">[\s\S]*?<\/article>/)[0];
 const plus=clinic.match(/<article class="plan plan-plus">[\s\S]*?<\/article>/)[0];
 assert.ok(basic.indexOf('AIで診療案内・記事の下書き')<basic.indexOf('セキュリティ修正・更新後'));
 assert.ok(plus.indexOf('AIウェブ管理のAI活用・情報発信・アクセス解析')<plus.indexOf('WAFによる攻撃対策'));
 for(const term of ['稼働監視・バックアップ・復元','ストレージ（5GB）','Webサーバー・CDN：AWS','公開・更新：ファイルのアップロード','SSL・ドメイン管理','Googleアナリティクスの導入・基本設定'])assert.ok(basic.includes(term));
 assert.ok(clinic.includes('担当者によるGoogleマップ・AI検索の運用支援は、両プラン共通の追加オプションです。'));
 assert.ok(clinic.includes('AIへの依頼の仕方や、診療情報・記事・口コミ返信案の整え方を相談できます。'));
});


test('Growth plan labels and recording consultation stay consistent without changing prices',()=>{
 const page=fs.readFileSync('site/hp-management/clinic/index.html','utf8');
 for(const name of ['AIウェブ管理','AIウェブ管理　安心プラス']){
  const titles=[...page.matchAll(/<h3>([\s\S]*?)<\/h3>/g)].map(m=>m[1].replace(/<[^>]+>/g,''));
  assert.ok(titles.includes(name));
  assert.ok(page.includes('<strong>'+name+'</strong>'));
 }
 assert.doesNotMatch(page,/<h3>基本保守<\/h3>|<h3>セキュリティ強化<\/h3>|SECURITY PLUS/);
 const plus=page.match(/<article class="plan plan-plus">[\s\S]*?<\/article>/)[0];
 assert.ok(plus.includes('診察室の録音を、HPの記事に。'));
 for(const text of ['同意を得た録音','個人情報を除き','先生の確認・承認後','実施範囲・費用は別途'])assert.ok(plus.includes(text));
 assert.ok(plus.includes('href="#clinical-content"'));
 assert.ok(page.includes('id="clinical-content"'));
 assert.match(page,/name="plan"[^>]*value="19800"/);assert.match(page,/name="plan"[^>]*value="29800"/);
});
