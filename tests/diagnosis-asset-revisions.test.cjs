const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto');
const digest=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex').slice(0,12);
test('lazy PDF revision changes with the generated PDF code',()=>{
 const js=fs.readFileSync('site/website-check.js','utf8');
 assert.equal(js.match(/\/diagnosis-pdf\.js\?v=([a-f0-9]+)/)?.[1],digest('site/diagnosis-pdf.js'));
});
test('diagnosis entry pages publish current interactive asset revisions',()=>{
 for(const file of ['site/hp-management/index.html','site/hp-management/clinic/index.html']){
  const html=fs.readFileSync(file,'utf8');
  for(const asset of ['website-check.js','information-flow.js','clinic-layout.css','clinic-rebuild.js','preview-edit.js']){
   const match=html.match(new RegExp('/'+asset.replaceAll('.','\\.')+'\\?v=([a-f0-9]+)'));
   if(match)assert.equal(match[1],digest('site/'+asset),file+': '+asset);
  }
 }
});

test('clinic entry resolves current deferred PDF assets and exports its displayed plan names',()=>{
 const html=fs.readFileSync('site/hp-management/clinic/index.html','utf8');
 const entries=[...html.matchAll(/<script[^>]*src="([^"]+)"/g)].map(m=>new URL(m[1],'https://simy.one'))
  .filter(url=>url.origin==='https://simy.one'&&fs.existsSync('site'+url.pathname))
  .map(url=>({url,code:fs.readFileSync('site'+url.pathname,'utf8')}))
  .filter(entry=>/\/assets\/clinic-service-v2\/report-pdf-[a-f0-9]+\.js\?v=/.test(entry.code));
 assert.equal(entries.length,1,'one connected deferred PDF loader');
 const entry=entries[0],pdfUrl=new URL(entry.code.match(/\/assets\/clinic-service-v2\/report-pdf-[a-f0-9]+\.js\?v=[a-f0-9]+/)[0],'https://simy.one');
 assert.equal(entry.url.searchParams.get('v'),digest('site'+entry.url.pathname),'page pins the current loader');
 assert.equal(pdfUrl.searchParams.get('v'),digest('site'+pdfUrl.pathname),'loader pins the current PDF renderer');
 const vm=require('node:vm'),{jsPDF}=require('../site/vendor/report-pdf/jspdf-4.2.1.min.js');
 require('../site/vendor/report-pdf/autotable-5.0.9.min.js').applyPlugin(jsPDF);
 const context={URL};context.window=context;
 vm.runInNewContext(fs.readFileSync('site'+pdfUrl.pathname,'utf8'),context);
 const texts=[];class Capture extends jsPDF{constructor(options){super(options);const original=this.text;this.text=function(value,...args){texts.push(Array.isArray(value)?value.join('\n'):value);return original.call(this,value,...args);};}}
 const font=fs.readFileSync('site/vendor/report-pdf/NotoSansJP-Regular.ttf').toString('base64');
 const doc=context.SimyReportPdf.create({report:{url:'https://clinic.example/',checkedAt:'2026-11-16T00:00:00Z',findings:[],growth:{status:'unavailable'}},versions:[],insuranceEnabled:false},font,Capture);
 const planNames=[...html.matchAll(/<article class="plan(?: plan-plus)?">[\s\S]*?<h3>([\s\S]*?)<\/h3>/g)].map(m=>m[1].replace(/<[^>]+>/g,''));
 const pdfText=texts.join('\n').replace(/\s/gu,'');
 assert.equal(planNames.length,2);for(const name of planNames)assert.ok(pdfText.includes(name.replace(/\s/gu,'')),'generated PDF preserves displayed plan: '+name);
 assert.ok(doc.output().startsWith('%PDF-'),'the connected renderer generated a real PDF');
});
