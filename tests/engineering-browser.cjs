// Run with Playwright available in NODE_PATH: node tests/engineering-browser.cjs
// Starts a private loopback server and verifies only local, synthetic page states.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");
const { chromium } = require("playwright");
const root = path.resolve(__dirname, "..");
const site = path.join(root, "site");
const output =
  process.env.ENGINEERING_EVIDENCE_DIR ||
  path.join(root, "docs/engineering-experience/screenshots");
const contentTypes = {
  ".html": "text/html",
  ".css": "text/css",
  ".js": "application/javascript",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".json": "application/json",
};
const server = http.createServer((req, res) => {
  const url = new URL(req.url, "http://localhost");
  const file = path.resolve(
    site,
    "." +
      (decodeURIComponent(url.pathname) + (url.pathname.endsWith("/") ? "index.html" : "")),
  );
  if (!file.startsWith(site + path.sep)) {
    res.writeHead(403).end();
    return;
  }
  fs.readFile(file, (err, data) => {
    if (err) {
      res.writeHead(404).end();
      return;
    }
    res
      .writeHead(200, {
        "Content-Type":
          contentTypes[path.extname(file)] || "application/octet-stream",
      })
      .end(data);
  });
});
const report = { views: [], scenarios: 0, errors: [], theme: {} };
(async () => {
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({
    channel: process.env.PLAYWRIGHT_CHANNEL || "chrome",
  });
  try {
    fs.mkdirSync(output, { recursive: true });
    // The shared theme must look the same across the homepage/detail-page boundary.
    const themePage = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    for (const route of ["/ja.html", "/for/engineers/", "/for/en/engineers/"]) {
      await themePage.goto(origin + route);
      report.theme[route] = await themePage.evaluate(() => {
        const body = getComputedStyle(document.body);
        const button = getComputedStyle(document.querySelector(".hero .button-primary"));
        return { background: body.backgroundColor, color: body.color, font: body.fontFamily,
          button: { background: button.backgroundColor, color: button.color,
            border: button.borderColor, radius: button.borderRadius, weight: button.fontWeight } };
      });
    }
    assert.deepEqual(report.theme["/for/engineers/"], report.theme["/ja.html"], "Japanese page uses the homepage theme");
    assert.deepEqual(report.theme["/for/en/engineers/"], report.theme["/ja.html"], "English page uses the homepage theme");
    for (const [alias, target] of [["/engineers.html", "/for/engineers/"], ["/engineers-en.html", "/for/en/engineers/"]]) {
      await themePage.goto(origin + alias);
      await themePage.waitForURL(origin + target);
      assert.equal(await themePage.locator("h1").count(), 1);
    }
    await themePage.close();
    for (const lang of ["ja", "en"]) {
      const page = await browser.newPage({
        viewport: { width: 1440, height: 1000 },
        reducedMotion: "reduce",
      });
      page.on("pageerror", (error) => report.errors.push(error.message));
      page.on("console", (message) => {
        if (message.type() === "error") report.errors.push(message.text());
      });
      page.on("response", (response) => {
        if (response.status() >= 400)
          report.errors.push(`${response.status()} ${response.url()}`);
      });
      const route = lang === "ja" ? "/for/engineers/" : "/for/en/engineers/";
      await page.goto(origin + route);
      await page.keyboard.press("Tab");
      assert.ok(await page.locator(".skip").evaluate((link) => {
        const r = link.getBoundingClientRect();
        const front = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
        return document.activeElement === link && (front === link || link.contains(front));
      }), "First Tab exposes skip link above sticky header");
      assert.equal(await page.locator("h1").count(), 1);
      const headline = await page.locator("h1").textContent();
      assert.match(
        headline,
        lang === "ja"
          ? /AIに、開発と品質チェックを任せる/
          : /Let AI build, test,and check your code/,
      );
      assert.equal(
        await page.locator(".faq[open]").count(),
        0,
        "Details do not compete with the primary promise",
      );
      const data = await page
        .locator("#engineering-data")
        .textContent()
        .then(JSON.parse);
      for (let example = 0; example < 3; example++) {
        await page.locator(`[data-example="${example}"]`).click();
        assert.equal(
          await page.locator("[data-request]").textContent(),
          data[example].request,
        );
        assert.deepEqual(
          await page.locator("[data-output]").allTextContents(),
          data[example].outputs,
        );
        assert.equal(
          await page.locator('[data-example][aria-pressed="true"]').count(),
          1,
        );
        assert.ok(
          (await page.locator("[data-announcement]").textContent()).includes(
            data[example].request,
          ),
        );
        report.scenarios++;
      }
      await page.locator('[data-example="0"]').focus();
      await page.keyboard.press("Enter");
      assert.equal(
        await page.locator('[data-example="0"]').getAttribute("aria-pressed"),
        "true",
      );
      await page.locator('[data-example="2"]').focus();
      await page.keyboard.press("Space");
      assert.equal(
        await page.locator('[data-example="2"]').getAttribute("aria-pressed"),
        "true",
      );
      await page.locator("#levels > summary").focus();
      await page.keyboard.press("Enter");
      assert.ok(await page.locator(".level-list").isVisible());
      await page.locator(".level > summary").first().focus();
      await page.keyboard.press("Enter");
      assert.ok(await page.locator(".level-detail").first().isVisible());
      await page.locator("#levels > summary").click();
      for (const width of [360, 390, 768, 1440, 720]) {
        await page.setViewportSize({
          width,
          height: width === 720 ? 500 : 1000,
        });
        await page.locator('[data-example="0"]').click();
        await page.evaluate(() =>
          window.scrollTo({ top: 0, behavior: "instant" }),
        );
        const geometry = await page.evaluate(() => {
          const rect = (element) => {
            const r = element.getBoundingClientRect();
            return { x: r.x, y: r.y, right: r.right, bottom: r.bottom };
          };
          const peers = [".capabilities", ".setup", ".example-grid"].map(
            (selector) => {
              const items = [...document.querySelector(selector).children].map(
                rect,
              );
              const sameRow = items.every(
                (item) => Math.abs(item.y - items[0].y) <= 1,
              );
              return {
                selector,
                sameRow,
                delta: sameRow
                  ? Math.max(...items.map((i) => i.bottom)) -
                    Math.min(...items.map((i) => i.bottom))
                  : 0,
              };
            },
          );
          const outside = [...document.querySelectorAll("main a,main button,header a")]
            .filter((element) => element.getClientRects().length)
            .filter((element) => {
              const r = rect(element);
              return r.x < -1 || r.right > innerWidth + 1;
            })
            .map((element) => element.textContent);
          return {
            rails: [...document.querySelectorAll(".site-shell")].map(rect),
            width: innerWidth,
            scrollWidth: document.documentElement.scrollWidth,
            peers,
            outside,
            headlineBottom: rect(document.querySelector("h1")).bottom,
            ctaBottom: rect(document.querySelector(".hero .primary")).bottom,
            outputsBottom: rect(document.querySelector(".result")).bottom,
          };
        });
        assert.ok(
          geometry.scrollWidth <= width + 1,
          `${lang} ${width} horizontal overflow`,
        );
        assert.deepEqual(
          geometry.outside,
          [],
          `${lang} ${width} clipped controls`,
        );
        for (const rail of geometry.rails) {
          assert.ok(Math.abs(rail.x - geometry.rails[0].x) <= 1 && Math.abs(rail.right - geometry.rails[0].right) <= 1, "Header, main and footer rails align");
        }
        geometry.peers.forEach((group) =>
          assert.ok(
            group.delta <= 1,
            `${lang} ${width} ${group.selector} alignment`,
          ),
        );
        if (width === 1440)
          assert.ok(
            geometry.outputsBottom <= 1000,
            "Desktop shows request and outputs in the first viewport",
          );
        if (width <= 390)
          assert.ok(
            geometry.ctaBottom <= 540,
            "Mobile shows the promise and primary action without a long scroll",
          );
        report.views.push({ lang, ...geometry });
        if (width === 1440 || width === 390) {
          await page.screenshot({
            path: path.join(output, `${lang}-${width}.png`),
            fullPage: true,
          });
          await page.screenshot({
            path: path.join(output, `${lang}-${width}-first-screen.png`),
          });
        }
      }
      await page.setViewportSize({ width: 1440, height: 1000 });
      await page.locator('[data-example="2"]').click();
      await page
        .locator(".example")
        .screenshot({ path: path.join(output, `${lang}-quality-example.png`) });
      const links = await page
        .locator("a")
        .evaluateAll((links) =>
          links.map((a) => ({ href: a.getAttribute("href"), url: a.href })),
        );
      for (const link of links) {
        const url = new URL(link.url);
        if (url.origin !== origin) continue;
        if (link.href.startsWith("#"))
          assert.equal(await page.locator(link.href).count(), 1);
        else
          assert.equal(
            (await page.request.get(url.origin + url.pathname)).status(),
            200,
            link.href,
          );
      }
      await page.locator(".sh-language > summary").click();
      await page.locator(`[data-sh-link="locale-${lang === "ja" ? "en" : "ja"}"]`).click();
      assert.equal(
        await page.locator("html").getAttribute("lang"),
        lang === "ja" ? "en" : "ja",
      );
      await page.close();
    }
    for (const locale of ["en", "ja", "es", "fr", "hi", "zh-Hans"]) {
      const page = await browser.newPage({ reducedMotion: "reduce" });
      page.on("pageerror", (error) => report.errors.push(error.message));
      await page.goto(origin + (locale === "en" ? "/" : `/${locale}.html`));
      for (const width of [390, 1440]) {
        await page.setViewportSize({ width, height: 1000 });
        await page.waitForFunction(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        );
        const result = await page.evaluate(() => ({
          width: innerWidth,
          scrollWidth: document.documentElement.scrollWidth,
          header: [...document.querySelectorAll(".sh-brand,.sh-desktop > *,.sh-actions > *")]
            .filter((el) => el.checkVisibility() && el.getBoundingClientRect().width)
            .map((el) => {
              let r = el.getBoundingClientRect();
              return { x: r.x, right: r.right };
            }),
        }));
        assert.ok(
          result.scrollWidth <= width + 1,
          `home ${locale} ${width}: ${JSON.stringify(result)}`,
        );
        for (let i = 1; i < result.header.length; i++)
          assert.ok(
            result.header[i].x >= result.header[i - 1].right - 1,
            `home ${locale} header overlap ${width}`,
          );
        report.views.push({ home: locale, ...result });
      }
      const target = locale === "ja" ? "/for/engineers/" : "/for/en/engineers/";
      assert.equal(
        await page.locator(".engineering-home-link").getAttribute("href"),
        target,
      );
      if (locale === "ja") {
        await page
          .locator("#for-engineers")
          .screenshot({ path: path.join(output, "home-ja.png") });
        await page.locator(".engineering-home-link").click();
        assert.equal(new URL(page.url()).pathname, target);
      }
      await page.close();
    }
    const noJs = await browser.newContext({
      javaScriptEnabled: false,
      viewport: { width: 390, height: 844 },
    });
    const page = await noJs.newPage();
    await page.goto(origin + "/for/engineers/");
    assert.ok(await page.locator("noscript").isVisible());
    assert.ok(!(await page.locator("[data-example]").first().isVisible()));
    await page.locator("#levels > summary").click();
    await page.locator(".level summary").first().click();
    assert.ok(await page.locator(".level-detail").first().isVisible());
    await page.goto(origin + "/ja.html");
    assert.equal(
      await page.locator(".engineering-home-link").getAttribute("href"),
      "/for/engineers/",
    );
    await noJs.close();
    assert.deepEqual(report.errors, []);
    fs.writeFileSync(
      path.join(output, "verification.json"),
      JSON.stringify(report, null, 2) + "\n",
    );
    console.log(
      `PASS: ${report.scenarios} request/output examples, ${report.views.length} viewport/locale checks, keyboard, no-JS, local links and aligned geometry.`,
    );
  } finally {
    await browser.close();
  }
})()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(() => server.close());
