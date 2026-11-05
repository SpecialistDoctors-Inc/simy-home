const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const code=fs.readFileSync('site/website-check.js','utf8').split('async function readScanResponse(response){')[1].split('// Advertising identifiers')[0];
const ctx={TextDecoder,scanProgress(){}};vm.runInNewContext('async function readScanResponse(response){'+code,ctx);
const encoder=new TextEncoder();
function response(events,close=true){return new Response(new ReadableStream({start(c){for(const event of events)c.enqueue(encoder.encode(JSON.stringify(event)+'\n'));if(close)c.close();}}),{headers:{'content-type':'application/x-ndjson'}});}
test('completed report returns without waiting for the connection to close',async()=>{const report=await ctx.readScanResponse(response([{type:'result',report:{url:'https://example.com'}}],false));assert.equal(report.url,'https://example.com');});
test('timeout after checkpoint retains findings and explicitly marks partial',async()=>{const report=await ctx.readScanResponse(response([{type:'partial',report:{findings:[{id:'kept'}]}},{type:'error',error:'The operation was aborted due to timeout'}]));assert.equal(report.completion,'partial');assert.equal(report.findings[0].id,'kept');});
test('no checkpoint does not fabricate a diagnosis',async()=>{await assert.rejects(ctx.readScanResponse(response([{type:'error',error:'timeout'}])),/timeout/);});

test('EOF checkpoint is partial and retains the actual coverage reason',async()=>{const report=await ctx.readScanResponse(response([{type:'partial',report:{completionReason:'入口のみ',technologies:[],integrations:[]}}]));assert.equal(report.completion,'partial');assert.equal(report.completionReason,'入口のみ');});
test('transport failure preserves checkpoint coverage reason',async()=>{const report=await ctx.readScanResponse(response([{type:'partial',report:{completionReason:'入口のみ'}},{type:'error',error:'timeout'}]));assert.equal(report.completionReason,'入口のみ');});
