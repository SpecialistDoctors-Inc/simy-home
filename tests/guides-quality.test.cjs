// Quality checks for every guide page and download page in every language.
// Run: node --test tests/guides-quality.test.cjs
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const siteRoot = path.join(__dirname, "..", "site");
const LANGS = ["ja", "en", "zh-hans", "es", "fr", "hi"];
const HTML_LANG = { ja: "ja", en: "en", "zh-hans": "zh-Hans", es: "es", fr: "fr", hi: "hi" };
const authored = require('../scripts/content-pages.json').pages.filter(p => p.kind === 'guide');
const guideLanguages = (name) => {
  const page = authored.find(p => path.basename(p.paths.ja) === name);
  return page ? Object.keys(page.paths) : LANGS;
};

const decode = (s) =>
  s.replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&copy;/g, "©");
const strip = (s) => decode(s.replace(/<[^>]+>/g, "")).replace(/\s+/g, " ").trim();
// Width where full-width characters count 1 and half-width 0.5.
const width = (s) => [...s].reduce((n, ch) => n + (ch.charCodeAt(0) <= 0xff ? 0.5 : 1), 0);

function pagesFor(lang) {
  const dir = lang === "ja" ? path.join(siteRoot, "guides") : path.join(siteRoot, "guides", lang);
  if (!fs.existsSync(dir)) return [];
  const guides = fs.readdirSync(dir).filter((f) => f.endsWith(".html")).map((f) => path.join(dir, f));
  const dl = lang === "ja" ? path.join(siteRoot, "download.html") : path.join(siteRoot, "download", `${lang}.html`);
  return fs.existsSync(dl) ? [...guides, dl] : guides;
}
const urlOf = (file) => "https://simy.one/" + path.relative(siteRoot, file).split(path.sep).join("/");
const jaNames = fs.readdirSync(path.join(siteRoot, "guides")).filter((f) => f.endsWith(".html"));

for (const lang of LANGS) {
  for (const file of pagesFor(lang)) {
    const rel = path.relative(siteRoot, file);
    const html = fs.readFileSync(file, "utf8");
    const head = html.slice(0, html.indexOf("</head>"));
    const body = html.slice(html.indexOf("<body"));
    const bodyNoScript = body.replace(/<script[\s\S]*?<\/script>/g, "").replace(/<style[\s\S]*?<\/style>/g, "").replace(/<!--[\s\S]*?-->/g, "");
    const meta = (key) => {
      const m = head.match(new RegExp(`<meta (?:name|property)="${key}" content="([^"]*)"`));
      return m ? decode(m[1]) : undefined;
    };

    test(`${rel}: language, canonical and Open Graph`, () => {
      assert.match(html, new RegExp(`<html lang="${HTML_LANG[lang]}"`));
      const canonical = (head.match(/<link rel="canonical" href="([^"]+)"/) || [])[1];
      assert.equal(canonical, urlOf(file));
      assert.equal(meta("og:url"), canonical);
      assert.ok(meta("og:image"), "og:image missing");
      assert.equal(meta("twitter:card"), "summary_large_image");
      assert.match(head, /<meta name="viewport"/);
    });

    test(`${rel}: title and description lengths`, () => {
      const title = strip((head.match(/<title>([\s\S]*?)<\/title>/) || [])[1] || "");
      const desc = meta("description") || "";
      assert.match(title, /\| SIMY$/);
      if (lang === "ja" || lang === "zh-hans") {
        assert.ok(width(title) <= 48, `title too long (${width(title)}): ${title}`);
        assert.ok(width(desc) >= 50 && width(desc) <= 140, `description width ${width(desc)}`);
      } else {
        assert.ok(title.length <= 70, `title too long (${title.length}): ${title}`);
        assert.ok(desc.length >= 70 && desc.length <= 170, `description length ${desc.length}`);
      }
    });

    test(`${rel}: one H1 and no skipped heading levels`, () => {
      const hs = [...bodyNoScript.matchAll(/<h([1-6])\b/g)].map((m) => Number(m[1]));
      assert.equal(hs.filter((h) => h === 1).length, 1);
      for (let i = 1; i < hs.length; i++) assert.ok(hs[i] <= hs[i - 1] + 1, `h${hs[i - 1]} -> h${hs[i]}`);
    });

    test(`${rel}: structured data parses and FAQ matches the page`, () => {
      const blocks = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)];
      assert.ok(blocks.length >= 1);
      const graph = JSON.parse(blocks[0][1])["@graph"] || [];
      const visible = [...bodyNoScript.matchAll(/<details>\s*<summary>([\s\S]*?)<\/summary>\s*<div class="a">([\s\S]*?)<\/div>\s*<\/details>/g)]
        .map((m) => [strip(m[1]), strip(m[2])]);
      const faq = graph.find((n) => n["@type"] === "FAQPage");
      const ld = faq ? faq.mainEntity.map((q) => [q.name, q.acceptedAnswer.text]) : [];
      assert.deepEqual(ld, visible);
      const crumbs = graph.find((n) => n["@type"] === "BreadcrumbList");
      if (crumbs) {
        const last = crumbs.itemListElement[crumbs.itemListElement.length - 1];
        assert.equal(last.item, urlOf(file));
      }
    });

    test(`${rel}: table of contents matches sections`, () => {
      const toc = bodyNoScript.match(/<nav class="toc"[\s\S]*?<\/nav>/);
      if (!toc) return;
      const ids = [...toc[0].matchAll(/href="#([^"]+)"/g)].map((m) => m[1]);
      const secs = [...bodyNoScript.matchAll(/<section class="sec" id="([^"]+)"/g)].map((m) => m[1]);
      assert.deepEqual(ids, secs);
    });

    test(`${rel}: internal links resolve`, () => {
      const missing = [...new Set([...html.matchAll(/href="(\/[^"#?]*)/g)].map((m) => m[1]))]
        .filter((h) => h !== "/" && !fs.existsSync(path.join(siteRoot, h.replace(/^\//, ""))));
      assert.deepEqual(missing, []);
    });

    test(`${rel}: every illustration is labelled as an example`, () => {
      const figures = (bodyNoScript.match(/role="img"/g) || []).length;
      const captions = (bodyNoScript.match(/class="caption"/g) || []).length;
      assert.ok(captions >= figures, `${figures} figures, ${captions} captions`);
    });

    test(`${rel}: hreflang alternates cover every language and point back`, () => {
      const alts = [...head.matchAll(/<link rel="alternate" hreflang="([^"]+)" href="([^"]+)">/g)];
      const langs = alts.map((m) => m[1]);
      const expected = [...guideLanguages(path.basename(file)).map(l => HTML_LANG[l]), 'x-default'];
      assert.deepEqual([...langs].sort(), [...expected].sort());
      const self = alts.find((m) => m[1] === HTML_LANG[lang]);
      assert.equal(self && self[2], urlOf(file));
      for (const [, , href] of alts) {
        assert.ok(fs.existsSync(path.join(siteRoot, href.replace("https://simy.one/", ""))), `hreflang target missing: ${href}`);
      }
    });

    test(`${rel}: claims SIMY must not make`, () => {
      const text = strip(bodyNoScript);
      for (const bad of [/SIMY[^。]{0,12}Claude ?の(有料)?プランで動/, /SIMY[^。]{0,12}Gemini ?で動く/, /387 historical/, /1\/5 ?→ ?5\/5/, /(?<!による)提携(?!や承認)/]) {
        assert.doesNotMatch(text, bad);
      }
      if (lang !== "ja") assert.doesNotMatch(text, /[぀-ヿ]{2,}/, "Japanese kana left in a translation");
      // The page must actually be written in its language (guards against a draft in the wrong language).
      const count = (re) => (text.match(re) || []).length;
      const han = count(/[一-鿿]/g), latin = count(/[A-Za-z]/g), deva = count(/[ऀ-ॿ]/g);
      const kana = count(/[\u3040-\u30ff]/g);
      if (lang === "ja") assert.ok(kana > 150, `too little Japanese text (${kana})`);
      if (lang === "zh-hans") assert.ok(han > 250, `too little Chinese text (${han})`);
      if (lang === "hi") assert.ok(deva > 400, `too little Devanagari text (${deva})`);
      if (["en", "es", "fr"].includes(lang)) assert.ok(han < 40 + latin * 0.01 && latin > 800, `unexpected script mix han=${han} latin=${latin}`);
      if (lang === "es") assert.ok(count(/\b(el|los|las|para|que|con)\b/g) > 12, "does not read as Spanish");
      if (lang === "fr") assert.ok(count(/\b(le|les|des|pour|que|avec|vous)\b/g) > 12, "does not read as French");
      if (lang === "en") assert.ok(count(/\b(the|and|you|your|with)\b/g) > 12, "does not read as English");
    });

    test(`${rel}: scripts never block rendering`, () => {
      const blocking = [...html.matchAll(/<script\b[^>]*\bsrc="([^"]+)"[^>]*>/g)]
        .filter((m) => !/\b(defer|async)\b/.test(m[0]) || /^(https?:)?\/\//.test(m[1]));
      assert.deepEqual(blocking.map((m) => m[0]), []);
      assert.doesNotMatch(html.replace(/<link rel="stylesheet" href="\/site-header\.css\?v=[^"]+">/g, ""), /<link[^>]+rel="stylesheet"/);
    });
  }
}

test("every Japanese guide exists in every language", () => {
  for (const lang of LANGS.filter((l) => l !== "ja")) {
    for (const name of jaNames) {
      if (!guideLanguages(name).includes(lang)) continue;
      assert.ok(fs.existsSync(path.join(siteRoot, "guides", lang, name)), `missing ${lang}/${name}`);
    }
  }
});

test("sitemap lists every guide page", () => {
  const sitemap = fs.readFileSync(path.join(siteRoot, "sitemap.xml"), "utf8");
  for (const lang of LANGS) {
    for (const file of pagesFor(lang)) assert.ok(sitemap.includes(`<loc>${urlOf(file)}</loc>`), `sitemap missing ${urlOf(file)}`);
  }
});
