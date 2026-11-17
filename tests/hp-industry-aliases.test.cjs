const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {execFileSync} = require('node:child_process');
const setup = String.raw`
import sys, json, tempfile, importlib.util, os
from pathlib import Path
sys.path.insert(0,'scripts')
spec=importlib.util.spec_from_file_location('aliases','scripts/publish-hp-industry-aliases.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
workspace=tempfile.TemporaryDirectory(prefix='hp-alias-test-')
root=Path(workspace.name);site=root/'site'
for relative,body in [('hp-management/index.html','<h1>Current published industries</h1>'),('guides/index.html','<h1>Current guides</h1>')]:
 source=site/relative;source.parent.mkdir(parents=True,exist_ok=True);source.write_text(body)
os.environ['SITE_S3_BUCKET']='review-bucket'
calls=[]
def aws(args):
 assert args[:2]==['s3api','put-object']
 assert '--delete' not in args and 'sync' not in args
 calls.append({'args':args,'body':Path(args[args.index('--body')+1]).read_text(),'key':args[args.index('--key')+1]})
`;
function run(source) {
 return execFileSync('python3',['-c',setup+'\n'+source],{encoding:'utf8',maxBuffer:1024*1024}).trim();
}
test('ordinary alias publisher writes exactly five owned keys from two current sources, without a release snapshot',()=>{
 run(String.raw`
receipt=module.publish(root,aws)
expected={'hp-management.html','hp-management/','hp-management','guides.html','guides/'}
assert {call['key'] for call in calls}==expected and len(calls)==5
assert receipt['objects']==5 and set(receipt['object_keys'])==expected
assert not (root/'docs').exists()
for call in calls:
 key=call['key'];args=call['args']
 expected_source='hp-management/index.html' if key.startswith('hp-management') else 'guides/index.html'
 assert Path(args[args.index('--body')+1])==site/expected_source
 assert call['body']==(site/expected_source).read_text()
 assert args[args.index('--content-type')+1]=='text/html; charset=utf-8'
 assert args[args.index('--cache-control')+1]=='public, max-age=300'
 assert args[args.index('--bucket')+1]=='review-bucket'
# A later ordinary release must refresh aliases from new source bytes, rather
# than retaining the old hub HTML or consulting the one-time release manifest.
(site/'hp-management/index.html').write_text('<h1>New industry now published</h1>')
calls.clear();module.publish(root,aws)
assert all(call['body']=='<h1>New industry now published</h1>' for call in calls if call['key'].startswith('hp-management'))
`);
});
test('all alias sources are checked before AWS; missing, empty and escaping sources cannot partially publish',()=>{
 run(String.raw`
guide=site/'guides/index.html';original=guide.read_text()
for mode in ('missing','empty','escaping'):
 guide.unlink(missing_ok=True)
 if mode=='empty':guide.touch()
 if mode=='escaping':
  outside=root/'outside.html';outside.write_text('private outside source');guide.symlink_to(outside)
 try:module.publish(root,aws)
 except ValueError:pass
 else:raise AssertionError(mode+' source accepted')
 assert not calls
 guide.unlink(missing_ok=True);guide.write_text(original)
`);
});
const workflow=fs.readFileSync('.github/workflows/deploy-site.yml','utf8');
function step(name) {
 const marker='      - name: '+name;
 const start=workflow.indexOf(marker);assert.ok(start>=0,'missing step '+name);
 const end=workflow.indexOf('\n      - name:',start+marker.length);
 return workflow.slice(start,end<0?workflow.length:end);
}
function syncIncludes(body,key) {
 const rules=[...body.matchAll(/--(include|exclude) "([^"]+)"/g)];
 let included=true;
 for(const [,kind,glob] of rules) {
  const regex='^'+glob.replace(/[.+?^${}()|[\]\\]/g,'\\$&').replace(/\*/g,'.*')+'$';
  if(new RegExp(regex).test(key))included=kind==='include';
 }
 return included;
}
test('ordinary root sync deletion filters protect every publisher-owned alias until explicit refresh after static sync',()=>{
 const html=step('Sync HTML files (short cache)');
 const assets=step('Sync static assets (long cache)');
 const aliases=['hp-management.html','hp-management/','hp-management','guides.html','guides/'];
 assert.ok(html.includes('--delete')&&assets.includes('--delete'));
 for(const key of aliases) {
  assert.equal(syncIncludes(html,key),false,'HTML sync must preserve '+key);
  assert.equal(syncIncludes(assets,key),false,'static sync must preserve '+key);
 }
 assert.equal(syncIncludes(html,'unrelated-old.html'),true,'ordinary obsolete HTML remains owned by sync');
 assert.equal(syncIncludes(assets,'unrelated-old.css'),true,'ordinary obsolete assets remain owned by sync');
 const refresh=step('Refresh HP industry and guide aliases');
 assert.match(refresh,/SITE_S3_BUCKET: \$\{\{ secrets\.SITE_S3_BUCKET \}\}/);
 assert.match(refresh,/run: python3 scripts\/publish-hp-industry-aliases\.py/);
 assert.ok(workflow.indexOf(refresh)>workflow.indexOf(assets));
 assert.ok(workflow.indexOf(refresh)<workflow.indexOf('      - name: Invalidate CloudFront cache'));
 assert.ok(workflow.includes("- 'scripts/publish-hp-industry-aliases.py'"));
 assert.doesNotMatch(workflow,/hp_industry_release\.py|EXPECTED_RELEASE_SHA256/);
});
