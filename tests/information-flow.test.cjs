const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');const ctx={URL};vm.runInNewContext(fs.readFileSync('site/information-flow.js','utf8'),ctx);const model=ctx.SimyInformationFlow.model;
const item={domain:'drive.google.com',destination:'https://drive.google.com/file/d/123/view',page:'https://clinic.jp/',kind:'link',category:'用途未確認'};
test('diagram groups shared hosts but does not claim observed traffic from links',()=>{const g=model({integrations:[item,{...item,page:'https://clinic.jp/about'}]})[0];assert.equal(g.category,'資料共有');assert.equal(g.pages.length,2);assert.equal(g.observed,false);assert.match(g.labels[0],/未操作/);});
test('observed status requires the actual destination path',()=>{const report={integrations:[item],scripts:{browserEvidence:{connections:[{destination:'https://drive.google.com/unrelated'}]}}};assert.equal(model(report)[0].observed,false);report.scripts.browserEvidence.connections[0].destination=item.destination;assert.equal(model(report)[0].observed,true);});
test('sharing evidence joins only the exact host and preserves unknown state',()=>{const g=model({integrations:[item],sharing:{items:[{url:item.destination,status:'unknown'},{url:'https://evil.example/file',status:'preview-observed'}]}})[0];assert.equal(g.sharing.length,1);assert.equal(g.sharing[0].status,'unknown');});

test('same-origin form targets are not portrayed as external services',()=>{assert.equal(model({url:'https://clinic.jp/',integrations:[{...item,destination:'https://clinic.jp/contact',kind:'form'}]}).length,0);});

test('booking remains high priority even if another link on the host was found first',()=>{const g=model({integrations:[{...item,destination:'https://booking.example/about'}, {...item,destination:'https://booking.example/reserve',category:'予約'}]})[0];assert.equal(ctx.SimyInformationFlow.managementCopy(g).label,'患者情報の管理が重要');});
test('ordinary links are only conditionally low priority, not certified safe',()=>{const g=model({integrations:[{...item,destination:'https://example.org/'}]})[0];const copy=ctx.SimyInformationFlow.managementCopy(g);assert.match(copy.label,/なら/);assert.match(copy.reason,/入力する場合/);});
test('shared documents and scripts do not inherit low link priority',()=>{assert.match(ctx.SimyInformationFlow.managementCopy(model({integrations:[item]})[0]).label,/公開範囲/);assert.match(ctx.SimyInformationFlow.managementCopy({kinds:['link','script'],category:'用途未確認'}).label,/外部へ情報が送られる可能性/);});

const flow=ctx.SimyInformationFlow;
const assessed={status:'preview-observed',title:'プレゼンテーション2.pdf',content:{status:'extracted'},assessment:{status:'assessed',scope:'extracted-text-only',audience:'patient',topic:'診療報酬改定に伴う院内掲示',concern:'none'}};
test('document names use assessed topic, never numbered or ambiguous file labels',()=>{
 assert.equal(flow.sharingName(assessed),'診療報酬改定に伴う院内掲示に関する資料');
 assert.equal(flow.sharingName({title:'プレゼンテーション2.pdf'}),'内容を特定できていない資料');
 assert.match(flow.sharingName({title:'診療報酬改定によるウエブサイト掲示.pdf'}),/名称から表示・内容未判定/);
});
test('only assessed extracted text gets a scoped no-concern statement',()=>{
 assert.equal(flow.sharingCopy(assessed).reason,'確認した範囲では、秘匿情報は見つかりませんでした。');
 assert.match(flow.sharingCopy({...assessed,content:{status:'partial'}}).reason,/一部の文字/);
 for(const item of [{status:'preview-observed'},{...assessed,content:{status:'unavailable'}},{...assessed,assessment:{status:'withheld'}},{...assessed,assessment:{status:'unavailable'}},{...assessed,status:'access-required'}])assert.doesNotMatch(flow.sharingCopy(item).reason,/秘匿情報は見つかりません/);
});
test('internal and uncertain content remain qualified',()=>{
 assert.match(flow.sharingCopy({...assessed,assessment:{...assessed.assessment,audience:'internal'}}).reason,/断定できません/);
 assert.match(flow.sharingCopy({...assessed,assessment:{...assessed.assessment,concern:'review'}}).reason,/判断できません/);
});

test('reference links are summarized while actual embeds and booking remain visible',()=>{
 const el=(tag,text='',cls='')=>({tag,text,cls,children:[],append(...items){this.children.push(...items);},setAttribute(){}});
 const root=el('div');
 flow.render({url:'https://company.example/',integrations:[
  {...item,destination:'https://docs.example/a'},
  {...item,destination:'https://docs.example/b'},
  {...item,destination:'https://widget.example/js',kind:'script'},
  {...item,destination:'https://booking.example/',category:'予約'}
 ],sharing:{items:[]}},root,el);
 const text=n=>[n.text,...n.children.map(text)].join('\n');
 const output=text(root);
 assert.match(output,/案内・参考情報への外部リンク：1件/);
 assert.doesNotMatch(output,/docs\.example/);
 assert.match(output,/widget\.example/);assert.match(output,/booking\.example/);
 assert.match(output,/患者情報の管理が重要/);
});

test('folder listing is never treated as assessed document content',()=>{assert.equal(flow.sharingCopy({...assessed,kind:'folder'}).reason,'フォルダー内の資料は未確認です。');assert.doesNotMatch(flow.sharingCopy({...assessed,kind:'folder',folder:{discovered:2}}).reason,/秘匿情報は見つかりません/);});
test('sharing results show assessed concerns but hide clean and unassessed items',()=>{
 const has=ctx.SimyInformationFlow.sharingHasIssue;
 const base={status:'preview-observed',content:{status:'extracted'},assessment:{status:'assessed',scope:'extracted-text-only',audience:'patient',concern:'none'}};
 assert.equal(has(base),false);
 assert.equal(has({...base,assessment:{...base.assessment,audience:'internal'}}),true);
 assert.equal(has({...base,assessment:{...base.assessment,concern:'review'}}),true);
 assert.equal(has({...base,assessment:{status:'unavailable'}}),false);
 assert.equal(has({...base,kind:'folder',content:{status:'unavailable'}}),false);
});
