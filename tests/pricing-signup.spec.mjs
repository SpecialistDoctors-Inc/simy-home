import { expect, test } from '@playwright/test';

const selections = [
  { plan: 'starter', millions: 120, absolute: '120000000', feature: '120,000,000' },
  { plan: 'pro', millions: 240, absolute: '240000000', feature: '240,000,000' },
  { plan: 'scale', millions: 1200, absolute: '1200000000', feature: '1,200,000,000' }
];

function signupParams(href) {
  const url = new URL(href);
  return { url, params: url.searchParams };
}

async function expectSignup(card, expected) {
  const signup = signupParams(await card.locator('.plan-cta').getAttribute('href'));
  expect(signup.url.hostname).toBe('app-dev.simy.one');
  expect(signup.url.pathname).toBe('/signup');
  expect(signup.params.get('plan')).toBe(expected.plan);
  expect(signup.params.get('interval')).toBe(expected.interval);
  expect(signup.params.get('monthly_tokens')).toBe(expected.absolute);
  expect(signup.params.get('lang')).toBe(expected.lang);
  expect(signup.params.get('locale')).toBe(expected.lang);
  expect(signup.params.get('region')).toBe(expected.region);
}

test('selected monthly allocation reaches new signup across billing switches', async ({ page }) => {
  await page.goto('/?lang=ja&region=jp');
  const consent = page.locator('#cookieConsentOk');
  if (await consent.isVisible()) await consent.click();

  for (const expected of [
    { plan: 'starter', absolute: '80000000' },
    { plan: 'pro', absolute: '160000000' },
    { plan: 'scale', absolute: '400000000' }
  ]) {
    await expectSignup(page.locator(`.pricing-card[data-plan="${expected.plan}"]`), {
      ...expected,
      interval: 'yearly',
      lang: 'ja',
      region: 'jp'
    });
  }

  for (const selection of selections) {
    const card = page.locator(`.pricing-card[data-plan="${selection.plan}"]`);
    const trigger = card.getByRole('button', { name: /SIMYトークン/ });
    await trigger.click();
    await expect(trigger).toHaveAttribute('aria-expanded', 'true');

    const option = card.locator(`[role="menuitemradio"][data-tokens="${selection.millions}"]`);
    await option.click();
    await expect(option).toHaveAttribute('aria-checked', 'true');
    await expect(trigger).toHaveAttribute('aria-expanded', 'false');
    await expect(card.locator(`#feat-tokens-${selection.plan}`)).toContainText(selection.feature);

    await expectSignup(card, { ...selection, interval: 'yearly', lang: 'ja', region: 'jp' });
  }

  await page.getByRole('button', { name: '月払い' }).click();
  await expect(page.getByRole('button', { name: '月払い' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('button', { name: /年払い/ })).toHaveAttribute('aria-pressed', 'false');

  for (const selection of selections) {
    const card = page.locator(`.pricing-card[data-plan="${selection.plan}"]`);
    await expectSignup(card, { ...selection, interval: 'monthly', lang: 'ja', region: 'jp' });
  }

  await page.getByRole('button', { name: /年払い/ }).click();
  for (const selection of selections) {
    const href = await page.locator(`.pricing-card[data-plan="${selection.plan}"] .plan-cta`).getAttribute('href');
    expect(signupParams(href).params.get('monthly_tokens')).toBe(selection.absolute);
  }

  await page.locator('#pricing').screenshot({ path: 'output/playwright/pricing-signup-selections.png' });

  await page.locator('#langBtn').click();
  await page.locator('[data-lang-option="en"]').click();
  for (const selection of selections) {
    await expectSignup(page.locator(`.pricing-card[data-plan="${selection.plan}"]`), {
      ...selection,
      interval: 'yearly',
      lang: 'en',
      region: 'jp'
    });
  }

  await page.locator('.region-btn').click();
  await page.locator('[data-region-btn="us"]').click();
  for (const selection of selections) {
    await expectSignup(page.locator(`.pricing-card[data-plan="${selection.plan}"]`), {
      ...selection,
      interval: 'yearly',
      lang: 'en',
      region: 'us'
    });
  }

});

test('token menu supports keyboard navigation and closes on focus exit', async ({ page }) => {
  await page.goto('/?lang=en&region=us');
  const consent = page.locator('#cookieConsentOk');
  if (await consent.isVisible()) await consent.click();
  const card = page.locator('.pricing-card[data-plan="pro"]');
  const trigger = page.locator('.pricing-card[data-plan="pro"] .token-dropdown-btn');
  await trigger.click();
  await expect(trigger).toHaveAttribute('aria-expanded', 'true');
  await expect(card.locator('[role="menuitemradio"][data-tokens="160"]')).toBeFocused();
  await card.screenshot({ path: 'output/playwright/pricing-token-menu-open.png' });
  await page.keyboard.press('End');
  await expect(card.locator('[role="menuitemradio"][data-tokens="640"]')).toBeFocused();
  await page.keyboard.press('Home');
  await page.keyboard.press('ArrowDown');
  await expect(card.locator('[role="menuitemradio"][data-tokens="240"]')).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(trigger).toHaveAttribute('aria-expanded', 'false');
  await expect(trigger).toBeFocused();

  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Enter');
  await expect(card.locator('[role="menuitemradio"][data-tokens="240"]')).toHaveAttribute('aria-checked', 'true');
  await expect(trigger).toHaveAttribute('aria-expanded', 'false');
  await expect(trigger).toBeFocused();

  await page.keyboard.press('ArrowUp');
  await expect(card.locator('[role="menuitemradio"][data-tokens="640"]')).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(trigger).toHaveAttribute('aria-expanded', 'false');
  await expect(card.locator('.plan-cta')).toBeFocused();
});
