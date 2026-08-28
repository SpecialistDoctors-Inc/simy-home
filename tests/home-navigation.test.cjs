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

test("homepage cache-busts the menu dismissal behavior", () => {
  assert.match(homeHtml, /home\.js\?v=20260828-menu-dismiss-1/);
});
