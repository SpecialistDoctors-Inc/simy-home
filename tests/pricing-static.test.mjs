import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const html = await readFile(new URL('../site/index.html', import.meta.url), 'utf8');

test('both paid plan actions remain inside their comparison-table headings', () => {
  const table = html.match(/<table[^>]*class="pricing-table"[\s\S]*?<\/table>/)?.[0];
  assert.ok(table, 'pricing comparison table is present');
  for (const plan of ['starter', 'quality']) {
    const column = table.match(new RegExp(`<th[^>]*data-pricing-plan="${plan}"[^>]*>[\\s\\S]*?<\\/th>`))?.[0];
    assert.ok(column, `${plan} has a table column`);
    assert.match(column, /class="pricing-plan-link"/);
    assert.match(column, new RegExp(`plan=${plan}&amp;interval=annual`));
  }
});

test('billing switches expose their selected state and preserve the free trial', () => {
  assert.match(html, /data-billing-cycle="annual"[^>]*aria-pressed="true"|aria-pressed="true"[^>]*data-billing-cycle="annual"/);
  assert.match(html, /data-billing-cycle="monthly"[^>]*aria-pressed="false"|aria-pressed="false"[^>]*data-billing-cycle="monthly"/);
  assert.equal((html.match(/class="pricing-trial">1 month free/g) || []).length, 2);
});
