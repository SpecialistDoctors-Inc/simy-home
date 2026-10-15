const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const repoRoot = path.resolve(__dirname, "..");
const fallback = fs.readFileSync(path.join(repoRoot, "site/auth-callback.html"), "utf8");
const cloudFrontFunction = fs.readFileSync(
  path.join(repoRoot, "infra/cloudfront-functions/redirect-prod.js"),
  "utf8",
);

function handlerResult(uri) {
  const sandbox = {};
  vm.createContext(sandbox);
  vm.runInContext(`${cloudFrontFunction}; this.run = handler;`, sandbox);
  return sandbox.run({
    request: { uri, querystring: { code: { value: "secret" } }, headers: { host: { value: "simy.one" } } },
  });
}

function renderFallback({ pathname, search = "", hash = "" }) {
  const elements = new Map([
    ["#title", { textContent: "SIMY アプリに戻ります" }],
    ["#message", { textContent: "" }],
    ["#open-app", { href: "simy://oauth-callback", hidden: false }],
    ["#store-link", { hidden: false }],
    ["#retry-links", { hidden: true }],
    ["#retry-links a[href$=\"/login\"]", { href: "https://app.simy.one/login" }],
    ["#retry-links a[href$=\"/signup\"]", { href: "https://app.simy.one/signup" }],
  ]);
  const history = { url: null, replaceState(_state, _title, url) { this.url = url; } };
  const script = fallback.match(/<script>\s*([\s\S]*?)\s*<\/script>/)[1];
  const sandbox = {
    URLSearchParams,
    window: { location: { pathname, search, hash }, history },
    document: { title: "SIMY アプリに戻る", getElementById(id) { return elements.get(`#${id}`); }, querySelector(selector) { return elements.get(selector); } },
  };
  vm.createContext(sandbox);
  vm.runInContext(script, sandbox);
  return { elements, history };
}

test("each Universal Link callback path rewrites to the Safari fallback page", () => {
  for (const uri of [
    "/app/auth/callback", "/app/auth/callback/",
    "/dev-app/auth/callback", "/dev-app/auth/callback/",
    "/stg-app/auth/callback", "/stg-app/auth/callback/",
  ]) {
    assert.equal(handlerResult(uri).uri, "/auth-callback.html", uri);
  }
});

test("the fallback never declares web-page authentication success", () => {
  assert.match(fallback, /<meta name="referrer" content="no-referrer">/);
  assert.match(fallback, /window\.history\.replaceState/);
  assert.match(fallback, /SIMY アプリを開いて、このリンクを安全に確認してください/);
  assert.doesNotMatch(fallback, /認証に成功/);
});

test("the page maps every environment to its own app scheme", () => {
  assert.match(fallback, /'\/app\/auth\/callback': 'prod'/);
  assert.match(fallback, /'\/dev-app\/auth\/callback': 'dev'/);
  assert.match(fallback, /'\/stg-app\/auth\/callback': 'stg'/);
  assert.match(fallback, /simy:\/\/oauth-callback/);
  assert.match(fallback, /simy\.dev:\/\/oauth-callback/);
  assert.match(fallback, /simy\.stg:\/\/oauth-callback/);
  assert.match(fallback, /scheme \+ window\.location\.search \+ window\.location\.hash/);
});

test("expired or consumed links offer login and sign-up without forwarding auth values", () => {
  assert.match(fallback, /new URLSearchParams\(window\.location\.hash\.slice\(1\)\)/);
  assert.match(fallback, /\['error', 'error_code', 'error_description'\]/);
  assert.match(fallback, /expired\|used\|invalid\|consumed/);
  assert.match(fallback, /https:\/\/app\.simy\.one\/login/);
  assert.match(fallback, /https:\/\/app\.simy\.one\/signup/);
  assert.match(fallback, /https:\/\/app-dev\.simy\.one/);
  assert.match(fallback, /https:\/\/app-stg\.simy\.one/);
  assert.match(fallback, /apps\.apple\.com\/app\/id6745385262/);
});

test("fragment errors stay in their environment and do not open the app", () => {
  const { elements, history } = renderFallback({
    pathname: "/dev-app/auth/callback",
    hash: "#error_code=link_expired",
  });
  assert.equal(elements.get("#open-app").hidden, true);
  assert.equal(elements.get("#retry-links").hidden, false);
  assert.equal(elements.get('#retry-links a[href$="/login"]').href, "https://app-dev.simy.one/login");
  assert.equal(elements.get('#retry-links a[href$="/signup"]').href, "https://app-dev.simy.one/signup");
  assert.equal(history.url, "/dev-app/auth/callback");
});

test("staging uses its scheme and does not advertise the production store", () => {
  const { elements } = renderFallback({ pathname: "/stg-app/auth/callback", search: "?code=test" });
  assert.equal(elements.get("#open-app").href, "simy.stg://oauth-callback?code=test");
  assert.equal(elements.get("#store-link").hidden, true);
});

test("unknown callback paths never forward credentials to production", () => {
  for (const pathname of ["/auth-callback.html", "/dev-app/auth/callback-extra"]) {
    const { elements, history } = renderFallback({ pathname, search: "?code=test" });
    assert.equal(elements.get("#open-app").hidden, true);
    assert.equal(elements.get("#store-link").hidden, true);
    assert.equal(history.url, pathname);
    assert.equal(elements.get("#open-app").href.includes("code="), false);
  }
});

test("each environment preserves callback credentials only in its app action", () => {
  for (const [prefix, scheme] of [["app", "simy"], ["dev-app", "simy.dev"], ["stg-app", "simy.stg"]]) {
    const pathname = `/${prefix}/auth/callback`;
    const { elements, history } = renderFallback({ pathname, search: "?code=test%2Bvalue", hash: "#state=fixture" });
    assert.equal(elements.get("#open-app").href, `${scheme}://oauth-callback?code=test%2Bvalue#state=fixture`);
    assert.equal(history.url, pathname);
    assert.equal(elements.get("#retry-links").hidden, true);
    assert.equal(elements.get("#store-link").hidden, prefix !== "app");
  }
});
