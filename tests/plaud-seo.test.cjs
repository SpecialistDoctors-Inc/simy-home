// Static SEO checklist for site/guides/plaud.html.
// Each test maps to one item in docs/seo/seo-complete-definition.md.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const repoRoot = path.resolve(__dirname, "..");
const siteRoot = path.join(repoRoot, "site");
const html = fs.readFileSync(path.join(siteRoot, "guides", "plaud.html"), "utf8");

const CANONICAL = "https://simy.one/guides/plaud.html";
const OG_IMAGE = "https://simy.one/ogp-plaud.png";

// ---------- helpers ----------
const decode = (s) =>
  s
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&copy;/g, "©");
const stripTags = (s) => decode(s.replace(/<[^>]+>/g, "")).replace(/\s+/g, " ").trim();
const attrs = (tag) => {
  const out = {};
  for (const m of tag.matchAll(/([\w:-]+)="([^"]*)"/g)) out[m[1]] = decode(m[2]);
  return out;
};
const metaTags = [...html.matchAll(/<meta\b[^>]*>/g)].map((m) => attrs(m[0]));
const meta = (key) => {
  const tag = metaTags.find((t) => t.name === key || t.property === key);
  return tag ? tag.content : undefined;
};
// Width where full-width characters count 1 and half-width characters count 0.5.
const width = (s) => [...s].reduce((sum, ch) => sum + (ch.charCodeAt(0) <= 0xff ? 0.5 : 1), 0);

const head = html.slice(0, html.indexOf("</head>"));
const body = html.slice(html.indexOf("<body"));
const bodyNoScript = body.replace(/<script[\s\S]*?<\/script>/g, "").replace(/<!--[\s\S]*?-->/g, "");
const visibleText = stripTags(bodyNoScript);
const title = stripTags(head.match(/<title>([\s\S]*?)<\/title>/)[1]);
const headings = [...bodyNoScript.matchAll(/<h([1-6])\b[^>]*>([\s\S]*?)<\/h\1>/g)].map((m) => ({
  level: Number(m[1]),
  text: stripTags(m[2]),
}));
const faqVisible = [...bodyNoScript.matchAll(/<details>\s*<summary>([\s\S]*?)<\/summary>\s*<div class="a">([\s\S]*?)<\/div>\s*<\/details>/g)].map((m) => ({
  q: stripTags(m[1]),
  a: stripTags(m[2]),
}));
const jsonLdBlocks = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const graph = () => JSON.parse(jsonLdBlocks[0])["@graph"];
const node = (type) => graph().find((n) => n["@type"] === type);
const sectionIds = [...bodyNoScript.matchAll(/<section class="sec" id="([^"]+)"/g)].map((m) => m[1]);
const allIds = new Set([...html.matchAll(/\bid="([^"]+)"/g)].map((m) => m[1]));

// ---------- target queries and co-occurrence terms ----------
const TARGET_QUERIES = [
  { query: "PLAUD 使ってる", pattern: /すでに使って/ },
  { query: "PLAUD 買った", pattern: /買った/ },
  { query: "PLAUD 届いた", pattern: /届いた/ },
  { query: "PLAUD NOTE 文字起こし", pattern: /文字起こし/ },
  { query: "PLAUD 要約", pattern: /要約/ },
  { query: "PLAUD エクスポート", pattern: /エクスポート/ },
  { query: "PLAUD MCP", pattern: /MCP/ },
  { query: "PLAUD 料金", pattern: /料金/ },
  { query: "PLAUD Unlimited", pattern: /Unlimited/ },
  { query: "PLAUD NOTE Pro", pattern: /NOTE Pro/ },
  { query: "Plaud NotePin", pattern: /NotePin/ },
  // Added from Ahrefs Keywords Explorer (JP, 2026-09-30): high-volume post-purchase terms.
  { query: "PLAUD 使い方", pattern: /使い方/ },
  { query: "Plaud Web", pattern: /Plaud Web/ },
  { query: "Plaud Desktop", pattern: /Plaud Desktop/ },
  { query: "PLAUD どこの国", pattern: /どこの国/ },
  { query: "PLAUD 情報漏洩", pattern: /情報漏洩/ },
];

// Co-occurrence terms from the top-20 SERP analysis that fit a post-purchase guide.
const ADOPTED_TERMS = [
  "録音", "AI", "機能", "文字起こし", "要約", "ボイスレコーダー", "レビュー", "NOTE", "無料", "対応",
  "会議", "アプリ", "時間", "データ", "価格", "精度", "記録", "音声", "モード", "スマホ",
  "比較", "議事録", "対面", "本体", "通話", "送信", "企業", "書き起こし", "会話", "プラン",
  "連携", "報告", "ノイズ", "製品", "必要", "再生", "評価", "自動", "ボタン", "デバイス",
  "プラウド", "日本", "複数", "選択", "モデル", "マイク", "整理", "ユーザー", "活用", "入力",
  "最大", "開始", "音質", "テンプレート", "種類", "Ask", "共有", "ビジネス", "マルチモーダル", "通話録音",
  "容量", "クリア", "プライバシー", "ハイライト", "Pro", "便利", "生成", "仕事", "安心", "以内",
  "写真", "ポケット", "削除", "専用", "ファイル", "追加", "保存", "話者", "転送", "オンライン",
  "管理", "理解", "作成", "マインドマップ", "質問", "自動的", "準拠", "言語", "連続", "問題",
  "検証", "ノート", "日本語",
  // Ahrefs "Also talk about" and matching-term vocabulary (JP, 2026-09-30).
  "使い方", "ログイン", "Web", "Desktop", "パソコン", "充電", "接続", "セキュリティ", "情報漏洩", "学習",
  "Zoom", "アカウント", "違い", "方法", "GPT", "Gemini", "Claude", "SOC 2", "HIPAA", "GDPR",
  "AutoFlow", "暗号化", "データセンター", "月額", "翻訳", "ダウンロード",
];

// Terms that pull the page toward e-commerce listings; the guide must not use them.
const EXCLUDED_TERMS = ["Amazon", "在庫", "最安", "ショップ", "発送", "注文", "ブラック", "シルバー", "99mm", "ケース", "サイズ", "GB"];

// ---------- A. intent and content ----------
test("A1 every target query is answered in title, headings or FAQ questions", () => {
  const places = [title, ...headings.map((h) => h.text), ...faqVisible.map((f) => f.q)].join("\n");
  const missing = TARGET_QUERIES.filter((t) => !t.pattern.test(places)).map((t) => t.query);
  assert.deepEqual(missing, [], `queries without a heading or FAQ answer: ${missing.join(", ")}`);
});

test("A2 at least 90% of adopted co-occurrence terms appear in the body", () => {
  const missing = ADOPTED_TERMS.filter((t) => !visibleText.includes(t));
  const coverage = (ADOPTED_TERMS.length - missing.length) / ADOPTED_TERMS.length;
  assert.ok(coverage >= 0.9, `coverage ${(coverage * 100).toFixed(1)}%; missing: ${missing.join(", ")}`);
});

test("A3 no excluded e-commerce terms appear in the body", () => {
  const found = EXCLUDED_TERMS.filter((t) => visibleText.includes(t));
  assert.deepEqual(found, []);
});

test("A4 facts cite official sources with a verification date", () => {
  const sources = bodyNoScript.match(/<section class="sec" id="sources"[\s\S]*?<\/section>/);
  assert.ok(sources, "sources section is missing");
  const officialLinks = [...sources[0].matchAll(/href="https:\/\/[^"]*plaud\.ai[^"]*"/g)];
  assert.ok(officialLinks.length >= 3, `need at least 3 official links, found ${officialLinks.length}`);
  assert.match(stripTags(sources[0]), /確認日：\d{4}年\d{1,2}月\d{1,2}日/);
});

test("A5 illustrations and samples are labelled as examples", () => {
  const figures = (bodyNoScript.match(/role="img"/g) || []).length;
  const captions = (visibleText.match(/イメージです/g) || []).length;
  assert.ok(captions >= figures, `${figures} illustrations but only ${captions} captions`);
  const sample = bodyNoScript.match(/<section class="sec" id="sample"[\s\S]*?<\/section>/)[0];
  assert.match(stripTags(sample), /サンプル/);
});

test("A6 visible update date and publisher match structured data", () => {
  const time = bodyNoScript.match(/<p class="byline">[\s\S]*?<time datetime="([^"]+)">/);
  assert.ok(time, "byline with <time> is missing");
  assert.equal(time[1], node("Article").dateModified);
  assert.match(visibleText, /発行：SIMY/);
});

test("A7 body has at least 5,000 characters", () => {
  const chars = visibleText.replace(/\s/g, "").length;
  assert.ok(chars >= 5000, `only ${chars} characters`);
});

// ---------- B. meta ----------
test("B1 title starts with PLAUD and is 25-35 full-width characters", () => {
  assert.ok(title.startsWith("PLAUD"), title);
  const w = width(title);
  assert.ok(w >= 25 && w <= 35, `title width ${w}`);
});

test("B2 meta description mentions PLAUD and is 80-120 full-width characters", () => {
  const description = meta("description");
  assert.ok(description && description.includes("PLAUD"));
  const w = width(description);
  assert.ok(w >= 80 && w <= 120, `description width ${w}`);
});

test("B3 canonical is the absolute self URL", () => {
  const link = head.match(/<link rel="canonical" href="([^"]+)">/);
  assert.ok(link);
  assert.equal(link[1], CANONICAL);
});

test("B4 language is Japanese", () => {
  assert.match(html, /<html lang="ja">/);
  assert.equal(meta("og:locale"), "ja_JP");
});

test("B5 Open Graph and Twitter card are complete and consistent", () => {
  for (const key of ["og:type", "og:title", "og:description", "og:url", "og:image", "og:site_name", "og:image:alt", "twitter:title", "twitter:description", "twitter:image"]) {
    assert.ok(meta(key), `${key} is missing`);
  }
  assert.equal(meta("twitter:card"), "summary_large_image");
  assert.equal(meta("og:url"), CANONICAL);
  assert.equal(meta("twitter:image"), meta("og:image"));
});

test("B6 og:image is page-specific and a real 1200x630 PNG", () => {
  assert.equal(meta("og:image"), OG_IMAGE);
  assert.equal(meta("og:image:width"), "1200");
  assert.equal(meta("og:image:height"), "630");
  const file = path.join(siteRoot, "ogp-plaud.png");
  assert.ok(fs.existsSync(file), "site/ogp-plaud.png is missing");
  const png = fs.readFileSync(file);
  assert.equal(png.toString("ascii", 1, 4), "PNG");
  assert.equal(png.readUInt32BE(16), 1200);
  assert.equal(png.readUInt32BE(20), 630);
});

test("B7 robots allows indexing", () => {
  const robots = meta("robots");
  assert.match(robots, /\bindex\b/);
  assert.match(robots, /\bfollow\b/);
  assert.doesNotMatch(robots, /noindex|nofollow/);
});

test("B8 viewport is set for mobile", () => {
  assert.match(meta("viewport"), /width=device-width/);
});

// ---------- C. headings and structure ----------
test("C1 exactly one H1 and it contains PLAUD", () => {
  const h1 = headings.filter((h) => h.level === 1);
  assert.equal(h1.length, 1);
  assert.match(h1[0].text, /PLAUD/);
});

test("C2 heading levels never skip", () => {
  const skips = [];
  headings.forEach((h, i) => {
    if (i > 0 && h.level > headings[i - 1].level + 1) skips.push(`${headings[i - 1].text} -> ${h.text}`);
  });
  assert.deepEqual(skips, []);
});

test("C3 table of contents covers every section and every anchor resolves", () => {
  const toc = bodyNoScript.match(/<nav class="toc"[\s\S]*?<\/nav>/)[0];
  const tocIds = [...toc.matchAll(/href="#([^"]+)"/g)].map((m) => m[1]);
  assert.deepEqual(tocIds, sectionIds);
  const broken = [...html.matchAll(/href="#([^"]+)"/g)].map((m) => m[1]).filter((id) => !allIds.has(id));
  assert.deepEqual(broken, []);
});

test("C4 visible breadcrumbs match BreadcrumbList", () => {
  const crumbs = bodyNoScript.match(/<ol class="crumbs"[\s\S]*?<\/ol>/)[0];
  const names = [...crumbs.matchAll(/<li[^>]*>([\s\S]*?)<\/li>/g)].map((m) => stripTags(m[1]));
  const ld = node("BreadcrumbList").itemListElement.map((i) => i.name);
  assert.deepEqual(names, ld);
});

// ---------- D. structured data ----------
test("D1 JSON-LD parses", () => {
  assert.equal(jsonLdBlocks.length, 1);
  assert.doesNotThrow(() => JSON.parse(jsonLdBlocks[0]));
});

test("D2 Article has the fields search engines require", () => {
  const a = node("Article");
  assert.ok(a.headline && [...a.headline].length <= 110);
  assert.equal(a.image.url, OG_IMAGE);
  assert.match(a.datePublished, /^\d{4}-\d{2}-\d{2}$/);
  assert.match(a.dateModified, /^\d{4}-\d{2}-\d{2}$/);
  assert.ok(a.author && a.author.name);
  assert.ok(a.publisher && a.publisher.logo && a.publisher.logo.url);
  assert.equal(a.mainEntityOfPage, CANONICAL);
});

test("D3 FAQPage matches the visible FAQ exactly", () => {
  const ld = node("FAQPage").mainEntity.map((q) => ({ q: q.name, a: q.acceptedAnswer.text }));
  assert.ok(faqVisible.length > 0);
  assert.deepEqual(faqVisible, ld);
});

test("D4 BreadcrumbList uses absolute URLs and ends at the canonical", () => {
  const items = node("BreadcrumbList").itemListElement;
  for (const item of items) assert.match(item.item, /^https:\/\/simy\.one\//);
  assert.equal(items[items.length - 1].item, CANONICAL);
});

// ---------- E. crawl and index ----------
test("E1 robots.txt does not block the page", () => {
  const robots = fs.readFileSync(path.join(siteRoot, "robots.txt"), "utf8");
  const blocked = [...robots.matchAll(/^Disallow:\s*(\S+)/gm)].map((m) => m[1]).filter((p) => "/guides/plaud.html".startsWith(p));
  assert.deepEqual(blocked, []);
});

test("E2 sitemap lists the canonical with the current lastmod", () => {
  const sitemap = fs.readFileSync(path.join(siteRoot, "sitemap.xml"), "utf8");
  const entry = sitemap.match(/<url>\s*<loc>https:\/\/simy\.one\/guides\/plaud\.html<\/loc>\s*<lastmod>([^<]+)<\/lastmod>/);
  assert.ok(entry, "plaud.html is not in sitemap.xml");
  assert.equal(entry[1], node("Article").dateModified);
});

test("E3 at least one other page links to the guide", () => {
  const linking = fs
    .readdirSync(siteRoot)
    .filter((f) => f.endsWith(".html"))
    .filter((f) => /href="\/guides\/plaud\.html"/.test(fs.readFileSync(path.join(siteRoot, f), "utf8")));
  assert.ok(linking.length >= 1, "no page links to /guides/plaud.html");
});

test("E4 every internal link points to an existing file", () => {
  const broken = [];
  for (const m of html.matchAll(/href="([^"]+)"/g)) {
    let href = decode(m[1]);
    if (href.startsWith("https://simy.one")) href = href.slice("https://simy.one".length) || "/";
    if (!href.startsWith("/") || href.startsWith("//")) continue;
    const pathname = href.split(/[?#]/)[0];
    const file = pathname === "/" ? "index.html" : pathname.slice(1);
    if (!fs.existsSync(path.join(siteRoot, file))) broken.push(href);
  }
  assert.deepEqual(broken, []);
});

test("E5 production redirects /guides/plaud to /guides/plaud.html", () => {
  const fn = fs.readFileSync(path.join(repoRoot, "infra/cloudfront-functions/redirect-prod.js"), "utf8");
  assert.match(fn, /if \(uri !== '\/' && !uri\.includes\('\.'\)\) \{[\s\S]*?statusCode: 301[\s\S]*?uri \+ '\.html'/);
});

// ---------- F. performance-related markup ----------
test("F7 every image has alt, width and height", () => {
  const bad = [...html.matchAll(/<img\b[^>]*>/g)].map((m) => m[0]).filter((tag) => {
    const a = attrs(tag);
    return a.alt === undefined || !a.width || !a.height;
  });
  assert.deepEqual(bad, []);
});

test("F9 images loaded by the page total 50KB or less", () => {
  const sources = [...html.matchAll(/<(?:img|link)\b[^>]*(?:src|href)="(\/[^"]+\.(?:png|jpe?g|webp|svg|ico))"/g)].map((m) => m[1]);
  const total = sources.reduce((sum, src) => sum + fs.statSync(path.join(siteRoot, src.slice(1))).size, 0);
  assert.ok(sources.length > 0);
  assert.ok(total <= 50 * 1024, `images total ${total} bytes: ${sources.join(", ")}`);
});

test("F8 no external CSS, JavaScript or web fonts block rendering", () => {
  assert.doesNotMatch(html, /<link[^>]+rel="stylesheet"/);
  // Scripts are allowed only when they cannot block rendering: same-origin and deferred or async.
  const blocking = [...html.matchAll(/<script\b[^>]*\bsrc="([^"]+)"[^>]*>/g)]
    .filter((m) => !/\b(defer|async)\b/.test(m[0]) || /^(https?:)?\/\//.test(m[1]))
    .map((m) => m[0]);
  assert.deepEqual(blocking, []);
  assert.doesNotMatch(html, /fonts\.googleapis|fonts\.gstatic/);
});
