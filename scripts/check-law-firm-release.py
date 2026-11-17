"""Validate only the isolated law-firm service release; no network or dependencies."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
import hashlib,json,os,re
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]/'site'
ENTRY='hp-management/law-firm.html'
PREFIX='hp-management/law-firm/'
MANIFEST=ROOT/PREFIX/'release-manifest.json'
data=MANIFEST.read_bytes()
digest=hashlib.sha256(data).hexdigest()
expected=os.environ.get('EXPECTED_RELEASE_SHA256')
if expected:assert re.fullmatch('[a-f0-9]{64}',expected) and digest==expected,'Unexpected release manifest'
manifest=json.loads(data)
assert manifest['url']=='https://simy.one/'+ENTRY
paths=set()
for item in manifest['files']:
    path=item['path']
    assert path == ENTRY or path.startswith(PREFIX),path
    assert '..' not in Path(path).parts and not Path(path).is_absolute(),path
    assert path not in paths,path
    paths.add(path)
    blob=(ROOT/path).read_bytes()
    assert len(blob)==item['bytes'] and hashlib.sha256(blob).hexdigest()==item['sha256'],path
assert ENTRY in paths
actual={p.relative_to(ROOT).as_posix() for p in (ROOT/PREFIX).rglob('*') if p.is_file() and p!=MANIFEST}|{ENTRY}
assert actual==paths,'Untracked or missing release files'
urls=[e.text for e in ET.parse(ROOT/'sitemap.xml').findall('.//{*}loc')]
assert len(urls)==len(set(urls)) and urls.count(manifest['url'])==1

class Page(HTMLParser):
    def __init__(self):super().__init__();self.meta={};self.canonical=None;self.resources=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='meta':self.meta[a.get('name',a.get('property'))]=a.get('content','')
        if tag=='link' and a.get('rel')=='canonical':self.canonical=a.get('href')
        if tag in ['script','img'] and a.get('src'):self.resources.append(a['src'])
        if tag=='link' and a.get('rel') in ['stylesheet','icon','apple-touch-icon']:self.resources.append(a['href'])
p=Page();p.feed((ROOT/ENTRY).read_text())
assert p.canonical==manifest['url'] and 'noindex' not in p.meta['robots']
assert p.meta['og:url']==manifest['url'] and p.meta['og:image'].startswith('https://simy.one/'+PREFIX)
for value in p.resources:
    url=urlsplit(value)
    if url.scheme:assert url.scheme=='https',value;continue
    assert url.path.lstrip('/') in paths,value
    assert url.path.startswith('/'+PREFIX),value
for path in paths:
    if not path.endswith(('.js','.css')):continue
    text=(ROOT/path).read_text()
    if path.endswith('/10c67d62bb46fb.js'):
        # Preserve real product names and their linked disclosures verbatim.
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()=='10c67d62bb46fb22e393ff5edcd2c4f9d969548793204f81690bf79e54efd419'
        continue
    assert not re.search(r'''["']/(?:assets/|vendor/|simy-icon|hp-management/clinic-checkout)''',text),path
    assert not re.search(r'医療機関|患者さん|診療|院長|この医院|感染症|治療|専門外来|病歴|保護者への影響|成長相談ページ',text),path
    assert 'https://simy.one/hp-management/clinic.html' not in text,path
    assert 'clinic-growth-workflow-' not in text,path
print(json.dumps({'files':len(paths),'bytes':sum(f['bytes'] for f in manifest['files']),'manifest_sha256':digest,'status':'passed'}))
