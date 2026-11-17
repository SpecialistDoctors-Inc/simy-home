"""Upload the law-firm package and its additive sitemap entry; never sync/delete."""
from pathlib import Path
import hashlib,json,mimetypes,os,re,subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
subprocess.run(['python3',str(ROOT/'scripts/check-law-firm-release.py')],check=True)
bucket=os.environ['SITE_S3_BUCKET'];distribution=os.environ['SITE_CF_DISTRIBUTION_ID']
assert re.fullmatch('[a-z0-9][a-z0-9.-]+',bucket)
assert re.fullmatch('[A-Z0-9]+',distribution)
entry='hp-management/law-firm.html';prefix='hp-management/law-firm/'
manifest_path=ROOT/'site'/prefix/'release-manifest.json'
manifest=json.loads(manifest_path.read_text())
assert 'IfMatch' in json.loads(subprocess.check_output(['aws','s3api','put-object','--generate-cli-skeleton','input'])),'AWS CLI conditional writes required'
# Refuse to overwrite concurrent sitemap changes; only our URL may be added.
sitemap_before=ROOT/'law-firm-sitemap-before.xml'
head=json.loads(subprocess.check_output(['aws','s3api','get-object','--bucket',bucket,'--key','sitemap.xml',str(sitemap_before),'--output','json']))
records=lambda path:{e.find('{*}loc').text:ET.tostring(e,encoding='unicode').strip() for e in ET.parse(path).getroot()}
old=records(sitemap_before);new=records(ROOT/'site/sitemap.xml')
assert set(new)==set(old)|{manifest['url']},'Sitemap baseline changed'
assert all(new[url]==value for url,value in old.items()),'Existing sitemap metadata changed'
files=sorted([f['path'] for f in manifest['files'] if f['path'] not in [entry,'sitemap.xml']])+[prefix+'release-manifest.json',entry,'sitemap.xml']
for key in files:
    assert key in [entry,'sitemap.xml'] or key.startswith(prefix)
    source=ROOT/'site'/key
    content_type=mimetypes.guess_type(key)[0] or 'application/octet-stream'
    if key.endswith('.js'):content_type='text/javascript'
    if key.endswith(('.html','.css','.js','.txt')):content_type+='; charset=utf-8'
    command=['aws','s3api','put-object','--bucket',bucket,'--key',key,'--body',str(source),'--content-type',content_type,'--cache-control','public, max-age=300']
    if key=='sitemap.xml':command+=['--if-match',head['ETag']]
    subprocess.run(command,check=True,stdout=subprocess.DEVNULL)
result=json.loads(subprocess.check_output(['aws','cloudfront','create-invalidation','--distribution-id',distribution,'--paths','/'+entry,'/'+prefix+'*','/sitemap.xml','--output','json']))
invalidation=result['Invalidation']['Id']
subprocess.run(['aws','cloudfront','wait','invalidation-completed','--distribution-id',distribution,'--id',invalidation],check=True)
receipt={'url':manifest['url'],'commit':os.environ.get('GITHUB_SHA'),'objects':len(files),'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),'invalidation_id':invalidation,'status':'uploaded_and_invalidated'}
(ROOT/'law-firm-deployment.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt))
