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
const homeScript = fs.readFileSync(path.join(repoRoot, "site/home.js"), "utf8");

test("Japanese user-facing copy describes checks without internal evidence jargon", () => {
  const japaneseCopy = extractJapaneseCopy();
  assert.equal(japaneseCopy["Verify the evidence"], "事実を確かめる");
  assert.equal(
    japaneseCopy["Prepare the evidence for the next decision."],
    "次の判断に必要な情報を揃える。"
  );
  assert.equal(japaneseCopy["Proof where we have it."], "実績は、確認済みの数字で。");

  const userFacingJapaneseSources = [
    i18nSource,
    fs.readFileSync(path.join(repoRoot, "site/lang/ja.json"), "utf8"),
    fs.readFileSync(path.join(repoRoot, "site/lang/i18n-bundle.js"), "utf8"),
    fs.readFileSync(path.join(repoRoot, "site/old/index.html"), "utf8"),
    fs.readFileSync(path.join(repoRoot, "site/old/lang/ja.json"), "utf8")
  ];
  for (const source of userFacingJapaneseSources) {
    assert.doesNotMatch(source, /根拠/);
  }
});

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

test("company overview links directly to AwakApp company information", () => {
  assert.match(
    homeHtml,
    /<a data-company-overview href="https:\/\/www\.awak\.app\/#company">Company overview<\/a>/,
    "the SIMY footer must take visitors directly to the parent-company overview"
  );

  const locales = { ja: extractJapaneseCopy(), ...loadAdditionalLocales() };
  for (const [locale, copy] of Object.entries(locales)) {
    assert.ok(copy["Company overview"]?.trim(), `${locale} must localize the company overview link`);
  }
});

test("pricing reflects the active signup plans and localizes the decision", () => {
  const pricingSection = homeHtml.match(/<section class="pricing[\s\S]*?<\/section>/)?.[0];
  assert.ok(pricingSection);
  assert.deepEqual(
    [...pricingSection.matchAll(/data-pricing-plan="([^"]+)"/g)].map((match) => match[1]),
    ["starter", "pro", "team"]
  );
  assert.doesNotMatch(pricingSection, /data-billing-cycle|1 month free|SIMY by Industry|pricing-realtime-addon/);
  assert.match(pricingSection, /100 \/ month/);
  assert.match(pricingSection, /Maximum users/);
  assert.match(pricingSection, /mailto:sales@simy\.one/);

  const locales = { ja: extractJapaneseCopy(), ...loadAdditionalLocales() };
  const keys = [
    "Simple monthly pricing",
    "Choose the plan that fits your work.",
    "Choose Starter, Pro, or Team. Select an industry package during signup; it does not change the plan price.",
    "Plans are billed monthly in USD. Prices below exclude applicable taxes.",
    "Maximum users",
    "Choose Starter plan",
    "Choose Pro plan",
    "Choose Team plan"
  ];
  for (const [locale, copy] of Object.entries(locales)) {
    for (const key of keys) {
      assert.ok(copy[key]?.trim(), locale + " must localize " + key);
    }
  }
});

test("pricing decision copy remains visibly larger than disclaimer typography", () => {
  const minimumRemBySelector = new Map([
    [".pricing-period", 0.78],
    [".pricing-tax-mode,\n.pricing-tax-included-price", 0.72],
    [".pricing-popular", 0.78],
    [".pricing-plan-link", 0.8]
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
  for (const selector of [".pricing-popular", ".pricing-plan-link"]) {
    const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const block = homeCss.match(new RegExp(`${escapedSelector}\\s*\\{([^}]*)\\}`))?.[1];
    assert.doesNotMatch(block, /position:\s*absolute/, `${selector} must stay in the badge stack flow`);
  }
  assert.match(homeCss, /\.pricing-team\s+\.pricing-plan-link\s*\{[^}]*background:\s*#fff;/s);
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
    "Bring in the conversations that matter. SIMY learns the checks, priorities, and non-negotiables behind your best work, turns them into focused Workflows, and selects the right one automatically. Autorun takes it from there.",
    "Choose the conversations that reveal your checks, priorities, and non-negotiables. SIMY extracts the patterns that repeat, separates them from one-off detail, and ignores the rest.",
    "Your conversations become the way work gets done.",
    "SIMY finds the missing inputs, the right people, and the next move. Autorun handles the sequence, so the work keeps moving until your attention is actually needed.",
    "General agents complete tasks.",
    "SIMY preserves your way of working.",
    "Choose the plan that fits your work.",
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
    "No agent or workflow to choose",
    "You ask. SIMY selects the workflow. Autorun gets to work.",
    "A general agent can do the task.",
    "Put a Quality Loop around every Autorun.",
    "Choose the conversations that reveal your standards. SIMY extracts the patterns that repeat, separates them from one-off detail, and ignores the rest."
  ]) {
    assert.ok(!homeHtml.includes(retired), `live HTML must retire: ${retired}`);
    assert.ok(!i18nSource.includes(JSON.stringify(retired)), `JA_COPY must retire: ${retired}`);
    assert.ok(!localesSource.includes(JSON.stringify(retired)), `locale copy must retire: ${retired}`);
  }
});

test("all published product copy calls pipelines workflows", () => {
  const legacyTerms = /\bpipelines?\b|パイプライン|पाइपलाइन|管线|流水线|流水線|파이프라인|خط أنابيب|ಪೈಪ್‌ಲೈನ್|పైప్‌లైన్|ท่อส่ง|Конвейер/iu;
  const copySources = {
    "site/index.html": homeHtml,
    "site/home-i18n.js": i18nSource,
    "site/home-locales.js": localesSource,
    "site/home.js": homeScript,
    "site/lang/i18n-bundle.js": fs.readFileSync(path.join(repoRoot, "site/lang/i18n-bundle.js"), "utf8")
  };

  for (const directory of ["site/lang", "site/old/lang"]) {
    for (const file of fs.readdirSync(path.join(repoRoot, directory)).filter((name) => name.endsWith(".json"))) {
      copySources[`${directory}/${file}`] = fs.readFileSync(path.join(repoRoot, directory, file), "utf8");
    }
  }

  for (const [file, source] of Object.entries(copySources)) {
    assert.doesNotMatch(source, legacyTerms, `${file} must not expose legacy pipeline terminology`);
  }

  const locales = { ja: extractJapaneseCopy(), ...loadAdditionalLocales() };
  assert.equal(locales.ja.WORKFLOW, "ワークフロー");
  assert.equal(locales.hi.WORKFLOW, "वर्कफ़्लो");
  assert.equal(locales["zh-Hans"].WORKFLOW, "工作流");
  for (const [locale, copy] of Object.entries(locales)) {
    assert.ok(copy["Save and reuse Workflows"]?.trim(), `${locale} must localize the Workflow pricing feature`);
  }

  for (const file of [
    "site/assets/index-DnVveaIK.js",
    "site/assets/index-DnVveaIK.js.bak",
    "site/old/assets/index-DnVveaIK.js",
    "site/old/assets/index-DnVveaIK.js.bak"
  ]) {
    const demoBundle = fs.readFileSync(path.join(repoRoot, file), "utf8");
    assert.match(demoBundle, /"View Workflow Progress"/, `${file} must expose Workflow progress`);
    assert.match(demoBundle, /children:"Workflow Progress"/, `${file} must label Workflow progress`);
    assert.doesNotMatch(
      demoBundle,
      /"View Pipeline Progress"|children:"Pipeline Progress"|"Showing pipeline progress"/,
      `${file} must not expose legacy Pipeline progress copy`
    );
  }
});
