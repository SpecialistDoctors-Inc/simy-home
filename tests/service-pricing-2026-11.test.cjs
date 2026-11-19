const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const map=require('../scripts/service-pricing-2026-11-map.json');
const copy=require('../scripts/service-pricing-2026-11-copy.json');
const baseline=require('./fixtures/service-pricing-2026-11-baseline.json');
function read(p){return fs.readFileSync(path.join(root,p),'utf8');}
function own(html){return html.match(/<!-- service-pricing-2026-11:start -->([\s\S]*?)<!-- service-pricing-2026-11:end -->/)[1];}
function current(html){return html.replace(/<!-- service-pricing-2026-11:start -->[\s\S]*?<!-- service-pricing-2026-11:end -->/g,'').replace(/<!-- service-pricing-2026-11:notice -->[\s\S]*?<!-- \/service-pricing-2026-11:notice -->/g,'');}
function links(html){return [...html.matchAll(/<a\b[^>]*\bhref="([^"]*)"/g)].map(x=>x[1].replaceAll('&amp;','&'));}
test('all 24 canonical service pages are mapped by function and reproducibly generated',()=>{
 assert.equal(map.routes.length,24);assert.equal(new Set(map.routes.map(x=>x.path)).size,24);
 const result=spawnSync('python3',['scripts/build-service-pricing-pages.py','--check'],{cwd:root,encoding:'utf8'});
 assert.equal(result.status,0,result.stdout+result.stderr);
 for(const route of map.routes){
  const html=read('site/'+route.path),section=own(html),c=copy[route.locale],profile=map.profiles[route.profile];
  assert.equal(html.split('<!-- service-pricing-2026-11:start -->').length,2,route.path);
  assert.ok(section.includes(c.status),route.path);assert.ok(section.includes(c.allowance),route.path);
  assert.ok(section.includes(c.beforeTax),route.path);assert.ok(section.includes(c.transcriptionSla),route.path);
  assert.doesNotMatch(section,/<form\b|<button\b|href="[^\"]*(?:signup|checkout|buy)|drawing_quote|storage_100gb|storage_1tb/);
  assert.deepEqual([...section.matchAll(/data-sku="([^"]*)"/g)].map(x=>x[1]),[...profile.primary,...profile.optional,...profile.usage],route.path);
  const old=baseline.actions['site/'+route.path];let now=links(current(html));
  for(const form of current(html).matchAll(/<form\b([^>]*)>/g)){const a=form[1].match(/action="([^"]*)"/),m=form[1].match(/method="([^"]*)"/);now.push('FORM:'+(a?.[1]||'')+':'+(m?.[1]||'get'));}
  if(route.existingContact)now.push(route.existingContact.href);
  const expected = route.locale === 'ja' && route.path.startsWith('for/')
    ? [...old, '/for/rosenz/'].sort()
    : old;
  assert.deepEqual(now.sort(),expected,route.path+' existing links and common Japanese work navigation');
 }
});
test('prices and Base-inclusive arithmetic follow the approved specification in both currencies',()=>{
 const script=`from service_pricing_2026_11 import ROWS,MAP,COPY,price_cell,examples,render,apply,SITE\nfor route in MAP['routes']:\n c=COPY[route['locale']];p=MAP['profiles'][route['profile']];html=render(route)\n for code in p['primary']+p['optional']+p['usage']:\n  for cur in ['jpy','usd']:\n   assert price_cell(code,cur,False,c) in html\n   if code in p['primary']+p['optional']:assert price_cell(code,cur,True,c) in html\n source=(SITE/route['path']).read_text();assert apply(source,SITE/route['path'])==source\nassert ROWS['base']['jpy']==2280 and ROWS['base']['jpy_annual']==22800\nassert ROWS['sqm_check']['jpy']==3780 and ROWS['sqm_check']['jpy_annual']==38160\nassert ROWS['base']['usd']==1500 and ROWS['base']['usd_annual']==15000\nassert ROWS['land_valuation']['jpy']==14800 and ROWS['land_valuation']['usd']==9900\n`;
 const result=spawnSync('python3',['-c',script],{cwd:path.join(root,'scripts'),encoding:'utf8'});assert.equal(result.status,0,result.stderr);
 const dev=own(read('site/for/engineers/index.html')),rosenz=own(read('site/for/rosenz/index.html'));
 assert.ok(dev.includes('¥6,060'));assert.ok(dev.includes('¥60,960'));assert.ok(dev.includes('$40'));assert.ok(dev.includes('$402'));
 assert.ok(rosenz.includes('¥17,080'));assert.ok(rosenz.includes('$114'));assert.ok(rosenz.includes('60件/月・同時利用1人'));
 assert.ok(rosenz.includes('mailto:sales@simy.one'));
});
test('the general and service rate tables use the same CSS and group prices by currency',()=>{
 const overview=read('site/pricing-2026-11.html');
 const asset=overview.match(/href="(\/pricing-rate-tables\.css\?v=[a-f0-9]+)"/)[1];
 assert.match(overview, /class="pricing-rate-table"/);
 for (const route of map.routes) {
  const page=read('site/'+route.path);
  if (route.path!=='hp-management/law-firm.html') assert.ok(page.includes(asset),route.path);
  const tables=[...own(page).matchAll(/<table\b[^>]*>([\s\S]*?)<\/table>/g)];
  for (const [markup,body] of tables) {
   const usage=markup.includes('class="sp26-table sp26-usage"');
   assert.equal([...body.matchAll(/scope="col"/g)].length,usage?4:5,route.path);
   for (const [,row] of body.matchAll(/<tr role="row" data-sku="[^"]+">([\s\S]*?)<\/tr>/g)) {
    assert.equal([...row.matchAll(/class="rate-currency"/g)].length,2,route.path);
    assert.equal([...row.matchAll(/class="rate-annual"/g)].length,usage?0:2,route.path);
   }
  }
 }
 const rosenz=own(read('site/for/rosenz/index.html'));
 assert.ok(rosenz.indexOf('data-example="base,land_valuation"') < rosenz.indexOf('data-sku="base"'));
});
test('existing checkout assets stay byte-identical and the law-firm CSS is packaged',()=>{
 for(const [file,expected] of Object.entries(baseline.immutableSha256))assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex'),expected,file);
 assert.equal(read('site/hp-management/law-firm/pricing-rate-tables.css'),read('site/pricing-rate-tables.css'));
 const result=spawnSync('python3',['scripts/check-law-firm-release.py'],{cwd:root,encoding:'utf8'});assert.equal(result.status,0,result.stdout+result.stderr);
});
