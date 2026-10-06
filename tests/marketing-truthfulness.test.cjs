const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');
const root = path.join(__dirname, '..');
const read = p => fs.readFileSync(path.join(root, p), 'utf8');

test('SEO-01 / AC-8: security fallback and every runtime locale preserve website-only transport scope', () => {
  execFileSync('python3', ['scripts/build-i18n-bundle.py', '--check'], { cwd: root });
  const context = { window: {} };
  vm.runInNewContext(read('site/lang/i18n-bundle.js'), context);
  const bundle = context.window.SIMY_I18N_BUNDLE;
  for (const file of fs.readdirSync(path.join(root, 'site/lang')).filter(f => f.endsWith('.json'))) {
    const source = JSON.parse(read('site/lang/' + file));
    assert.equal(bundle[file.slice(0, -5)]['sec.transitP'], source['sec.transitP']);
    assert.match(source['sec.transitP'], /HTTPS/);
    assert.doesNotMatch(source['sec.transitP'], /TLS\s*1\.3/);
  }
  assert.ok(read('site/security.html').includes(bundle.en['sec.transitP']));
});

test('UX-04/05 / AC-4/5: six download FAQs agree with visible trial wording and warning recovery links', () => {
  const prohibited = /Run anyway|詳細情報.*→.*実行|Ejecutar de todas formas|Exécuter quand même|仍要运行/;
  for (const file of ['site/download.html', ...['en', 'es', 'fr', 'hi', 'zh-hans'].map(l => `site/download/${l}.html`)]) {
    const html = read(file);
    assert.doesNotMatch(html, prohibited, file);
    const scripts = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)];
    const graphs = scripts.flatMap(m => { const j = JSON.parse(m[1]); return j['@graph'] || [j]; });
    const answer = graphs.find(j => j['@type'] === 'FAQPage').mainEntity[0].acceptedAnswer.text;
    assert.ok(html.includes(`<p>${answer}</p>`), file + ' structured FAQ differs');
    assert.doesNotMatch(answer, /^There is no free plan|^無料プランはありません/);
    const win = html.match(/data-install="win"([\s\S]*?)<\/ol>/)[1];
    assert.match(win, /https:\/\/app\.simy\.one\/login\?lang=/, file + ' no actionable recovery');
    const expectedLocale = file === 'site/download.html' ? 'ja' : path.basename(file, '.html').replace('zh-hans', 'zh-Hans');
    const recovery = new URL(win.match(/href="(https:\/\/app\.simy\.one\/login[^"]*)"/)[1].replaceAll('&amp;', '&'));
    assert.equal(recovery.searchParams.get('lang'), expectedLocale, file + ' recovery language');
    if (expectedLocale === 'zh-Hans') assert.equal(recovery.searchParams.get('locale'), expectedLocale);
  }
});

test('UX-02/03 / AC-2/3: synthetic note produces draft, internal checks and next actions without claiming execution', () => {
  const sales = JSON.parse(read('scripts/content-pages.json')).pages.find(p => p.id === 'sales');
  const ja = sales.ja.sections.find(s => s.id === 'output').p.join('\n');
  const en = sales.en.sections.find(s => s.id === 'output').p.join('\n');
  for (const part of ['件名：', 'ご担当者様', '差出人名', '社内の確認事項', '次の行動', '実行結果ではありません']) assert.ok(ja.includes(part));
  for (const part of ['Subject:', 'Dear Example Company', 'Sender name', 'Internal checks:', 'Next actions:', 'not an observed SIMY task result']) assert.ok(en.includes(part));
  assert.match(en, /Nothing has been sent or attached/);
  assert.match(ja, /送信や添付はまだ行っていない/);
});

test('SEO-01 / AC-8: frozen forty pairs and three additional historical markets retain pending research', () => {
  execFileSync('python3', ['-c', `
import csv
from pathlib import Path
root = Path('docs/systems/marketing-site')
rows = list(csv.DictReader((root/'market-route-ledger.csv').open()))
assert len(rows) == 40
assert len({(r['route'],r['market']) for r in rows}) == 40
assert {r['market'] for r in rows} == {'Japan','United States','United Kingdom','India','Singapore'}
for market in {r['market'] for r in rows}:
    assert len([r for r in rows if r['market'] == market]) == 8
assert all(r['page_specific_status'] == 'Ahrefs credit-limit pending' for r in rows)
extra = list(csv.DictReader((root/'existing-market-ledger.csv').open()))
assert {(r['market'],r['intent']) for r in extra} == {(m,i) for m in ['Spain','Mexico','France'] for i in ['home','guide hub','download']}
assert all(r['page_specific_status'] == 'Ahrefs credit-limit pending' for r in extra)
assert all((Path('site')/r['existing_route'].lstrip('/')).is_file() for r in extra)
`], { cwd: root });
});

test('SEO-01 / AC-8: unsubstantiated security promises cannot return through locale sources or SEO metadata', () => {
  const html = read('site/security.html');
  const prohibited = /AES-256|AWS\/GCP|RBAC|SAML|HIPAA|SOC\s?2|GDPR|CCPA|24 hours|72 hours/;
  assert.doesNotMatch(html, prohibited);
  assert.match(html, /href="mailto:security@simy\.one"[^>]*>security@simy\.one<\/a>/);
  for (const policy of ['privacy', 'terms']) {
    assert.match(html, new RegExp(`href="/${policy}\\.html" data-i18n="footer\\.legal\\.${policy}"`));
  }
  const code = read('site/i18n.js');
  const start = code.indexOf('  var SEO = {');
  const end = code.indexOf('\n  function pageKey()', start);
  const context = {};
  vm.runInNewContext(code.slice(start, end), context);
  for (const file of fs.readdirSync(path.join(root, 'site/lang')).filter(f => f.endsWith('.json'))) {
    const dict = JSON.parse(read('site/lang/' + file));
    const retired = Object.keys(dict).filter(k => /^sec\.(rest|cloud|access|data|dt|comp|heroP|reportP)/.test(k));
    assert.deepEqual(retired, [], file + ' unsupported security claims');
    const meta = context.SEO[file.slice(0, -5)].p.security;
    assert.doesNotMatch(meta.t + meta.d, prohibited, file + ' security metadata');
    assert.equal(meta.d, dict['sec.transitP'], file + ' metadata scope');
    if (dict['home.faq.a4']) assert.equal(dict['home.faq.a4'], dict['sec.transitP'], file + ' FAQ scope');
  }
});

test('SEO-01 / AC-8: legacy home assets and their translations omit unsupported isolation and encryption promises', () => {
  const retired = /Enterprise-grade trust\.|By design\.|Physical DB Isolation|End-to-End Encrypted|Zero Training Guarantee|Your data\. Your instance\. No shared tenants\.|Channel-Based Access|Only participants of the original thread can access\.|Every organisation gets a dedicated, isolated database instance\.|Enterprise data never trains global models\./;
  const scoped = JSON.parse(read('site/lang/en.json'))['sec.transitP'];
  for (const asset of [
    'site/assets/index-DnVveaIK.js',
    'site/assets/index-DnVveaIK.js.bak',
    'site/old/assets/index-DnVveaIK.js',
    'site/old/assets/index-DnVveaIK.js.bak',
    'site/lang/home-dom-bundle.js',
  ]) assert.doesNotMatch(read(asset), retired, asset);
  for (const folder of ['site/lang/home-dom', 'site/old/lang/home-dom']) {
    for (const file of fs.readdirSync(path.join(root, folder)).filter(f => f.endsWith('.json'))) {
      const text = read(`${folder}/${file}`);
      assert.doesNotMatch(text, retired, `${folder}/${file}`);
      const locale = file.slice(0, -5);
      const dict = JSON.parse(text);
      const source = JSON.parse(read(`site/lang/${file}`));
      assert.equal(dict['Security at SIMY'], source['sec.h1'], `${folder}/${file} security heading`);
      assert.equal(dict[scoped], source['sec.transitP'], `${folder}/${file} scoped copy`);
    }
  }
  const current = Object.fromEntries(fs.readdirSync(path.join(root, 'site/lang/home-dom')).filter(f => f.endsWith('.json')).sort().map(f => [f.slice(0, -5), JSON.parse(read(`site/lang/home-dom/${f}`))]));
  assert.equal(read('site/lang/home-dom-bundle.js'), `window.SIMY_HOME_DOM_BUNDLE = ${JSON.stringify(current, null, 2)};\n`);
});


test('UX-02/03/07: first-task reference keeps unknowns and separates illustration from product evidence', () => {
  const page = JSON.parse(read('scripts/content-pages.json')).pages.find(p => p.id === 'simy-getting-started');
  for (const lang of ['ja', 'en']) {
    const scene = page[lang].sections.find(s => s.id === 'scene');
    const rendered = read('site' + page.paths[lang]);
    for (const text of [scene.p[0], scene.example, ...scene.pAfter]) assert.ok(rendered.includes(text), lang);
    assert.match(scene.example, lang === 'ja' ? /担当者や期限.*不明.*外部には送らず/ : /owner or date.*unknown.*Do not send/);
    assert.match(scene.pAfter.join(' '), lang === 'ja' ? /金額や日付を補わない/ : /do not add a price or date/);
    assert.match(scene.pAfter.join(' '), lang === 'ja' ? /SIMYでの実行結果ではありません/ : /not an observed SIMY task result/);
  }
});
