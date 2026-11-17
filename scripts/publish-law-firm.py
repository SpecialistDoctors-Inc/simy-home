"""Upload only law-firm objects and conditionally extend the live sitemap."""
from pathlib import Path
import hashlib,json,mimetypes,os,re,subprocess,tempfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parents[1]
subprocess.run(['python3',str(ROOT/'scripts/check-law-firm-release.py')],check=True)
bucket=os.environ['SITE_S3_BUCKET'];distribution=os.environ['SITE_CF_DISTRIBUTION_ID']
assert re.fullmatch('[a-z0-9][a-z0-9.-]+',bucket)
assert re.fullmatch('[A-Z0-9]+',distribution)
entry='hp-management/law-firm.html';prefix='hp-management/law-firm/'
manifest_path=ROOT/'site'/prefix/'release-manifest.json'
manifest=json.loads(manifest_path.read_text())
files=sorted(f['path'] for f in manifest['files'] if f['path']!=entry)+[prefix+'release-manifest.json',entry]
written=[]
with tempfile.TemporaryDirectory(prefix='law-firm-sitemap-') as temporary:
    sitemap=Path(temporary)/'sitemap.xml'
    head=json.loads(subprocess.check_output(['aws','s3api','get-object','--bucket',bucket,'--key','sitemap.xml',str(sitemap),'--output','json']))
    original=sitemap.read_bytes()
    root=ET.fromstring(original)
    assert root.tag=='{http://www.sitemaps.org/schemas/sitemap/0.9}urlset','Unexpected sitemap root'
    urls=[node.findtext('{*}loc') for node in root.findall('{*}url')]
    assert urls.count(manifest['url'])<=1,'Duplicate law-firm sitemap URL'
    sitemap_updated=manifest['url'] not in urls
    if sitemap_updated:
        assert head.get('ETag'),'Sitemap ETag is required'
        assert 'IfMatch' in json.loads(subprocess.check_output(['aws','s3api','put-object','--generate-cli-skeleton','input'])),'AWS CLI conditional writes required'
        # Insert one element without reserializing any existing XML or metadata.
        closing=list(re.finditer(rb'</(?:[A-Za-z_][\w.-]*:)?urlset\s*>',original))
        assert len(closing)==1,'Unexpected sitemap closing element'
        addition=('<url xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><loc>'+escape(manifest['url'])+'</loc></url>\n').encode('utf-8')
        updated=original[:closing[0].start()]+addition+original[closing[0].start():]
        assert [n.findtext('{*}loc') for n in ET.fromstring(updated).findall('{*}url')]==urls+[manifest['url']]
        sitemap.write_bytes(updated)
    for key in files:
        assert key==entry or key.startswith(prefix)
        source=ROOT/'site'/key
        content_type=mimetypes.guess_type(key)[0] or 'application/octet-stream'
        if key.endswith('.js'):content_type='text/javascript'
        if key.endswith(('.html','.css','.js','.txt')):content_type+='; charset=utf-8'
        subprocess.run(['aws','s3api','put-object','--bucket',bucket,'--key',key,'--body',str(source),'--content-type',content_type,'--cache-control','public, max-age=300'],check=True,stdout=subprocess.DEVNULL)
        written.append(key)
    if sitemap_updated:
        command=['aws','s3api','put-object','--bucket',bucket,'--key','sitemap.xml','--body',str(sitemap),'--if-match',head['ETag']]
        for field,flag in [('ContentType','--content-type'),('CacheControl','--cache-control'),('ContentDisposition','--content-disposition'),('ContentEncoding','--content-encoding'),('ContentLanguage','--content-language'),('Expires','--expires'),('WebsiteRedirectLocation','--website-redirect-location')]:
            if field in head:command += [flag,head[field]]
        if 'Metadata' in head:command += ['--metadata',json.dumps(head['Metadata'])]
        try:subprocess.run(command,check=True,stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError as error:
            raise RuntimeError('Conditional sitemap publication failed; concurrent sitemap was not overwritten. Law-firm objects were uploaded; invalidation was not requested.') from error
        written.append('sitemap.xml')
paths=['/'+entry,'/'+prefix+'*']+(['/sitemap.xml'] if sitemap_updated else [])
result=json.loads(subprocess.check_output(['aws','cloudfront','create-invalidation','--distribution-id',distribution,'--paths',*paths,'--output','json']))
invalidation=result['Invalidation']['Id']
subprocess.run(['aws','cloudfront','wait','invalidation-completed','--distribution-id',distribution,'--id',invalidation],check=True)
receipt={'url':manifest['url'],'commit':os.environ.get('GITHUB_SHA'),'objects':len(written),'object_keys':written,'sitemap_updated':sitemap_updated,'invalidation_paths':paths,'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),'invalidation_id':invalidation,'status':'uploaded_and_invalidated'}
(ROOT/'law-firm-deployment.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt))
