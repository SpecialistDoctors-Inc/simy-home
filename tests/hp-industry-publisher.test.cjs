const test = require('node:test');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const setup = String.raw`
import sys, json, tempfile, importlib.util, os, subprocess, hashlib
from pathlib import Path
sys.path.insert(0, 'scripts')
import hp_industry_release as release
spec=importlib.util.spec_from_file_location('publisher', 'scripts/publish-hp-industry-navigation.py')
pub=importlib.util.module_from_spec(spec); spec.loader.exec_module(pub)
workspace=tempfile.TemporaryDirectory(prefix='industry-publisher-test-')
root=Path(workspace.name)
site=root/'site'; site.mkdir()
for relative in release.ASSETS:
 p=site/relative; p.parent.mkdir(parents=True,exist_ok=True); p.write_text('reviewed support')
for relative in (release.HUB, 'index.html', 'ja.html', 'for/index.html', 'for/engineers/index.html', 'for/pharmaceutical-companies/index.html', 'guides/index.html'):
 p=site/relative; p.parent.mkdir(parents=True,exist_ok=True); p.write_text('<header class="sh-solutions-panel">menu</header>')
(site/'foreign.html').write_text('<header>other industry own header</header>')
(site/'clinic-service-v2.html').write_text('<header class="sh-solutions-panel">menu</header><link rel="canonical" href="https://simy.one/hp-management/clinic.html">')
manifest_path=root/release.MANIFEST.relative_to(release.ROOT)
manifest_path.parent.mkdir(parents=True)
manifest_path.write_bytes(release.encoded(release.plan(root)))
os.environ.update(SITE_S3_BUCKET='review-bucket',SITE_CF_DISTRIBUTION_ID='EREVIEW123',GITHUB_SHA='reviewed-commit')
os.environ.pop('EXPECTED_RELEASE_SHA256',None)
foreign='<url><loc>https://simy.one/foreign.html</loc><lastmod>2026-11-01</lastmod><priority>0.8</priority><image:image><image:loc>https://simy.one/keep.png</image:loc></image:image></url>'
original=('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n<!-- retain exact bytes -->\n'+foreign+'\n</urlset>').encode()
live=original
calls=[]
head={'ETag':'"live-etag"','ContentType':'application/xml','CacheControl':'public, max-age=900','ContentDisposition':'inline','ContentEncoding':'identity','ContentLanguage':'ja','Expires':'2030-01-01T00:00:00Z','WebsiteRedirectLocation':'/sitemap.xml','Metadata':{'owner':'whole-site','custom':'preserved'}}
conflict=False
http_mode='valid'
http_reads=[]
class Response:
 status=200
 def __init__(self,url): self.url=url; self.status=200 if http_mode!='http-error' else 404
 def __enter__(self): return self
 def __exit__(self,*args): pass
 def geturl(self): return self.url if http_mode!='foreign-origin' else 'https://foreign.example/landing'
 def read(self,limit):
  canonical=self.url if http_mode!='unknown-canonical' else 'https://simy.one/hp-management/unknown.html'
  ids='<section id="diagnosis"></section><section id="pricing"></section>' if http_mode!='missing-anchor' else ''
  return ('<link rel="canonical" href="'+canonical+'">'+ids).encode()
def opener(request,timeout):
 assert not calls, 'HTTP preflight must finish before all AWS calls'
 assert request.get_method()=='GET'
 http_reads.append(request.full_url)
 return Response(request.full_url)
def runner(args,output=False):
 global live
 calls.append(args)
 if args[:2]==['s3api','get-object']:
  Path(args[args.index('--key')+2]).write_bytes(live)
  return dict(head)
 if '--generate-cli-skeleton' in args: return {'IfMatch':''}
 if args[:2]==['s3api','put-object']:
  key=args[args.index('--key')+1]
  if key=='sitemap.xml':
   assert args[args.index('--if-match')+1]==head['ETag']
   if conflict:
    live=b'<concurrent keep="true"/>'
    raise subprocess.CalledProcessError(1,args,stderr='PreconditionFailed')
   live=Path(args[args.index('--body')+1]).read_bytes()
  return {}
 if args[:2]==['cloudfront','create-invalidation']: return {'Invalidation':{'Id':'mock-invalidation'}}
 if args[:2]==['cloudfront','wait']: return {}
 raise AssertionError(args)
def puts():return [args for args in calls if args[:2]==['s3api','put-object'] and '--body' in args]
def keys():return [args[args.index('--key')+1] for args in puts()]
`;
function run(source) {
  return execFileSync('python3', ['-c', setup + '\n' + source], {encoding:'utf8', maxBuffer:1024*1024}).trim();
}
test('plan deterministically scopes sources, aliases, metadata and excludes foreign industry objects', () => {
  run(String.raw`
first=release.encoded(release.plan(root)); assert first==manifest_path.read_bytes()
release.check(root)
objects=json.loads(first)['objects']; allowed={o['key'] for o in objects}
assert set(release.HUB_KEYS)<=allowed
assert 'foreign.html' not in allowed and 'sitemap.xml' not in allowed
assert 'hp-management/clinic.html' not in allowed
assert '/hp-management/clinic.html' in json.loads(first)['invalidation_paths']
for key,source in [('for/','for/index.html'),('for/engineers/','for/engineers/index.html'),('for/pharmaceutical-companies.html','for/pharmaceutical-companies/index.html'),('guides.html','guides/index.html'),('guides/','guides/index.html')]:
 alias=next(o for o in objects if o['key']==key)
 original=next(o for o in objects if o['key']==source)
 assert alias['source']==source and alias['sha256']==original['sha256'] and alias['bytes']==original['bytes']
assert 'for/engineers.html' not in allowed

assert {key for key in allowed if key.startswith('hp-management/law-firm/')}=={'hp-management/law-firm/release-manifest.json'}
assert all(o['bytes']>0 and len(o['sha256'])==64 for o in objects)
`);
});
test('actual publisher puts only planned keys, support/hub before menus, sitemap last, exact invalidation and receipt', () => {
  const output=JSON.parse(run(String.raw`
receipt=pub.publish(root,opener,runner)
planned=release.plan(root)['objects']; expected=[o['key'] for o in planned]+['sitemap.xml']
assert keys()==expected
phases=[o['phase'] for o in planned]; assert phases==sorted(phases,key={'support':0,'hub':1,'menu':2}.get)
assert live==original.replace(b'</urlset>',('<url xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><loc>'+release.URL+'</loc></url>\n</urlset>').encode())
assert live.count(release.URL.encode())==1
sitemap=puts()[-1]
for field,flag in [('ContentType','--content-type'),('CacheControl','--cache-control'),('ContentDisposition','--content-disposition'),('ContentEncoding','--content-encoding'),('ContentLanguage','--content-language'),('Expires','--expires'),('WebsiteRedirectLocation','--website-redirect-location')]:assert sitemap[sitemap.index(flag)+1]==head[field]
assert json.loads(sitemap[sitemap.index('--metadata')+1])==head['Metadata']
assert receipt['object_keys']==expected and receipt['objects']==len(expected)
assert receipt['manifest_sha256']==hashlib.sha256(manifest_path.read_bytes()).hexdigest()
assert receipt['commit']=='reviewed-commit' and receipt['invalidation_id']=='mock-invalidation'
assert receipt['invalidation_paths']==sorted(set(release.plan(root)['invalidation_paths'])|{'/sitemap.xml'})
assert '/' in receipt['invalidation_paths'] and '/hp-management/' in receipt['invalidation_paths']
assert all('*' not in p for p in receipt['invalidation_paths'])
assert calls[-1][:3]==['cloudfront','wait','invalidation-completed']
assert not any('sync' in a or '--delete' in a for a in calls)
assert receipt['preflight_urls']==http_reads and len(http_reads)==2
print(json.dumps({'objects':len(expected),'status':receipt['status']}))
`));
  assert.ok(output.objects>0); assert.equal(output.status,'uploaded_and_invalidated');
});
test('existing canonical hub URL skips live sitemap write preserving bytes and metadata', () => {
  run(String.raw`
live=original.replace(b'</urlset>',('<url><loc>'+release.URL+'</loc><lastmod>2020-01-01</lastmod></url></urlset>').encode())
before=live
receipt=pub.publish(root,opener,runner)
assert live==before and 'sitemap.xml' not in keys()
assert not receipt['sitemap_updated'] and '/sitemap.xml' not in receipt['invalidation_paths']
`);
});
test('legacy hub loc migrates to canonical HTML preserving all remaining XML bytes and metadata', () => {
  run(String.raw`
legacy='<url><loc>'+release.LEGACY_URL+'</loc><lastmod>2026-11-17</lastmod><priority>0.8</priority></url>'
live=original.replace(b'</urlset>',(legacy+'</urlset>').encode())
before=live
receipt=pub.publish(root,opener,runner)
assert live==before.replace(('<loc>'+release.LEGACY_URL+'</loc>').encode(),('<loc>'+release.URL+'</loc>').encode())
assert live.count(release.URL.encode())==1 and release.LEGACY_URL.encode() not in live
assert receipt['sitemap_updated'] and keys()[-1]=='sitemap.xml'
sitemap=puts()[-1]
assert sitemap[sitemap.index('--if-match')+1]==head['ETag']
assert json.loads(sitemap[sitemap.index('--metadata')+1])==head['Metadata']
`);
});
test('canonical already present keeps legacy URL untouched and skips writes; ambiguous legacy URLs fail safely', () => {
  run(String.raw`
legacy='<url><loc>'+release.LEGACY_URL+'</loc></url>'
canonical='<url><loc>'+release.URL+'</loc></url>'
both=original.replace(b'</urlset>',(legacy+canonical+'</urlset>').encode())
assert pub.extend_sitemap(both,head)==(both,False)
ambiguous=original.replace(b'</urlset>',(legacy+legacy+'</urlset>').encode())
try:pub.extend_sitemap(ambiguous,head)
except ValueError:pass
else:raise AssertionError('Duplicate legacy URLs accepted')
`);
});
test('If-Match conflict refuses concurrent overwrite and never retries or invalidates', () => {
  run(String.raw`
conflict=True
try:pub.publish(root,opener,runner)
except RuntimeError as error:assert 'concurrent sitemap was not overwritten' in str(error)
else:raise AssertionError('Conflict accepted')
assert live==b'<concurrent keep="true"/>'
assert keys().count('sitemap.xml')==1
assert not any(a[0]=='cloudfront' for a in calls)
assert not (root/'hp-industry-navigation-deployment.json').exists()
`);
});
test('foreign key injection, duplicate keys, changed bytes and reviewed digest mismatch fail before HTTP or AWS', () => {
  run(String.raw`
original_manifest=manifest_path.read_bytes()
for mode in ('foreign-key','duplicate-key','changed-source','wrong-digest'):
 manifest_path.write_bytes(original_manifest)
 data=json.loads(original_manifest)
 if mode=='foreign-key':data['objects'][0]['key']='private/foreign-object'
 if mode=='duplicate-key':data['objects'][1]['key']=data['objects'][0]['key']
 if mode=='changed-source':data['objects'][0]['bytes']+=1
 if mode=='wrong-digest':os.environ['EXPECTED_RELEASE_SHA256']='0'*64
 else:manifest_path.write_bytes(release.encoded(data))
 try:pub.publish(root,opener,runner)
 except ValueError:pass
 else:raise AssertionError(mode+' accepted')
 assert not calls and not http_reads
 os.environ.pop('EXPECTED_RELEASE_SHA256',None)
`);
});
test('unsafe source traversal and symlink escape fail plan construction', () => {
  run(String.raw`
for relative in ('../private.html','/etc/passwd','hp-management/../private.html','hp-management//index.html'):
 try:release.source_path(site,relative)
 except ValueError:pass
 else:raise AssertionError(relative)
external=root/'external.html';external.write_text('<header class="sh-solutions-panel">escape</header>')
(site/'escape.html').symlink_to(external)
try:release.plan(root)
except ValueError:pass
else:raise AssertionError('Escaping symlink accepted')
`);
});
test('unknown canonical, foreign redirect origin, non-200 and missing anchors stop all AWS writes', () => {
  run(String.raw`
for mode in ('unknown-canonical','foreign-origin','http-error','missing-anchor'):
 http_mode=mode
 try:pub.publish(root,opener,runner)
 except ValueError:pass
 else:raise AssertionError(mode+' accepted')
 assert not calls
`);
});
