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
test('PDF puts component-only disclosures in section 01 without an external-service section',()=>{
 const local={URL};for(const f of ['information-flow','service-security','diagnosis-pdf'])vm.runInNewContext(fs.readFileSync('site/'+f+'.js','utf8'),local);
 const output=[];class Capture extends jsPDF{constructor(o){super(o);const original=this.text;this.text=function(s,...args){output.push(Array.isArray(s)?s.join('\n'):s);return original.call(this,s,...args);};}}
 const names=['Apache','jQuery','WordPress'];const report={url:'https://clinic.example/',checkedAt:'2026-10-29T01:00:00Z',technologies:names.map(name=>({name,status:'detected',versions:[]})),scripts:{libraries:[{name:'jquery',version:'3.7.1'}]},serviceSecurity:{catalog:names.map(name=>({id:name==='jQuery'?'jQuery-3.5.0':name,subjectId:'component:'+name,name,published:'2020-04-10',checkedAt:'2026-10-28',kind:'vulnerability',scope:'対象版は未確認',summary:'公表事例',title:name+'の公表',url:'https://official.example/'+name}))}};
 local.SimyReportPdf.create({report,versions:names.map(name=>[name,'バージョン未確認','公式情報を別途確認',name+'の公表\n'+(name==='jQuery'?'影響範囲外':'この版への該当は未確認')])},font,Capture);const text=output.join('\n');
 assert(text.includes('01 / SOFTWARE COMPONENTS'));for(const name of names)assert(text.includes(name+'の公表'));
 assert(text.includes('影響範囲外'));assert(!text.includes('03 / PUBLIC ADVISORIES'));
});
test('PDF lists current and unknown components plus all external services, with public incidents first',()=>{
 const local={URL};for(const f of ['information-flow','service-security','diagnosis-pdf'])vm.runInNewContext(fs.readFileSync('site/'+f+'.js','utf8'),local);
 const output=[],tables=[];class Capture extends jsPDF{constructor(o){super(o);const original=this.text,table=this.autoTable;this.text=function(s,...args){output.push(Array.isArray(s)?s.join('\n'):s);return original.call(this,s,...args);};this.autoTable=function(o){tables.push(o);return table.call(this,o);};}}
 const report={url:'https://clinic.example/',checkedAt:'2026-10-29T01:00:00Z',integrations:[{destination:'https://unknown.example/',kind:'link'},{destination:'https://patient.digikar-smart.jp/',kind:'link'},{destination:'https://blastmail.jp/',kind:'script'}],providers:{facts:[{role:'制作元の記載',name:'未特定',status:'未確認'}]},serviceSecurity:{searchedSubjectIds:['digikar'],catalog:[],notices:[]}};
 local.SimyReportPdf.create({report,versions:[['Modern','2.0.0','2.0.0','最新の公式版と一致'],['Mystery','バージョン未確認','公式情報を別途確認','バージョン不明'],['Old','1.0.0','2.0.0','旧バージョン']]},font,Capture);
 const all=output.join('\n');for(const name of ['Modern','Mystery','Old'])assert(all.includes(name));assert(all.includes('1件 / 脆弱性・更新リスク'));
 const external=tables.find(t=>t.head[0][0]==='サービス・接続先');assert.equal(external.body.length,3);assert.match(external.body[0][0],/ブラストメール/);assert(external.body.some(r=>r[1].includes('未確認')));assert(external.body.some(r=>r[1].includes('特定できませんでした')));
 const providers=tables.find(t=>t.head[0][0]==='項目');assert.equal(providers.body[0][1],'未特定');
});
test('PDF preserves observed and unmeasured search findings without counting them as security issues',()=>{
 for(const file of ['site/diagnosis-pdf.js']){
  const local={URL};vm.runInNewContext(fs.readFileSync(file,'utf8'),local);const texts=[],tables=[];
  class Capture extends jsPDF{constructor(o){super(o);const text=this.text,table=this.autoTable;this.text=function(s,...a){texts.push(Array.isArray(s)?s.join('\n'):s);return text.call(this,s,...a);};this.autoTable=function(o){tables.push(o);return table.call(this,o);};}}
  const findings=[{id:'seo-title',title:'検索結果の見出し',state:'observed',summary:'記載あり',evidence:'地域のクリニック'},{id:'seo-canonical',title:'正規URL',state:'review',summary:'記載なし',evidence:'canonical未検出'},{id:'sem-performance',title:'検索広告の成果',state:'unknown',summary:'広告アカウント未接続'},{id:'geo-visibility',title:'AI検索での引用',state:'unknown',summary:'引用観測未実施'}];
  local.SimyReportPdf.create({report:{url:'https://clinic.example/',checkedAt:'2026-11-04T00:00:00Z',findings},versions:[]},font,Capture);
  const search=tables.find(t=>t.head[0][0]==='項目'&&t.head[0][1]==='確認結果');assert(search,file);assert.equal(search.body.length,4);assert.equal(search.body[0][1],'記載を確認');assert.equal(search.body[2][1],'未確認');assert.equal(search.body[3][1],'未確認');assert(texts.join('\n').includes('0件 / その他の改善点'));assert(!texts.join('\n').includes('05 / RECOMMENDATIONS'));
 }
});

test('clinic PDF uses the same factual growth summary as the screen and omits unmeasured advertisements',()=>{
 const local={URL};vm.runInNewContext(fs.readFileSync('site/clinic-growth.js','utf8'),local);
 vm.runInNewContext(fs.readFileSync('site/assets/clinic-service-v2/report-pdf-9758bc1cc10886.js','utf8'),local);
 const texts=[],tables=[];
 class Capture extends jsPDF{constructor(o){super(o);const text=this.text,table=this.autoTable;this.text=function(s,...a){texts.push(Array.isArray(s)?s.join('\n'):s);return text.call(this,s,...a);};this.autoTable=function(o){tables.push(o);return table.call(this,o);};}}
 const report={url:'https://clinic.example/',checkedAt:'2026-11-04T00:00:00Z',findings:[],growth:{status:'assessed',sources:[{id:'p0'}],bookingLinks:2,analysis:{clinicName:'テスト医院',headline:'初診の案内を予約につなげる',summary:'診療と予約の案内を本文で確認しました。',strengths:[],questions:[{label:'予約',status:'found',answer:'初診も予約できます。'}],priorities:[{title:'予約への入口をまとめる',observation:'案内が分かれています。',change:'持ち物と予約を並べます。'}],proposal:{heading:'港区の小児科',body:'専門医が診療します。',button:'初診の案内'}}}};
 local.SimyReportPdf.create({report,versions:[]},font,Capture);
 const metrics=tables.find(t=>t.head[0][0]==='項目'&&t.head[0][1]==='確認結果');assert(metrics);assert.equal(metrics.body[0][1],'1ページ');assert(texts.join(' ').includes('初診の案内を予約につなげる'));assert(!texts.join(' ').includes('検索広告の成果'));
 const m=local.SimyClinicGrowth.model(report);assert(m.questions[0].answer.includes('初診'));assert(m.proposal.description.includes('専門医'));assert(!m.proposal.description.includes('費用'));
 assert.equal(local.SimyClinicGrowth.model({url:report.url,findings:[{id:'seo-title',state:'observed',evidence:'医院'}]}).available,false);

});
test('AI Mode and dated journey findings print with verified destinations and survive missing model output',()=>{
 const local={URL};local.window=local;for(const f of ['clinic-ai-observations','clinic-growth'])vm.runInNewContext(fs.readFileSync('site/'+f+'.js','utf8'),local);vm.runInNewContext(fs.readFileSync('site/assets/clinic-service-v2/report-pdf-9758bc1cc10886.js','utf8'),local);
 const texts=[],tables=[];class Capture extends jsPDF{constructor(o){super(o);const txt=this.text,table=this.autoTable;this.text=function(s,...a){texts.push(Array.isArray(s)?s.join('\n'):s);return txt.call(this,s,...a)};this.autoTable=function(o){tables.push(o);return table.call(this,o);};}}
 local.SimyReportPdf.create({report:{url:'https://urachil.com/',checkedAt:'2026-11-05T00:00:00Z',findings:[],growth:{status:'unavailable'}},versions:[]},font,Capture);
 const text=texts.join('\n');assert(text.includes('5 / 6'));assert(text.includes('公式サイトへの到達を確認'));assert(text.includes('2026/11/5'));assert(text.includes('各質問1回'));assert(!text.includes('本文から確認した数値'));const t=tables.find(t=>t.head[0][0]==='患者さんの質問');assert.equal(t.body.length,6);assert(t.body.some(r=>r[2].includes('浦上')));assert(text.includes('担当医の')||text.includes('担当医と予約'));assert(text.includes('選ぶ予約枠'));
});
