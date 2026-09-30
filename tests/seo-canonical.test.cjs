const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

// One HTML file serves every ?lang= variant of a page, so the canonical is set
// at runtime. These tests run the real page scripts against each page's real
// <head> and check that every hreflang alternate is self-canonical: a
// translation whose canonical names the English x-default URL is treated as a
// duplicate and is not indexed for its own language.

const repoRoot = path.resolve(__dirname, "..");
const siteRoot = path.join(repoRoot, "site");
const read = (file) => fs.readFileSync(path.join(siteRoot, file), "utf8");
const homeI18n = new vm.Script(read("home-i18n.js"), { filename: "home-i18n.js" });
const siteI18n = new vm.Script(read("i18n.js"), { filename: "i18n.js" });

function withoutComments(html) {
  return html.replace(/<!--[\s\S]*?-->/g, "");
}

function staticCanonicals(file) {
  return withoutComments(read(file)).match(/<link[^>]*rel="canonical"[^>]*>/g) ?? [];
}

function makeElement(tagName, attributes = {}) {
  const attrs = new Map(Object.entries(attributes));
  const element = {
    tagName: tagName.toUpperCase(),
    dataset: {},
    style: {},
    textContent: "",
    getAttribute: (name) => (attrs.has(name) ? attrs.get(name) : null),
    setAttribute: (name, value) => attrs.set(name, String(value)),
    hasAttribute: (name) => attrs.has(name),
    removeAttribute: (name) => attrs.delete(name),
    addEventListener() {},
    querySelector: () => null,
    querySelectorAll: () => []
  };
  for (const name of ["rel", "href", "hreflang", "content"]) {
    Object.defineProperty(element, name, {
      get: () => element.getAttribute(name) ?? "",
      set: (value) => element.setAttribute(name, value)
    });
  }
  return element;
}

// Supports the `tag[attr="value"]...` selectors the scripts use for head
// metadata; every other selector (nav, #root, data hooks) matches nothing.
function matches(element, selector) {
  const parsed = selector.match(/^([a-z]+)((?:\[[\w:-]+="[^"]*"\])*)$/);
  if (!parsed || element.tagName !== parsed[1].toUpperCase()) return false;
  return [...parsed[2].matchAll(/\[([\w:-]+)="([^"]*)"\]/g)]
    .every(([, name, value]) => element.getAttribute(name) === value);
}

function loadPage(script, file, href, { storage = {}, languages = ["en-US"], timeZone = "America/Los_Angeles" } = {}) {
  const headHtml = withoutComments(read(file).split("</head>")[0]);
  const head = [...headHtml.matchAll(/<(link|meta)\s([^>]*)>/g)].map(([, tag, attrs]) =>
    makeElement(tag, Object.fromEntries([...attrs.matchAll(/([\w:-]+)="([^"]*)"/g)].map(([, k, v]) => [k, v])))
  );
  const store = new Map(Object.entries(storage));
  const location = {};
  const setLocation = (value) => {
    const url = new URL(value, location.href);
    Object.assign(location, {
      href: url.href, origin: url.origin, protocol: url.protocol, hostname: url.hostname,
      pathname: url.pathname, search: url.search, hash: url.hash
    });
  };
  setLocation(href);
  const noop = () => 0;
  const document = {
    readyState: "complete",
    title: "",
    body: null,
    documentElement: makeElement("html"),
    head: {
      appendChild: (element) => (head.push(element), element),
      append: (...elements) => head.push(...elements)
    },
    createElement: (tag) => makeElement(tag),
    createTreeWalker: () => ({ nextNode: () => null }),
    querySelector: (selector) => head.find((element) => matches(element, selector)) ?? null,
    querySelectorAll: (selector) => head.filter((element) => matches(element, selector)),
    getElementById: () => null,
    getElementsByTagName: () => [],
    addEventListener() {}
  };
  const sandbox = {
    document,
    location,
    navigator: { languages, language: languages[0] },
    localStorage: {
      getItem: (key) => (store.has(key) ? store.get(key) : null),
      setItem: (key, value) => store.set(key, String(value))
    },
    history: { replaceState: (state, title, url) => setLocation(url) },
    Intl: { DateTimeFormat: () => ({ resolvedOptions: () => ({ timeZone }) }) },
    NodeFilter: { SHOW_TEXT: 4 },
    CustomEvent: class CustomEvent {
      constructor(type, init = {}) { this.type = type; this.detail = init.detail; }
    },
    MutationObserver: class MutationObserver { observe() {} disconnect() {} },
    XMLHttpRequest: class XMLHttpRequest { open() {} send() {} },
    URL,
    URLSearchParams,
    setTimeout: noop,
    setInterval: noop,
    clearInterval: noop,
    addEventListener() {},
    dispatchEvent() {}
  };
  sandbox.window = sandbox;
  script.runInContext(vm.createContext(sandbox));

  const canonicals = head.filter((element) => matches(element, 'link[rel="canonical"]'));
  assert.ok(canonicals.length <= 1, `${href} must not declare conflicting canonicals`);
  return {
    canonical: canonicals[0]?.href ?? null,
    alternates: head.filter((element) => element.rel === "alternate" && element.hreflang)
      .map((element) => ({ hreflang: element.hreflang, href: element.href })),
    url: location.href,
    detectedLang: sandbox.simyI18n?.detect()
  };
}

const loadHome = (href, options) => loadPage(homeI18n, "index.html", href, options);
const loadLocalized = (file, href, options) => loadPage(siteI18n, file, href, options);

const localizedPages = [...read("sitemap.xml").matchAll(/<loc>https:\/\/simy\.one\/([^<]+)<\/loc>/g)]
  .map(([, file]) => file)
  .filter((file) => read(file).includes("i18n.js?v="));

test("homepage ships no static canonical and an absolute hreflang cluster for every locale", () => {
  assert.deepEqual(staticCanonicals("index.html"), [], "a static canonical would name one variant for all of them");

  const supported = Function(`return ${read("home-i18n.js").match(/SUPPORTED_LOCALES = new Set\((\[[^\]]*\])\)/)[1]}`)();
  const { alternates } = loadHome("https://simy.one/");
  assert.deepEqual(
    alternates.map((alternate) => alternate.hreflang).sort(),
    [...supported, "x-default"].sort()
  );
  for (const { hreflang, href } of alternates) {
    assert.equal(href, hreflang === "x-default" ? "https://simy.one/" : `https://simy.one/?lang=${hreflang}`);
  }
});

test("every homepage hreflang URL is self-canonical", () => {
  const { alternates } = loadHome("https://simy.one/");
  for (const { href } of alternates) {
    assert.equal(loadHome(href).canonical, href, `${href} must canonicalize to itself`);
  }
});

test("homepage URLs outside the cluster canonicalize to the variant they name", () => {
  const cases = {
    "https://simy.one/?lang=JA&utm_source=newsletter": "https://simy.one/?lang=ja",
    "https://simy.one/?lang=zh": "https://simy.one/?lang=zh-Hans",
    "https://simy.one/?lang=fr#pricing": "https://simy.one/?lang=fr",
    "https://simy.one/?region=jp": "https://simy.one/",
    "https://simy.one/?lang=de": "https://simy.one/",
    "https://www.simy.one/?lang=es": "https://simy.one/?lang=es"
  };
  for (const [href, canonical] of Object.entries(cases)) {
    assert.equal(loadHome(href).canonical, canonical, href);
  }
});

test("a saved homepage language moves the URL and the canonical together", () => {
  const page = loadHome("https://simy.one/", { storage: { "simy-home-locale": "ja" } });
  assert.equal(page.url, "https://simy.one/?lang=ja");
  assert.equal(page.canonical, "https://simy.one/?lang=ja");
});

test("localized pages in the sitemap leave the canonical to i18n.js", () => {
  for (const file of ["compare.html", "press-release.html", "privacy.html", "terms.html"]) {
    assert.ok(localizedPages.includes(file), `${file} is region-redirected and must stay covered`);
  }
  for (const file of localizedPages) {
    assert.deepEqual(staticCanonicals(file), [], `${file} serves every ?lang= variant from one file`);
    assert.doesNotMatch(read(file).match(/<meta name="robots"[^>]*>/)?.[0] ?? "", /noindex/, `${file} is in the sitemap`);
  }
});

test("every hreflang URL on localized pages is self-canonical and renders its own language", () => {
  for (const file of localizedPages) {
    const { alternates, canonical } = loadLocalized(file, `https://simy.one/${file}`);
    assert.equal(canonical, `https://simy.one/${file}`);
    assert.equal(alternates.find((alternate) => alternate.hreflang === "x-default")?.href, canonical);
    assert.equal(alternates.length, 19, `${file} declares x-default plus 18 languages`);
    for (const { hreflang, href } of alternates) {
      const page = loadLocalized(file, href);
      assert.equal(page.canonical, href, `${href} must canonicalize to itself`);
      if (hreflang !== "x-default") assert.equal(page.detectedLang, hreflang, `${href} must render ${hreflang}`);
    }
  }
});

test("localized page canonicals follow the URL, not the visitor", () => {
  const tokyo = { languages: ["ja-JP"], timeZone: "Asia/Tokyo" };
  const cases = [
    ["https://simy.one/privacy.html", "https://simy.one/privacy.html", tokyo],
    ["https://simy.one/privacy.html", "https://simy.one/privacy.html", { storage: { "simy-lang": "fr", "simy-lang-source": "manual" } }],
    ["https://simy.one/privacy.html?region=jp", "https://simy.one/privacy.html?lang=ja"],
    ["https://simy.one/compare.html?lang=ja&locale=ja&region=jp", "https://simy.one/compare.html?lang=ja"],
    ["https://simy.one/press-release.html?region=us", "https://simy.one/press-release.html?lang=en"],
    ["https://simy.one/terms.html?lang=zh-tw", "https://simy.one/terms.html?lang=zh-Hant"],
    ["https://simy.one/terms.html?lang=xx", "https://simy.one/terms.html"],
    ["https://www.simy.one/about.html?lang=fr", "https://simy.one/about.html?lang=fr"]
  ];
  for (const [href, canonical, options] of cases) {
    const page = loadLocalized(href.split("/").pop().split("?")[0], href, options);
    assert.equal(page.canonical, canonical, href);
  }
});

test("pages with their own canonical or noindex get no language cluster", () => {
  const legacyCompare = loadLocalized("compare/index.html", "https://simy.one/compare/index.html?lang=ja");
  assert.equal(legacyCompare.canonical, "https://simy.one/compare");
  assert.deepEqual(legacyCompare.alternates, []);

  const notFound = loadLocalized("404.html", "https://simy.one/missing?lang=ja");
  assert.equal(notFound.canonical, null);
  assert.deepEqual(notFound.alternates, []);
});
