const test = require('node:test');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const audit = JSON.parse(execFileSync('python3', ['-c', `
import sys,json
from pathlib import Path
sys.path.insert(0,'scripts')
from page_accessibility import Elements,classification,apply
site=Path('site').resolve()
result=[]
for path in sorted(site.rglob('*.html')):
 source=path.read_text(); parser=Elements(source); parser.feed(source)
 tags=parser.tags
 result.append({'path':path.relative_to(site).as_posix(),'kind':classification(source,path.relative_to(site).as_posix()),
 'mains':[a for t,a,_,_ in tags if t=='main' or a.get('role')=='main'],
 'skips':[a for t,a,_,_ in tags if t=='a' and any('skip' in c for c in a.get('class','').split())],
 'ids':[a['id'] for t,a,_,_ in tags if 'id' in a],
 'skipBeforeHeader':next((pos for t,a,pos,_ in tags if t=='a' and 'skip' in a.get('class','')),10**9)<next((pos for t,a,pos,_ in tags if t=='header'),10**9),
 'stable':apply(source,path,site)==source,
 'css':'page-accessibility.css?v=' in source})
print(json.dumps(result))
`], {cwd:root, encoding:'utf8'}));

test('all deployed HTML is classified, and public documents expose a focusable main through a bypass link', () => {
  assert.equal(audit.length, 199, 'Update the reviewed page inventory when adding pages');
  const kinds = {};
  for (const page of audit) {
    kinds[page.kind] = (kinds[page.kind] || 0) + 1;
    if (page.kind !== 'public-document') continue;
    assert.equal(page.mains.length, 1, `${page.path}: exactly one main`);
    const main = page.mains[0];
    assert.ok(main.id, `${page.path}: main has an existing or generated ID`);
    assert.equal(page.ids.filter(id => id === main.id).length, 1, `${page.path}: unique main target`);
    assert.equal(main.tabindex, '-1', `${page.path}: bypass destination accepts focus`);
    assert.ok(page.skips.some(a => a.href === '#' + main.id), `${page.path}: bypass targets main`);
    assert.ok(page.css, `${page.path}: shared focus/scroll treatment`);
    assert.ok(page.skipBeforeHeader, `${page.path}: bypass precedes navigation in keyboard order`);
    assert.ok(page.stable, `${page.path}: applying accessibility generation twice is stable`);
  }
  assert.deepEqual(kinds, {'public-document':185, 'authentication-return':1, 'verification':1, 'redirect':12});
});

test('service navigation and existing bypass IDs are preserved; archived contact has usable static content', () => {
  for (const file of ['hp-management/clinic/index.html', 'hp-management/law-firm.html']) {
    const page = audit.find(p => p.path === file);
    assert.equal(page.mains[0].id, 'main');
    assert.equal(page.skips[0].href, '#main');
  }
  assert.equal(audit.find(p => p.path === 'old/contact.html').kind, 'public-document');
  assert.equal(audit.find(p => p.path === 'old/contact.html').mains.length, 1);
  const source = require('node:fs').readFileSync(path.join(root, 'site/old/contact.html'), 'utf8');
  assert.match(source, /mailto:sales@simy.one/);
  assert.doesNotMatch(source, /<script type="module"[^>]+index-/);
  assert.match(source, /<meta name="robots" content="noindex/);
});

// A narrowly shared, same-origin stylesheet preserves the guide performance contract.
test('shared accessibility CSS stays below 2 KiB and has no remote dependencies', () => {
  const fs = require('node:fs');
  const css = fs.readFileSync(path.join(root, 'site/page-accessibility.css'), 'utf8');
  assert.ok(Buffer.byteLength(css) < 2048);
  assert.doesNotMatch(css, /@import|url\s*\(/i);
  assert.doesNotMatch(css, /!important/);
  assert.equal(fs.readFileSync(path.join(root, 'site/hp-management/law-firm/page-accessibility.css'), 'utf8'), css);
});
