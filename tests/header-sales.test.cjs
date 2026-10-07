const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
test('every rendered shared header links to an existing sales page with honest fallback',()=>{
 for(const file of fs.readdirSync(path.join(root,'site'),{recursive:true}).filter(f=>f.endsWith('.html'))){
  const source=fs.readFileSync(path.join(root,'site',file),'utf8');
  const header=source.match(/<header class="simy-header"[\s\S]*?<\/header>/)?.[0];
  if(!header)continue;
  const locale=source.match(/<html[^>]*lang="([^"]+)"/)?.[1]||'en';
  const sales=header.match(/<a href="([^\"]*\/sales\/)">([\s\S]*?)<\/a>/);
  assert.ok(sales,file);assert.equal(sales[1],locale==='ja'?'/for/sales/':'/for/en/sales/',file);
  assert.equal(sales[2].replace(/<[^>]*>/g,''),locale==='ja'?'営業':(locale==='en'?'For sales':'For sales (English)'),file);
  assert.match(sales[2],/data-label-en="For sales" data-label-ja="(?:営業|&#21942;&#26989;)"/,file);
  assert.ok(fs.existsSync(path.join(root,'site',sales[1],'index.html')),file);
 }
});
test('repeated locale changes retain the sales destination instead of occupation index',()=>{
 const source=fs.readFileSync(path.join(root,'site/site-header.js'),'utf8');
 const body=source.slice(source.indexOf('    header.querySelectorAll(\'.sh-navigation a:not(.sh-store)\')'),source.indexOf('\n  };'));
 const label={textContent:''};const link={href:'https://simy.one/for/sales/',querySelector:()=>label};
 const header={querySelectorAll:()=>({forEach:fn=>fn(link)})};
 for(const locale of ['fr','ja','en','hi','zh-Hans','es','ja']){
  link.href=new URL(link.href,'https://simy.one').href;
  vm.runInNewContext(body,{header,locale,home:locale==='en'?'/':`/${locale}.html`,URL,location:{origin:'https://simy.one'}});
  assert.equal(link.href,locale==='ja'?'/for/sales/':'/for/en/sales/');
  assert.equal(label.textContent,locale==='ja'?'営業':(locale==='en'?'For sales':'For sales (English)'));
 }
});

test('raw Japanese and English headers provide understandable visible and accessible labels without JS',()=>{
 for(const [file,expected] of [['ja.html',['プロダクト','職業別','ガイド・情報','料金','ログイン','新規登録','メニュー','言語: 日本語','App Storeでダウンロード']],['index.html',['Product','Solutions','Resources','Pricing','Log in','Sign up','Navigation menu','Language: English','Download on the App Store']]]){
  const header=fs.readFileSync(path.join(root,'site',file),'utf8').match(/<header class="simy-header"[\s\S]*?<\/header>/)[0];
  for(const label of expected)assert.ok(header.includes(`>${label}</span>`)||header.includes(`aria-label="${label}"`),label);
 }
});
