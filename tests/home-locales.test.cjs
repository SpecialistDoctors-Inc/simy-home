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

test("homepage exposes every supported language in both selectors and hreflang metadata", () => {
  for (const locale of ["en", "ja", "hi", "es", "fr", "zh-Hans"]) {
    assert.equal(
      homeHtml.match(new RegExp(`data-locale-select[\\s\\S]*?<option value="${locale}" lang="${locale}"`, "g"))?.length,
      2,
      `${locale} must appear in the desktop and mobile language selectors`
    );
    assert.match(homeHtml, new RegExp(`hreflang="${locale}"`), `${locale} must have an hreflang link`);
  }
});

test("locale bundle loads before the homepage translation runtime", () => {
  assert.ok(
    homeHtml.indexOf("home-locales.js") < homeHtml.indexOf("home-i18n.js"),
    "translated copy must be available before home-i18n.js applies the initial locale"
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
