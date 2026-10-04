const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync('site/download-release.js', 'utf8');
async function run(manifest, ok = true, reject = false) {
  const nodes = {};
  for (const key of ['mac', 'win']) {
    nodes[`[data-dl="${key}"]`] = {href:'pinned-0.5.64'};
    nodes[`[data-meta="${key}"]`] = {textContent:'v0.5.64'};
    nodes[`[data-release-status="${key}"]`] = {textContent:'Latest unconfirmed; reload to retry', getAttribute:()=> 'Latest confirmed'};
  }
  const fetch = async () => {if (reject) throw new Error('offline'); return {ok,json:async()=>manifest};};
  vm.runInNewContext(code,{document:{querySelector:s=>nodes[s]},window:{fetch},fetch,URL});
  await new Promise(r=>setImmediate(r));
  return nodes;
}
const good = {version:'0.5.65',artifacts:[
 {platform:'win32',arch:'x64',url:'https://simy.one/downloads/simy-cli/windows/0.5.65/setup.exe'},
 {platform:'darwin',arch:'arm64',url:'https://simy.one/downloads/simy-cli/0.5.65/app.dmg'}]};
test('selects each OS artifact rather than the first artifact',async()=>{
 const n=await run(good);assert.match(n['[data-dl="mac"]'].href,/app.dmg$/);assert.match(n['[data-dl="win"]'].href,/setup.exe$/);assert.equal(n['[data-release-status="mac"]'].textContent,'Latest confirmed');
});
test('offline, HTTP failure and malformed metadata retain an explicit retryable pinned fallback',async()=>{
 for(const args of [[null],[good,false],[good,true,true],[{}],[{version:'bad',artifacts:[]}],[{version:'0.5.65',artifacts:[null]}]]) {
  const n=await run(...args);assert.equal(n['[data-dl="mac"]'].href,'pinned-0.5.64');assert.match(n['[data-release-status="mac"]'].textContent,/unconfirmed/);
 }
});
test('rejects wrong origin, version, credentials and OS while retaining fallback',async()=>{
 for(const url of ['https://example.org/app.dmg','https://simy.one/downloads/simy-cli/0.5.64/app.dmg','https://user@simy.one/downloads/simy-cli/0.5.65/app.dmg','javascript:alert(1)','https://simy.one/downloads/simy-cli/0.5.65/app.dmg?q=x']) {
  const n=await run({version:'0.5.65',artifacts:[{platform:'darwin',arch:'arm64',url}]});assert.equal(n['[data-dl="mac"]'].href,'pinned-0.5.64');
 }
});
