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
      locale === "ja" ? "for/engineers/" : `for/${locale.toLowerCase()}/engineers/`;
    const links = [...home.matchAll(/href="(\/for\/(?:(?:en|es|fr|hi|zh-hans)\/)?engineers\/)"/g)].map(
      (match) => match[1],
    );
    assert.ok(
      links.length >= 2,
      `${locale} has shared navigation and content entry points`,
    );
    assert.ok(links.every((href) => href === `/${destination}`));
    const page = fs.readFileSync(path.join(root, "site", destination, "index.html"), "utf8");
    assert.match(
      page,
      new RegExp(`<html lang="${locale}">`),
    );
    assert.ok(page.includes(`href="https://simy.one/${destination}"`));
  }
});

test("engineering captures and full-size links use the page language", () => {
  const copy = JSON.parse(fs.readFileSync(path.join(root, "scripts/engineering-experience.json"), "utf8"));
  for (const lang of ["ja", "en", "es", "fr", "hi", "zh-Hans"]) {
    const route = lang === "ja" ? "for/engineers/" : `for/${lang.toLowerCase()}/engineers/`;
    const html = fs.readFileSync(path.join(root, "site", route, "index.html"), "utf8");
    const images = [...html.matchAll(/<img src="(\/assets\/engineer-experience\/[^\"]+)" width="(\d+)" height="(\d+)" alt="([^\"]+)"/g)];
    assert.equal(images.length, 9);
    const expected = copy[lang].scenes.flatMap(scene => scene.frames.map(frame => frame.image));
    assert.deepEqual(images.map(match => path.basename(match[1])), expected);
    for (const [, url, width, height, alt] of images) {
      assert.equal(url.endsWith(lang === "ja" ? ".png" : `-${lang}.png`), true, `${lang}: ${url}`);
      if (lang === "ja") assert.doesNotMatch(url, /-(en|es|fr|hi|zh-Hans)\.png$/);
      const bytes = fs.readFileSync(path.join(root, "site", url));
      assert.equal(bytes.readUInt32BE(16), Number(width));
      assert.equal(bytes.readUInt32BE(20), Number(height));
      assert.ok(html.includes(`class="capture-zoom" href="${url}"`));
      assert.ok(html.includes(`href="${url}" target="_blank" rel="noopener"`));
      if (lang === "en") {
        assert.doesNotMatch(alt, /Japanese|[\u3040-\u30ff\u3400-\u9fff]/u);
      }
    }
  }
});

test("localized illustrations preserve provenance, sample-data limits and asset integrity", () => {
  const html = fs.readFileSync(path.join(root, "site/for/en/engineers/index.html"), "utf8");
  assert.match(html, /Localized illustrations adapted from Quality Monitor implementation test captures with fixed synthetic data/);
  assert.doesNotMatch(html, /Screens shown in Japanese/);
  assert.match(html, /Not production results or complete live SQM integration/);
  const manifest = JSON.parse(fs.readFileSync(path.join(root, "docs/engineer-wow/asset-manifest.json"), "utf8"));
  for (const asset of manifest.filter(asset => /^(threads|quality)-.+-(en|es|fr|hi|zh-Hans)\.png$/.test(asset.file))) {
    const bytes = fs.readFileSync(path.join(root, "site/assets/engineer-experience", asset.file));
    assert.equal(require("node:crypto").createHash("sha256").update(bytes).digest("hex"), asset.sha256);
  }
  for (const lang of ["ja", "en", "es", "fr", "hi", "zh-Hans"]) {
    const asset = manifest.find(asset => asset.file === `social-${lang}.png`);
    assert.ok(asset, `social card manifest: ${lang}`);
    const bytes = fs.readFileSync(path.join(root, "site/assets/engineer-experience", asset.file));
    assert.equal(bytes.readUInt32BE(16), 1200);
    assert.equal(bytes.readUInt32BE(20), 630);
    assert.equal(require("node:crypto").createHash("sha256").update(bytes).digest("hex"), asset.sha256);
  }
  assert.equal(manifest.filter(asset => /^(threads|quality)-.+-(en|es|fr|hi|zh-Hans)\.png$/.test(asset.file)).length, 25);
});

test('manga and mechanism images use dedicated assets in every translated page', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'scripts/engineering-manga-assets.json'), 'utf8'));
  for (const lang of ['en','es','fr','hi','zh-Hans']) {
    const html = fs.readFileSync(path.join(root,'site/for',lang.toLowerCase(),'engineers/index.html'),'utf8');
    assert.equal((html.match(/class="manga-panel"/g)||[]).length,8);
    assert.equal((html.match(/class="mechanism-image"/g)||[]).length,3);
    assert.ok(html.includes('class="manga-more"'));
    for (const asset of Object.values(manifest[lang])) {
      assert.ok(asset.url.endsWith(`-${lang}.webp`));
      assert.ok(html.includes(asset.url));
      assert.ok(html.includes(`width="${asset.width}" height="${asset.height}"`));
      assert.ok(fs.statSync(path.join(root,'site',asset.url)).size > 10000);
    }
    assert.doesNotMatch(html, /release-crew-ja\.webp|delivery-team\.webp|rules-application\.webp|systems-application\.webp/);
  }
});
