const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');
const root = path.join(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'site/i18n.js'), 'utf8');
const dictionaries = Object.fromEntries(fs.readdirSync(path.join(root, 'site/lang/home-dom'))
  .filter(f => f.endsWith('.json')).map(f => [f.slice(0, -5), JSON.parse(fs.readFileSync(path.join(root, 'site/lang/home-dom', f)))]));

test('all 18 locales have a complete contact sentence and localized input hints', () => {
  assert.equal(Object.keys(dictionaries).length, 18);
  for (const [locale, dict] of Object.entries(dictionaries)) {
    assert.ok(dict['Tell us what you need.']?.trim(), locale);
    if (locale === 'en') continue;
    for (const key of ['Your name', 'Company name', "Tell us about your team, your workflows, and what you're hoping to achieve with SIMY."]) {
      assert.ok(dict[key]?.trim(), `${locale}: ${key}`);
      assert.notEqual(dict[key], key, `${locale}: untranslated hint`);
    }
  }
  assert.equal(dictionaries.ja['Tell us what you need.'], 'SIMYについて、ご相談ください。');
});

test('both file-preview bundles match their source dictionaries', () => {
  execFileSync('python3', ['scripts/build-i18n-bundle.py', '--check'], { cwd: root });
});

test('the demo uses the updated runtime and raw English fallback', () => {
  const demo = fs.readFileSync(path.join(root, 'site/demo.html'), 'utf8');
  assert.match(demo, /i18n\.js\?v=20261006-copy-clarity-1/);
  assert.match(demo, /Meeting ends\. Roadmap ready\./);
  assert.doesNotMatch(demo, /Meeting ends\. Roadmap ships\./);
});

test('reviewed standup copy refers to a team meeting rather than physical standing', () => {
  // Semantic terms for the locales previously mistranslated as getting up/standing.
  const terms = { ar: 'اجتماع', de: 'Stand-up', es: 'reunión', id: 'rapat', it: 'riunione',
    ja: '進捗共有', kn: 'ಸಭೆ', ko: '진행 상황 공유', 'pt-BR': 'reunião', ru: 'встреч',
    te: 'సమావేశ', th: 'ประชุม', vi: 'họp', 'zh-Hans': '晨会', 'zh-Hant': '晨會' };
  const scene = 'Scene 04. The outcome lands on her dashboard — roadmap ready before standup.';
  for (const [locale, term] of Object.entries(terms)) {
    assert.ok(dictionaries[locale]['Before standup'].includes(term), `${locale}: outcome label must mean team sync`);
    assert.ok(dictionaries[locale][scene].includes(term), `${locale}: scene must mean team sync`);
  }
});

test('input hints switch languages, survive rerenders and fall back without changing entered values', () => {
  const makeField = placeholder => ({
    placeholder, value: 'Synthetic user input',
    getAttribute() { return this.placeholder; },
    setAttribute(name, value) { assert.equal(name, 'placeholder'); this.placeholder = value; }
  });
  const fields = [makeField('Your name'), makeField('Company name'), makeField('unknown hint')];
  const heading = { nodeValue: 'Tell us what you need.', isConnected: true };
  const element = { querySelectorAll: () => fields };
  const context = {
    document: { getElementById: () => element }, ROOT_NODE_MAP: new WeakMap(),
    ROOT_PLACEHOLDER_MAP: new WeakMap(), ROOT_APPLYING: false,
    HOME_DOM_CACHE: dictionaries, captureRootOriginals() {}, injectScreenStudio() {},
    loadHomeDom(lang, cb) { this.HOME_DOM_CACHE[lang] = {}; cb(); }
  };
  context.ROOT_NODE_MAP._list = [heading];
  context.ROOT_NODE_MAP.set(heading, heading.nodeValue);
  const start = source.indexOf('  function applyRoot(');
  const end = source.indexOf('\n  /*', start);
  vm.runInNewContext(source.slice(start, end), context);
  for (const locale of ['ja', 'fr', 'en', 'ar', 'ja']) {
    fields[0].placeholder = 'Your name'; // React restores its original prop.
    context.applyRoot(locale);
    assert.equal(heading.nodeValue, dictionaries[locale]['Tell us what you need.']);
    assert.equal(fields[0].placeholder, dictionaries[locale]['Your name'] || 'Your name');
    assert.equal(fields[1].placeholder, dictionaries[locale]['Company name'] || 'Company name');
    assert.equal(fields[2].placeholder, 'unknown hint');
    assert.ok(fields.every(f => f.value === 'Synthetic user input'));
  }
  context.HOME_DOM_CACHE.failed = {};
  context.applyRoot('failed');
  assert.equal(heading.nodeValue, 'Tell us what you need.');
  assert.equal(fields[0].placeholder, 'Your name');
  assert.equal(fields[1].placeholder, 'Company name');
});
