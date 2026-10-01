const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { test } = require('node:test');
const pricing = require('../site/pricing-catalog.js');

const html = readFileSync(require.resolve('../site/index.html'), 'utf8');
const expected = { starter: [3000, 3300], pro: [5000, 5500], team: [8000, 8800] };

test('advertised plans match signup monthly amounts and preserve selection', () => {
  const columns = [...html.matchAll(/<th\b[^>]*data-pricing-plan="([^"]+)"[^>]*>([\s\S]*?)<\/th>/g)];
  assert.equal(columns.length, 3);
  for (const [, plan, column] of columns) {
    const [net, gross] = expected[plan];
    assert.equal(pricing.priceCents(plan), net);
    assert.equal(pricing.grossCents(net, pricing.JAPAN_CONSUMPTION_TAX_BPS), gross);
    assert.match(column, new RegExp(`data-price-amount>${net / 100}<`));
    assert.match(column, new RegExp(`data-tax-included-price>\\$${gross / 100}<`));
    const href = column.match(/class="pricing-plan-link" href="([^"]+)"/)?.[1];
    assert.ok(href, `missing signup link for ${plan}`);
    const url = new URL(href.replaceAll('&amp;', '&'));
    assert.equal(url.origin, 'https://app.simy.one');
    assert.equal(url.pathname, '/signup/');
    assert.equal(url.searchParams.get('plan'), plan);
    assert.equal(url.searchParams.get('industry_package_code'), 'general');
  }
  assert.equal(html.includes('data-billing-cycle'), false);
  assert.equal(html.includes('1 month free'), false);
});
