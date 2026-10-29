const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const src=fs.readFileSync('site/website-check.js','utf8');
const el=(tag,text='',className='')=>({tag,text,className,children:[],append(...items){this.children.push(...items);},setAttribute(){}});
const text=n=>[n.text,...n.children.map(text)].join('\n');
function run(report){
 const results=el('main'),ctx={URL,window:{},element:el,results,releaseReferences:{},compareReleaseVersions:()=>null,releaseLabel:()=>'',appendIssueEvidence(){}};
 vm.runInNewContext(fs.readFileSync('site/service-security.js','utf8'),ctx);
 vm.runInNewContext(src.slice(src.indexOf('function renderEvaluationTable'),src.indexOf('function renderSummary'))+src.slice(src.indexOf('function renderNoticeTable'),src.indexOf('function groupLibraryFindings')),ctx);
 ctx.renderEvaluationTable(report);ctx.renderServiceSecurity(report);return results;
}
const notice=name=>({id:name==='jQuery'?'jQuery-3.5.0':name+'-case',subjectId:'component:'+name,name,published:'2021-10-04',checkedAt:'2026-10-28',kind:'vulnerability',url:'https://official.example/'+name,scope:'対象版・設定への該当は未確認',summary:'過去の公表事例',title:name+'の修正'});
test('component disclosures render under 01 even when unknown versions produce no comparison rows',()=>{
 const r=run({technologies:[{name:'Apache',status:'detected',versions:[]},{name:'WordPress',status:'detected',versions:[]}],scripts:{libraries:[]},serviceSecurity:{catalog:[notice('Apache'),notice('WordPress')]}});
 const output=text(r);assert.match(output,/01 \/ 使用部品/);assert.match(output,/Apacheの修正/);assert.match(output,/WordPressの修正/);assert.doesNotMatch(output,/03 \/ ご利用中/);assert.match(output,/使用部品/);assert.match(output,/過去の公表事例/);
});
test('fixed jQuery is not reclassified as affected by a historical disclosure and external services stay in 03',()=>{
 const r=run({technologies:[],scripts:{libraries:[{name:'jquery',version:'3.7.1',issues:[]}]},integrations:[{destination:'https://blastmail.jp/',kind:'link'}],serviceSecurity:{catalog:[notice('jQuery')]}});
 assert.equal(r.children.length,2);assert.match(text(r.children[0]),/01 \/ 使用部品/);assert.match(text(r.children[0]),/影響範囲外/);assert.match(text(r.children[1]),/03 \/ ご利用中/);assert.doesNotMatch(text(r.children[1]),/jQuery/);
});
test('PDF version extraction selects comparison rows rather than the component disclosure table',()=>{
 const ctx={URL};vm.runInNewContext(fs.readFileSync('site/diagnosis-pdf.js','utf8'),ctx);const selectors=[];
 const model=ctx.SimyReportPdf.model({report:{},root:{querySelectorAll(s){selectors.push(s);return [];}}});
 assert.equal(model.versions.length,0);assert.equal(selectors[0],'.evaluation-section .component-version-table tbody tr');
});
