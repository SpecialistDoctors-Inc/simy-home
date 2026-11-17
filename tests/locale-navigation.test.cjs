const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('site/locale-navigation.js','utf8');
function boot({url='https://simy.one/',timezone='Asia/Tokyo',browserLanguages=['en-US'],country,values={},blocked=false,lang='en',links=[],scripts=[]}={}){
 const replacements=[],callbacks=[];
 const storage={getItem(k){if(blocked)throw Error('blocked');return values[k]??null;},setItem(k,v){if(blocked)throw Error('blocked');values[k]=v;}};
 const context={URL,Set,Object,String,Intl:{DateTimeFormat(){if(timezone===null)throw Error('unavailable');return {resolvedOptions:()=>({timeZone:timezone})};}},navigator:{languages:browserLanguages},document:{documentElement:{dataset:{viewerCountry:country},lang},readyState:'loading',addEventListener(n,f){if(n==='DOMContentLoaded')callbacks.push(f);},querySelectorAll(s){return s==='script[src]'?scripts:s==='a[href]'?links:links.filter(l=>l.dataset.localeOption);}},window:{location:{href:url,origin:new URL(url).origin,replace:u=>replacements.push(u)},localStorage:storage}};
 vm.runInNewContext(source,context);for(const f of callbacks)f();return {replacements,values,api:context.window.SIMY_LOCALE_NAVIGATION};
}
function link(locale,href){return {dataset:{localeOption:locale},href,events:{},addEventListener(n,f){this.events[n]=f;}};}
test('Japan OS country signal restores Japanese even with an English browser, retaining query and hash',()=>{
 const r=boot({url:'https://simy.one/?utm_source=a&tag=one&tag=two#pricing'});
 assert.deepEqual(r.replacements,['https://simy.one/ja.html?utm_source=a&tag=one&tag=two#pricing']);
 assert.deepEqual(boot({url:r.replacements[0],timezone:'Europe/Paris',values:{'simy-home-locale':'fr'},lang:'ja'}).replacements,[]);
});
test('known country, supported timezones and browser fallback choose available static languages',()=>{
 assert.equal(new URL(boot({country:'FR'}).replacements[0]).pathname,'/fr.html');
 for(const [timezone,locale] of [['Europe/Paris','fr'],['Europe/Madrid','es'],['Asia/Kolkata','hi'],['Asia/Shanghai','zh-Hans']])assert.equal(new URL(boot({timezone}).replacements[0]).pathname,'/'+locale+'.html');
 assert.equal(new URL(boot({timezone:'Unknown/Place',country:'DE',browserLanguages:['de-DE','ja-JP']}).replacements[0]).pathname,'/ja.html');
 assert.deepEqual(boot({timezone:'UTC',browserLanguages:['zh-TW']}).replacements,[]);
});
test('manual preferences and explicit language outrank geography; stale automatic values do not',()=>{
 for(const values of [{'simy-home-locale':'en'},{'simy-lang':'en','simy-lang-source':'manual'},{'simy-language':'en','simy-language-source':'manual'}])assert.deepEqual(boot({values}).replacements,[]);
 assert.equal(new URL(boot({values:{'simy-lang':'en'}}).replacements[0]).pathname,'/ja.html');
 assert.equal(new URL(boot({url:'https://simy.one/?locale=fr',values:{'simy-home-locale':'ja'}}).replacements[0]).pathname,'/fr.html');
 assert.deepEqual(boot({url:'https://simy.one/?locale=en',blocked:true}).replacements,[]);
 assert.deepEqual(boot({url:'https://simy.one/hp-management.html'}).replacements,[]);
 for(const locale of ['ja','fr','es','hi','zh-Hans'])assert.deepEqual(boot({url:'https://simy.one/'+locale+'.html',values:{'simy-home-locale':'en'}}).replacements,[]);
});
test('blocked storage and missing Intl still allow browser-language fallback without a loop',()=>{
 const r=boot({blocked:true,timezone:null,browserLanguages:['ja-JP']});assert.equal(r.replacements.length,1);assert.equal(new URL(r.replacements[0]).pathname,'/ja.html');
 assert.deepEqual(boot({blocked:true,timezone:null,browserLanguages:[]}).replacements,[]);
});
test('language links persist all supported manual keys and English remains explicit without storage',()=>{
 const english=link('en','https://simy.one/');const r=boot({url:'https://simy.one/ja.html',lang:'ja',links:[english]});assert.equal(english.href,'/?locale=en');english.events.click();
 for(const key of ['simy-home-locale','simy-lang','simy-language'])assert.equal(r.values[key],'en');
 assert.equal(r.values['simy-lang-source'],'manual');assert.equal(r.values['simy-language-source'],'manual');
 const e=link('en','https://simy.one/');boot({url:'https://simy.one/ja.html',lang:'ja',links:[e],blocked:true});e.events.click();assert.deepEqual(boot({url:'https://simy.one'+e.href,blocked:true}).replacements,[]);
});
test('English home actions retain explicit language when storage cannot persist it',()=>{
 const a=link(undefined,'https://simy.one/#pricing');boot({url:'https://simy.one/?locale=en',blocked:true,links:[a]});assert.equal(a.href,'/?locale=en#pricing');
});
test('Japanese HP logo change preserves all other bytes and release hashes',()=>{
 for(const [file,hash] of [['site/hp-management/clinic/index.html','eb70431ef8954765db62a9aa136308edda5998eb12e538ba6d46c640b9a50eb3'],['site/hp-management/law-firm.html','036c39fb6eb06737534d7e6c02b340308d425b969c2dcbbc041b1ef9f0bd559e']]){
  const text=fs.readFileSync(file,'utf8');const logo=text.match(/<a\b[^>]*aria-label="SIMY公式サイト"[^>]*>/)[0];assert.match(logo,/href="https:\/\/simy.one\/ja.html"/);assert.equal(require('node:crypto').createHash('sha256').update(text.replace(logo,logo.replace('/ja.html','/'))).digest('hex'),hash);
 }
});
test('legacy click decoration preserves English intent before the root entry policy runs',()=>{
 const legacy=fs.readFileSync('site/i18n.js','utf8');const start=legacy.indexOf('  function decorateSiteUrl('),end=legacy.indexOf('  function decorateAppLinks(',start);
 for(const current of ['en','ja']){
  const c={URL,location:{href:'https://simy.one/about.html?lang='+current,hostname:'simy.one'},CURRENT_LANG:current,document:{documentElement:{lang:current}},isLegalPath:()=>false,currentRegionForApp:()=> 'jp'};vm.runInNewContext(legacy.slice(start,end),c);
  const destination=c.decorateSiteUrl('/?locale=en&tag=one&tag=two#pricing');assert.equal(destination,'/?tag=one&tag=two&locale=en#pricing');
  assert.deepEqual(boot({url:'https://simy.one'+destination,blocked:true}).replacements,[]);
 }
});
test('legacy language picker updates the same manual preference and tolerates storage denial',()=>{
 const legacy=fs.readFileSync('site/i18n.js','utf8');const start=legacy.indexOf('  function setLang('),end=legacy.indexOf('  function installLangKeySync(',start);
 const values={'simy-home-locale':'en'};const loaded=[];
 const c={SUPPORTED:['en','ja'],DEFAULT:'en',safeLangForPage:x=>x,localStorage:{setItem(k,v){values[k]=v;}},load:lang=>loaded.push(lang),apply(){}};
 vm.runInNewContext(legacy.slice(start,end),c);c.setLang('ja',{skipRegionSync:true});assert.equal(values['simy-home-locale'],'ja');assert.equal(new URL(boot({values,timezone:'Europe/Paris'}).replacements[0]).pathname,'/ja.html');
 c.localStorage={setItem(){throw Error('blocked')}};assert.doesNotThrow(()=>c.setLang('en',{skipRegionSync:true}));assert.equal(loaded.at(-1),'en');
});
test('pages that translate after loading keep generic home links for the existing language decorator',()=>{
 const generic=link(undefined,'https://simy.one/#pricing');const english=link('en','https://simy.one/');
 boot({url:'https://simy.one/about.html',links:[generic,english],scripts:[{src:'https://simy.one/i18n.js?v=reviewed'}]});
 assert.equal(generic.href,'https://simy.one/#pricing');assert.equal(english.href,'/?locale=en');
 const legacy=fs.readFileSync('site/i18n.js','utf8');const start=legacy.indexOf('  function decorateSiteUrl('),end=legacy.indexOf('  function decorateAppLinks(',start);
 const c={URL,location:{href:'https://simy.one/about.html',hostname:'simy.one'},CURRENT_LANG:'ja',document:{documentElement:{lang:'ja'}},isLegalPath:()=>false,currentRegionForApp:()=> 'jp'};vm.runInNewContext(legacy.slice(start,end),c);assert.equal(c.decorateSiteUrl(generic.href),'/ja.html#pricing');
});
