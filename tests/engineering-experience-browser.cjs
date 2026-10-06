// NODE_PATH=<existing Playwright installation> node tests/engineering-experience-browser.cjs
// Local static files and synthetic demonstrations only; no remote mutations.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");
const { chromium } = require("playwright");
const root = path.resolve(__dirname, "..");
const site = path.join(root, "site");
const output =
  process.env.ENGINEERING_EVIDENCE_DIR ||
  path.join(root, "docs/engineer-wow/screenshots");
const types = {
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
      decodeURIComponent(url.pathname) +
      (url.pathname.endsWith("/") ? "index.html" : ""),
  );
  if (!file.startsWith(site + path.sep)) return res.writeHead(403).end();
  fs.readFile(file, (err, data) => {
    if (err) return res.writeHead(404).end();
    res
      .writeHead(200, {
        "Content-Type": types[path.extname(file)] || "application/octet-stream",
      })
      .end(data);
  });
});
const report = { viewports: [], frames: [], checks: [], errors: [] };
(async () => {
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({
    channel: process.env.PLAYWRIGHT_CHANNEL || "chrome",
  });
  fs.mkdirSync(output, { recursive: true });
  try {
    for (const lang of ["ja", "en"]) {
      const route = lang === "ja" ? "/for/engineers/" : "/for/en/engineers/";
      const p = await browser.newPage({
        viewport: { width: 1440, height: 1000 },
        reducedMotion: "reduce",
      });
      p.on("pageerror", (e) => report.errors.push(e.message));
      p.on("console", (m) => {
        if (m.type() === "error") report.errors.push(m.text());
      });
      p.on("response", (r) => {
        if (r.status() >= 400) report.errors.push(`${r.status()} ${r.url()}`);
      });
      await p.goto(origin + route);
      await p.locator(".hero .secondary").click();
      const entry = await p.evaluate(() => ({
        story: document.querySelector("#scene-build").getBoundingClientRect()
          .top,
        header: document.querySelector(".simy-header").getBoundingClientRect()
          .bottom,
      }));
      assert.ok(
        entry.story >= entry.header - 1 && entry.story <= entry.header + 32,
        `Hero anchor lands immediately after header: ${JSON.stringify(entry)}`,
      );
      assert.equal(await p.locator(".experience-story:visible").count(), 3);
      for (const width of [360, 390, 768, 1440, 720]) {
        await p.setViewportSize({ width, height: width === 720 ? 500 : 1000 });
        const heroGeometry = await p
          .locator("[data-hero-demo]")
          .evaluate((hero) =>
            [...hero.querySelectorAll(".mini-receipt")].map((e) => {
              const r = e.getBoundingClientRect(),
                parent = e.parentElement.getBoundingClientRect();
              return {
                fits:
                  e.scrollWidth <= e.clientWidth + 1 &&
                  r.bottom <= parent.bottom + 1,
              };
            }),
          );
        assert.ok(
          heroGeometry.every((r) => r.fits),
          `${lang} ${width} hero receipts fit`,
        );
        assert.equal(await p.locator("[data-hero-replay]").isVisible(), false);
        for (const id of ["build", "progress", "knowledge"]) {
          const demo = p.locator(`[data-demo="${id}"]`);
          const heights = [];
          for (let i = 0; i < 3; i++) {
            await demo.locator(`[data-step="${i}"]`).focus();
            await p.keyboard.press(i % 2 ? "Space" : "Enter");
            assert.equal(await demo.locator(".demo-frame:visible").count(), 1);
            assert.equal(
              await demo
                .locator(`[data-step="${i}"]`)
                .getAttribute("aria-pressed"),
              "true",
            );
            const frame = demo.locator(`[data-frame="${i}"]`);
            await frame.locator("img").evaluate((i) => i.decode());
            heights.push(
              await demo
                .locator(".demo-stage")
                .evaluate((e) => e.getBoundingClientRect().height),
            );
            assert.equal(await demo.getAttribute("data-playing"), "false");
            if (width === 1440) {
              await p.locator(`#scene-${id}`).screenshot({
                path: path.join(output, `${lang}-${id}-${i}.png`),
              });
              report.frames.push(`${lang}:${id}:${i}`);
            }
          }
          assert.ok(
            Math.max(...heights) - Math.min(...heights) <= 1,
            `${lang} ${width} ${id} frame height shifts: ${heights}`,
          );
          await demo.locator("[data-motion]").click();
          assert.equal(
            await demo.locator('[data-step="0"]').getAttribute("aria-pressed"),
            "true",
          );
        }
        const geometry = await p.evaluate(() => {
          const overflow = [...document.querySelectorAll("main a, main button")]
            .filter((e) => e.getClientRects().length)
            .filter((e) => {
              const r = e.getBoundingClientRect();
              return r.left < -1 || r.right > innerWidth + 1;
            })
            .map((e) => e.textContent);
          const borders = [
            ...document.querySelectorAll(".experience-story"),
          ].map((e) => getComputedStyle(e).borderTopWidth);
          return {
            scrollWidth: document.documentElement.scrollWidth,
            width: innerWidth,
            overflow,
            borders,
          };
        });
        assert.ok(geometry.scrollWidth <= width + 1);
        assert.deepEqual(geometry.overflow, []);
        assert.deepEqual(geometry.borders, ["1px", "1px", "1px"]);
        report.viewports.push({ lang, ...geometry });
        if ([390, 1440].includes(width)) {
          await p.locator("[data-hero-demo]").screenshot({
            path: path.join(output, `${lang}-${width}-hero-demo.png`),
          });
          await p.locator(".engineer-close").screenshot({
            path: path.join(output, `${lang}-${width}-closing.png`),
          });
          await p.evaluate(() => scrollTo(0, 0));
          await p.screenshot({
            path: path.join(output, `${lang}-${width}-first-screen.png`),
          });
          await p.screenshot({
            path: path.join(output, `${lang}-${width}.png`),
            fullPage: true,
          });
        }
      }
      for (const width of [414, 430, 851, 900]) {
        await p.setViewportSize({ width, height: 1000 });
        const fit = await p
          .locator("[data-hero-demo]")
          .evaluate((hero) =>
            [...hero.querySelectorAll(".mini-receipt")].every(
              (e) =>
                e.scrollWidth <= e.clientWidth + 1 &&
                e.getBoundingClientRect().bottom <=
                  e.parentElement.getBoundingClientRect().bottom + 1,
            ),
          );
        assert.ok(fit, `${lang} ${width} hero receipt fits`);
      }
      await p.goto(origin + route + "?private=not-shared#scene-knowledge");
      await p.evaluate(() =>
        Object.defineProperty(navigator, "clipboard", {
          configurable: true,
          value: {
            writeText: async (text) => {
              window.__copied = text;
            },
          },
        }),
      );
      await p.locator('[data-share="knowledge"]').click();
      const copied = await p.evaluate(() => window.__copied);
      assert.equal(copied, origin + route + "#scene-knowledge");
      assert.ok(
        (await p.locator("#scene-knowledge [data-share-status]").textContent())
          .length > 0,
      );
      assert.equal(
        await p.locator("#scene-build [data-share-status]").textContent(),
        "",
      );
      await p.evaluate(() =>
        Object.defineProperty(navigator, "clipboard", {
          configurable: true,
          value: {
            writeText: async () => {
              throw Error("denied");
            },
          },
        }),
      );
      await p.locator('[data-share="knowledge"]').click();
      await p.locator("#share-knowledge").waitFor({ state: "visible" });
      assert.equal(await p.locator("#share-knowledge").inputValue(), copied);
      assert.equal(
        await p
          .locator("#share-knowledge")
          .evaluate((e) => document.activeElement === e),
        true,
      );
      await p.goto(copied);
      assert.equal(await p.locator("#scene-knowledge").isVisible(), true);
      for (const [old, next] of [
        ["outcome", "build"],
        ["decision", "progress"],
      ]) {
        await p.goto(origin + route + "#scene-" + old);
        await p.waitForURL(origin + route + "#scene-" + next);
      }
      await p.close();
    }
    // Verify actual timed progression, pause, offscreen suspension and OS preference changes.
    const p = await browser.newPage({
      viewport: { width: 390, height: 700 },
      reducedMotion: "no-preference",
    });
    await p.goto(origin + "/for/engineers/");
    await p.bringToFront();
    const hero = p.locator("[data-hero-demo]");
    await p
      .locator(".hero-comparison")
      .evaluate((e) =>
        scrollTo(0, e.getBoundingClientRect().top + scrollY - innerHeight + 10),
      );
    await p.evaluate(
      () =>
        new Promise((r) =>
          requestAnimationFrame(() => requestAnimationFrame(r)),
        ),
    );
    assert.notEqual(
      await hero.getAttribute("data-hero-running"),
      "true",
      "Does not spend animation when only the top edge is visible",
    );
    await p.locator(".hero-comparison").scrollIntoViewIfNeeded();
    await p.waitForFunction(
      () =>
        document.querySelector("[data-hero-demo]").dataset.heroRunning ===
        "true",
    );
    await p.waitForFunction(
      () =>
        document.querySelector("[data-hero-demo]").dataset.heroRunning ===
        "false",
    );

    await p.locator("[data-hero-replay]").focus();
    await p.keyboard.press("Enter");
    assert.equal(await hero.getAttribute("data-hero-running"), "true");
    await p.waitForFunction(
      () =>
        document.querySelector("[data-hero-demo]").dataset.heroRunning ===
        "false",
      null,
      { timeout: 4000 },
    );
    await p.emulateMedia({ reducedMotion: "reduce" });
    await p.locator("[data-hero-replay]").waitFor({ state: "hidden" });
    await p.emulateMedia({ reducedMotion: "no-preference" });
    await p.setViewportSize({ width: 1440, height: 1000 });
    const demo = p.locator('[data-demo="build"]');
    await demo.scrollIntoViewIfNeeded();
    await p.waitForFunction(
      () =>
        document.querySelector('[data-demo="build"]').dataset.playing ===
        "true",
    );
    const first = await demo
      .locator('[aria-pressed="true"]')
      .getAttribute("data-step");
    await p.waitForFunction(
      (first) =>
        document.querySelector('[data-demo="build"] [aria-pressed="true"]')
          .dataset.step !== first,
      first,
      { timeout: 7000 },
    );
    await demo.locator("[data-motion]").click();
    const stopped = await demo
      .locator('[aria-pressed="true"]')
      .getAttribute("data-step");
    await p.waitForTimeout(4400);
    assert.equal(
      await demo.locator('[aria-pressed="true"]').getAttribute("data-step"),
      stopped,
    );
    await demo.locator("[data-motion]").click();
    await p.locator(".hero").scrollIntoViewIfNeeded();
    await p.waitForFunction(
      () =>
        document.querySelector('[data-demo="build"]').dataset.playing ===
        "false",
    );
    await demo.scrollIntoViewIfNeeded();
    await p.emulateMedia({ reducedMotion: "reduce" });
    await p.waitForFunction(
      () =>
        document.querySelector('[data-demo="build"]').dataset.playing ===
        "false",
    );
    const reducedStep = await demo
      .locator('[aria-pressed="true"]')
      .getAttribute("data-step");
    await p.waitForTimeout(4400);
    assert.equal(
      await demo.locator('[aria-pressed="true"]').getAttribute("data-step"),
      reducedStep,
    );
    const animations = await demo.evaluate(
      (e) =>
        [...e.querySelectorAll("*")].filter(
          (n) => getComputedStyle(n).animationName !== "none",
        ).length,
    );
    assert.equal(animations, 0);
    await p.emulateMedia({ reducedMotion: "no-preference" });
    await demo.locator(".demo-frame:visible a").focus();
    assert.equal(await demo.getAttribute("data-playing"), "false");
    report.checks.push(
      "Timed progression, pause/resume, offscreen suspension, live reduced-motion and focus pause",
    );
    await p.close();
    const noJs = await browser.newPage({
      javaScriptEnabled: false,
      viewport: { width: 390, height: 844 },
    });
    await noJs.goto(origin + "/for/engineers/");
    assert.equal(await noJs.locator(".experience-story:visible").count(), 3);
    assert.equal(await noJs.locator("[data-motion]:visible").count(), 0);
    for (const id of ["build", "progress", "knowledge"]) {
      await noJs.locator(`#scene-${id} .demo-transcript summary`).click();
      assert.equal(
        await noJs.locator(`#scene-${id} .demo-transcript li:visible`).count(),
        3,
      );
    }
    report.checks.push(
      "No-JS all three stories and all nine stage transcripts/links; clipboard success/fallback; deep links; keyboard",
    );
    await noJs.close();
    assert.deepEqual(report.errors, []);
    fs.writeFileSync(
      path.join(output, "verification.json"),
      JSON.stringify(report, null, 2) + "\n",
    );
    console.log(
      `PASS: ${report.frames.length} frame captures; ${report.viewports.length} viewport checks; motion, keyboard, sharing, no-JS; zero errors`,
    );
  } finally {
    await browser.close();
  }
})()
  .catch((e) => {
    console.error(e);
    process.exitCode = 1;
  })
  .finally(() => server.close());
