const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const repoRoot = path.resolve(__dirname, "..");
const i18nSource = fs.readFileSync(path.join(repoRoot, "site/home-i18n.js"), "utf8");
const localesSource = fs.readFileSync(path.join(repoRoot, "site/home-locales.js"), "utf8");
const homeHtml = fs.readFileSync(path.join(repoRoot, "site/index.html"), "utf8");
const homeCss = fs.readFileSync(path.join(repoRoot, "site/home.css"), "utf8");

function extractJapaneseCopy() {
  const marker = "const JA_COPY = Object.freeze(";
  const start = i18nSource.indexOf(marker) + marker.length;
  const end = i18nSource.indexOf(");", start);
  assert.ok(start >= marker.length && end > start, "JA_COPY must remain readable by the locale coverage test");
  return Function(`"use strict"; return ${i18nSource.slice(start, end)}`)();
}

function extractJapaneseSourceKeys() {
  return Object.keys(extractJapaneseCopy());
}

function loadAdditionalLocales() {
  const context = { window: {} };
  vm.createContext(context);
  vm.runInContext(localesSource, context);
  return context.window.SIMY_HOME_LOCALES;
}

const intentionallyShared = new Set([
  "My AI",
  "SIMY Autorun",
  "Codex",
  "Claude Code",
  "GitHub Copilot",
  "Google Workspace",
  "Gmail · Drive · Calendar",
  "GA4 · Search Console",
  "60m",
  "10–15m",
  "3.5–4d",
  "<24h",
  "Meeting Autorun",
  "Quality Loop"
]);

test("Hindi, Spanish, French, and Simplified Chinese cover all homepage copy", () => {
  const sourceKeys = extractJapaneseSourceKeys();
  const locales = loadAdditionalLocales();

  assert.deepEqual(Object.keys(locales), ["es", "fr", "hi", "zh-Hans"]);
  for (const [locale, copy] of Object.entries(locales)) {
    const missing = sourceKeys.filter((key) => !(key in copy) && !intentionallyShared.has(key));
    assert.deepEqual(missing, [], `${locale} is missing translated homepage copy`);
    for (const [source, translation] of Object.entries(copy)) {
      assert.equal(typeof translation, "string", `${locale}: ${source} must translate to text`);
      assert.ok(translation.trim(), `${locale}: ${source} must not have an empty translation`);
    }
  }
});

test("homepage exposes every supported language in one responsive, no-JS-safe picker", () => {
  for (const locale of ["en", "ja", "hi", "es", "fr", "zh-Hans"]) {
    assert.equal(
      homeHtml.match(new RegExp(`data-locale-option="${locale}"`, "g"))?.length,
      1,
      `${locale} must appear once in the responsive language picker`
    );
    assert.match(homeHtml, new RegExp(`hreflang="${locale}"`), `${locale} must have an hreflang link`);
  }
  assert.match(homeHtml, /<details class="language-picker"[^>]*data-language-picker>/);
  assert.match(homeHtml, /<summary class="language-trigger"[^>]*aria-label="Language: English"[^>]*data-language-trigger/);
  assert.doesNotMatch(homeHtml, /<summary class="language-trigger"[^>]*aria-expanded=/);
  assert.doesNotMatch(homeHtml, /data-language-panel[^>]*hidden/);
  assert.doesNotMatch(homeHtml, /data-locale-select/);
  assert.match(i18nSource, /option\.setAttribute\("aria-current", "true"\)/);
  assert.match(i18nSource, /trigger\.setAttribute\("aria-label", `\$\{translate\("Language"\)\}: \$\{presentation\.label\}`\)/);
  assert.match(homeCss, /\.language-trigger\s*\{[^}]*min-height:\s*2\.75rem/s);
  assert.match(
    homeCss,
    /@media \(max-width: 620px\)[\s\S]*?\.language-option-grid\s*\{[^}]*grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/s
  );
  assert.match(
    homeCss,
    /@media \(max-width: 620px\)[\s\S]*?\.language-option\s*\{[^}]*min-height:\s*3\.25rem/s
  );
});

test("locale bundle loads before the homepage translation runtime", () => {
  assert.ok(
    homeHtml.indexOf("home-locales.js") < homeHtml.indexOf("home-i18n.js"),
    "translated copy must be available before home-i18n.js applies the initial locale"
  );
});

test("existing-account login links open the SIMY app home", () => {
  const loginLinks = [...homeHtml.matchAll(/<a\b[^>]*data-existing-account-login[^>]*>/g)];

  assert.equal(loginLinks.length, 4, "desktop header, mobile header, final CTA, and footer must expose login");
  for (const [link] of loginLinks) {
    assert.match(link, /href="https:\/\/app\.simy\.one\/"/);
  }
  assert.doesNotMatch(homeHtml, /https:\/\/app\.simy\.one\/login(?:[?"'])/);
});

test("pricing gives Starter unlimited Autorun, free trials, and a truthful Enterprise inquiry", () => {
  const pricingSection = homeHtml.match(/<section class="pricing[\s\S]*?<\/section>/)?.[0];
  assert.ok(pricingSection, "pricing section must remain present");

  const planHeaders = Object.fromEntries(
    [...pricingSection.matchAll(/<th[^>]*data-pricing-plan="(starter|quality|pro)"[^>]*>([\s\S]*?)<\/th>/g)]
      .map(([, plan, content]) => [plan, content])
  );
  assert.deepEqual(Object.keys(planHeaders), ["starter", "quality", "pro"]);
  assert.match(planHeaders.starter, /pricing-trial">1 month free</);
  assert.match(planHeaders.quality, /pricing-trial">1 month free</);
  assert.doesNotMatch(planHeaders.pro, /pricing-trial/);
  assert.equal(pricingSection.match(/pricing-trial">1 month free</g)?.length, 2);
  assert.equal(
    pricingSection.match(/class="pricing-badge-stack"/g)?.length,
    4,
    "every plan header must reserve the same in-flow badge area"
  );

  const autorunRow = pricingSection.match(/<th scope="row">Autorun allowance<\/th>([\s\S]*?)<\/tr>/)?.[1];
  assert.ok(autorunRow, "Autorun allowance row must remain present");
  assert.equal(autorunRow.match(/pricing-value">Unlimited</g)?.length, 3);
  assert.match(autorunRow, /pricing-value pricing-value-custom">Tailored</);
  assert.doesNotMatch(homeHtml, /100 runs/);

  assert.match(pricingSection, /<th class="pricing-enterprise" scope="col">/);
  assert.match(pricingSection, /pricing-enterprise-price">Custom pricing</);
  assert.match(pricingSection, /href="mailto:sales@simy\.one">Talk to us about Enterprise/);
  assert.match(pricingSection, /Enterprise rollout/);
  assert.match(pricingSection, /Security and rollout support/);
  assert.doesNotMatch(pricingSection, /pricing-value pricing-value-custom">Contact us/);
  const pricingRows = [...pricingSection.matchAll(/<tbody>[\s\S]*?<\/tbody>/g)]
    .flatMap(([body]) => [...body.matchAll(/<tr>([\s\S]*?)<\/tr>/g)])
    .map(([, row]) => row);
  assert.ok(pricingRows.length > 0, "pricing comparison must keep its feature rows");
  for (const row of pricingRows) {
    assert.equal(row.match(/<td\b/g)?.length, 4, "each feature row must align across all four plans");
  }

  const enterpriseIncludedFeatures = [
    "Codex account connection",
    "Meeting Autorun",
    "Save and reuse Pipelines",
    "Use your connected ChatGPT plan",
    "Quality Loop",
    "Target error rate ≤3%",
    "Hearing Mode",
    "Real-time suggestions",
    "Logical database isolation by organization"
  ];
  for (const feature of enterpriseIncludedFeatures) {
    const row = pricingRows.find((content) => content.includes(feature));
    assert.ok(row, `${feature} must remain in the pricing comparison`);
    const cells = [...row.matchAll(/<td\b[^>]*>([\s\S]*?)<\/td>/g)].map(([, content]) => content);
    assert.match(cells.at(-1), /pricing-status pricing-status-included/, `${feature} must be available in Enterprise`);
  }

  const locales = { ja: extractJapaneseCopy(), ...loadAdditionalLocales() };
  for (const [locale, copy] of Object.entries(locales)) {
    assert.ok(copy["1 month free"]?.trim(), `${locale} must localize the one-month offer`);
    assert.notEqual(copy["1 month free"], "1 month free", `${locale} must not reuse the English offer`);
    for (const key of ["Custom pricing", "Talk to us about Enterprise", "Tailored", "Logical database isolation by organization"]) {
      assert.ok(copy[key]?.trim(), `${locale} must localize ${key}`);
    }
  }
});

test("pricing decision copy remains visibly larger than disclaimer typography", () => {
  const minimumRemBySelector = new Map([
    [".pricing-saving", 0.75],
    [".pricing-period", 0.78],
    [".pricing-tax-mode,\n.pricing-total,\n.pricing-tax-included-price", 0.72],
    [".pricing-popular", 0.78],
    [".pricing-trial", 0.78],
    [".pricing-enterprise-copy", 0.76],
    [".pricing-enterprise-link", 0.76],
    [".pricing-status", 0.74]
  ]);

  for (const [selector, minimumRem] of minimumRemBySelector) {
    const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const block = homeCss.match(new RegExp(`${escapedSelector}\\s*\\{([^}]*)\\}`))?.[1];
    assert.ok(block, `${selector} must remain styled`);
    const fontSize = Number(block.match(/font-size:\s*([0-9.]+)rem/)?.[1]);
    assert.ok(
      fontSize >= minimumRem,
      `${selector} must use at least ${minimumRem}rem so offer and billing terms do not look like hidden disclaimers`
    );
  }

  assert.match(
    homeCss,
    /\.pricing-badge-stack\s*\{[^}]*display:\s*flex;[^}]*min-height:\s*4\.75rem;[^}]*flex-direction:\s*column;/s,
    "plan badges must use one shared vertical flow instead of language-sensitive absolute placement"
  );
  for (const selector of [".pricing-popular", ".pricing-trial"]) {
    const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const block = homeCss.match(new RegExp(`${escapedSelector}\\s*\\{([^}]*)\\}`))?.[1];
    assert.doesNotMatch(block, /position:\s*absolute/, `${selector} must stay in the badge stack flow`);
  }
  assert.doesNotMatch(homeHtml, /pricing-enterprise-badge/, "Enterprise must not show a redundant inquiry badge above its heading");
});

test("header exposes direct login and signup actions outside the mobile menu", () => {
  assert.match(
    homeHtml,
    /<div class="nav-actions">[\s\S]*?data-existing-account-login[\s\S]*?data-new-account-signup[\s\S]*?<\/div>/,
    "login and signup must remain visible in the page header"
  );
  assert.match(
    homeHtml,
    /<div class="site-frame mobile-auth-actions"[^>]*>[\s\S]*?data-existing-account-login[\s\S]*?data-new-account-signup[\s\S]*?<\/div>/,
    "mobile login and signup must follow the menu button in logical focus order"
  );
  const signupLinks = [...homeHtml.matchAll(/<a\b[^>]*data-new-account-signup[^>]*>/g)];
  assert.equal(signupLinks.length, 2, "desktop and mobile headers must expose signup");
  for (const [link] of signupLinks) {
    assert.match(link, /href="https:\/\/app\.simy\.one\/signup\?lang=en&amp;locale=en&amp;region=us"/);
  }
  assert.doesNotMatch(
    homeHtml,
    /<nav class="mobile-menu"[\s\S]*?(?:data-existing-account-login|data-new-account-signup)[\s\S]*?<\/nav>/,
    "auth actions must not be duplicated behind the hamburger menu"
  );
  assert.match(
    homeCss,
    /@media \(max-width: 620px\)[\s\S]*?\.mobile-auth-actions\s*\{[^}]*display:\s*grid;[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\);/s,
    "narrow screens must show login and signup in a full-width header row"
  );
});

test("connected apps feature the three AI coding tools without disturbing the work-apps grid", () => {
  for (const [className, productName] of [
    ["app-codex", "Codex"],
    ["app-claude", "Claude Code"],
    ["app-copilot", "GitHub Copilot"]
  ]) {
    assert.match(
      homeHtml,
      new RegExp(`<li class="app-tile ${className}">[\\s\\S]*?<strong>${productName}</strong>`),
      `${productName} must appear in the connected-apps section`
    );
  }

  assert.match(homeHtml, /<ul class="apps-grid apps-grid-ai"[^>]*>[\s\S]*?<\/ul>/);
  assert.match(homeCss, /\.apps-grid-ai\s*\{[^}]*grid-template-columns:\s*repeat\(3,/s);
  assert.match(homeCss, /@media \(max-width: 620px\)[\s\S]*?\.apps-grid-ai\s*\{[^}]*grid-template-columns:\s*1fr/s);
});

test("all section-level messages share one responsive typography role", () => {
  const sectionHeadingIds = [
    "product-title",
    "codex-title",
    "method-title",
    "connected-apps-title",
    "use-cases-title",
    "comparison-title",
    "pricing-title",
    "final-title"
  ];

  for (const id of sectionHeadingIds) {
    assert.match(
      homeHtml,
      new RegExp(`<h2 class="section-heading" id="${id}">`),
      `${id} must use the shared section-heading role`
    );
  }

  assert.match(homeCss, /\.section-heading\s*\{[^}]*font-size:\s*var\(--type-section-heading\)/s);
  assert.match(homeCss, /h1,\s*h2,\s*h3\s*\{[^}]*text-wrap:\s*balance/s);
  assert.doesNotMatch(homeCss, /\.final-copy h2\s*\{[^}]*font-size:/s);
});

test("use-case metrics size themselves from the card instead of the viewport", () => {
  assert.match(homeCss, /\.use-case-card\s*\{[^}]*container-type:\s*inline-size/s);
  assert.match(
    homeCss,
    /\.case-metric\s*>\s*div\s*\{[^}]*grid-template-columns:\s*repeat\(3,\s*max-content\)[^}]*gap:\s*clamp\([^;]*cqi/s
  );
  assert.match(
    homeCss,
    /\.case-metric b,\s*\.case-metric strong\s*\{[^}]*font-size:\s*clamp\([^;]*cqi/s
  );
  assert.equal(
    homeHtml.match(/class="case-metric case-metric-wide"/g)?.length,
    2,
    "the two copy-dense metrics must use the compact, container-aware size"
  );
  const metricPattern = (className, metric) => new RegExp(
    `<div class="${className}">\\s*<span class="sr-only">[\\s\\S]*?</span>\\s*<div aria-hidden="true"><b>${metric.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}</b>`
  );
  for (const metric of ["60m", "3.5–4d"]) {
    assert.match(
      homeHtml,
      metricPattern("case-metric case-metric-wide", metric),
      `${metric} must use the copy-dense metric treatment`
    );
  }
  for (const metric of ["1/5", "1.0×"]) {
    assert.match(
      homeHtml,
      metricPattern("case-metric", metric),
      `${metric} must retain the large metric treatment`
    );
  }
  assert.doesNotMatch(
    homeCss,
    /\.case-metric (?:b|strong)[^{]*\{[^}]*font-size:\s*clamp\([^;]*vw/s,
    "metric values must not grow from the full viewport width"
  );
});

test("keeps Traditional Chinese distinct and omits unsupported China region", () => {
  assert.doesNotMatch(i18nSource, /locale\.startsWith\("zh-"\)/);
  assert.match(i18nSource, /\["zh", "zh-cn", "zh-sg", "zh-hans"\]/);
  assert.doesNotMatch(i18nSource, /region: "cn"/);
});

test("protects the global editorial message in every locale", () => {
  const locales = { ja: extractJapaneseCopy(), ...loadAdditionalLocales() };
  const editorialKeys = [
    "Bring in the conversations that matter. SIMY learns the checks, priorities, and non-negotiables behind your best work, turns them into focused Pipelines, and selects the right one automatically. Autorun takes it from there.",
    "Choose the conversations that reveal your checks, priorities, and non-negotiables. SIMY extracts the patterns that repeat, separates them from one-off detail, and ignores the rest.",
    "Your conversations become the way work gets done.",
    "SIMY finds the missing inputs, the right people, and the next move. Autorun handles the sequence, so the work keeps moving until your attention is actually needed.",
    "General agents complete tasks.",
    "SIMY preserves your way of working.",
    "Make every Autorun earn your confidence.",
    "Tell SIMY what needs to move.",
    "Autorun takes it from there."
  ];

  for (const key of editorialKeys) {
    assert.ok(homeHtml.includes(key), `live HTML must include the editorial message: ${key}`);
    assert.ok(i18nSource.includes(JSON.stringify(key)), `JA_COPY must include the editorial message: ${key}`);
    for (const [locale, copy] of Object.entries(locales)) {
      assert.ok(copy[key]?.trim(), `${locale} must include the editorial message: ${key}`);
      assert.notEqual(copy[key], key, `${locale} must localize the editorial message: ${key}`);
    }
  }

  for (const retired of [
    "No agent or pipeline to choose",
    "You ask. SIMY selects the pipeline. Autorun gets to work.",
    "A general agent can do the task.",
    "Put a Quality Loop around every Autorun.",
    "Choose the conversations that reveal your standards. SIMY extracts the patterns that repeat, separates them from one-off detail, and ignores the rest."
  ]) {
    assert.ok(!homeHtml.includes(retired), `live HTML must retire: ${retired}`);
    assert.ok(!i18nSource.includes(JSON.stringify(retired)), `JA_COPY must retire: ${retired}`);
    assert.ok(!localesSource.includes(JSON.stringify(retired)), `locale copy must retire: ${retired}`);
  }
});
