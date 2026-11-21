const test = require('node:test');
const {execFileSync} = require('node:child_process');
const path = require('node:path');

test('article authors/dates and breadcrumb structured data agree with visible editorial information', () => {
  execFileSync('python3', ['-c', `
import json,re,html
from urllib.parse import urljoin
from pathlib import Path
data=json.loads(Path('scripts/content-pages.json').read_text())
for page in data['pages']:
 for locale,url in page['paths'].items():
  source=(Path('site')/(url.lstrip('/')+('index.html' if url.endswith('/') else ''))).read_text()
  graph=next(json.loads(s)['@graph'] for s in re.findall(r'<script type="application/ld\\+json">(.*?)</script>',source,re.S) if '@graph' in s)
  schema=next(o for o in graph if o['@type']=='BreadcrumbList')
  visible=re.search(r'<ol class="crumbs">(.*?)</ol>',source,re.S)[1]
  names=[html.unescape(re.sub('<[^>]+>','',s)).strip() for s in re.findall(r'<li[^>]*>(.*?)</li>',visible,re.S)]
  assert names==[o['name'] for o in schema['itemListElement']],(url,names)
  links=re.findall(r'<a href="([^\"]+)">',visible)
  assert [urljoin('https://simy.one',html.unescape(h)) for h in links]==[o['item'] for o in schema['itemListElement'][:-1]],url
  assert [o['position'] for o in schema['itemListElement']]==list(range(1,len(names)+1)),url
  if page['kind']=='guide':
   article=next(o for o in graph if o['@type']=='Article')
   byline=re.search(r'<p class="byline">(.*?)</p>',source,re.S)[1]
   assert article['author']['name'] in byline,url
   dates=re.findall(r'<time datetime="([^\"]+)">([^<]+)</time>',byline)
   assert (article['datePublished'],article['datePublished']) in dates,url
   assert (article['dateModified'],article['dateModified']) in dates,url
   assert article['datePublished']<=article['dateModified'],url
for name in ['20261005.html','20261005-en.html']:
 source=(Path('site/news')/name).read_text()
 article=next(json.loads(s) for s in re.findall(r'<script type="application/ld\\+json">(.*?)</script>',source,re.S) if json.loads(s).get('@type')=='Article')
 assert article['datePublished']=='2026-10-05',name
 assert '<time datetime="2026-10-05">2026-10-05</time>' in source,name
`], {cwd:path.resolve(__dirname, '..'), stdio:'pipe'});
});
