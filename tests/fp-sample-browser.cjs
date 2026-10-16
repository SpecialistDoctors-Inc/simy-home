// Standalone sample in an isolated CI browser, never production customer data.
const { chromium } = require(process.env.FP_SAMPLE_PLAYWRIGHT);
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://127.0.0.1:8347/samples/fp-management/');
    await page.locator('[data-testid="sony-workbench"][data-ready="true"]').waitFor();
    assert.match(await page.locator('h1').innerText(), /次の面談/);
    assert.ok(await page.locator('svg').count() > 5);
    fs.mkdirSync('artifacts/fp-sample', {recursive:true});
    await page.screenshot({path:'artifacts/fp-sample/sales.png',fullPage:true});
    await page.getByRole('button',{name:'顧客体験と募集品質',exact:true}).click();
    assert.match(await page.locator('h1').innerText(), /顧客の納得/);
    await page.screenshot({path:'artifacts/fp-sample/quality.png',fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:'artifacts/fp-sample/quality-mobile.png',fullPage:true});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth+1), 'Mobile root must not overflow');
    assert.deepEqual(errors, []);
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode=1;});
