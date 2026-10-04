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
