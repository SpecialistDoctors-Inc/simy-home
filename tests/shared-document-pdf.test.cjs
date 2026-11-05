const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const ctx={URL};for(const file of ['site/information-flow.js','site/diagnosis-pdf.js'])vm.runInNewContext(fs.readFileSync(file,'utf8'),ctx);
test('PDF shares document labels and scoped assessment with screen, with only assessed concerns',()=>{
 const tables=[];
 class Pdf {addFileToVFS(){}addFont(){}setFont(){}setProperties(){}setFontSize(){}setTextColor(){}splitTextToSize(s){return [s];}text(){}addPage(){}getNumberOfPages(){return 1;}setPage(){}link(){}setDrawColor(){}setFillColor(){}roundedRect(){}line(){}autoTable(options){tables.push(options);this.lastAutoTable={finalY:50};}}
 const items=[{url:'https://drive.google.com/file/d/123456789012/view',status:'preview-observed',title:'プレゼンテーション2.pdf',content:{status:'extracted'},assessment:{status:'assessed',scope:'extracted-text-only',audience:'patient',topic:'診療報酬改定に伴う院内掲示',concern:'none'}},{url:'https://drive.google.com/file/d/234567890123/view',status:'preview-observed',title:'プレゼンテーション3.pdf'}];
 items.push({...items[0],assessment:{...items[0].assessment,audience:'internal',concern:'review'}});
 ctx.SimyReportPdf.create({report:{url:'https://clinic.example/',checkedAt:'2026-10-28T00:00:00Z',sharing:{items}},registration:{clinicName:'テスト医院'},versions:[],connections:[]},'',Pdf);
 const sharing=tables.find(t=>t.head[0][0]==='資料');assert(sharing);
 assert.equal(sharing.body.length,1);
 assert.equal(sharing.body[0][0].split('\n')[0],ctx.SimyInformationFlow.sharingName(items[2]));
 assert(sharing.body[0][1].startsWith(ctx.SimyInformationFlow.sharingCopy(items[2]).reason));
});
test('PDF preserves live research coverage separately from catalog incidents',()=>{
 for(const [status,expected] of [['completed','診断時に公式情報を検索しました。'],['partial','一部のみ完了'],['unavailable','未実施または取得できません'],[undefined,'未実施または取得できません']]){
  const output=[];
  class Pdf {addFileToVFS(){}addFont(){}setFont(){}setProperties(){}setFontSize(){}setTextColor(){}splitTextToSize(s){return [s];}text(s){output.push(...(Array.isArray(s)?s:[s]));}addPage(){}getNumberOfPages(){return 1;}setPage(){}link(){}setDrawColor(){}setFillColor(){}roundedRect(){}line(){}}
  const local={SimyServiceSecurity:{assess:()=>({research:{status},notices:[]}),providerNotices:()=>[],visibleServices:()=>[]}};
  vm.runInNewContext(fs.readFileSync('site/diagnosis-pdf.js','utf8'),local);
  local.SimyReportPdf.create({report:{url:'https://clinic.example/',checkedAt:'2026-10-28T00:00:00Z'},registration:{clinicName:'テスト医院'},versions:[],connections:[]},'',Pdf);
  assert(output.some(s=>s.includes(expected)));
  if(status!=='completed')assert(!output.includes('診断時に公式情報を検索しました。'));
 }
});
test('PDF includes SIMY icon and inquiry links without sending a message',()=>{
 const output=[],images=[],links=[];
 class Pdf {addFileToVFS(){}addFont(){}setFont(){}setProperties(){}setFontSize(){}setTextColor(){}splitTextToSize(s){return [s];}text(s){output.push(...(Array.isArray(s)?s:[s]));}addPage(){}getNumberOfPages(){return 1;}setPage(){}link(...args){links.push(args.at(-1).url);}setDrawColor(){}setFillColor(){}roundedRect(){}line(){}addImage(...args){images.push(args);}}
 ctx.SimyReportPdf.create({report:{url:'https://clinic.example/',checkedAt:'2026-10-29T00:00:00Z',diagnosisId:'test-id'},registration:{clinicName:'確認'},versions:[],connections:[]},'',Pdf,'ICON');
 assert.equal(images[0][0],'ICON');assert(output.includes('この診断結果を、SIMYに相談する'));
 assert(links.some(u=>u.startsWith('mailto:sales@simy.one?subject=')&&decodeURIComponent(u).includes('test-id')));
});
