const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {execFileSync}=require('node:child_process');
const run=source=>execFileSync('python3',['-c',source],{encoding:'utf8'}).trim();
const setup=`import sys, json, copy, tempfile, importlib.util
from pathlib import Path
sys.path.insert(0, 'scripts')
import hp_management_industries as c
catalog=json.loads(c.CATALOG.read_text())
`;
test('published catalog uses actual canonical paths and local sources',()=>{
 const data=JSON.parse(run(setup+`print(json.dumps({'published':c.published_industries(),'featured':c.featured_industries(),'aliases':c.published_aliases()}))`));
 assert.deepEqual(data.published.map(i=>i.id),['clinic','law-firm']);
 assert.equal(data.aliases['/hp-management/clinic.html'],'hp-management/clinic/index.html');
 assert.equal(data.featured.length,2);
});
test('additional published industries appear automatically; drafts stay hidden and featured navigation stays bounded',()=>{
 run(setup+`extra=copy.deepcopy(catalog['industries'][0])
extra.update(id='accountant',label='税理士',nav_label='税理士向けHP管理',url='/hp-management/accountant.html',source='hp-management/accountant.html')
draft=copy.deepcopy(extra)
draft.update(id='draft-industry',url='/hp-management/draft-industry.html',source='hp-management/draft-industry.html',status='draft')
with tempfile.TemporaryDirectory() as directory:
 site=Path(directory)
 for item in catalog['industries']+[extra]:
  for key in ('source','checkout_config'):
   p=site/item[key]; p.parent.mkdir(parents=True,exist_ok=True); p.touch()
 records=c.validate_catalog({'version':1,'industries':catalog['industries']+[extra,draft]},site)
 c._catalog=lambda: records
 assert len(c.published_industries()) == 3
 assert len(c.featured_industries()) == 2
 spec=importlib.util.spec_from_file_location('hub','scripts/build-hp-management-industries.py')
 hub=importlib.util.module_from_spec(spec); spec.loader.exec_module(hub)
 output=hub.render()
 assert 'data-industry="accountant"' in output
 assert 'draft-industry.html' not in output
 assert '"numberOfItems": 3' in output
`);
});
test('catalog rejects duplicate identifiers, unsafe paths, reserved hub, missing source and invalid status',()=>{
 run(setup+`cases=[None,[],{'version':1,'industries':[None]}]
for key,value in [('id','Bad_ID'),('id',12),('url','/hp-management/index.html'),('url','/other/foo.html'),('url','/hp-management/../foo.html'),('source','../escape.html'),('source','hp-management/missing.html'),('status','coming-soon'),('checkout_config','hp-management/../private.json')]:
 data=copy.deepcopy(catalog); data['industries'][0][key]=value; cases.append(data)
for key in ('id','url','source'):
 data=copy.deepcopy(catalog); data['industries'][1][key]=data['industries'][0][key]; cases.append(data)
for data in cases:
 try: c.validate_catalog(data)
 except ValueError: pass
 else: raise AssertionError('Invalid catalog accepted: '+repr(data))
`);
});
test('hub generation is deterministic and checkout prices are source-backed',()=>{
 execFileSync('python3',['scripts/build-hp-management-industries.py','--check']);
 const page=fs.readFileSync('site/hp-management/index.html','utf8');
 const records=require('../scripts/hp-management-industries.json').industries.filter(i=>i.status==='published');
 for(const item of records){
  for(const suffix of ['', '#diagnosis','#pricing'])assert.ok(page.includes(`href="${item.url}${suffix}"`));
  const prices=Object.values(JSON.parse(fs.readFileSync('site/'+item.checkout_config)).plans);
  const min=prices.reduce((a,b)=>a.monthlyYen<b.monthlyYen?a:b);
  assert.ok(page.includes(min.monthlyYen.toLocaleString('en-US')));
  assert.ok(page.includes(min.taxInclusiveYen.toLocaleString('en-US')));
 }
 assert.match(page,/<meta name="robots" content="index,follow">/);
 assert.match(page,/<link rel="canonical" href="https:\/\/simy.one\/hp-management\/">/);
 assert.doesNotMatch(page,/location.replace|http-equiv="refresh"/);
 run(setup+`from html.parser import HTMLParser
class Links(HTMLParser):
 def __init__(self): super().__init__(); self.active=False
 def handle_starttag(self,tag,attrs):
  if tag=='a': assert not self.active, 'Nested anchor'; self.active=True
 def handle_endtag(self,tag):
  if tag=='a': self.active=False
Links().feed(Path('site/hp-management/index.html').read_text())
`);
});
test('SEO aliases and canonical helper resolve both hub and production clinic URL',()=>{
 run(setup+`spec=importlib.util.spec_from_file_location('seo','scripts/check-site-seo.py')
seo=importlib.util.module_from_spec(spec); spec.loader.exec_module(seo)
assert seo.canonical_url('hp-management/index.html') == 'https://simy.one/hp-management/'
assert seo.canonical_url('hp-management/clinic/index.html') == 'https://simy.one/hp-management/clinic.html'
`);
});
