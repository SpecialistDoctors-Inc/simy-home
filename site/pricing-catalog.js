(function (root, factory) {
  var pricing = factory();
  if (typeof module === 'object' && module.exports) module.exports = pricing;
  if (root) root.SIMY_PRICING = pricing;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  // Keep these amounts aligned with simy-web/src/lib/billing/pricing-v2.ts.
  var JAPAN_CONSUMPTION_TAX_BPS = 1000;
  var PLAN_PRICE_CENTS = Object.freeze({ starter: 3000, pro: 5000, team: 8000 });

  function grossCents(baseCents, taxBasisPoints) {
    if (!Number.isInteger(baseCents) || baseCents < 0) {
      throw new TypeError('baseCents must be a non-negative integer');
    }
    if (!Number.isInteger(taxBasisPoints) || taxBasisPoints < 0) {
      throw new TypeError('taxBasisPoints must be a non-negative integer');
    }
    return Math.round((baseCents * (10000 + taxBasisPoints)) / 10000);
  }

  function priceCents(plan) {
    var cents = PLAN_PRICE_CENTS[plan];
    if (!Number.isInteger(cents)) throw new TypeError('unknown pricing plan: ' + plan);
    return cents;
  }

  return Object.freeze({
    JAPAN_CONSUMPTION_TAX_BPS: JAPAN_CONSUMPTION_TAX_BPS,
    PLAN_PRICE_CENTS: PLAN_PRICE_CENTS,
    grossCents: grossCents,
    priceCents: priceCents
  });
});
