const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { test } = require('node:test');
const pricing = require('../site/pricing-catalog.js');
const html = readFileSync(require.resolve('../site/index.html'), 'utf8');
const expected = { starter: { annual: 2980, monthly: 3580 }, quality: { annual: 5980, monthly: 7180 } };

test('original prices, trial and billing periods remain in the plan table', () => {
  const columns = [...html.matchAll(/<th\b[^>]*data-pricing-plan="([^"]+)"[^>]*>([\s\S]*?)<\/th>/g)];
  assert.equal(columns.length, 2);
  for (const [ , plan, column] of columns) {
    assert.equal(pricing.priceCents(plan, 'annual'), expected[plan].annual);
    assert.equal(pricing.priceCents(plan, 'monthly'), expected[plan].monthly);
    assert.match(column, /1 month free/);
    const href = column.match(/class="pricing-plan-link" href="([^"]+)"/)?.[1];
    assert.ok(href);
    const url = new URL(href.replaceAll('&amp;', '&'));
    assert.equal(url.pathname, '/signup/');
    assert.equal(url.searchParams.get('plan'), plan);
    assert.equal(url.searchParams.get('interval'), 'annual');
  }
  assert.match(html, /data-billing-cycle="annual"/);
  assert.match(html, /data-billing-cycle="monthly"/);
});
