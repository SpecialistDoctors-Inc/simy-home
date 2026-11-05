// NODE_PATH=<existing Playwright installation> node scripts/capture-engineering-locales.cjs
// Render static, localized HTML illustrations. No live app, accounts, or API calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
const source = path.join(__dirname, 'engineer-captures');
const assets = path.join(root, 'site/assets/engineer-experience');
const english = JSON.parse(fs.readFileSync(path.join(source, 'en.json'), 'utf8'));
const locales = ['en', 'es', 'fr', 'hi', 'zh-Hans'];
const japanese = /[\u3040-\u30ff\u3400-\u9fff]/u;
const names = ['threads-progress', 'threads-decision', 'threads-outcome', 'quality-incident', 'quality-knowledge'];
(async () => {
  const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' });
  try {
    for (const lang of locales) {
    const localized = lang === 'en' ? {} : JSON.parse(fs.readFileSync(path.join(source, `${lang}.json`), 'utf8'));
    for (const name of names) {
      const threads = name.startsWith('threads-');
      const page = await browser.newPage({
        viewport: { width: threads ? 1280 : 1440, height: threads ? 960 : name === 'quality-incident' ? 1260 : 1020 },
        deviceScaleFactor: threads ? 1.5 : 1,
        reducedMotion: 'reduce',
      });
      page.on('request', request => assert.equal(new URL(request.url()).protocol, 'file:', 'Captures must be self-contained'));
      await page.goto(pathToFileURL(path.join(source, `${name}.html`)).href);
      const missing = await page.evaluate(({ english, localized, lang }) => {
        document.documentElement.lang = lang;
        document.title = 'SIMY — Localized screen illustration';
        const missing = [];
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
          const original = node.textContent.trim();
          if (!original) continue;
          const key = english[original] ?? original;
          let text = key;
          if (lang !== 'en') {
            if (Object.hasOwn(localized, key)) text = localized[key];
            else if (!/^[\d\s:/.%✓›●↗—+−-]+$/u.test(key) && !/^(SIMY|Threads|PR|DOC|\d+h \d+m|SpecialistDoctors-Inc\/simy-web)$/u.test(key)) missing.push(key);
          } else if (/[\u3040-\u30ff\u3400-\u9fff]/u.test(key)) missing.push(key);
          node.textContent = node.textContent.replace(original, text);
        }
        return missing;
      }, { english, localized, lang });
      assert.deepEqual(missing, [], `${name}: missing translations`);
      if (lang !== 'zh-Hans') assert.ok(!japanese.test(await page.locator('body').innerText()), `${lang} ${name}: Japanese text remains`);
      if (threads && lang !== 'en') await page.addStyleTag({ content: `
        .threadmeta { flex-wrap: wrap; align-items: flex-start; }
        .threadmeta > span { flex: 0 0 auto; max-width: 100%; white-space: normal; overflow: visible; }
        .threadtitle { white-space: normal; }
      ` });
      await page.evaluate(() => document.fonts.ready);
      const overflow = await page.evaluate(() => {
        const violations = [];
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
          if (!node.textContent.trim()) continue;
          const parent = node.parentElement;
          if (!parent.getClientRects().length) continue;
          const range = document.createRange(); range.selectNodeContents(node);
          const r = range.getBoundingClientRect();
          if (r.right > innerWidth + 1 || r.left < -1) violations.push(node.textContent.trim());
          // Check direct text controls where clipping/nowrap could hide translations.
          if (['BUTTON', 'SELECT'].includes(parent.tagName) && parent.scrollWidth > parent.clientWidth + 1) violations.push(node.textContent.trim());
        }
        return violations;
      });
      assert.deepEqual(overflow, [], `${name}: text overflows`);
      await page.screenshot({ path: path.join(assets, `${name}-${lang}.png`), fullPage: true });
      console.log(`Rendered ${name}-${lang}.png`);
      await page.close();
    }
    }
    const manifest = fs.readdirSync(assets).filter(name => name.endsWith('.png')).sort().map(file => {
      const data = fs.readFileSync(path.join(assets, file));
      return { file, width: data.readUInt32BE(16), height: data.readUInt32BE(20), bytes: data.length,
        sha256: require('node:crypto').createHash('sha256').update(data).digest('hex') };
    });
    fs.writeFileSync(path.join(root, 'docs/engineer-wow/asset-manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
