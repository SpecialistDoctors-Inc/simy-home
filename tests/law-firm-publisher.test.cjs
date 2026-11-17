const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const url='https://simy.one/hp-management/law-firm.html';
const foreign='<url><loc>https://simy.one/hp-management/</loc><lastmod>2026-11-17</lastmod><priority>0.8</priority><image:image><image:loc>https://simy.one/hub.png</image:loc></image:image></url>';
function runPublisher(mode){
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'law-publisher-'));
 const log=path.join(dir,'calls.jsonl');
 const receiptPath=path.join(root,'law-firm-deployment.json');
 const previous=fs.existsSync(receiptPath)?fs.readFileSync(receiptPath):null;
 const own=mode==='existing'?`<url><loc>${url}</loc><lastmod>2026-10-01</lastmod></url>`:'';
 const original=`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n<!-- keep this exact metadata -->\n${foreign}\n${own}</urlset>`;
 fs.writeFileSync(path.join(dir,'live.xml'),original);
 fs.writeFileSync(path.join(dir,'aws'),`#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
a=sys.argv[1:]; directory=Path(os.environ['MOCK_DIRECTORY'])
record={'args':a}
if a[:2]==['s3api','put-object'] and '--body' in a:
 record['body']=Path(a[a.index('--body')+1]).read_text() if a[a.index('--key')+1]=='sitemap.xml' else None
with open(directory/'calls.jsonl','a') as f:f.write(json.dumps(record)+'\\n')
if '--generate-cli-skeleton' in a: print(json.dumps({'IfMatch':''}))
elif a[:2]==['s3api','get-object']:
 Path(a[a.index('--key')+2]).write_bytes((directory/'live.xml').read_bytes())
 print(json.dumps({'ETag':'"live-version"','ContentType':'application/xml','CacheControl':'public, max-age=900','ContentLanguage':'ja','Metadata':{'owner':'whole-site'}}))
elif a[:2]==['s3api','put-object']:
 if a[a.index('--key')+1]=='sitemap.xml':
  if os.environ['MOCK_MODE']=='conflict':
   (directory/'live.xml').write_text('<concurrent metadata="preserve"/>')
   print('PreconditionFailed: live sitemap ETag changed',file=sys.stderr);sys.exit(1)
  assert a[a.index('--if-match')+1]=='"live-version"'
  (directory/'live.xml').write_bytes(Path(a[a.index('--body')+1]).read_bytes())
 print('{}')
elif a[:2]==['cloudfront','create-invalidation']:print(json.dumps({'Invalidation':{'Id':'mock-invalidation'}}))
elif a[:2]==['cloudfront','wait']:pass
else:raise RuntimeError(a)
`,{mode:0o755});
 try{
  const result=spawnSync('python3',['scripts/publish-law-firm.py'],{cwd:root,encoding:'utf8',env:{...process.env,PATH:dir+path.delimiter+process.env.PATH,MOCK_DIRECTORY:dir,MOCK_MODE:mode,SITE_S3_BUCKET:'review-bucket',SITE_CF_DISTRIBUTION_ID:'EREVIEW123'}});
  return {result,original,live:fs.readFileSync(path.join(dir,'live.xml'),'utf8'),calls:fs.readFileSync(log,'utf8').trim().split('\n').map(JSON.parse),receipt:result.status===0?JSON.parse(fs.readFileSync(receiptPath,'utf8')):null};
 }finally{
  if(previous)fs.writeFileSync(receiptPath,previous);else fs.rmSync(receiptPath,{force:true});
  fs.rmSync(dir,{recursive:true,force:true});
 }
}
function puts(calls){return calls.filter(({args:a})=>a[0]==='s3api'&&a[1]==='put-object'&&a.includes('--body'));}
function key({args:a}){return a[a.indexOf('--key')+1];}
test('manifest owns only law entry and prefix, independently of the global sitemap',()=>{
 const manifest=JSON.parse(fs.readFileSync(path.join(root,'site/hp-management/law-firm/release-manifest.json'),'utf8'));
 assert.ok(manifest.files.every(f=>f.path==='hp-management/law-firm.html'||f.path.startsWith('hp-management/law-firm/')));
});
test('publisher conditionally appends only own URL while preserving live XML and S3 metadata',()=>{
 const {result,calls,original,live,receipt}=runPublisher('add');assert.equal(result.status,0,result.stderr);
 const uploads=puts(calls);const keys=uploads.map(key);
 assert.ok(keys.every(k=>k.startsWith('hp-management/law-firm/')||k==='hp-management/law-firm.html'||k==='sitemap.xml'));
 assert.deepEqual(keys.slice(-2),['hp-management/law-firm.html','sitemap.xml']);
 const addition=`<url xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><loc>${url}</loc></url>\n`;
 assert.equal(live,original.replace('</urlset>',addition+'</urlset>'));
 assert.equal(live.split(url).length-1,1);
 const sitemap=uploads.at(-1).args;
 assert.equal(sitemap[sitemap.indexOf('--if-match')+1],'"live-version"');
 assert.equal(sitemap[sitemap.indexOf('--cache-control')+1],'public, max-age=900');
 assert.equal(sitemap[sitemap.indexOf('--content-type')+1],'application/xml');
 assert.equal(sitemap[sitemap.indexOf('--content-language')+1],'ja');
 assert.deepEqual(JSON.parse(sitemap[sitemap.indexOf('--metadata')+1]),{owner:'whole-site'});
 assert.equal(receipt.objects,uploads.length);assert.deepEqual(receipt.object_keys,keys);
 assert.equal(receipt.sitemap_updated,true);
 assert.deepEqual(receipt.invalidation_paths,['/hp-management/law-firm.html','/hp-management/law-firm/*','/sitemap.xml']);
 const invalidation=calls.find(({args:a})=>a[1]==='create-invalidation').args;
 assert.deepEqual(invalidation.slice(invalidation.indexOf('--paths')+1,invalidation.indexOf('--output')),receipt.invalidation_paths);
 assert.ok(!calls.some(({args:a})=>a.includes('--delete')||a.includes('sync')));
});
test('existing own URL skips sitemap writes and invalidation, preserving all original metadata',()=>{
 const {result,calls,original,live,receipt}=runPublisher('existing');assert.equal(result.status,0,result.stderr);
 assert.equal(live,original);
 assert.ok(!puts(calls).some(p=>key(p)==='sitemap.xml'));
 assert.equal(receipt.sitemap_updated,false);assert.equal(receipt.objects,puts(calls).length);
 assert.deepEqual(receipt.invalidation_paths,['/hp-management/law-firm.html','/hp-management/law-firm/*']);
 const invalidation=calls.find(({args:a})=>a[1]==='create-invalidation').args;
 assert.deepEqual(invalidation.slice(invalidation.indexOf('--paths')+1,invalidation.indexOf('--output')),receipt.invalidation_paths);
});
test('conditional failure refuses overwrite without retry or invalidation',()=>{
 const {result,calls,live,receipt}=runPublisher('conflict');assert.notEqual(result.status,0);
 assert.match(result.stderr,/PreconditionFailed/);assert.match(result.stderr,/concurrent sitemap was not overwritten/);
 assert.equal(live,'<concurrent metadata="preserve"/>');
 assert.equal(puts(calls).filter(p=>key(p)==='sitemap.xml').length,1);
 assert.ok(!calls.some(({args:a})=>a[1]==='create-invalidation'));
 assert.equal(receipt,null);
});
