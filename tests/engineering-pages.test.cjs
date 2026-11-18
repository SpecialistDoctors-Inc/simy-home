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

test("both CLI locales use current native captures, full-size links and matching provenance", () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, "site/assets/cli-ui/manifest.json"), "utf8"));
  assert.equal(manifest.version, "1.2.11");
  assert.equal(manifest.sourceCommit, "9146fe2ced9f79571210f087665d7e94795dfdb9");
  assert.equal(manifest.images.length, 10);
  for (const locale of ["ja", "en"]) {
    const route = locale === "ja" ? "for/engineers/index.html" : "for/en/engineers/index.html";
    const html = fs.readFileSync(path.join(root, "site", route), "utf8");
    const urls = [...html.matchAll(/<img src="(\/assets\/cli-ui\/(?:ja|en)\/(?:overview|goal|sqm|connection|usage)\.png)" width="(\d+)" height="(\d+)"[^>]+alt="([^\"]+)"/g)];
    assert.equal(urls.length, 5);
    const localized = JSON.parse(fs.readFileSync(path.join(root, `site/assets/cli-ui/${locale}/manifest.json`), "utf8"));
    assert.equal(localized.locale, locale);
    assert.equal(localized.version, manifest.version);
    for (const [, url, width, height, alt] of urls) {
      assert.ok(url.startsWith(`/assets/cli-ui/${locale}/`), url);
      const bytes = fs.readFileSync(path.join(root, "site", url));
      assert.equal(bytes.readUInt32BE(16), Number(width), url);
      assert.equal(bytes.readUInt32BE(20), Number(height), url);
      const record = manifest.images.find(item => item.file === `${locale}/${path.basename(url)}`);
      assert.equal(record?.locale, locale);
      assert.ok(record.sampleData, url);
      const sha = require("node:crypto").createHash("sha256").update(bytes).digest("hex");
      assert.equal(sha, record.sha256, url);
      assert.equal(sha, localized.images.find(item => item.file === path.basename(url))?.sha256, url);
      assert.ok(alt.includes(locale === "ja" ? "サンプル" : "sample") || alt.includes("illustrative"));
      assert.ok(html.includes(`href="${url}" target="_blank" rel="noopener"`));
    }
    assert.match(html, /v1\.2\.11/);
    assert.doesNotMatch(html, /v1\.2\.8|Japanese interface|Japanese UI|Japanese illustrative data|sample data in Japanese/);
    for (const id of ["features", "delivery", "quality", "screens", "start", "screen-notes"]) {
      assert.ok(html.includes(`id="${id}"`));
    }
  }
  const ja = fs.readFileSync(path.join(root, "site/for/engineers/index.html"), "utf8");
  assert.match(ja, /公式サンプルデータ/);
  assert.match(ja, /PR作成やpushだけでは実行されません/);
  assert.match(ja, /変更全体の品質を確認したことにはなりません/);
  assert.match(ja, /既存の会話は/);
});

test("CLI and affiliate pages use matching locale images including navigation badges", () => {
  for (const locale of ["ja", "en"]) {
    const routes = locale === "ja" ? ["for/engineers/index.html", "affiliate.html"] : ["for/en/engineers/index.html", "affiliate-en.html"];
    for (const route of routes) {
      const html = fs.readFileSync(path.join(root, "site", route), "utf8");
      const suffix = locale === "ja" ? "-ja" : "";
      for (const [name, ext] of [["app-store", "svg"], ["google-play", "png"]]) {
        assert.ok(html.includes(`src="/assets/store-badges/${name}${suffix}.${ext}"`));
      }
      if (route.startsWith("affiliate")) {
        const url = `/assets/cli-ui/${locale}/affiliate-dashboard-launch.jpg`;
        assert.ok(html.includes(`src="${url}"`));
        assert.ok(html.includes(`href="${url}" target="_blank"`));
        assert.ok(fs.statSync(path.join(root, "site", url)).size > 10000);
        assert.doesNotMatch(html, /shown in Japanese|sample in Japanese/);
      }
    }
  }
});

test("CLI prices follow existing SIMY contracts and preserve plan, interval and locale at signup", () => {
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
    for (const cycle of key === "quality" ? ["monthly", "annual"] : []) {
      const hrefs=[...card.matchAll(/href="(https:\/\/app\.simy\.one\/signup\/\?[^"]+)"/g)].map(m=>new URL(m[1].replaceAll("&amp;","&")));
      const target=hrefs.find(url=>url.searchParams.get("interval")===cycle);
      assert.ok(target); assert.equal(target.searchParams.get("plan"),key); assert.equal(target.searchParams.get("lang"),"ja");
    }
    if(key === "quality") {assert.match(card, /追加利用料：\$0/);assert.ok(card.includes("industry_package_code=it_engineer"));} else {assert.match(card,/CLIは対象外/);assert.doesNotMatch(card,/https:\/\/app\.simy\.one\/signup/);}

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
    assert.equal((html.match(/class="cli-comic-frame"/g) || []).length, 4);
    assert.equal((html.match(/class="cli-speech"/g) || []).length, 7);
    assert.equal((html.match(/src="\/assets\/cli-ui\/booking-story-art-v2.png"/g) || []).length, 4);
    for (const panel of story[locale]) for (const line of panel.dialogue) assert.ok(html.includes(line.text));
    assert.ok(html.includes(locale === "ja" ? 'href="/for/en/engineers/"' : 'href="/for/engineers/"'));
    assert.doesNotMatch(html, /release-crew-(?:ja|en)\.webp/);
    if (locale === "en") {
      const main = html.match(/<main[\s\S]*?<\/main>/)[0].replace(/<a[^>]*lang="ja"[^>]*>日本語<\/a>/g, "");
      // Product brands keep their approved Japanese spelling in every locale.
      assert.doesNotMatch(main.replaceAll("SIMY 開発支援", "SIMY Development Support").replaceAll("SIMY ロセンズ", "SIMY Rosenz"), /[\u3040-\u30ff\u3400-\u9fff]/u);
      assert.match(main, /English interface/);
      assert.match(main, /SIMY CLI: \$0 additional fee/);
      assert.match(main, /href="\/download\/en\.html"/);
      assert.doesNotMatch(main, /href="\/download\.html"/);
    }
  }
});

test("comic credits implementation and checks to Codex, with SIMY prompting the missing check", () => {
  const story = JSON.parse(fs.readFileSync(path.join(root, "scripts/engineering-cli-story.json"), "utf8"));
  for (const locale of ["ja", "en"]) {
    assert.equal(story[locale][2].dialogue[0].speaker, "Codex");
    assert.equal(story[locale][2].dialogue[1].speaker, "SIMY");
    assert.equal(story[locale][3].dialogue[0].speaker, "Codex");
    const route = locale === "ja" ? "for/engineers/index.html" : "for/en/engineers/index.html";
    const html = fs.readFileSync(path.join(root, "site", route), "utf8");
    assert.ok(html.includes('id="mechanism"'));
    assert.ok(html.includes('class="cli-role-map"'));
    assert.ok(html.includes('class="cli-detail cli-role-faq"'));
    assert.ok(html.includes('https://code.claude.com/docs/en/how-claude-code-works'));
    assert.ok(html.includes('https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex'));
    assert.doesNotMatch(html, /スマホで試しましたが|I tried it on mobile/);
  }
});

test("published affiliate information does not send visitors to an unavailable portal", () => {
  for (const file of ["affiliate.html", "affiliate-en.html"]) {
    const html = fs.readFileSync(path.join(root, "site", file), "utf8");
    assert.doesNotMatch(html, /href="https:\/\/app\.simy\.one\/affiliate/);
    assert.match(html, /mailto:sales@simy.one/);
  }
});

test("referral terms match current USD HOME contract policy", () => {
 const policy=JSON.parse(fs.readFileSync(path.join(root,"scripts/cli-affiliate-policy.json"),"utf8"));
 assert.equal(policy.currency,"usd"); assert.equal(policy.minimumPayoutMinor,10000); assert.equal(policy.eligibleContracts.length,4);
 for (const file of ["affiliate.html","affiliate-en.html"]) {
  const html=fs.readFileSync(path.join(root,"site",file),"utf8");
  assert.ok(html.includes("$100")); assert.doesNotMatch(html,/JPY10,000|1万円/);
  assert.ok(html.includes("SIMY by Industry"));
 }
});
