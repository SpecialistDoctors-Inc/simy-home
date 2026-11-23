#!/usr/bin/env python3
"""Check declared FAQ pairs against visible details; inventory Article metadata.

This establishes text correspondence, not factual truth or search eligibility.
"""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
class Content(HTMLParser):
    def __init__(self,source):
        super().__init__();self.hidden=0;self.text=[];self.stack=[];self.pairs=[];self.times=[];self.feed(source)
    def handle_starttag(self,t,a):
        if t in ('script','style'):self.hidden+=1
        if t=='time':self.times.append(dict(a).get('datetime'))
        if t=='details':self.stack.append({'q':[],'a':[],'summary':False})
        if t=='summary' and self.stack:self.stack[-1]['summary']=True
    def handle_endtag(self,t):
        if t in ('script','style'):self.hidden=max(0,self.hidden-1)
        if t=='summary' and self.stack:self.stack[-1]['summary']=False
        if t=='details' and self.stack:self.pairs.append(self.stack.pop())
    def handle_data(self,s):
        if not self.hidden:
            self.text.append(s)
            for d in self.stack:d['q' if d['summary'] else 'a'].append(s)

def norm(s):return re.sub(r'\s+','',s)
def text(s):return norm(' '.join(Content(s).text))

def audit():
    inventory=json.loads((ROOT/'docs/seo/sitewide-page-inventory.json').read_text());results=[];faq=[];errors=[]
    for name,item in inventory.items():
        if item['policy']!='index':continue
        source=(ROOT/'site'/name).read_text();p=Content(source);visible=norm(' '.join(p.text));schemas=[]
        for blob in re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',source,re.S):
            o=json.loads(blob);schemas+=o.get('@graph',[o]) if isinstance(o,dict) else o
        pairs=[(norm(' '.join(d['q'])),norm(' '.join(d['a']))) for d in p.pairs]
        for obj in schemas:
            typ=obj.get('@type')
            if typ=='FAQPage':
                for q in obj.get('mainEntity',[]):
                    question=q.get('name','');answer=q.get('acceptedAnswer',{}).get('text','')
                    matching=[a for name,a in pairs if name==text(question)]
                    ok=any(text(answer) in a for a in matching)
                    faq.append({'file':name,'question':question,'answer':answer,'matchingVisiblePair':ok})
                    if not ok:errors.append(name+': FAQ pair is not represented by its visible question and answer: '+question)
                    for field,value in [('question',question),('answer',answer)]:
                        results.append({'file':name,'type':typ,'field':field,'text':value,'visibleTextContains':text(value) in visible})
            if typ in ('Article','NewsArticle','BlogPosting'):
                for field in ['author','datePublished','dateModified']:
                    value=obj.get(field)
                    results.append({'file':name,'type':typ,'field':field,'value':value,'present':bool(value),'matchingTimeElement':value in p.times if isinstance(value,str) else None})
    return {'scope':'All indexable HTML. FAQ questions must match a visible details/summary and the accepted answer must occur in that same answer body. This is text correspondence, not factual accuracy, complete editorial review or rich-result eligibility. Article metadata presence and time-element agreement are reported separately; dateModified is optional and is not invented.',
            'indexPages':sum(v['policy']=='index' for v in inventory.values()),'faqPairs':faq,'errors':errors,'results':results}

if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--check',action='store_true');args=cli.parse_args()
    data=audit();expected=json.dumps(data,ensure_ascii=False,indent=2)+'\n';output=ROOT/'docs/sitewide-quality/evidence/schema-inventory.json'
    if data['errors']:raise SystemExit('\n'.join(data['errors']))
    if args.check:
        if not output.exists() or output.read_text()!=expected:raise SystemExit('Schema evidence is stale; run python3 scripts/check-schema-visible-content.py')
    else:output.write_text(expected)
    print(f"PASS: {data['indexPages']} indexable pages, {len(data['faqPairs'])} FAQ pairs, {len(data['results'])} field observations")
