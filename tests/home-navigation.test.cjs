const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const repoRoot = path.resolve(__dirname, "..");
const homeScript = fs.readFileSync(path.join(repoRoot, "site/home.js"), "utf8");
const homeHtml = fs.readFileSync(path.join(repoRoot, "site/index.html"), "utf8");

test("mobile navigation closes from blank and outside clicks", () => {
  assert.match(
    homeScript,
    /mobileMenu\.addEventListener\("click", \(event\) => \{\s*if \(event\.target === mobileMenu\) setMenuOpen\(false\);\s*\}\);/s,
    "clicking the empty mobile-menu surface must dismiss the menu"
  );
  assert.match(
    homeScript,
    /document\.addEventListener\("pointerdown", \(event\) => \{[\s\S]*?menuButton\.contains\(event\.target\)[\s\S]*?mobileMenu\.contains\(event\.target\)[\s\S]*?setMenuOpen\(false\);\s*\}\);/,
    "clicking outside the menu and its toggle must dismiss the menu"
  );
});

test("homepage cache-busts the current home assets", () => {
  assert.match(homeHtml, /home\.css\?v=20260907-industry-realtime-pricing-3/);
  assert.match(homeHtml, /home-locales\.js\?v=20260907-industry-realtime-pricing-3/);
  assert.match(homeHtml, /home-i18n\.js\?v=20260907-industry-realtime-pricing-3/);
  assert.match(homeHtml, /pricing-catalog\.js\?v=20260907-industry-realtime-pricing-3/);
  assert.match(homeHtml, /home\.js\?v=20260907-industry-realtime-pricing-3/);
});

test("active subpages do not route visitors into the retired Pro plan", () => {
  const subpages = ["compare.html", "privacy.html", "terms.html", "press-release.html"];
  const bundleSource = fs.readFileSync(path.join(repoRoot, "site", "lang", "i18n-bundle.js"), "utf8");
  const bundle = JSON.parse(bundleSource.replace(/^window\.SIMY_I18N_BUNDLE\s*=\s*/, "").replace(/;\s*$/, ""));

  for (const file of subpages) {
    const source = fs.readFileSync(path.join(repoRoot, "site", file), "utf8");
    assert.doesNotMatch(source, /signup\?plan=pro|data-i18n="home\.cta\.primary"|Start with Pro/);
  }

  const pressRelease = fs.readFileSync(path.join(repoRoot, "site", "press-release.html"), "utf8");
  assert.doesNotMatch(pressRelease, /data-i18n="newpress\.avail\.p"|Teams can begin with Pro/);

  for (const file of fs.readdirSync(path.join(repoRoot, "site", "lang")).filter((name) => name.endsWith(".json"))) {
    const copy = JSON.parse(fs.readFileSync(path.join(repoRoot, "site", "lang", file), "utf8"));
    const locale = file.replace(/\.json$/, "");
    assert.equal(copy["home.cta.primary"], copy["pricing.cta"], `${file} must use the neutral plan-choice CTA`);
    assert.equal(copy["newpress.avail.p"], copy["pricing.webNote"], `${file} must not advertise Pro as a course`);
    assert.equal(bundle[locale]["home.cta.primary"], copy["home.cta.primary"], `${file} CTA must match the file-preview bundle`);
    assert.equal(bundle[locale]["newpress.avail.p"], copy["newpress.avail.p"], `${file} availability must match the file-preview bundle`);
  }
});

test("homepage omits the redundant learning-control cards", () => {
  assert.doesNotMatch(homeHtml, /class="control-grid"/);
  assert.doesNotMatch(homeHtml, /Choose what SIMY can learn from\./);
  assert.doesNotMatch(homeHtml, /See exactly what SIMY kept\./);
  assert.doesNotMatch(homeHtml, /Set the guardrails once\./);
});

test("language picker follows its responsive grid and closes when focus leaves", () => {
  assert.match(
    homeScript,
    /const columns = window\.matchMedia\("\(max-width: 620px\)"\)\.matches \? 3 : 2;/,
    "arrow navigation must follow the rendered two- or three-column language grid"
  );
  assert.match(homeScript, /event\.key === 'ArrowDown' && index \+ columns < languageOptions\.length/);
  assert.match(homeScript, /event\.key === 'ArrowRight' && index % columns < columns - 1/);
  assert.match(
    homeScript,
    /languagePicker\.addEventListener\("focusout", \(\) => \{[\s\S]*?!languagePicker\.contains\(document\.activeElement\)[\s\S]*?setLanguagePickerOpen\(false\)/,
    "moving focus to the next header action must dismiss the language panel"
  );
});
