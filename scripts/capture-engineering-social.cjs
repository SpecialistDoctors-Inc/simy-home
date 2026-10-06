// Capture native page markup as the social preview. Run the static site locally first.
// NODE_PATH=<Playwright installation> node scripts/capture-engineering-social.cjs
const { chromium } = require("playwright");
const path = require("node:path");
(async () => {
  const origin =
    process.env.ENGINEERING_PREVIEW_ORIGIN || "http://127.0.0.1:8766";
  const browser = await chromium.launch({ channel: "chrome" });
  try {
    for (const lang of ["ja", "en"]) {
      const page = await browser.newPage({
        viewport: { width: 1200, height: 800 },
        deviceScaleFactor: 1,
        reducedMotion: "reduce",
      });
      await page.goto(
        origin + (lang === "ja" ? "/for/engineers/" : "/for/en/engineers/"),
      );
      await page.addStyleTag({
        content: `
        .simy-header { display:none; } main.site-shell { width:1200px; margin:0; border:0; }
        .hero { height:630px; padding:38px 0; box-sizing:border-box; }
        .hero .frame { width:1100px; max-width:none; }
        .hero-layout { grid-template-columns:1fr 1fr; gap:44px; }
        .hero h1 { font-size:40px; }
        .hero-copy::before { content:'SIMY / FOR ENGINEERS'; display:block; font-size:18px; font-weight:700; margin-bottom:30px; }
        .hero-actions,.hero .provider { display:none; }
        .hero-lead { font-size:16px; }
        .mission-bar { padding:16px 24px; }
        .mission-body { padding:16px 20px; }
        .mission h2 { margin:12px 0; font-size:24px; }
        .hero-process-label { margin-top:12px; padding-top:10px; }
        .hero-demo-note { margin-top:10px; }
        .comparison-side { padding-top:10px; }
      `,
      });
      await page.locator(".hero").screenshot({
        path: path.join(
          __dirname,
          `../site/assets/engineer-experience/social-${lang}.png`,
        ),
      });
      await page.close();
    }
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
