"""Upload verified law-firm objects only. Never sync/delete the wider site."""
from pathlib import Path
import hashlib,json,mimetypes,os,re,subprocess

ROOT=Path(__file__).resolve().parents[1]
subprocess.run(['python3',str(ROOT/'scripts/check-law-firm-release.py')],check=True)
bucket=os.environ['SITE_S3_BUCKET'];distribution=os.environ['SITE_CF_DISTRIBUTION_ID']
assert re.fullmatch('[a-z0-9][a-z0-9.-]+',bucket)
assert re.fullmatch('[A-Z0-9]+',distribution)
entry='hp-management/law-firm.html';prefix='hp-management/law-firm/'
manifest_path=ROOT/'site'/prefix/'release-manifest.json'
manifest=json.loads(manifest_path.read_text())
files=sorted([f['path'] for f in manifest['files'] if f['path']!=entry])+[prefix+'release-manifest.json',entry]
for key in files:
    assert key==entry or key.startswith(prefix)
    source=ROOT/'site'/key
    content_type=mimetypes.guess_type(key)[0] or 'application/octet-stream'
    if key.endswith('.js'):content_type='text/javascript'
    if key.endswith(('.html','.css','.js','.txt')):content_type+='; charset=utf-8'
    subprocess.run(['aws','s3api','put-object','--bucket',bucket,'--key',key,'--body',str(source),'--content-type',content_type,'--cache-control','public, max-age=300'],check=True,stdout=subprocess.DEVNULL)
result=json.loads(subprocess.check_output(['aws','cloudfront','create-invalidation','--distribution-id',distribution,'--paths','/'+entry,'/'+prefix+'*','--output','json']))
invalidation=result['Invalidation']['Id']
subprocess.run(['aws','cloudfront','wait','invalidation-completed','--distribution-id',distribution,'--id',invalidation],check=True)
receipt={'url':manifest['url'],'commit':os.environ.get('GITHUB_SHA'),'objects':len(files),'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),'invalidation_id':invalidation,'status':'uploaded_and_invalidated'}
(ROOT/'law-firm-deployment.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt))
