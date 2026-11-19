const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const ctx={};vm.runInNewContext(fs.readFileSync('site/preview-edit.js','utf8'),ctx);
const {selectAttachment:select}=ctx.SimyPreviewEdit;

test('free-form edits have no local command parser or banner fallback',()=>{
 for(const method of ['parse','apply','applyChange','normalize'])assert.equal(ctx.SimyPreviewEdit[method],undefined);
});

test('with several photos, only an inspected current asset ID picks a thumbnail',()=>{
 const first={id:'a0',name:'入口.JPG'}, second={id:'a1',name:'受付.jpg'};
 assert.equal(select([first,second]),undefined);
 assert.equal(select([first,second],'入口.JPG'),undefined);
 assert.equal(select([second]),second);
 const sameName={...second,name:first.name};
 assert.equal(select([first,sameName],'a0'),first);
 assert.equal(select([first,sameName],'a1'),sameName);
 assert.equal(select([second],'a0'),undefined);
});
