const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const site = path.join(root, 'site');
const locales = ['en', 'ja', 'hi', 'es', 'fr', 'zh-Hans'];
function files(dir) { return fs.readdirSync(dir, {withFileTypes:true}).flatMap(d => d.isDirectory() ? files(path.join(dir,d.name)) : d.name.endsWith('.html') ? [path.join(dir,d.name)] : []); }
const decode = s => s.replaceAll('&amp;', '&').replaceAll('&#x27;', "'");
for (const file of files(site)) {
  const rel = path.relative(site,file); const html = fs.readFileSync(file,'utf8');
  const excluded = /http-equiv=["']refresh["']/i.test(html) || rel === 'google-site-verification-TODO.html';
  test(`AC-1/AC-2 ${rel}: raw shared navigation and actual destinations`, () => {
    const headers = [...html.matchAll(/<header class="simy-header"[\s\S]*?<\/header>/g)];
    assert.equal(headers.length, excluded ? 0 : 1);
    if (excluded) return;
    const header = headers[0][0];
    const desktop = header.match(/<div class="sh-desktop"[\s\S]*?<div class="sh-actions">/)[0];
    for (const key of ['product','work','pricing','guides','download']) assert.ok(desktop.includes(`data-sh-label="${key}"`));
    for (const locale of locales) assert.equal((header.match(new RegExp(`data-sh-link="locale-${locale}"`,'g')) || []).length,1);
    assert.equal((header.match(/data-new-account-signup/g)||[]).length,1);
    assert.equal((header.match(/data-existing-account-login/g)||[]).length,2);
    for (const m of header.matchAll(/<a\b[^>]*href="([^"]+)"[^>]*>/g)) {
      const url = new URL(decode(m[1]), 'https://simy.one');
      if (url.hostname === 'app.simy.one') {
        assert.equal(url.protocol,'https:');
        assert.ok(['/', '/signup', '/signup/', '/login'].includes(url.pathname));
        continue;
      }
      assert.equal(url.hostname,'simy.one');
      const target = path.join(site,url.pathname.endsWith('/') ? url.pathname+'index.html' : url.pathname);
      assert.ok(fs.existsSync(target),`${rel}: missing ${url.pathname}`);
      if (url.hash) assert.ok(fs.readFileSync(target,'utf8').includes(`id="${url.hash.slice(1)}"`),`${rel}: missing ${url.hash}`);
    }
  });
}
test('AC-3 all shared raw headers are reproducible',()=>execFileSync('python3',['scripts/build-shared-header.py','--check'],{cwd:root,stdio:'pipe'}));
test('AC-3 assets precede HTML and occupation slash publication',()=>{
 const workflow=fs.readFileSync(path.join(root,'.github/workflows/deploy-site.yml'),'utf8');
 assert.ok(workflow.indexOf('Prepare shared navigation assets') < workflow.indexOf('Prepare occupation pages and assets'));
 assert.ok(workflow.indexOf('Prepare shared navigation assets') < workflow.indexOf('Sync HTML files'));
 assert.match(workflow,/for asset in shared-header.css shared-header.js i18n.js home-i18n.js home.js; do/);
});
test('AC-2 account handoffs preserve baseline endpoint, plan, interval and attribution',()=>{
 const accounts=require('../scripts/header-account-links.json');
 for(const [rel,links] of Object.entries(accounts)){
  const html=fs.readFileSync(path.join(site,rel),'utf8');
  const header=html.match(/<header class="simy-header"[\s\S]*?<\/header>/)[0];
  for(const [key,original] of Object.entries(links)){
   const actual=new URL(decode(header.match(new RegExp(`data-sh-link="${key}" href="([^"]+)"`))[1]));
   const prior=new URL(original);assert.equal(actual.origin+actual.pathname,prior.origin+prior.pathname,rel);
   for(const [name,value] of prior.searchParams)if(!['lang','locale','region'].includes(name))assert.equal(actual.searchParams.get(name),value,`${rel} ${name}`);
  }
 }
});
