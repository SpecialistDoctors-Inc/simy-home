import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const html = await readFile(new URL('../site/index.html', import.meta.url), 'utf8');

const plans = [
  { name: 'starter', tokens: 80_000_000 },
  { name: 'pro', tokens: 160_000_000 },
  { name: 'scale', tokens: 400_000_000 }
];

test('default pricing CTAs carry each plan monthly token allocation into signup', () => {
  for (const plan of plans) {
    const ctaPattern = new RegExp(
      `class="plan-cta" href="https://app\\.simy\\.one/signup\\?plan=${plan.name}` +
      `&amp;interval=yearly&amp;monthly_tokens=${plan.tokens}&amp;lang=en&amp;locale=en&amp;region=us"`
    );
    assert.match(html, ctaPattern, `${plan.name} CTA should include its absolute monthly token allocation`);
    assert.match(html, new RegExp(`id="feat-tokens-${plan.name}"`));
  }
});

test('token selectors expose button, menu, and checked selection semantics', () => {
  for (const plan of plans) {
    assert.match(
      html,
      new RegExp(
        `aria-controls="token-menu-${plan.name}" aria-expanded="false" ` +
        `aria-haspopup="menu" class="token-dropdown-btn" id="token-button-${plan.name}"`
      )
    );
    assert.match(
      html,
      new RegExp(
        `aria-labelledby="token-button-${plan.name}" class="token-dropdown-list" ` +
        `data-plan="${plan.name}" id="token-menu-${plan.name}" role="menu"`
      )
    );
  }

  assert.equal((html.match(/role="menuitemradio"/g) || []).length, 14);
  assert.equal((html.match(/aria-checked="true" class="token-dropdown-item active"/g) || []).length, 3);
  assert.match(html, /data-billing="monthly"[^>]+aria-pressed="false"|aria-pressed="false"[^>]+data-billing="monthly"/);
  assert.match(html, /data-billing="yearly"[^>]+aria-pressed="true"|aria-pressed="true"[^>]+data-billing="yearly"/);
});

test('dynamic signup URL uses the absolute monthly_tokens contract', () => {
  assert.match(html, /function signupUrl\(plan, interval, monthlyTokens\)/);
  assert.match(html, /'&monthly_tokens=' \+ encodeURIComponent\(monthlyTokens\)/);
  assert.match(html, /signupUrl\(plan, currentBilling, tokens \* 1000000\)/);
});

test('Starter first-month offer opens below the subscription plan grid and defaults to no renewal', () => {
  assert.match(
    html,
    /aria-controls="starter-trial-dialog" aria-haspopup="dialog" class="starter-trial-entry"/
  );
  assert.doesNotMatch(
    html,
    /data-plan="starter"[\s\S]*?starter-trial-entry[\s\S]*?data-plan="pro"/
  );
  assert.match(
    html,
    /<dialog aria-labelledby="starter-trial-title" class="starter-trial-dialog" id="starter-trial-dialog">/
  );
  assert.match(html, /<input id="starter-trial-auto-renew" type="checkbox">/);
  assert.match(
    html,
    /offer_id=starter_trial_v1&amp;auto_renew=false&amp;plan=starter&amp;interval=monthly&amp;monthly_tokens=80000000&amp;seats=1/
  );
  assert.match(html, /function openStarterTrialOffer\(\)/);
  assert.match(html, /starterTrialEntry\.addEventListener\('click', openStarterTrialOffer\)/);
});
