const test = require('node:test');
const assert = require('node:assert/strict');
const pricing = require('../site/pricing-catalog.js');

test('monthly plan prices match the live signup contract', () => {
  assert.deepEqual(pricing.PLAN_PRICE_CENTS, {
    starter: 3000,
    pro: 5000,
    team: 8000
  });
  assert.equal(pricing.priceCents('starter'), 3000);
  assert.equal(pricing.priceCents('pro'), 5000);
  assert.equal(pricing.priceCents('team'), 8000);
  assert.throws(() => pricing.priceCents('unknown'), /unknown pricing plan/);
});

test('Japanese tax-inclusive detail uses integer-cent arithmetic', () => {
  assert.equal(pricing.grossCents(3000, pricing.JAPAN_CONSUMPTION_TAX_BPS), 3300);
  assert.equal(pricing.grossCents(5000, pricing.JAPAN_CONSUMPTION_TAX_BPS), 5500);
  assert.equal(pricing.grossCents(8000, pricing.JAPAN_CONSUMPTION_TAX_BPS), 8800);
  assert.throws(() => pricing.grossCents(10.5, 1000), /baseCents/);
  assert.throws(() => pricing.grossCents(1000, -1), /taxBasisPoints/);
});
