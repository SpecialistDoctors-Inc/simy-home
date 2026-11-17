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

test("translated engineering captures and full-size links use the page language", () => {
  const copy = JSON.parse(fs.readFileSync(path.join(root, "scripts/engineering-experience.json"), "utf8"));
  for (const lang of ["es", "fr", "hi", "zh-Hans"]) {
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

test("Japanese CLI page uses current native captures and preserves their provenance", () => {
  const html = fs.readFileSync(path.join(root, "site/for/engineers/index.html"), "utf8");
  const manifest = JSON.parse(fs.readFileSync(path.join(root, "site/assets/cli-ui/manifest.json"), "utf8"));
  assert.equal(manifest.version, "1.2.8");
  const images = [...html.matchAll(/<img src="(\/assets\/cli-ui\/(?:overview|goal|sqm|connection|usage)\.png)" width="(\d+)" height="(\d+)"[^>]+alt="([^\"]+)"/g)];
  assert.equal(images.length, 5);
  for (const [, url, width, height, alt] of images) {
    const bytes = fs.readFileSync(path.join(root, "site", url));
    assert.equal(bytes.readUInt32BE(16), Number(width), url);
    assert.equal(bytes.readUInt32BE(20), Number(height), url);
    const record = manifest.images.find(item => item.file === path.basename(url));
    assert.ok(record?.sampleData, url);
    assert.equal(require("node:crypto").createHash("sha256").update(bytes).digest("hex"), record.sha256, url);
    assert.ok(alt.includes("サンプル"));
    assert.ok(html.includes(`href="${url}" target="_blank" rel="noopener"`));
  }
  assert.match(html, /v1\.2\.8/);
  assert.match(html, /公式サンプルデータ/);
  assert.doesNotMatch(html, /Threadsは設計プレビュー|threads-progress\.png/);
  assert.match(html, /PR作成やpushだけでは実行されません/);
  assert.match(html, /変更全体の品質を確認したことにはなりません/);
  assert.match(html, /既存の会話は/);
  for (const id of ["features", "delivery", "quality", "screens", "start", "screen-notes"]) {
    assert.match(html, new RegExp(`id="${id}"`));
  }
});

test("CLI proposed prices follow the SIMY catalog without starting a new purchase flow", () => {
  const html = fs.readFileSync(path.join(root, "site/for/engineers/index.html"), "utf8");
  const pricing = html.match(/<section id="pricing"[\s\S]*?<\/section>/)?.[0];
  assert.ok(pricing);
  const catalog = require("../site/pricing-catalog.js");
  for (const key of ["starter", "quality"]) {
    const card = pricing.match(new RegExp(`<article class="cli-plan" data-cli-plan="${key}">[\\s\\S]*?<\\/article>`))?.[0];
    assert.ok(card);
    for (const cycle of ["monthly", "annual"]) {
      const values = catalog.presentation("jp", "ja", cycle);
      assert.ok(card.includes(values.baseAmounts[key]), `${key} ${cycle} tax-exclusive`);
      if (cycle === "monthly") assert.ok(card.includes(values.taxInclusiveAmounts[key]), `${key} monthly tax-inclusive`);
      else assert.ok(card.includes(values.annualTotals[key]), `${key} annual payment total`);
    }
    assert.match(card, /仮料金・受付未開始/);
    assert.doesNotMatch(card, /https:\/\/app\.simy\.one\/(?:signup|checkout)/);
  }
  assert.match(pricing, /AIサービスの利用料金は含みません/);
  for (const destination of ["manga", "pricing", "enterprise", "affiliate"]) {
    assert.ok(html.includes(`href="#${destination}"`));
    assert.ok(html.includes(`id="${destination}"`));
  }
});

test("localized illustrations preserve provenance, sample-data limits and asset integrity", () => {
  const html = fs.readFileSync(path.join(root, "site/for/es/engineers/index.html"), "utf8");
  assert.match(html, /ilustraciones en español/);
  assert.doesNotMatch(html, /Screens shown in Japanese/);
  assert.match(html, /simulados|sintéticos/);
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
  for (const lang of ['es','fr','hi','zh-Hans']) {
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


test("bilingual comics use real speech text inside the frame and preserve the same story", () => {
  const story = JSON.parse(fs.readFileSync(path.join(root, "scripts/engineering-cli-story.json"), "utf8"));
  for (const locale of ["ja", "en"]) {
    const route = locale === "ja" ? "for/engineers/index.html" : "for/en/engineers/index.html";
    const html = fs.readFileSync(path.join(root, "site", route), "utf8");
    assert.equal((html.match(/class="cli-comic-frame"/g) || []).length, 8);
    assert.equal((html.match(/class="cli-speech"/g) || []).length, 15);
    assert.equal((html.match(/src="\/assets\/cli-ui\/comic-art.png"/g) || []).length, 8);
    for (const panel of story[locale]) for (const line of panel.dialogue) assert.ok(html.includes(line.text));
    assert.ok(html.includes(locale === "ja" ? 'href="/for/en/engineers/"' : 'href="/for/engineers/"'));
    assert.doesNotMatch(html, /release-crew-(?:ja|en)\.webp/);
    if (locale === "en") {
      const main = html.match(/<main[\s\S]*?<\/main>/)[0].replace(/<a[^>]*lang="ja"[^>]*>日本語<\/a>/g, "");
      assert.doesNotMatch(main, /[\u3040-\u30ff\u3400-\u9fff]/u);
      assert.match(main, /Japanese interface/);
      assert.match(main, /Draft pricing/);
    }
  }
});

test("published affiliate information does not send visitors to an unavailable portal", () => {
  for (const file of ["affiliate.html", "affiliate-en.html"]) {
    const html = fs.readFileSync(path.join(root, "site", file), "utf8");
    assert.doesNotMatch(html, /href="https:\/\/app\.simy\.one\/affiliate/);
    assert.match(html, /mailto:sales@simy.one/);
  }
});
