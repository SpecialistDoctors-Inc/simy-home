const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {execFileSync}=require('node:child_process');

function headerModel(page){
 return JSON.parse(execFileSync('python3',['-c',`
import json,sys
from pathlib import Path
from html.parser import HTMLParser
class Header(HTMLParser):
 def __init__(self):super().__init__();self.inside=False;self.stack=[];self.links=[]
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if tag=='header' and attrs.get('class')=='simy-header':self.inside=True
  if not self.inside:return
  if tag=='a':self.links.append({'attrs':attrs,'navigation':any('sh-navigation' in c for _,c in self.stack)})
  if tag not in ['img','input','br','link','meta','path','circle','ellipse']:self.stack.append((tag,attrs.get('class','').split()))
 def handle_endtag(self,tag):
  if not self.inside:return
  if self.stack and self.stack[-1][0]==tag:self.stack.pop()
  if tag=='header':self.inside=False
p=Header();p.feed((Path('site')/sys.argv[1]).read_text());print(json.dumps(p.links))
`,page],{encoding:'utf8'}));
}

function runHeader(page){
 const origin='https://simy.one', location={origin,href:origin+'/'+page.replace(/index\.html$/,'')};
 const element=attrs=>({attrs:{...attrs},get href(){return new URL(this.attrs.href,location.href).href;},set href(value){this.attrs.href=value;},get lang(){return this.attrs.lang;},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this.attrs[k];},hasAttribute(k){return k in this.attrs;},addEventListener(){}});
 const links=headerModel(page).map(row=>({...row,element:element(row.attrs)}));
 const byClass=name=>links.find(row=>(row.attrs.class||'').split(' ').includes(name))?.element;
 const menu={open:false,addEventListener(){}};
 const summary={lastChild:{textContent:''},setAttribute(){}};
 const header={dataset:{},addEventListener(){},getBoundingClientRect:()=>({height:76}),querySelector(selector){return {'.sh-menu':menu,'.sh-language summary':summary,'.sh-google-play':byClass('sh-google-play'),'.sh-brand':byClass('sh-brand'),'.sh-pricing':byClass('sh-pricing')}[selector];},querySelectorAll(selector){if(selector==='.sh-language a')return links.filter(row=>row.attrs.lang).map(row=>row.element);if(selector==='.sh-navigation a:not(.sh-store)')return links.filter(row=>row.navigation&&!(row.attrs.class||'').split(' ').includes('sh-store')).map(row=>row.element);return [];}};
 const document={documentElement:{lang:'ja',style:{setProperty(){}}},querySelector:selector=>selector==='.simy-header'?header:null,addEventListener(){}};
 const context={document,location,URL,ResizeObserver:class{observe(){}},MutationObserver:class{observe(){}},window:{matchMedia:()=>({matches:false,addEventListener(){}}),addEventListener(){}}};
 const source=fs.readFileSync('site/site-header.js','utf8');
 vm.runInNewContext(source,context);vm.runInNewContext(source,context);
 return links;
}

test('Japanese shared menus group HP industries separately and preserve existing product destinations',()=>{
 const catalog=JSON.parse(fs.readFileSync('scripts/hp-management-industries.json','utf8'));
 for(const page of ['ja.html','for/index.html','hp-management/index.html']){
  const html=fs.readFileSync('site/'+page,'utf8');
  assert.match(html,/sh-solutions-panel/);
  assert.ok(html.includes('SIMYの業務活用')&&html.includes('ホームページ管理'));
  const links=runHeader(page);
  for(const item of catalog.industries.filter(item=>item.status==='published'&&item.featured).slice(0,2))assert.ok(links.some(row=>new URL(row.element.href).pathname===item.url),page+': '+item.url);
  for(const pathname of ['/hp-management/','/for/engineers/','/for/financial-planners/','/for/pharmaceutical-companies/'])assert.ok(links.some(row=>new URL(row.element.href).pathname===pathname),page+': '+pathname);
 }
});

test('locale runtime retains the HP hub pricing and start journey while app pages keep app pricing',()=>{
 const links=runHeader('hp-management/index.html');
 const pricing=links.find(row=>row.attrs.class==='sh-pricing').element;
 assert.equal(new URL(pricing.href).pathname,'/hp-management/');assert.equal(new URL(pricing.href).hash,'#pricing');
 const start=links.find(row=>row.attrs.class==='sh-signup').element;
 assert.equal(new URL(start.href).pathname,'/hp-management/');assert.equal(new URL(start.href).hash,'#industries');
 const appPricing=runHeader('ja.html').find(row=>row.attrs.class==='sh-pricing').element;
 assert.equal(new URL(appPricing.href).pathname,'/ja.html');assert.equal(new URL(appPricing.href).hash,'#pricing');
});
