const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const js=fs.readFileSync('site/website-check.js','utf8'),pdf=fs.readFileSync('site/diagnosis-pdf.js','utf8');
test('report keeps requested section order and does not reintroduce removed content',()=>{
 const render=js.slice(js.indexOf('function renderReport'),js.indexOf('// Results are immediately'));
 assert(render.indexOf('renderEvaluationTable(report)')<render.indexOf('renderInfrastructure(report)'));
 assert(render.indexOf('renderInfrastructure(report)')<render.indexOf('renderServiceSecurity(report)'));
 for(const text of ['調べたページを見る','同じサイト内の','院長先生が次にすること','その他の確認・改善点'])assert(!render.includes(text));
 assert(render.includes('その他おすすめの改善点'));assert(!pdf.includes("table('調べたページ'"));
});
test('public risk illustrations exist and are conditionally associated with detected issues',()=>{
 for(const file of ['clinic-aws-migration-v1.png','clinic-component-risks-v1.png'])assert(fs.statSync('site/assets/website-check/'+file).size>10000);
 assert(js.includes("row.name.toLowerCase()!=='php'&&row.issues.length"));
 const incident=js.slice(js.indexOf('function appendIssueEvidence'),js.indexOf('// Compare only complete'));
 assert(!incident.includes("element('details'"));
});
