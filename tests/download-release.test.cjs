const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync('site/download-release.js', 'utf8');
function harness(fetchImpl, source = code) {
  const nodes = {}, timers = new Map(), requests = [];
  let sequence = 0;
  for (const key of ['mac', 'win']) {
    nodes[`[data-dl="${key}"]`] = {href:'pinned-0.5.65'};
    nodes[`[data-meta="${key}"]`] = {textContent:'v0.5.65'};
    nodes[`[data-release-status="${key}"]`] = {textContent:'Latest unconfirmed; reload to retry', getAttribute:()=> 'Latest confirmed'};
  }
  const fetch = (url, options) => { requests.push({url, options}); return fetchImpl(url, options); };
  vm.runInNewContext(source, {document:{querySelector:s=>nodes[s]}, window:{fetch, AbortController}, fetch, URL,
    setTimeout:(fn, delay)=>{const id=++sequence;timers.set(id,{fn,delay});return id;},
    clearTimeout:id=>timers.delete(id)});
  const flush = async()=>{for(let i=0;i<20;i++)await Promise.resolve();};
  const tick = async delay=>{for(const [id,t] of [...timers])if(t.delay===delay){timers.delete(id);t.fn();}await flush();};
  return {nodes, requests, timers, flush, tick};
}
async function run(manifest, ok = true, reject = false) {
  const h=harness(async()=>{if(reject)throw new Error('offline');return {ok,status:ok?200:503,json:async()=>manifest};});
  await h.flush(); await h.tick(250);
  return h.nodes;
}
const good = {version:'0.5.65',artifacts:[
 {platform:'win32',arch:'x64',url:'https://simy.one/downloads/simy-cli/windows/0.5.65/setup.exe'},
 {platform:'darwin',arch:'arm64',url:'https://simy.one/downloads/simy-cli/0.5.65/app.dmg'}]};
test('selects each OS artifact rather than the first artifact',async()=>{
 const n=await run(good);assert.match(n['[data-dl="mac"]'].href,/app.dmg$/);assert.match(n['[data-dl="win"]'].href,/setup.exe$/);assert.equal(n['[data-release-status="mac"]'].textContent,'Latest confirmed');
});
test('offline, HTTP failure and malformed metadata retain an explicit retryable pinned fallback',async()=>{
 for(const args of [[null],[good,false],[good,true,true],[{}],[{version:'bad',artifacts:[]}],[{version:'0.5.65',artifacts:[null]}]]) {
  const n=await run(...args);assert.equal(n['[data-dl="mac"]'].href,'pinned-0.5.65');assert.match(n['[data-release-status="mac"]'].textContent,/unconfirmed/);
 }
});
test('rejects wrong origin, version, credentials and OS while retaining fallback',async()=>{
 for(const url of ['https://example.org/app.dmg','https://simy.one/downloads/simy-cli/0.5.64/app.dmg','https://user@simy.one/downloads/simy-cli/0.5.65/app.dmg','javascript:alert(1)','https://simy.one/downloads/simy-cli/0.5.65/app.dmg?q=x']) {
  const n=await run({version:'0.5.65',artifacts:[{platform:'darwin',arch:'arm64',url}]});assert.equal(n['[data-dl="mac"]'].href,'pinned-0.5.65');
 }
});

test('transient GET failures recover once without reloading or duplicating successful OS reads',async()=>{
 const counts={mac:0,win:0};
 const h=harness(async url=>{const key=url.includes('/windows/')?'win':'mac';counts[key]++;
  if(key==='mac'&&counts[key]===1)throw new Error('temporary connection loss');
  return {ok:true,json:async()=>good};});
 await h.flush();assert.equal(h.nodes['[data-release-status="win"]'].textContent,'Latest confirmed');
 assert.match(h.nodes['[data-release-status="mac"]'].textContent,/unconfirmed/);
 await h.tick(250);assert.equal(h.nodes['[data-release-status="mac"]'].textContent,'Latest confirmed');
 assert.deepEqual(counts,{mac:2,win:1});assert.equal(h.timers.size,0);
});
test('server failure retries once; permanent HTTP and malformed bodies do not retry',async()=>{
 for(const scenario of ['server','not-found','rate-limit','retry-after','bad-json']){
  const h=harness(async()=>scenario==='bad-json'?{ok:true,json:async()=>{throw new SyntaxError('bad JSON');}}:
    {ok:false,status:scenario==='server'||scenario==='retry-after'?502:scenario==='rate-limit'?429:404,headers:{get:()=>scenario==='retry-after'?'60':null}});
  await h.flush();await h.tick(250);await h.tick(250);
  assert.equal(h.requests.length,scenario==='server'?4:2,scenario);
  assert.match(h.nodes['[data-release-status="mac"]'].textContent,/unconfirmed/);assert.equal(h.timers.size,0);
 }
});
test('a hung body times out while another OS succeeds, retries once, and ignores stale late data',async()=>{
 let resolveBody;let count=0;
 const h=harness(async url=>{
  if(!url.includes('/windows/')&&++count===1)return {ok:true,json:()=>new Promise(r=>{resolveBody=r;})};
  return {ok:true,json:async()=>({...good,version:'0.5.66',artifacts:good.artifacts.map(a=>({...a,url:a.url.replaceAll('0.5.65','0.5.66')}))})};
 });
 await h.flush();assert.equal(h.nodes['[data-release-status="win"]'].textContent,'Latest confirmed');
 await h.tick(5000);assert.equal(h.requests[0].options.signal.aborted,true);
 await h.tick(250);assert.match(h.nodes['[data-dl="mac"]'].href,/0\.5\.66/);
 resolveBody(good);await h.flush();assert.match(h.nodes['[data-dl="mac"]'].href,/0\.5\.66/);
 assert.equal(h.requests.length,3);assert.equal(h.timers.size,0);
});
test('persistent hangs exhaust the bound and retain clickable fallback; a later page load recovers',async()=>{
 const h=harness(()=>new Promise(()=>{}));await h.flush();
 await h.tick(5000);await h.tick(250);await h.tick(5000);await h.tick(250);
 assert.equal(h.requests.length,4);assert.equal(h.timers.size,0);
 for(const key of ['mac','win']){assert.equal(h.nodes[`[data-dl="${key}"]`].href,'pinned-0.5.65');assert.match(h.nodes[`[data-release-status="${key}"]`].textContent,/unconfirmed/);}
 const recovered=await run(good);assert.equal(recovered['[data-release-status="mac"]'].textContent,'Latest confirmed');
});
test('all six authored download pages use the recovery script cache revision',()=>{
 for(const file of ['site/download.html',...['en','hi','es','fr','zh-hans'].map(l=>`site/download/${l}.html`)])
  assert.match(fs.readFileSync(file,'utf8'),/src="\/download-release\.js\?v=20261007-bounded-recovery-1"/);
});
