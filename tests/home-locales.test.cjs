const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const repoRoot = path.resolve(__dirname, "..");
const i18nSource = fs.readFileSync(path.join(repoRoot, "site/home-i18n.js"), "utf8");
const localesSource = fs.readFileSync(path.join(repoRoot, "site/home-locales.js"), "utf8");
const homeHtml = fs.readFileSync(path.join(repoRoot, "site/index.html"), "utf8");

function extractJapaneseSourceKeys() {
  const marker = "const JA_COPY = Object.freeze(";
  const start = i18nSource.indexOf(marker) + marker.length;
  const end = i18nSource.indexOf(");", start);
  assert.ok(start >= marker.length && end > start, "JA_COPY must remain readable by the locale coverage test");
  return Object.keys(Function(`"use strict"; return ${i18nSource.slice(start, end)}`)());
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

test("keeps Traditional Chinese distinct and omits unsupported China region", () => {
  assert.doesNotMatch(i18nSource, /locale\.startsWith\("zh-"\)/);
  assert.match(i18nSource, /\["zh", "zh-cn", "zh-sg", "zh-hans"\]/);
  assert.doesNotMatch(i18nSource, /region: "cn"/);
});
