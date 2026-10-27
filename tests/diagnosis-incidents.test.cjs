const{test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('site/website-check.js','utf8'),ctx={};vm.runInNewContext(source.slice(source.indexOf('const incidentEvidence'),source.indexOf('// Compare only complete'))+';globalThis.data=incidentEvidence;',ctx);
test('incident evidence is joined only by exact CVE and distinguishes reported exploitation from unknown',()=>{
 assert.equal(ctx.issueIncident({ids:['CVE-2024-4577']}).kind,'case');
 assert.equal(ctx.issueIncident({ids:['CVE-2025-55182']}).publisher,'Google Threat Intelligence');
 assert.equal(ctx.issueIncident({ids:['CVE-2021-44228']}).kind,'exploited');
 assert.equal(ctx.issueIncident({ids:['CVE-2024-45770'],name:'PHP'}).kind,'unconfirmed');
 assert.equal(ctx.issueIncident({ids:[],name:'React'}).kind,'unconfirmed');
 assert.match(ctx.issueIncident({ids:[]}).summary,/事故がないことを意味しません/);
});
test('stored evidence matches shipped snapshot and includes sources for case descriptions',()=>{
 assert.deepEqual(JSON.parse(JSON.stringify(ctx.data)),JSON.parse(fs.readFileSync('scripts/security-incident-evidence.json','utf8')));
 for(const c of Object.values(ctx.data.cases)){assert.match(c.source,/^https:\/\//);assert(c.date&&c.publisher&&c.summary);}
});
