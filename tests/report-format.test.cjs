const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {jsPDF}=require('../site/vendor/report-pdf/jspdf-4.2.1.min.js');require('../site/vendor/report-pdf/autotable-5.0.9.min.js').applyPlugin(jsPDF);
const font=fs.readFileSync('site/vendor/report-pdf/NotoSansJP-Regular.ttf').toString('base64');
const ctx={URL};for(const f of ['information-flow','diagnosis-pdf'])vm.runInNewContext(fs.readFileSync('site/'+f+'.js','utf8'),ctx);
function build(clinic,url,versions,findings=[]){const texts=[],options=[];class Capture extends jsPDF{constructor(o){super(o);options.push(o);const original=this.text;this.text=function(s,x,y,...args){texts.push({s:Array.isArray(s)?s.join('\n'):s,x,y,page:this.getCurrentPageInfo().pageNumber});return original.call(this,s,x,y,...args);};}}
 const doc=ctx.SimyReportPdf.create({report:{url,checkedAt:'2026-10-29T01:00:00Z',diagnosisId:clinic,findings},registration:{clinicName:clinic},versions},font,Capture);return {doc,texts,options};}
test('reference format is portrait and clinic content is isolated between reports',()=>{
 const a=build('医院A','https://a.example/',[['PHP','7.2.24\n2019年10月24日公開','8.5.12','サポート終了']]);
 const b=build('医院B','https://b.example/',[['Vue','2.6.12','3.5.0','旧バージョン']]);
 assert.equal(a.options[0].orientation,'portrait');assert.equal(a.doc.internal.pageSize.width,210.0015555555555);
 const sa=a.texts.map(t=>t.s).join('\n'),sb=b.texts.map(t=>t.s).join('\n');
 assert(sa.includes('医院A')&&sa.includes('7.2.24')&&sa.includes('2019年10月24日公開'));
 assert(sb.includes('医院B')&&sb.includes('Vue')&&!sb.includes('7.2.24')&&!sb.includes('医院A')&&!sb.includes('urachil'));
 for(const title of ['今のホームページを、SIMYへ。','権利の確認から、','お問い合わせ：sales@simy.one'])assert(sa.includes(title));
});
test('variable length issues paginate inside printable body, without dropping issue text',()=>{
 const versions=Array.from({length:9},(_,i)=>['部品'+i,'1.0.0\n2019年1月1日公開','2.0.0','既知の問題\n'+('公表された問題の内容を確認しました。'.repeat(i===0?160:8))+'END-'+i]);
 const {doc,texts}=build('長い医院名のテストクリニック','https://long.example/',versions,[{title:'フォームの問題',summary:'通信が暗号化されていません。',state:'review'},{title:'正常な設定',summary:'異常なし',state:'ok'}]);
 assert(doc.getNumberOfPages()>8);const content=texts.map(t=>t.s).join('\n');for(let i=0;i<9;i++)assert(content.includes('END-'+i));assert(!content.includes('正常な設定'));
 for(const t of texts){assert(t.y<=290,'text origin outside paper: '+t.y);assert(t.x>=17&&t.x<=193,'text outside horizontal margin');}
});
