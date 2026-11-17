const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {execFileSync} = require('node:child_process');
const setup = String.raw`
import sys,json,tempfile,importlib.util,os,hashlib,copy
from pathlib import Path
sys.path.insert(0,'scripts')
import locale_navigation_release as release
spec=importlib.util.spec_from_file_location('publisher','scripts/publish-locale-navigation.py')
pub=importlib.util.module_from_spec(spec);spec.loader.exec_module(pub)
workspace=tempfile.TemporaryDirectory(prefix='locale-publisher-test-')
root=Path(workspace.name);site=root/'site';site.mkdir()
for source in release.SUPPORT:
 path=site/source;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('reviewed support')
for source in ('index.html','ja.html','for/index.html','for/engineers/index.html','for/pharmaceutical-companies/index.html','guides/index.html','hp-management/index.html'):
 path=site/source;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(release.MARKER+'<h1>Shared locale page</h1>')
for source in release.EXPLICIT_PAGES:
 path=site/source;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('<a href="/ja.html">SIMY</a><h1>Japanese service page</h1>')
(site/'clinic-service-v2.html').write_text(release.MARKER+'<link rel="canonical" href="https://simy.one/hp-management/clinic.html">')
(site/'foreign.html').write_text('<h1>No shared locale header</h1>')
for source in ('hp-management/law-firm/assets/image.png','hp-management/law-firm/diagnosis.js','hp-management/law-firm/pricing.json','sitemap.xml'):
 path=site/source;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('Unrelated data must not publish')
manifest=root/release.MANIFEST_RELATIVE;manifest.parent.mkdir(parents=True,exist_ok=True)
manifest.write_bytes(release.encoded(release.plan(root)))
os.environ.update(SITE_S3_BUCKET='review-bucket',SITE_CF_DISTRIBUTION_ID='EREVIEW123',GITHUB_SHA='reviewed-commit')
os.environ.pop('EXPECTED_RELEASE_SHA256',None)
calls=[]
def aws(args,output=False):
 calls.append(args)
 if args[:2]==['s3api','put-object']:return {}
 if args[:2]==['cloudfront','create-invalidation']:return {'Invalidation':{'Id':'review-invalidation'}}
 if args[:2]==['cloudfront','wait']:return {}
 raise AssertionError(args)
def uploads():return [a for a in calls if a[:2]==['s3api','put-object']]
`;
function run(source) {return execFileSync('python3',['-c',setup+'\n'+source],{encoding:'utf8',maxBuffer:1024*1024}).trim();}
test('deterministic locale plan owns marker HTML, explicit Japanese clinic/law pages and bounded index aliases only',()=>{
 run(String.raw`
plan=release.plan(root);assert release.encoded(plan)==manifest.read_bytes()
objects=plan['objects'];keys={o['key'] for o in objects}
assert keys=={'site-header.js','i18n.js','hp-management/law-firm/release-manifest.json','index.html','ja.html','for/index.html','for/','for/engineers/index.html','for/engineers/','for/pharmaceutical-companies/index.html','for/pharmaceutical-companies/','for/pharmaceutical-companies.html','guides/index.html','guides/','guides.html','hp-management/index.html','hp-management/','hp-management.html','hp-management','hp-management/clinic/index.html','hp-management/clinic/','hp-management/clinic.html','hp-management/law-firm.html','clinic-service-v2.html'}
assert '' not in keys and '/' not in keys
assert '/' in plan['invalidation_paths']
assert all(o['source'].endswith('.html') or o['source'] in release.SUPPORT for o in objects)
assert not any(o['key'] in ('sitemap.xml','foreign.html') or o['key'].endswith(('.png','diagnosis.js','pricing.json')) for o in objects)
for source in ('hp-management/clinic/index.html','hp-management/law-firm.html'):
 assert release.MARKER not in (site/source).read_text()
 assert any(o['source']==source for o in objects)
assert len([o for o in objects if o['key'].startswith('hp-management/law-firm/')])==1
clinic=next(o for o in objects if o['key']=='hp-management/clinic.html')
assert clinic['source']=='hp-management/clinic/index.html'
`);
});
test('actual publisher writes exact reviewed keys, preserves cache/content types, invalidates exact paths then waits and receipts hashes',()=>{
 run(String.raw`
plan=release.plan(root)
os.environ['EXPECTED_RELEASE_SHA256']=hashlib.sha256(manifest.read_bytes()).hexdigest()
receipt=pub.publish(root,aws)
assert [a[a.index('--key')+1] for a in uploads()]==[o['key'] for o in plan['objects']]
assert all('sync' not in a and '--delete' not in a for a in calls)
assert all(a[a.index('--cache-control')+1]=='public, max-age=300' for a in uploads())
for args,item in zip(uploads(),plan['objects']):
 assert Path(args[args.index('--body')+1])==site/item['source']
 kind='text/html' if item['source'].endswith('.html') else 'text/javascript' if item['source'].endswith('.js') else 'application/json'
 assert args[args.index('--content-type')+1]==kind+'; charset=utf-8'
assert calls[-2][:2]==['cloudfront','create-invalidation'] and calls[-1][:3]==['cloudfront','wait','invalidation-completed']
assert calls[-2][calls[-2].index('--paths')+1:calls[-2].index('--output')]==plan['invalidation_paths']
assert all('*' not in path for path in receipt['invalidation_paths'])
assert receipt['object_keys']==[o['key'] for o in plan['objects']]
assert receipt['objects']==len(uploads()) and receipt['commit']=='reviewed-commit'
assert receipt['manifest_sha256']==os.environ['EXPECTED_RELEASE_SHA256']
assert receipt['object_hashes']==[{key:o[key] for key in ('key','source','bytes','sha256')} for o in plan['objects']]
assert json.loads((root/'locale-navigation-deployment.json').read_text())==receipt
`);
});
test('tampered source, digest, source path, injected key, duplicate key and changed invalidation scope reject before AWS',()=>{
 run(String.raw`
original=manifest.read_bytes()
for mode in ('source','digest','traversal','foreign-key','duplicate-key','invalidation'):
 manifest.write_bytes(original);data=json.loads(original)
 if mode=='source':(site/'site-header.js').write_text('tampered after review')
 if mode=='digest':os.environ['EXPECTED_RELEASE_SHA256']='0'*64
 if mode=='traversal':data['objects'][0]['source']='../private'
 if mode=='foreign-key':data['objects'][0]['key']='hp-management/law-firm/pricing.json'
 if mode=='duplicate-key':data['objects'][1]['key']=data['objects'][0]['key']
 if mode=='invalidation':data['invalidation_paths']=['/*']
 if mode not in ('source','digest'):manifest.write_bytes(release.encoded(data))
 try:pub.publish(root,aws)
 except ValueError:pass
 else:raise AssertionError(mode+' tamper accepted')
 assert not calls
 (site/'site-header.js').write_text('reviewed support');os.environ.pop('EXPECTED_RELEASE_SHA256',None)
`);
});
test('escaping symlink and missing explicit service source fail before any upload',()=>{
 run(String.raw`
source=site/'hp-management/clinic/index.html';original=source.read_bytes();source.unlink()
for mode in ('missing','symlink'):
 if mode=='symlink':
  outside=root/'external.html';outside.write_bytes(original);source.symlink_to(outside)
 try:pub.publish(root,aws)
 except ValueError:pass
 else:raise AssertionError(mode+' source accepted')
 assert not calls
`);
});
test('canonical-only utility URL never assigns upload ownership',()=>{
 run(String.raw`
path=site/'utility.html';path.write_text(release.MARKER+'<link rel="canonical" href="https://simy.one/untouched-landing.html">')
plan=release.plan(root)
assert '/untouched-landing.html' in plan['invalidation_paths']
assert not any(o['key']=='untouched-landing.html' for o in plan['objects'])
`);
});
test('manual workflow pins reviewed digest before credentials, main branch, production environment and bounded duration',()=>{
 const workflow=fs.readFileSync('.github/workflows/deploy-locale-navigation.yml','utf8');
 assert.match(workflow,/workflow_dispatch:/);assert.doesNotMatch(workflow,/\n  push:/);
 assert.match(workflow,/if: github\.ref == 'refs\/heads\/main'/);
 assert.match(workflow,/timeout-minutes: 20/);assert.match(workflow,/environment: prod/);
 assert.match(workflow,/group: locale-navigation-production/);
 assert.match(workflow,/EXPECTED_RELEASE_SHA256: \$\{\{ inputs.expected_manifest_sha256 \}\}/);
 assert.ok(workflow.indexOf('python3 scripts/locale_navigation_release.py --check')<workflow.indexOf('uses: aws-actions/configure-aws-credentials'));
 assert.match(workflow,/test -n "\$EXPECTED_RELEASE_SHA256"/);
 assert.match(workflow,/python3 scripts\/publish-locale-navigation.py/);
 assert.doesNotMatch(workflow,/sync |--delete|publish-function/);
});
