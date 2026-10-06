const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname, '..');
test('FP generated pages are current', () => {
 const result = spawnSync('python3', ['scripts/build-financial-planner-pages.py', '--check'], {cwd:root,encoding:'utf8'});
 assert.equal(result.status,0,result.stdout+result.stderr);
});
const locales=['ja','en','es','fr','hi','zh-Hans'];
const translations=JSON.parse(fs.readFileSync(path.join(root,'scripts/financial-planner-locales.json'),'utf8'));
for (const lang of locales) {
 const prefix=lang==='ja'?'':lang.toLowerCase()+'/';
 const copy=(ja,en)=>lang==='ja'?ja:lang==='en'?en:translations[lang][en];
 test(`${lang}: FP experience is linked and includes readable web and iOS examples`, () => {
  const file = fs.readFileSync(path.join(root,`site/for/${prefix}financial-planners/index.html`),'utf8');
  const home=fs.readFileSync(path.join(root,'site',lang==='en'?'index.html':lang+'.html'),'utf8');
  assert.ok(home.includes(`/for/${prefix}financial-planners/`));
  assert.ok(file.includes(`<html lang="${lang}"`));
  for (const code of locales) {
   const target=`/for/${code==='ja'?'':code.toLowerCase()+'/'}financial-planners/`;
   assert.ok(file.includes(`hreflang="${code}" href="https://simy.one${target}"`));
   assert.ok(file.includes(`href="${target}" lang="${code}"`));
  }
  if(lang!=='ja'&&lang!=='en') {
   assert.deepEqual(Object.keys(translations[lang]).sort(),Object.keys(translations.es).sort(),`${lang}: complete translation keys`);
   assert.doesNotMatch(file,/Your next steps\.|Practice your opening question out loud\.|PROPOSED NEXT ACTION \/ ADVISOR REVIEW NEEDED/);
   assert.ok(file.includes(translations[lang]['My wife and I decide together, but she isn’t comfortable yet.']));
   assert.ok(file.includes(translations[lang]['Evidence and a question to ask']));
   assert.doesNotMatch(file,/[\u3040-\u30ff]/);
  }
  for (const id of ['meeting','red-flags','roleplay','knowledge']) assert.ok(file.includes(`id="${id}"`));
  assert.equal((file.match(/data-panel=/g)||[]).length,6);
  assert.equal((file.match(/data-controls hidden/g)||[]).length,2);
  for (const [key, state] of [['budget','red'],['decision','red'],['timing','amber'],['engagement','amber'],['next-step','amber'],['need','green']]) {
   assert.ok(file.includes(`data-risk="${key}" data-state="${state}"`), `${key} has the appropriate evidence status`);
  }
  assert.equal((file.match(/class="risk-evidence"/g)||[]).length,6);
  assert.ok(file.includes('trailhead.salesforce.com'));
  assert.ok(file.includes(copy('どちらも失注の断定ではありません','Red flag: a concern expressed by the client. To confirm: missing or outdated information. Neither means the opportunity is lost.')));
  assert.ok(file.includes(copy('担当FPの確認待ち','PROPOSED NEXT ACTION / ADVISOR REVIEW NEEDED')));
  assert.ok(file.includes('https://apps.apple.com/app/id6745385262'));
  assert.ok(file.includes(copy('未送信・要確認','Not sent · Review needed')));
  assert.ok(file.includes(copy('録音・音声送信は行いません','Illustrative iOS screens. Switch views to explore the example.<br>This page does not record or transmit audio.')));
  assert.ok(fs.existsSync(path.join(root,`site/assets/fp-experience/social-${lang}.png`)));
 });
}
test('the illustrative demos do not access audio or external services', () => {
 const script=fs.readFileSync(path.join(root,'site/financial-planners.js'),'utf8');
 assert.doesNotMatch(script,/getUserMedia|MediaRecorder|fetch\s*\(|XMLHttpRequest|WebSocket/);
});
