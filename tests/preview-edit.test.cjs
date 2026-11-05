const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const ctx={};vm.runInNewContext(fs.readFileSync('site/preview-edit.js','utf8'),ctx);const parse=ctx.SimyPreviewEdit.parse;
test('preview edits distinguish notices from exact text replacement',()=>{assert.equal(parse('お知らせ：11月3日は休診です。').type,'notice');assert.equal(parse('告知: 予約時間変更').text,'予約時間変更');const edit=parse('「午前9時」を「午前10時」に変更');assert.equal(edit.from,'午前9時');assert.equal(edit.to,'午前10時');});
test('unsupported requests fail without pretending an AI change was made',()=>{for(const input of ['もっといい感じに','お知らせ：','<script>alert(1)</script>'])assert.throws(()=>parse(input),/入力してください/);});

test('guided editing accepts a plain clinic notice without command syntax',()=>{
 const change=ctx.SimyPreviewEdit.normalize({type:'notice',text:'明日は午後休診です。'});
 assert.equal(change.text,'明日は午後休診です。');assert.equal(change.type,'notice');
 const replacement=ctx.SimyPreviewEdit.normalize({type:'replace',from:'午前9時',to:'午前10時'});
 assert.equal(replacement.from,'午前9時');assert.equal(replacement.to,'午前10時');
});
test('guided editing requires meaningful bounded content and a known action',()=>{
 for(const input of [{type:'notice',text:'  '},{type:'replace',from:'',to:'何か'},{type:'notice',text:'a'.repeat(501)},{type:'script',text:'alert(1)'}])assert.throws(()=>ctx.SimyPreviewEdit.normalize(input));
});
