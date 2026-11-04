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
test('the established clinic page ships the current preview editor under its content hash',()=>{
 const html=fs.readFileSync('site/hp-management/clinic/index.html','utf8');
 const editors=[...html.matchAll(/<script src="(\/assets\/clinic-service-v2\/[a-f0-9]+\.js)"/g)]
  .map(match=>({path:'site'+match[1],source:fs.readFileSync('site'+match[1],'utf8')}))
  .filter(asset=>asset.source.includes('global.SimyPreviewEdit='));
 assert.equal(editors.length,1,'the live clinic page loads one editor');
 assert.equal(editors[0].source,fs.readFileSync('site/preview-edit.js','utf8'));
 const hash=crypto.createHash('sha256').update(editors[0].source).digest('hex').slice(0,14);
 assert.ok(editors[0].path.endsWith('/'+hash+'.js'));
});
