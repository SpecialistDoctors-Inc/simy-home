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
  const cardEdges = await page.locator('.pricing-card').evaluateAll((cards) =>
    cards.map((card) => {
      const rect = card.getBoundingClientRect();
      return { top: rect.top, bottom: rect.bottom };
    })
  );
  expect(Math.max(...cardEdges.map(({ top }) => top)) - Math.min(...cardEdges.map(({ top }) => top))).toBeLessThanOrEqual(1);
  expect(Math.max(...cardEdges.map(({ bottom }) => bottom)) - Math.min(...cardEdges.map(({ bottom }) => bottom))).toBeLessThanOrEqual(1);

  await page.locator('#langBtn').click();
  await page.locator('[data-lang-option="en"]').click();
  await expect(page.locator('#starter-trial-entry')).toContainText('Trial for one month · USD 10');
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

test('Trial offer opens above the plan grid and defaults to no renewal', async ({ page }) => {
  await page.goto('/?lang=ja&region=jp');
  const consent = page.locator('#cookieConsentOk');
  if (await consent.isVisible()) await consent.click();

  const card = page.locator('.pricing-card[data-plan="starter"]');
  const entry = page.locator('#starter-trial-entry');
  const dialog = page.locator('#starter-trial-dialog');

  await expect(card.locator('#starter-trial-entry')).toHaveCount(0);
  await expect(entry).toContainText('Trial 1か月 · USD 10');
  await expect(entry).toContainText('自動更新は任意です');
  expect(
    await entry.evaluate((offer, grid) =>
      Boolean(offer.compareDocumentPosition(grid) & Node.DOCUMENT_POSITION_FOLLOWING)
    , await page.locator('.pricing-grid').elementHandle())
  ).toBe(true);
  await expect(dialog).not.toBeVisible();
  await entry.click();
  await expect(dialog).toBeVisible();

  const autoRenew = dialog.locator('#starter-trial-auto-renew');
  await expect(autoRenew).not.toBeChecked();
  await expect(dialog.locator('#starter-trial-next-charge')).toHaveText('なし');
  await expect(dialog.locator('#starter-trial-end-condition')).toHaveText(
    '自動更新せず、支払済みの1か月で終了します。'
  );

  let signup = signupParams(await dialog.locator('#starter-trial-cta').getAttribute('href'));
  expect(signup.url.hostname).toBe('app-dev.simy.one');
  expect(signup.url.pathname).toBe('/signup');
  expect(signup.params.get('offer_id')).toBe('starter_trial_v1');
  expect(signup.params.get('auto_renew')).toBe('false');
  expect(signup.params.get('plan')).toBe('starter');
  expect(signup.params.get('interval')).toBe('monthly');
  expect(signup.params.get('monthly_tokens')).toBe('80000000');
  expect(signup.params.get('seats')).toBe('1');
  expect(signup.params.get('lang')).toBe('ja');
  expect(signup.params.get('region')).toBe('jp');

  await page.screenshot({ path: 'output/playwright/starter-one-time-offer-dialog-off.png' });
  await autoRenew.check();
  await expect(dialog.locator('#starter-trial-next-charge')).toHaveText('USD 20 / 月');
  signup = signupParams(await dialog.locator('#starter-trial-cta').getAttribute('href'));
  expect(signup.params.get('auto_renew')).toBe('true');

  await dialog.screenshot({ path: 'output/playwright/starter-one-time-offer-dialog-on.png' });
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(entry).toBeFocused();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await entry.scrollIntoViewIfNeeded();
  await entry.click();
  await expect(dialog).toBeVisible();
  await expect(autoRenew).not.toBeChecked();
  await dialog.screenshot({ path: 'output/playwright/starter-one-time-offer-dialog-mobile.png' });
  await dialog.locator('#starter-trial-dialog-close').click();
  await expect(dialog).not.toBeVisible();
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
