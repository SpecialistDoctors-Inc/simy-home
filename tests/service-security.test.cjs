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
