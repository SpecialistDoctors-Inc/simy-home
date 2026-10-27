const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');
const src=fs.readFileSync('site/website-check.js','utf8');const ctx={URL};vm.runInNewContext(src.slice(src.indexOf('function normalizeDiagnosisUrl'),src.indexOf("diagnosisInput.addEventListener('input'")),ctx);
test('tracking URLs keep their path and remove advertising identifiers and fragments',()=>{
 assert.equal(ctx.normalizeDiagnosisUrl(' https://example.com/clinic/?utm_source=google&gad_campaignid=14993528040&gbraid=abc&gclid=xyz#contact ').href,'https://example.com/clinic/');
 assert.equal(ctx.normalizeDiagnosisUrl('example.com/?UTM_campaign=a&utm_campaign=b&fbclid=c').href,'https://example.com/');
 assert.equal(ctx.normalizeDiagnosisUrl('http://example.com/path#access').href,'http://example.com/path');
});
test('page selecting and private query values are not silently changed or sent',()=>{
 for(const url of ['https://example.com/?p=12&utm_source=a','https://example.com/?token=secret','https://user:pass@example.com/','javascript:alert(1)'])assert.throws(()=>ctx.normalizeDiagnosisUrl(url));
});
