const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const map = require('../scripts/service-pricing-2026-11-map.json');
const simple = require('../scripts/simple-pricing-copy.json');
const catalog = require('../site/pricing-catalog.js');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');
const section = html => html.match(/<!-- service-pricing-2026-11:start -->([\s\S]*?)<!-- service-pricing-2026-11:end -->/)[1];
const collapsed = html => {
  // Details can nest in future templates; remove their full subtree.
  let depth = 0, end = 0, result = '';
  for (const match of html.matchAll(/<\/?details\b[^>]*>/g)) {
    if (match[0].startsWith('</')) {
      depth--;
      if (!depth) end = match.index + match[0].length;
    } else {
      if (!depth) result += html.slice(end, match.index);
      depth++;
    }
  }
  return result + html.slice(end);
};

test('all service pages lead with relevant monthly totals and hide component price tables', () => {
  for (const route of map.routes.filter(route => route.profile !== 'rosenz')) {
    const html = section(read('site/' + route.path));
    const visible = collapsed(html);
    const currency = route.locale === 'ja' ? 'jpy' : 'usd';
    const expected = {
      jpy: {hearing: [2280], development: [6060], fp: [6660], homepage: [22080, 32080]},
      usd: {hearing: [1500], development: [4000], fp: [4400], homepage: [14700, 21400]}
    }[currency][route.profile];
    assert.deepEqual([...visible.matchAll(/data-total-amount="(\d+)"/g)].map(m => Number(m[1])), expected, route.path);
    assert.doesNotMatch(visible, /<table\b|rate-annual|sp26-example/, route.path);
    assert.ok(visible.includes(simple[route.locale].total), route.path);
    if (['hearing', 'fp'].includes(route.profile)) {
      assert.ok(visible.includes(simple[route.locale].workflow), route.path);
      assert.ok(html.includes(simple[route.locale].recording), route.path);
      assert.doesNotMatch(visible, /月2時間|2 recorded-transcription hours/);
      assert.ok(html.includes(simple[route.locale].hearingNote), route.path);
    }
    if (['hearing', 'fp', 'development'].includes(route.profile)) {
      assert.ok(visible.includes(simple[route.locale].ai), route.path);
      assert.ok(visible.includes(simple[route.locale].baseValue), route.path);
    }
    if (['development', 'homepage'].includes(route.profile)) {
      assert.doesNotMatch(html, /data-sku="transcription_(?:20h|overage)"/, route.path);
    }
  }
});

test('all quoted totals and currencies agree with the authoritative specification', () => {
  const prices = JSON.parse(execFileSync('python3', ['-c',
    'import json; from pathlib import Path; from pricing_2026_11_data import parse_prices; print(json.dumps(parse_prices(Path("../docs/pricing/pricing-2026-11-spec.md"))))'
  ], {cwd: path.join(root, 'scripts'), encoding: 'utf8'}));
  const pages = [...map.routes.map(route => 'site/' + route.path), 'site/pricing-2026-11.html'];
  for (const file of pages) {
    for (const [, codes, currency, amount] of read(file).matchAll(/data-plan-codes="([^"]+)" data-total-currency="(jpy|usd)" data-total-amount="(\d+)"/g)) {
      assert.equal(Number(amount), codes.split(',').reduce((total, code) => total + prices[code][currency], 0), `${file}: ${codes}`);
    }
  }
  const sales = section(read('site/for/sales/index.html'));
  assert.match(sales, /data-total-amount="6060"/);
  assert.match(sales, /data-total-amount="11560"/);
  const fp = section(read('site/for/financial-planners/index.html'));
  assert.match(fp, /data-total-amount="10440"/);
  assert.match(fp, /data-total-amount="15940"/);
  const hp = section(read('site/hp-management/index.html'));
  assert.match(hp, /data-total-amount="61880"/);
  assert.match(hp, /data-total-amount="71880"/);
});

test('all six homepages show actual current monthly prices and keep future prices separate', () => {
  for (const locale of Object.keys(simple)) {
    const html = read('site/' + (locale === 'en' ? 'index' : locale) + '.html');
    const pricing = html.match(/<section\b[^>]*id="pricing"[^>]*>([\s\S]*?)<\/section>/)[1];
    const visible = collapsed(pricing);
    assert.doesNotMatch(visible, /<table\b|data-billing-cycle|data-realtime-addon|data-storage-capacity/);
    assert.ok(visible.includes(simple[locale].current));
    assert.ok(visible.includes(simple[locale].ai));
    assert.ok(visible.includes('/pricing-2026-11.html'));
    for (const plan of ['starter', 'quality']) {
      const card = visible.match(new RegExp(`<article[^>]*data-current-monthly="${plan}"[^>]*>([\\s\\S]*?)<\\/article>`))[1];
      assert.ok(card.includes('$' + (catalog.priceCents(plan, 'monthly') / 100).toFixed(2)));
      const href = card.match(/href="([^"]+)"/)[1].replaceAll('&amp;', '&');
      const url = new URL(href);
      assert.equal(url.pathname, '/signup/');
      assert.equal(url.searchParams.get('plan'), plan);
      assert.equal(url.searchParams.get('interval'), 'monthly');
      assert.equal(url.searchParams.get('lang'), locale);
    }
  }
});

test('the full pricing page starts with complete totals and keeps all detailed rates expandable', () => {
  const html = read('site/pricing-2026-11.html');
  const visible = collapsed(html);
  for (const amount of [2280, 6060, 11560, 6660, 17080, 22080, 32080]) {
    assert.ok(visible.includes(`data-total-amount="${amount}"`), String(amount));
  }
  assert.doesNotMatch(visible, /<table\b|提供準備中の項目/);
  assert.ok(visible.includes('適用日未定・新料金での申込受付は開始していません'));
});
