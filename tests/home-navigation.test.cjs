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

test("homepage cache-busts the current navigation behavior", () => {
  assert.match(homeHtml, /home\.css\?v=20260828-direct-auth-1/);
  assert.match(homeHtml, /home-locales\.js\?v=20260828-direct-auth-1/);
  assert.match(homeHtml, /home-i18n\.js\?v=20260828-direct-auth-1/);
  assert.match(homeHtml, /home\.js\?v=20260828-direct-auth-1/);
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
