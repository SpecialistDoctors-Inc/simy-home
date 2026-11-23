const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

// The currently deployed edge redirects /hp-management/clinic/ to .html
// without the query. Keep existing published paths until edge deployment;
// preserving a mode must never introduce that extra redirect.
for (const path of ['/hp-management/clinic.html#pricing', '/hp-management.html']) {
  test(`sandbox navigation retains published path ${path}`, () => {
    const link = { href: `https://simy.one${path}` };
    const document = {
      querySelectorAll: () => [link], querySelector: () => null,
      addEventListener: () => {},
    };
    vm.runInNewContext(fs.readFileSync('site/site-header.js', 'utf8'), {
      URL, location: new URL('https://simy.one/ja.html?checkout_mode=sandbox'), document,
    });
    const target = new URL(link.href);
    assert.equal(target.pathname + target.hash, path);
    assert.equal(target.searchParams.get('checkout_mode'), 'sandbox');
  });
}
