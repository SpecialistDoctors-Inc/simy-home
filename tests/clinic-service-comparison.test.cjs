const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');
const source=fs.readFileSync('site/hp-management/clinic-service.html','utf8');
test('comparison page is separate, has its own navigation and uses real diagnostic/editor hooks',()=>{
 assert.match(source,/<meta name="robots" content="noindex,follow">/);
 assert.match(source,/href="\/hp-management\/clinic.html"/);
 for(const id of ['diagnosis-form','diagnosis-url','diagnosis-results','rebuild-form','rebuild-editor','preview-application'])assert.equal((source.match(new RegExp(`id="${id}"`,'g'))||[]).length,1,id);
 for(const path of ['website-check.js','preview-edit.js','clinic-rebuild.js'])assert.ok(source.includes('/'+path+'?'));
 assert.match(source,/id="main-nav"/);assert.match(source,/href="https:\/\/www.awak.app\//);
 assert.ok(!source.includes('generate-demo'));assert.ok(!source.includes('data:image'));
});
