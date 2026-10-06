const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
test('every rendered shared header links to an existing sales page with honest fallback',()=>{
 for(const file of fs.readdirSync(path.join(root,'site'),{recursive:true}).filter(f=>f.endsWith('.html'))){
  const source=fs.readFileSync(path.join(root,'site',file),'utf8');
  const header=source.match(/<header class="simy-header"[\s\S]*?<\/header>/)?.[0];
  if(!header)continue;
  const locale=source.match(/<html[^>]*lang="([^"]+)"/)?.[1]||'en';
  const sales=header.match(/<a href="([^\"]*\/sales\/)">([^<]+)<\/a>/);
  assert.ok(sales,file);assert.equal(sales[1],locale==='ja'?'/for/sales/':'/for/en/sales/',file);
  assert.equal(sales[2],['ja','en'].includes(locale)?'For sales':'For sales (English)',file);
  assert.ok(fs.existsSync(path.join(root,'site',sales[1],'index.html')),file);
 }
});
test('repeated locale changes retain the sales destination instead of occupation index',()=>{
 const source=fs.readFileSync(path.join(root,'site/site-header.js'),'utf8');
 const body=source.slice(source.indexOf('    header.querySelectorAll(\'.sh-navigation a:not(.sh-store)\')'),source.indexOf('\n  };'));
 const link={href:'https://simy.one/for/sales/'};
 const header={querySelectorAll:()=>({forEach:fn=>fn(link)})};
 for(const locale of ['fr','ja','en','hi','zh-Hans','es','ja']){
  link.href=new URL(link.href,'https://simy.one').href;
  vm.runInNewContext(body,{header,locale,home:locale==='en'?'/':`/${locale}.html`,URL,location:{origin:'https://simy.one'}});
  assert.equal(link.href,locale==='ja'?'/for/sales/':'/for/en/sales/');
  assert.equal(link.textContent,['ja','en'].includes(locale)?'For sales':'For sales (English)');
 }
});
