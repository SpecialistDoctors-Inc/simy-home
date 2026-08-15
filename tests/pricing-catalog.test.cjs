const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const pricing = require('../site/pricing-catalog.js');

test('Japan presents tax-inclusive totals with the 10% base amounts preserved', () => {
  const result = pricing.presentation('jp', 'ja');

  assert.equal(result.displayMode, 'tax-inclusive');
  assert.deepEqual(result.amounts, { starter: '$33', pro: '$55', team: '$88' });
  assert.equal(result.extraPrice, '30GB / $11（税込）/ 月');
  assert.match(result.details.starter, /税抜 \$30/);
  assert.match(result.disclaimer, /消費税10%を含みます/);
});

test('United States keeps base prices and does not invent a nationwide rate', () => {
  const result = pricing.presentation('us', 'en');

  assert.equal(result.displayMode, 'tax-exclusive');
  assert.deepEqual(result.amounts, { starter: '$30', pro: '$50', team: '$80' });
  assert.equal(result.unit, '+ applicable tax / month');
  assert.match(result.disclaimer, /varies by state, local jurisdiction, and billing address/);
  assert.doesNotMatch(result.disclaimer, /\b\d+%/);
});

test('unknown regions fall back to a non-committal tax-exclusive display', () => {
  const result = pricing.presentation('xx', 'en');

  assert.equal(result.region, 'other');
  assert.equal(result.displayMode, 'tax-exclusive');
  assert.match(result.disclaimer, /Tax may apply based on the billing location/);
});

test('tax arithmetic stays in integer cents', () => {
  assert.equal(pricing.grossCents(3000, 1000), 3300);
  assert.equal(pricing.grossCents(1000, 1000), 1100);
  assert.throws(() => pricing.grossCents(10.5, 1000), /baseCents/);
});

test('pricing and primary CTAs open the matching SIMY app signup flow', () => {
  const html = fs.readFileSync(path.join(__dirname, '../site/index.html'), 'utf8');

  for (const plan of ['starter', 'pro', 'team']) {
    assert.match(html, new RegExp(`class="plan-cta" href="https://app\\.simy\\.one/signup\\?plan=${plan}"`));
  }
  assert.match(html, /class="btn-primary" href="https:\/\/app\.simy\.one\/signup\?plan=pro"/);
  assert.doesNotMatch(html, /class="plan-cta" href="mailto:/);
});
