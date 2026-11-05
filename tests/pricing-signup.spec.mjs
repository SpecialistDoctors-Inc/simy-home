import { expect, test } from '@playwright/test';

// Serve repository bytes at each simulated host; no external signup or payment requests.
for (const [host, appHost] of [['simy.one', 'app.simy.one'], ['dev.simy.one', 'app-dev.simy.one']]) {
  test(`application destination and locale survive language changes on ${host}`, async ({ page }) => {
    await page.route('**/*', async (route) => {
      const url = new URL(route.request().url());
      if (url.hostname !== host) return route.abort();
      try {
        await route.fulfill({ path: new URL(`../site${url.pathname === '/' ? '/index.html' : url.pathname}`, import.meta.url).pathname });
      } catch {
        await route.abort();
      }
    });
    await page.goto(`https://${host}/?lang=ja`);
    await page.locator('[data-billing-cycle="monthly"]').click();
    for (const [lang, region] of [['en', 'us'], ['ja', 'jp'], ['hi', 'in'], ['es', 'es'], ['fr', 'fr'], ['zh-Hans', null]]) {
      await page.locator('[data-language-trigger]').click();
      await page.locator(`[data-locale-option="${lang}"]`).click();
      for (const plan of ['starter', 'quality']) {
        const href = await page.locator(`[data-pricing-plan="${plan}"] .pricing-plan-link`).getAttribute('href');
        const url = new URL(href);
        expect(url.hostname).toBe(appHost);
        expect(url.searchParams.get('plan')).toBe(plan);
        expect(url.searchParams.get('interval')).toBe('monthly');
        expect(url.searchParams.get('lang')).toBe(lang);
        expect(url.searchParams.get('locale')).toBe(lang);
        expect(url.searchParams.get('region')).toBe(region);
      }
    }
  });
}

for (const width of [390, 1280]) {
  for (const language of ['ja', 'en']) {
    test(`table handoff preserves prices and selection: ${language}, ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(`/?lang=${language}`);
      for (const interval of ['monthly', 'annual']) {
        await page.locator(`[data-billing-cycle="${interval}"]`).click();
        for (const [plan, monthly, annual] of [['starter', 35.8, 29.8], ['quality', 71.8, 59.8]]) {
          const column = page.locator(`[data-pricing-plan="${plan}"]`);
          const price = interval === 'annual' ? annual : monthly;
          await expect(column.locator('[data-price-amount]')).toHaveText(String(price));
          const href = await column.locator('.pricing-plan-link').getAttribute('href');
          const url = new URL(href);
          expect(url.hostname).toBe('app-dev.simy.one');
          expect(url.pathname).toBe('/signup/');
          expect(url.searchParams.get('plan')).toBe(plan);
          expect(url.searchParams.get('interval')).toBe(interval);
          expect(url.searchParams.get('lang')).toBe(language);
          expect(url.searchParams.get('locale')).toBe(language);
          expect(url.searchParams.get('region')).toBe(language === 'ja' ? 'jp' : 'us');
        }
      }
    });
  }
}

test('language switch preserves the selected monthly contract', async ({ page }) => {
  await page.goto('/?lang=ja');
  await page.locator('[data-billing-cycle="monthly"]').click();
  await page.locator('[data-language-trigger]').click();
  await page.locator('[data-locale-option="en"]').click();
  await expect(page.locator('[data-billing-cycle="monthly"]')).toHaveAttribute('aria-pressed', 'true');
  for (const plan of ['starter', 'quality']) {
    const href = await page.locator(`[data-pricing-plan="${plan}"] .pricing-plan-link`).getAttribute('href');
    const url = new URL(href);
    expect(url.hostname).toBe('app-dev.simy.one');
    expect(Object.fromEntries(url.searchParams)).toMatchObject({ plan, interval: 'monthly', lang: 'en', locale: 'en', region: 'us' });
  }
});
