const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const s=fs.readFileSync('site/website-check.js','utf8');
test('registration unlock requires matching saved receipt, with no pre-registration PDF button',()=>{
 const form=s.slice(s.indexOf('function appendEmailReceipt'),s.indexOf('// This is a presentation gate'));
 assert(form.indexOf("body.receiptId!==requestId||body.status!=='registered'")<form.indexOf('onSaved('));
 assert(form.includes("consentVersion:'2026-10-28-v3'"));
 for(const field of ['email','clinicName','contactName','consent'])assert(form.includes(field+'.required=true'));
 const render=s.slice(s.indexOf('function renderReport'),s.indexOf('function appendEmailReceipt'));
 assert(render.includes('gateReport(report)'));assert(!render.includes('appendReportDownload'));
 const gate=s.slice(s.indexOf('function gateReport'),s.indexOf('let scanClock'));
 assert(gate.indexOf('appendEmailReceipt(')<gate.indexOf("element('button','診断結果をPDFで保存 ↓'"));
 assert(gate.includes('if(!preview.isConnected)return'));
});
