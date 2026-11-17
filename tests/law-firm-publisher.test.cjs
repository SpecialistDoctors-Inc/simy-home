const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const artifacts=['law-firm-deployment.json','law-firm-sitemap-before.xml'];

function runPublisher(changed){
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'law-publisher-'));
 const log=path.join(dir,'calls.jsonl');
 for(const name of artifacts)assert.ok(!fs.existsSync(path.join(root,name)),`Preserve existing ${name}`);
 fs.writeFileSync(path.join(dir,'aws'),`#!/usr/bin/env python3
import json,os,sys,xml.etree.ElementTree as ET
from pathlib import Path
a=sys.argv[1:]
with open(os.environ['MOCK_AWS_LOG'],'a') as f:f.write(json.dumps(a)+'\\n')
if '--generate-cli-skeleton' in a: print(json.dumps({'IfMatch':''}))
elif a[:2]==['s3api','get-object']:
 tree=ET.parse('site/sitemap.xml');r=tree.getroot()
 for n in list(r):
  if n.findtext('{*}loc')=='https://simy.one/hp-management/law-firm.html':r.remove(n)
 if os.environ.get('MOCK_CHANGED')=='1':r[0].find('{*}loc').text='https://simy.one/concurrent-change.html'
 Path(a[a.index('--key')+2]).write_bytes(ET.tostring(r))
 print(json.dumps({'ETag':'"sitemap-baseline"'}))
elif a[:2]==['s3api','put-object']:print('{}')
elif a[:2]==['cloudfront','create-invalidation']:print(json.dumps({'Invalidation':{'Id':'mock-invalidation'}}))
elif a[:2]==['cloudfront','wait']:pass
else:raise RuntimeError(a)
`,{mode:0o755});
 try{
  const result=spawnSync('python3',['scripts/publish-law-firm.py'],{cwd:root,encoding:'utf8',env:{...process.env,PATH:dir+path.delimiter+process.env.PATH,MOCK_AWS_LOG:log,MOCK_CHANGED:changed?'1':'0',SITE_S3_BUCKET:'review-bucket',SITE_CF_DISTRIBUTION_ID:'EREVIEW123'}});
  return {result,calls:fs.readFileSync(log,'utf8').trim().split('\n').map(JSON.parse)};
 }finally{
  for(const name of artifacts)fs.rmSync(path.join(root,name),{force:true});
  fs.rmSync(dir,{recursive:true,force:true});
 }
}
test('publisher writes only reviewed objects and conditionally adds the sitemap entry',()=>{
 const {result,calls}=runPublisher(false);assert.equal(result.status,0,result.stderr);
 const puts=calls.filter(a=>a[0]==='s3api'&&a[1]==='put-object'&&!a.includes('--generate-cli-skeleton'));
 const keys=puts.map(a=>a[a.indexOf('--key')+1]);
 assert.ok(keys.every(k=>k.startsWith('hp-management/law-firm/')||k==='hp-management/law-firm.html'||k==='sitemap.xml'));
 assert.deepEqual(keys.slice(-2),['hp-management/law-firm.html','sitemap.xml']);
 const sitemap=puts.at(-1);assert.equal(sitemap[sitemap.indexOf('--if-match')+1],'"sitemap-baseline"');
 const invalidation=calls.find(a=>a[1]==='create-invalidation');
 assert.deepEqual(invalidation.slice(invalidation.indexOf('--paths')+1,invalidation.indexOf('--output')),['/hp-management/law-firm.html','/hp-management/law-firm/*','/sitemap.xml']);
 assert.ok(!calls.some(a=>a.includes('--delete')||a.includes('sync')));
});
test('publisher refuses a changed sitemap before uploading any object',()=>{
 const {result,calls}=runPublisher(true);assert.notEqual(result.status,0);
 assert.match(result.stderr,/Sitemap baseline changed/);
 assert.ok(!calls.some(a=>a[0]==='s3api'&&a[1]==='put-object'&&!a.includes('--generate-cli-skeleton')));
});
