const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const ctx={URL};vm.runInNewContext(fs.readFileSync('site/service-security.js','utf8'),ctx);const assess=ctx.SimyServiceSecurity.assess;const now=Date.parse('2026-10-28');
const connection=(host,kind='script')=>({destination:'https://'+host+'/asset',kind,category:'外部サービス'});
test('matches exact provider domains and subdomains, never lookalike hosts',()=>{
 assert.equal(assess({integrations:[connection('form.blastmail.jp')]},now).notices.length,1);
 for(const host of ['evilblastmail.jp','blastmail.jp.attacker.example'])assert.equal(assess({integrations:[connection(host)]},now).notices.length,0);
});
test('external link is not represented as a confirmed contract or victim',()=>{
 const n=assess({integrations:[connection('blastmail.jp','link')]},now).notices[0];assert.match(n.connection,/契約は未確認/);assert.match(n.impact,/影響は未確認/);assert.equal(n.recent,true);
});
test('XServer DNS alone does not imply hosting or affected customer',()=>{
 assert.equal(assess({providers:{facts:[{provider:'xserver',role:'DNS提供元'}]}},now).notices.length,0);
 const n=assess({providers:{facts:[{provider:'xserver',role:'サーバー・ネットワーク'}]}},now).notices[0];assert.match(n.summary,/侵入ではありません/);assert.match(n.connection,/推定/);
});
test('deduplicates integration pages, exposes unmatched and stale catalog',()=>{
 const r=assess({integrations:[connection('patient.digikar-smart.jp'),connection('patient.digikar-smart.jp')]},now);assert.equal(r.services.length,1);assert.equal(r.unmatched.length,1);
 const n=assess({integrations:[connection('blastmail.jp')]},Date.parse('2027-06-01')).notices[0];assert.equal(n.recent,false);assert.equal(n.stale,true);
});

test('DNS providers including Onamae are listed without implying a hosting incident',()=>{const r=assess({providers:{facts:[{provider:'onamae',name:'お名前.com',role:'DNS提供元',status:'記載を確認',evidence:'NS'}]}});assert.equal(r.services[0].name,'お名前.com');assert.equal(r.services[0].category,'DNS提供元');assert.equal(r.unmatched.length,0);assert.equal(r.notices.length,1);assert.match(r.notices[0].scope,/DNS・ドメイン登録の事故を示す発表ではありません/);});

test('research separates provider incidents from the detected service and excludes lookalikes',()=>{const info=assess({integrations:[connection('console.nomoca-ai.com')]},now);assert.equal(info.notices.length,1);assert.match(info.notices[0].scope,/chatの事故を示すものではありません/);assert.equal(assess({integrations:[connection('nomoca-ai.com.attacker.example')]},now).notices.length,0);});
test('provider notices include Onamae once for registrar plus DNS and keep scope explicit',()=>{
 const report={providers:{facts:[{role:'ドメイン登録会社',name:'GMO d/b/a Onamae.com',status:'記載を確認'},{role:'DNS提供元',name:'お名前.com',provider:'onamae',status:'推定'}]}};
 const notices=ctx.SimyServiceSecurity.providerNotices(report);assert.equal(notices.length,1);assert.match(notices[0].name,/デスクトップクラウド/);assert.match(notices[0].scope,/DNS・ドメイン登録の事故を示す発表ではありません/);
 assert.equal(ctx.SimyServiceSecurity.visibleServices(assess(report)).length,0);
});
test('external incident rows omit unresearched and no-disclosure services',()=>{
 const report={integrations:[connection('unknown.example'),connection('digikar-smart.jp'),connection('blastmail.jp')]};
 const rows=ctx.SimyServiceSecurity.visibleServices(assess(report));assert.equal(rows.length,1);assert.equal(rows[0].host,'blastmail.jp');
});

test('per-diagnosis research merges verified notices and keeps components separate',()=>{
 const notice={id:'component:Ruby:case',subjectId:'component:Ruby',name:'Ruby',published:'2024-07-16',checkedAt:'2026-10-28',kind:'vulnerability',relationship:'same-service',url:'https://www.ruby-lang.org/en/news/',summary:'REXML',scope:'対象版は未確認',affectedVersions:'REXML <=3.3.2'};
 const report={technologies:[{name:'Ruby',status:'hint'}],serviceSecurity:{checkedAt:'2026-10-28',status:'unavailable',catalog:[notice],notices:[]}};
 const info=assess(report,now),visible=ctx.SimyServiceSecurity.visibleServices(info);assert.equal(visible.length,1);assert.equal(visible[0].name,'Ruby');assert.equal(ctx.SimyServiceSecurity.findingsFor(visible[0],info)[0].affectedVersions,'REXML <=3.3.2');
 report.technologies[0].status='unknown';assert.equal(ctx.SimyServiceSecurity.visibleServices(assess(report)).length,0);
});
test('runtime results replace dated matching URLs and retain sibling classification',()=>{
 const n={...ctx.SimyServiceSecurity.catalog[1],subjectId:'onamae',relationship:'same-provider-other-service',kind:'incident',checkedAt:'2026-10-28T01:00:00Z'};
 const report={providers:{facts:[{name:'お名前.com',provider:'onamae',role:'DNS提供元',status:'推定'}]},serviceSecurity:{notices:[n],catalog:[],status:'completed',checkedAt:n.checkedAt}};
 const notices=ctx.SimyServiceSecurity.providerNotices(report);assert.equal(notices.length,1);assert.match(notices[0].type,/同社の別サービス/);assert.match(notices[0].scope,/DNS・ドメイン登録の事故を示す発表ではありません/);
});
test('successful empty runtime search does not create no-incident rows',()=>{
 const info=assess({integrations:[connection('digikar-smart.jp')],serviceSecurity:{status:'completed',notices:[],catalog:[],checkedAt:'2026-10-28'}});assert.equal(ctx.SimyServiceSecurity.visibleServices(info).length,0);
});
