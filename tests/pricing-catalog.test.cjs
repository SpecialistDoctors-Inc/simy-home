const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const pricing = require('../site/pricing-catalog.js');

test('annual billing is the default and exposes effective monthly prices and totals', () => {
  const result = pricing.presentation('us', 'en');

  assert.equal(result.billingCycle, 'annual');
  assert.deepEqual(result.amounts, { starter: '$29.80', quality: '$49.80', pro: '$79.80' });
  assert.deepEqual(result.annualTotals, {
    starter: '$357.60',
    quality: '$597.60',
    pro: '$957.60'
  });
  assert.deepEqual(result.savingsPercent, { starter: 17, quality: 17, pro: 17 });
});

test('monthly billing uses the higher flexible prices and has no annual total', () => {
  const result = pricing.presentation('us', 'en', 'monthly');

  assert.equal(result.billingCycle, 'monthly');
  assert.deepEqual(result.amounts, { starter: '$35.80', quality: '$59.80', pro: '$95.80' });
  assert.deepEqual(result.annualTotals, { starter: null, quality: null, pro: null });
});

test('Japan presents 10% tax-inclusive annual and monthly amounts', () => {
  const annual = pricing.presentation('jp', 'ja');
  const monthly = pricing.presentation('jp', 'ja', 'monthly');

  assert.equal(annual.displayMode, 'tax-inclusive');
  assert.deepEqual(annual.amounts, { starter: '$32.78', quality: '$54.78', pro: '$87.78' });
  assert.deepEqual(annual.annualTotals, {
    starter: '$393.36',
    quality: '$657.36',
    pro: '$1,053.36'
  });
  assert.deepEqual(monthly.amounts, { starter: '$39.38', quality: '$65.78', pro: '$105.38' });
  assert.deepEqual(annual.storageAmounts, {
    '30 GB': '$11',
    '200 GB': '$44',
    '1 TB': '$110',
    '5 TB': '$550'
  });
  assert.match(annual.taxNote, /消費税10%を含みます/);
});

test('other regions remain tax-exclusive without inventing a tax rate', () => {
  const result = pricing.presentation('fr', 'fr');

  assert.equal(result.region, 'other');
  assert.equal(result.displayMode, 'tax-exclusive');
  assert.match(result.taxNote, /billing address at checkout/);
  assert.doesNotMatch(result.taxNote, /\b\d+%/);
});

test('tax and price arithmetic stays in integer cents', () => {
  assert.equal(pricing.priceCents('starter', 'annual'), 2980);
  assert.equal(pricing.priceCents('starter', 'monthly'), 3580);
  assert.equal(pricing.grossCents(2980, 1000), 3278);
  assert.equal(pricing.grossCents(1000, 1000), 1100);
  assert.equal(pricing.storagePriceCents('30 GB'), 1000);
  assert.equal(pricing.storagePriceCents('5 TB'), 50000);
  assert.throws(() => pricing.priceCents('unknown', 'annual'), /unknown pricing plan/);
  assert.throws(() => pricing.storagePriceCents('unknown'), /unknown storage capacity/);
  assert.throws(() => pricing.grossCents(10.5, 1000), /baseCents/);
});

test('homepage storage rows use catalog capacity keys instead of duplicated prices', () => {
  const root = path.resolve(__dirname, '..');
  const html = fs.readFileSync(path.join(root, 'site/index.html'), 'utf8');
  const runtime = fs.readFileSync(path.join(root, 'site/home.js'), 'utf8');

  assert.doesNotMatch(html, /data-storage-price=/);
  assert.deepEqual(
    [...html.matchAll(/data-storage-capacity="([^"]+)"/g)].map((match) => match[1]),
    ['30 GB', '200 GB', '1 TB', '5 TB']
  );
  assert.match(runtime, /pricingCatalog\.storagePriceCents\(cell\.dataset\.storageCapacity\)/);
});

test('homepage pricing bundles do not ship the retired Starter Autorun cap', () => {
  const root = path.resolve(__dirname, '..');
  const localeBundles = ['home-i18n.js', 'home-locales.js'];

  localeBundles.forEach((file) => {
    const source = fs.readFileSync(path.join(root, 'site', file), 'utf8');
    assert.doesNotMatch(source, /"100 runs"\s*:/, `${file} must not retain the old Starter cap`);
  });
});
