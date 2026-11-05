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
