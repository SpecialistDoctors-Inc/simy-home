const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const repoRoot = path.resolve(__dirname, "..");
const homeScript = fs.readFileSync(path.join(repoRoot, "site/home.js"), "utf8");
const homeHtml = fs.readFileSync(path.join(repoRoot, "site/index.html"), "utf8");
const homeCss = fs.readFileSync(path.join(repoRoot, "site/home.css"), "utf8");

test("shared navigation owns outside-click dismissal", () => {
  const shared = fs.readFileSync(path.join(repoRoot, "site/shared-header.js"), "utf8");
  assert.match(shared, /document.addEventListener\('pointerdown'/);
  assert.match(shared, /!details.contains\(event.target\)/);
  assert.doesNotMatch(homeScript, /data-menu-button|data-language-picker/);
});

test("homepage cache-busts the current home assets", () => {
  assert.match(homeHtml, /home\.css\?v=20261004-theme-1/);
  assert.match(homeHtml, /home-locales\.js\?v=20261004-url-plan-1/);
  assert.match(homeHtml, /home-i18n\.js\?v=20261004-shared-header-1/);
  assert.match(homeHtml, /pricing-catalog\.js\?v=20260907-industry-realtime-pricing-3/);
  assert.match(homeHtml, /home\.js\?v=20261004-shared-header-1/);
});

test("pricing call to action opens the signup plan selection page", () => {
  assert.match(homeHtml, /data-billing-cycle="annual"/);
  assert.match(homeHtml, /data-billing-cycle="monthly"/);
  assert.match(homeHtml, /data-pricing-plan="quality"/);
  assert.match(homeHtml, /<th scope="col" data-pricing-plan="starter">[\s\S]*?<a class="pricing-plan-link"[^>]*>Choose a plan/);
  assert.match(homeHtml, /<th class="pricing-quality" scope="col" data-pricing-plan="quality">[\s\S]*?<a class="pricing-plan-link"[^>]*>Choose a plan/);
  assert.equal((homeHtml.match(/href="https:\/\/app\.simy\.one\/signup\/\?plan=(starter|quality)&amp;interval=annual&amp;lang=en&amp;locale=en&amp;region=us" aria-label="Choose a plan"/g) || []).length, 2);
});

test("pages loading the demo bundle cache-bust its workflow terminology", () => {
  const pages = ["contact.html"];
  for (const directory of ["site", "site/old"]) {
    for (const page of pages) {
      const source = fs.readFileSync(path.join(repoRoot, directory, page), "utf8");
      assert.match(
        source,
        /\/assets\/index-DnVveaIK\.js\?v=20260915-workflow-terminology-1/,
        `${directory}/${page} must load the updated workflow terminology bundle`
      );
    }
  }

  const publishedBackup = fs.readFileSync(path.join(repoRoot, "site/index.html.bak"), "utf8");
  assert.match(publishedBackup, /\/assets\/index-DnVveaIK\.js\?v=20260915-workflow-terminology-1/);
});

test("Realtime add-on keeps the currency symbol in the price line", () => {
  assert.match(
    homeCss,
    /\.pricing-realtime-price > strong \{[^}]*display: inline-flex;[^}]*align-items: center;/s,
    "the plus sign, currency symbol, and amount must share one centered price line"
  );
  assert.match(
    homeCss,
    /\.pricing-realtime-price > strong small \{[^}]*font-size: 0\.56em;[^}]*line-height: 1;/s
  );
  assert.doesNotMatch(
    homeCss,
    /\.pricing-realtime-price > strong small \{[^}]*vertical-align: top;/s,
    "the currency symbol must not render as a superscript"
  );
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

test("shared disclosure restores focus on Escape and closes when focus leaves", () => {
  const shared = fs.readFileSync(path.join(repoRoot, "site/shared-header.js"), "utf8");
  assert.match(shared, /event.key === 'Escape'/);
  assert.match(shared, /close\(details, true\)/);
  assert.match(shared, /!details.contains\(document.activeElement\)/);
});
