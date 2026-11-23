const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

// The currently deployed edge redirects /hp-management/clinic/ to .html
// without the query. Keep existing published paths until edge deployment;
// preserving a mode must never introduce that extra redirect.
for (const [path, expected = path] of [
  ['/hp-management/clinic.html#pricing'],
  ['/hp-management.html'],
  // Directory links in page bodies would lose the query on that redirect.
  ['/hp-management/', '/hp-management.html'],
  ['/hp-management/clinic/#review-support', '/hp-management/clinic.html#review-support'],
  ['/hp-management/law-firm/', '/hp-management/law-firm.html'],
  ['/for/es/engineers/', '/for/es/engineers.html'],
  ['/guides/', '/guides.html'],
  // Same-page anchors and directory URLs the edge serves directly keep their form.
  ['/ja.html#pricing'],
  ['/for/rosenz/'],
  ['/'],
]) {
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
    assert.equal(target.pathname + target.hash, expected);
    assert.equal(target.searchParams.get('checkout_mode'), 'sandbox');
  });
}

// HP checkout pages do not load site-header.js; their checkout script keeps
// the explicit mode on outbound links so returning never reaches live checkout.
for (const script of ['site/clinic-checkout.js', 'site/hp-management/law-firm/clinic-checkout.js']) {
  for (const [query, expectedMode] of [['?checkout_mode=sandbox', 'sandbox'], ['?checkout_mode=live', 'invalid'], ['', null]]) {
    test(`${script} keeps mode ${expectedMode} on HP page links`, async () => {
      const links = [
        { href: 'https://simy.one/pricing-2026-11.html' },
        { href: 'https://simy.one/hp-management/clinic/#pricing' },
        { href: 'https://app.simy.one/signup?lang=ja' },
        { href: 'https://buy.stripe.com/abc' },
      ];
      const element = { textContent: '', disabled: false, hidden: false, querySelector: () => element, querySelectorAll: () => [element, element] };
      const document = { querySelectorAll: () => links, querySelector: () => element, addEventListener: () => {} };
      const fetch = async () => ({ ok: false });
      const window = { document, fetch, URL, URLSearchParams, Promise, crypto: globalThis.crypto };
      vm.runInNewContext(fs.readFileSync(script, 'utf8'), {
        window, document, fetch, URL, URLSearchParams, Promise,
        location: new URL(`https://simy.one/hp-management/clinic.html${query}`),
      });
      await window.SimyClinicCheckout.ready;
      const modes = links.map((link) => new URL(link.href).searchParams.get('checkout_mode'));
      assert.deepEqual(modes, [expectedMode, expectedMode, expectedMode, null]);
      if (expectedMode) assert.equal(new URL(links[1].href).pathname, '/hp-management/clinic.html');
      else assert.equal(links[1].href, 'https://simy.one/hp-management/clinic/#pricing');
    });
  }
}
