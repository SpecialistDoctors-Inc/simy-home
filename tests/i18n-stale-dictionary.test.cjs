const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.join(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'site/i18n.js'), 'utf8');
const dictionary = locale => JSON.parse(fs.readFileSync(path.join(root, 'site/lang/home-dom', locale + '.json'), 'utf8'));

// Regression for dev #151: a slow dictionary for a language the visitor already
// left must not overwrite the copy of the language selected afterwards.
test('a delayed dictionary cannot overwrite the currently selected language', () => {
  const ja = dictionary('ja');
  const fr = dictionary('fr');
  const original = 'Request Access';
  assert.ok(ja[original] && fr[original] && ja[original] !== fr[original]);
  const heading = { nodeValue: original, isConnected: true };
  let finishFrench;
  const context = {
    DEFAULT: 'en',
    CURRENT_LANG: 'fr',
    document: { getElementById: () => ({ querySelectorAll: () => [] }) },
    ROOT_NODE_MAP: new WeakMap(), ROOT_APPLYING: false,
    HOME_DOM_CACHE: { ja }, captureRootOriginals() {}, injectScreenStudio() {},
    loadHomeDom(lang, cb) { assert.equal(lang, 'fr'); finishFrench = cb; }
  };
  context.ROOT_NODE_MAP._list = [heading];
  context.ROOT_NODE_MAP.set(heading, heading.nodeValue);
  const start = source.indexOf('  function applyRoot(');
  vm.runInNewContext(source.slice(start, source.indexOf('\n  /*', start)), context);
  context.applyRoot('fr');
  context.CURRENT_LANG = 'ja';
  context.applyRoot('ja');
  assert.equal(heading.nodeValue, ja[original]);
  context.HOME_DOM_CACHE.fr = fr;
  finishFrench();
  assert.equal(heading.nodeValue, ja[original]);
});
