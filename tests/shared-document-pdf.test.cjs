const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const ctx={URL};for(const file of ['site/information-flow.js','site/diagnosis-pdf.js'])vm.runInNewContext(fs.readFileSync(file,'utf8'),ctx);
test('PDF shares document labels and scoped assessment with screen, including unknown results',()=>{
 const tables=[];
 class Pdf {addFileToVFS(){}addFont(){}setFont(){}setProperties(){}setFontSize(){}setTextColor(){}splitTextToSize(s){return [s];}text(){}addPage(){}getNumberOfPages(){return 1;}setPage(){}link(){}setDrawColor(){}line(){}autoTable(options){tables.push(options);this.lastAutoTable={finalY:50};}}
 const items=[{url:'https://drive.google.com/file/d/123456789012/view',status:'preview-observed',title:'プレゼンテーション2.pdf',content:{status:'extracted'},assessment:{status:'assessed',scope:'extracted-text-only',audience:'patient',topic:'診療報酬改定に伴う院内掲示',concern:'none'}},{url:'https://drive.google.com/file/d/234567890123/view',status:'preview-observed',title:'プレゼンテーション3.pdf'}];
 ctx.SimyReportPdf.create({report:{url:'https://clinic.example/',checkedAt:'2026-10-28T00:00:00Z',sharing:{items}},registration:{clinicName:'テスト医院'},versions:[],connections:[]},'',Pdf);
 const sharing=tables.find(t=>t.head[0][0]==='資料');assert(sharing);
 items.forEach((item,i)=>{assert.equal(sharing.body[i][0].split('\n')[0],ctx.SimyInformationFlow.sharingName(item));assert(sharing.body[i][1].startsWith(ctx.SimyInformationFlow.sharingCopy(item).reason));});
 assert.doesNotMatch(sharing.body[1][1],/問題は見つかりません/);
});
test('PDF preserves live research coverage separately from catalog incidents',()=>{
 for(const [status,expected] of [['completed','診断時に公式情報を検索しました。'],['partial','一部のみ完了'],['unavailable','未実施または取得できません'],[undefined,'未実施または取得できません']]){
  const output=[];
  class Pdf {addFileToVFS(){}addFont(){}setFont(){}setProperties(){}setFontSize(){}setTextColor(){}splitTextToSize(s){return [s];}text(s){output.push(s);}addPage(){}getNumberOfPages(){return 1;}setPage(){}link(){}setDrawColor(){}line(){}}
  const local={SimyServiceSecurity:{assess:()=>({research:{status},notices:[]}),providerNotices:()=>[],visibleServices:()=>[]}};
  vm.runInNewContext(fs.readFileSync('site/diagnosis-pdf.js','utf8'),local);
  local.SimyReportPdf.create({report:{url:'https://clinic.example/',checkedAt:'2026-10-28T00:00:00Z'},registration:{clinicName:'テスト医院'},versions:[],connections:[]},'',Pdf);
  assert(output.some(s=>s.includes(expected)));
  if(status!=='completed')assert(!output.includes('診断時に公式情報を検索しました。'));
 }
});
