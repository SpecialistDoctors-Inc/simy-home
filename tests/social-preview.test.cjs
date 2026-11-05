const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
const root=path.resolve(__dirname,'..');const cards=require('../scripts/social-preview-pages.json');
const decode=s=>s.replace(/&quot;/g,'"').replace(/&#x27;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
const files=dir=>fs.readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?files(path.join(dir,e.name)):[path.join(dir,e.name)]);
test('every public indexable page has an intentional, content-specific sharing card',()=>{
 const pages=new Set(cards.map(c=>c.page));assert.equal(pages.size,cards.length);
 for(const f of files(path.join(root,'site')).filter(f=>f.endsWith('.html'))){const s=fs.readFileSync(f,'utf8');if(/<meta[^>]+name=["']robots["'][^>]+content=["'][^"']*noindex/i.test(s)||!/<meta[^>]+name=["']robots["']/i.test(s))continue;
 const p=path.relative(path.join(root,'site'),f);assert.ok(pages.has(p)||p.includes('pharmaceutical-companies/'),`Missing card: ${p}`);
 }
});
for(const c of cards)test(`sharing card: ${c.page}`,()=>{
 const s=fs.readFileSync(path.join(root,'site',c.page),'utf8');const metas=[...s.matchAll(/<meta\b[^>]*>/g)].map(m=>m[0]);
 const value=key=>{const matches=metas.filter(t=>t.includes(`="${key}"`));assert.equal(matches.length,1,`exactly one ${key}`);return decode(matches[0].match(/content="([^"]*)"/)[1])};
 assert.equal(value('og:image'),'https://simy.one'+c.image);assert.equal(value('twitter:image'),value('og:image'));assert.equal(value('og:image:alt'),c.alt);assert.equal(value('twitter:image:alt'),c.alt);assert.equal(value('og:image:width'),'1200');assert.equal(value('og:image:height'),'630');assert.equal(value('og:image:type'),'image/png');assert.equal(value('twitter:card'),'summary_large_image');
 assert.match(s,new RegExp(`<html[^>]+lang="${c.lang}"`));assert.ok(c.headline.length>4);
 const b=fs.readFileSync(path.join(root,'site',c.image));assert.deepEqual([...b.subarray(0,8)],[137,80,78,71,13,10,26,10]);assert.equal(b.readUInt32BE(16),1200);assert.equal(b.readUInt32BE(20),630);
});
