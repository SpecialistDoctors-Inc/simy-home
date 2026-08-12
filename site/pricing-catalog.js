(function (root, factory) {
  var pricing = factory();
  if (typeof module === 'object' && module.exports) module.exports = pricing;
  if (root) root.SIMY_PRICING = pricing;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  var JAPAN_CONSUMPTION_TAX_BPS = 1000;
  var PLAN_BASE_CENTS = Object.freeze({ starter: 3000, pro: 5000, team: 8000 });
  var STORAGE_ADD_ON_BASE_CENTS = 1000;

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

  function presentation(region, language) {
    var normalizedRegion = String(region || '').toLowerCase();
    var japanese = String(language || '').toLowerCase().indexOf('ja') === 0;

    if (normalizedRegion === 'jp') {
      return {
        region: 'jp',
        displayMode: 'tax-inclusive',
        amounts: {
          starter: usd(grossCents(PLAN_BASE_CENTS.starter, JAPAN_CONSUMPTION_TAX_BPS)),
          pro: usd(grossCents(PLAN_BASE_CENTS.pro, JAPAN_CONSUMPTION_TAX_BPS)),
          team: usd(grossCents(PLAN_BASE_CENTS.team, JAPAN_CONSUMPTION_TAX_BPS))
        },
        unit: japanese ? '税込 / 月' : 'tax included / month',
        details: {
          starter: japanese ? '税抜 $30（消費税10%）' : '$30 before 10% Japan consumption tax',
          pro: japanese ? '税抜 $50（消費税10%）' : '$50 before 10% Japan consumption tax',
          team: japanese ? '税抜 $80（消費税10%）' : '$80 before 10% Japan consumption tax'
        },
        extraPrice: japanese ? '30GB / $11（税込）/ 月' : '30GB / $11 tax included / month',
        extraDetail: japanese ? '税抜 $10（消費税10%）' : '$10 before 10% Japan consumption tax',
        disclaimer: japanese
          ? '* 「回数制限なし」はSIMY側のAutorun実行回数を指します。Codex側の利用枠および安全な利用に関する制限が適用されます。日本向け表示価格は消費税10%を含みます。税額と最終合計は、契約時に請求先住所を確認したうえで確定します。SIMYの料金にCodex利用料は含まれません。'
          : '* “No run limit” refers to SIMY Autorun executions. Codex account allowances and reasonable-use safeguards still apply. Japan prices include 10% consumption tax. We confirm the tax and final total from the billing address when you sign. Codex charges are not included in the SIMY fee.'
      };
    }

    var isUnitedStates = normalizedRegion === 'us';
    return {
      region: isUnitedStates ? 'us' : 'other',
      displayMode: 'tax-exclusive',
      amounts: {
        starter: usd(PLAN_BASE_CENTS.starter),
        pro: usd(PLAN_BASE_CENTS.pro),
        team: usd(PLAN_BASE_CENTS.team)
      },
      unit: japanese ? '+ 適用される税 / 月' : '+ applicable tax / month',
      details: {
        starter: japanese ? '税額は請求先住所から契約時に確定' : 'Tax is calculated from the billing address',
        pro: japanese ? '税額は請求先住所から契約時に確定' : 'Tax is calculated from the billing address',
        team: japanese ? '税額は請求先住所から契約時に確定' : 'Tax is calculated from the billing address'
      },
      extraPrice: japanese ? '30GB / $10 + 適用される税 / 月' : '30GB / $10 + applicable tax / month',
      extraDetail: japanese ? '税額は請求先住所から契約時に確定' : 'Tax is calculated from the billing address',
      disclaimer: isUnitedStates
        ? (japanese
          ? '* 「回数制限なし」はSIMY側のAutorun実行回数を指します。Codex側の利用枠および安全な利用に関する制限が適用されます。米国の売上税は州・地方自治体および請求先住所により異なります。適用される税額と最終合計は契約時に確定します。SIMYの料金にCodex利用料は含まれません。'
          : '* “No run limit” refers to SIMY Autorun executions. Codex account allowances and reasonable-use safeguards still apply. US sales tax varies by state, local jurisdiction, and billing address. We confirm the applicable tax and final total when you sign. Codex charges are not included in the SIMY fee.')
        : (japanese
          ? '* 「回数制限なし」はSIMY側のAutorun実行回数を指します。Codex側の利用枠および安全な利用に関する制限が適用されます。請求先所在地に応じた税が適用される場合があります。税額と最終合計は契約時に確定します。SIMYの料金にCodex利用料は含まれません。'
          : '* “No run limit” refers to SIMY Autorun executions. Codex account allowances and reasonable-use safeguards still apply. Tax may apply based on the billing location. We confirm the tax and final total when you sign. Codex charges are not included in the SIMY fee.')
    };
  }

  function applyToDocument(doc) {
    if (!doc || !doc.documentElement) return null;
    var result = presentation(
      doc.documentElement.getAttribute('data-hero-region'),
      doc.documentElement.lang
    );

    Object.keys(result.amounts).forEach(function (plan) {
      var card = doc.querySelector('#pricing .pricing-card[data-plan="' + plan + '"]');
      if (!card) return;
      var amount = card.querySelector('.price-amount');
      var unit = card.querySelector('.price-unit');
      var detail = card.querySelector('.price-tax-detail');
      if (amount) amount.textContent = result.amounts[plan];
      if (unit) unit.textContent = result.unit;
      if (detail) detail.textContent = result.details[plan];
    });

    var extraPrice = doc.querySelector('#pricing .pricing-extra-price');
    var extraDetail = doc.querySelector('#pricing .pricing-extra-tax-detail');
    var disclaimer = doc.querySelector('#pricing .pricing-disclaimer');
    if (extraPrice) extraPrice.textContent = result.extraPrice;
    if (extraDetail) extraDetail.textContent = result.extraDetail;
    if (disclaimer) disclaimer.textContent = result.disclaimer;
    doc.documentElement.setAttribute('data-pricing-tax-mode', result.displayMode);
    return result;
  }

  return Object.freeze({
    JAPAN_CONSUMPTION_TAX_BPS: JAPAN_CONSUMPTION_TAX_BPS,
    PLAN_BASE_CENTS: PLAN_BASE_CENTS,
    STORAGE_ADD_ON_BASE_CENTS: STORAGE_ADD_ON_BASE_CENTS,
    grossCents: grossCents,
    presentation: presentation,
    applyToDocument: applyToDocument
  });
});
