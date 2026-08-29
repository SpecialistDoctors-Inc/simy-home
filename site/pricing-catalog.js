(function (root, factory) {
  var pricing = factory();
  if (typeof module === 'object' && module.exports) module.exports = pricing;
  if (root) root.SIMY_PRICING = pricing;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  var JAPAN_CONSUMPTION_TAX_BPS = 1000;
  var PLAN_PRICE_CENTS = Object.freeze({
    annual: Object.freeze({ starter: 2980, quality: 4980, pro: 7980 }),
    monthly: Object.freeze({ starter: 3580, quality: 5980, pro: 9580 })
  });
  var STORAGE_ADD_ON_CENTS = Object.freeze({
    '30 GB': 1000,
    '200 GB': 4000,
    '1 TB': 10000,
    '5 TB': 50000
  });

  function grossCents(baseCents, taxBasisPoints) {
    if (!Number.isInteger(baseCents) || baseCents < 0) {
      throw new TypeError('baseCents must be a non-negative integer');
    }
    if (!Number.isInteger(taxBasisPoints) || taxBasisPoints < 0) {
      throw new TypeError('taxBasisPoints must be a non-negative integer');
    }
    return Math.round((baseCents * (10000 + taxBasisPoints)) / 10000);
  }

  function usd(cents) {
    if (!Number.isInteger(cents)) throw new TypeError('cents must be an integer');
    return '$' + (cents / 100).toLocaleString('en-US', {
      minimumFractionDigits: cents % 100 === 0 ? 0 : 2,
      maximumFractionDigits: 2
    });
  }

  function normalizeBillingCycle(billingCycle) {
    return billingCycle === 'monthly' ? 'monthly' : 'annual';
  }

  function priceCents(plan, billingCycle) {
    var cycle = normalizeBillingCycle(billingCycle);
    var cents = PLAN_PRICE_CENTS[cycle][plan];
    if (!Number.isInteger(cents)) throw new TypeError('unknown pricing plan: ' + plan);
    return cents;
  }

  function savingsPercent(plan) {
    var annualMonthlyEquivalent = priceCents(plan, 'annual');
    var monthly = priceCents(plan, 'monthly');
    return Math.round((1 - annualMonthlyEquivalent / monthly) * 100);
  }

  function storagePriceCents(capacity) {
    var cents = STORAGE_ADD_ON_CENTS[capacity];
    if (!Number.isInteger(cents)) throw new TypeError('unknown storage capacity: ' + capacity);
    return cents;
  }

  function presentation(region, language, billingCycle) {
    var cycle = normalizeBillingCycle(billingCycle);
    var normalizedRegion = String(region || '').toLowerCase();
    var japanese = String(language || '').toLowerCase().indexOf('ja') === 0;
    var taxInclusive = normalizedRegion === 'jp' || japanese;
    var amounts = {};
    var baseAmounts = {};
    var annualTotals = {};

    Object.keys(PLAN_PRICE_CENTS[cycle]).forEach(function (plan) {
      var base = priceCents(plan, cycle);
      var display = taxInclusive ? grossCents(base, JAPAN_CONSUMPTION_TAX_BPS) : base;
      amounts[plan] = usd(display);
      baseAmounts[plan] = usd(base);
      annualTotals[plan] = cycle === 'annual' ? usd(display * 12) : null;
    });

    return {
      region: taxInclusive ? 'jp' : (normalizedRegion === 'us' ? 'us' : 'other'),
      billingCycle: cycle,
      displayMode: taxInclusive ? 'tax-inclusive' : 'tax-exclusive',
      amounts: amounts,
      baseAmounts: baseAmounts,
      annualTotals: annualTotals,
      savingsPercent: {
        starter: savingsPercent('starter'),
        quality: savingsPercent('quality'),
        pro: savingsPercent('pro')
      },
      storageAmounts: Object.keys(STORAGE_ADD_ON_CENTS).reduce(function (result, capacity) {
        var base = storagePriceCents(capacity);
        result[capacity] = usd(taxInclusive ? grossCents(base, JAPAN_CONSUMPTION_TAX_BPS) : base);
        return result;
      }, {}),
      taxNote: taxInclusive
        ? (japanese
          ? '日本語表示の価格は消費税10%を含みます。'
          : 'Prices for Japan include 10% consumption tax.')
        : 'Applicable taxes are calculated from the billing address at checkout.'
    };
  }

  return Object.freeze({
    JAPAN_CONSUMPTION_TAX_BPS: JAPAN_CONSUMPTION_TAX_BPS,
    PLAN_PRICE_CENTS: PLAN_PRICE_CENTS,
    STORAGE_ADD_ON_CENTS: STORAGE_ADD_ON_CENTS,
    grossCents: grossCents,
    priceCents: priceCents,
    savingsPercent: savingsPercent,
    storagePriceCents: storagePriceCents,
    presentation: presentation
  });
});
