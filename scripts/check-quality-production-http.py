#!/usr/bin/env python3
"""Read-only HTTP audit of the current production canonical URLs; no publishing."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
class Metadata(HTMLParser):
    def __init__(self,s):
        super().__init__();self.canonical='';self.title='';self.in_title=False;self.feed(s)
    def handle_starttag(self,t,a):
        d=dict(a)
        if t=='link' and d.get('rel')=='canonical':self.canonical=d.get('href','')
        if t=='title':self.in_title=True
    def handle_endtag(self,t):
        if t=='title':self.in_title=False
    def handle_data(self,s):
        if self.in_title:self.title+=s

def fetch(item):
    file,url=item
    result={'file':file,'requestedURL':url,'observedAt':datetime.now(timezone.utc).isoformat()}
    try:
        with urlopen(Request(url,headers={'User-Agent':'SIMY-public-quality-review/1.0 (read-only)'}),timeout=25) as r:
            data=r.read(2*1024*1024);p=Metadata(data.decode('utf-8',errors='replace'))
            result.update(status=r.status,finalURL=r.url,contentType=r.headers.get('Content-Type'),canonical=p.canonical,title=p.title,canonicalMatches=p.canonical==url)
    except HTTPError as e:result.update(status=e.code,error=str(e))
    except Exception as e:result.update(status=None,error=str(e))
    return result

if __name__=='__main__':
    inventory=json.loads((ROOT/'docs/seo/sitewide-page-inventory.json').read_text())
    jobs=[]
    for file,item in inventory.items():
        if item['policy']=='index':jobs.append((file,Metadata((ROOT/'site'/file).read_text()).canonical))
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(fetch,jobs))
    output={'scope':'Current production only. HTTP success does not establish that local changes are deployed. No external form submission or authentication.', 'results':results}
    p=ROOT/'docs/sitewide-quality/evidence/production-http.json';p.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'urls':len(results),'http200':sum(r.get('status')==200 for r in results),'canonicalMatches':sum(r.get('canonicalMatches',False) for r in results)},ensure_ascii=False))
