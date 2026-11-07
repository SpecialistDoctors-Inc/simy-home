const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
test('paused insurance stays out of the page and PDF model even with a saved link',()=>{
 for(const [search,on] of [['',false],['?insurance=off',false],['?insurance=on',false],['?insurance=other',false]]){
  const local={URLSearchParams,location:{search},document:{documentElement:{dataset:{}}}};local.window=local;
  vm.runInNewContext(fs.readFileSync('site/clinic-insurance.js','utf8'),local);
  assert.equal(local.SimyClinicInsurance.enabled(),on);assert.equal(local.document.documentElement.dataset.clinicInsurance,on?'on':'off');
  vm.runInNewContext(fs.readFileSync('site/assets/clinic-service-v2/report-pdf-9758bc1cc10886.js','utf8'),local);
  assert.equal(local.SimyReportPdf.model({report:{},root:{querySelectorAll:()=>[]}}).insuranceEnabled,on);
 }
});
