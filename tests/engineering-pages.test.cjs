const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const test = require("node:test");
const root = path.resolve(__dirname, "..");

test("published engineering pages match their reviewed content source", () => {
  execFileSync("python3", ["scripts/build-engineering-pages.py", "--check"], {
    cwd: root,
  });
});

test("every raw homepage exposes a working engineering destination in its supported language", () => {
  for (const locale of ["en", "ja", "es", "fr", "hi", "zh-Hans"]) {
    const home = fs.readFileSync(
      path.join(
        root,
        "site",
        locale === "en" ? "index.html" : `${locale}.html`,
      ),
      "utf8",
    );
    const destination =
      locale === "ja" ? "for/engineers/" : "for/en/engineers/";
    const links = [...home.matchAll(/href="(\/for\/(?:en\/)?engineers\/)"/g)].map(
      (match) => match[1],
    );
    assert.ok(
      links.length >= 3,
      `${locale} has navigation, feature and footer entry points`,
    );
    assert.ok(links.every((href) => href === `/${destination}`));
    const page = fs.readFileSync(path.join(root, "site", destination, "index.html"), "utf8");
    assert.match(
      page,
      new RegExp(`<html lang="${locale === "ja" ? "ja" : "en"}">`),
    );
    assert.ok(page.includes(`href="https://simy.one/${destination}"`));
  }
});
