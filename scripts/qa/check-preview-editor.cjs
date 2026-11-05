// Run with a retained public Urachil HTML file. SIMY_DOM_PACKAGE may point to a separately installed linkedom.
const {DOMParser}=require(process.env.SIMY_DOM_PACKAGE||'linkedom');const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const ctx={DOMParser,NodeFilter:{SHOW_TEXT:4}};vm.createContext(ctx);vm.runInContext(fs.readFileSync('site/preview-edit.js','utf8'),ctx);const api=ctx.SimyPreviewEdit;
const html=api.index(api.prepare(fs.readFileSync(process.argv[2],'utf8')));const nodes=api.inventory(html);console.log(nodes.filter(n=>n.kind==='news').map(n=>({id:n.id,context:n.context})));
const general=nodes.find(n=>n.kind==='news'&&n.context==='お知らせ');assert(general);const empty={oldText:'',newText:'',title:'',body:'',date:'',property:'',value:''};
const changed=api.applyPlan(html,{status:'edit',summary:'お知らせに追加',operations:[{...empty,type:'insert_notice',target:general.id,title:'10月31日 午後休診のお知らせ',body:'10月31日は午後休診です。',date:'2026-10-30'}]});
const d=new DOMParser().parseFromString(changed.html,'text/html');assert.equal(d.querySelector('.notice_box dl dt').textContent,'2026.10.30　10月31日 午後休診のお知らせ');assert(!d.querySelector('#simy-preview-notice'));assert.equal(d.querySelectorAll('[data-simy-changed]').length,2);
const n2=api.inventory(changed.html).find(n=>n.kind==='text'&&n.text==='10月31日は午後休診です。');assert(n2,'new text must be editable');
const again=api.applyPlan(changed.html,{status:'edit',summary:'訂正',operations:[{...empty,type:'replace_text',target:n2.id,oldText:n2.text,newText:'10月31日は終日休診です。'}]});assert(again.html.includes('10月31日は終日休診です。'));
assert.throws(()=>api.applyPlan(html,{status:'edit',operations:[{...empty,type:'insert_notice',target:'e999999',title:'x',body:'x',date:'2026-10-30'}]}));
console.log('DOM acceptance passed: category, no banner, highlight, second edit, invalid target');
const photo=nodes.find(n=>n.kind==='image');assert(photo);const asset={id:'a0',data:'data:image/png;base64,iVBORw0KGgo='};
const swapped=api.applyPlan(html,{status:'edit',summary:'写真',operations:[{...empty,type:'replace_image',target:photo.id,value:'a0'}]},[asset]);assert(swapped.html.includes(asset.data));assert.throws(()=>api.applyPlan(html,{status:'edit',operations:[{...empty,type:'replace_image',target:photo.id,value:'a0'}]},[]));
const redesign=api.applyPlan(html,{status:'edit',summary:'全面変更',operations:[{...empty,type:'redesign',target:'e0',property:'warm',value:'#146854'}]});
const originalDoc=new DOMParser().parseFromString(html,'text/html'),newDoc=new DOMParser().parseFromString(redesign.html,'text/html');assert.equal(newDoc.body.textContent,originalDoc.body.textContent);assert.equal(newDoc.querySelectorAll('img').length,originalDoc.querySelectorAll('img').length);assert.equal(newDoc.querySelectorAll('link[rel="stylesheet"]').length,0);
fs.writeFileSync('/tmp/urachil-redesigned.html',redesign.html);fs.writeFileSync('/tmp/simy-broad-inventory.json',JSON.stringify({request:'',today:'2026-10-30',nodes,history:[]}));console.log('Broad DOM acceptance passed: photo binding, missing asset, redesign preserves text and images');
