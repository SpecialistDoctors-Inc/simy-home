// Standalone sample in an isolated CI browser, never production customer data.
const { chromium } = require(process.env.FP_SAMPLE_PLAYWRIGHT);
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000}});
    const errors = [];
    const externalRequests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => {if (new URL(request.url()).hostname !== '127.0.0.1') externalRequests.push(request.url());});
    await page.goto('http://127.0.0.1:8347/samples/fp-management/');
    await page.locator('[data-testid="sony-workbench"][data-ready="true"]').waitFor();
    assert.match(await page.locator('h1').innerText(), /次の面談/);
    assert.ok(await page.locator('svg').count() > 5);
    for (const selector of ['manager-metrics', 'manager-charts']) {
      const edges = await page.getByTestId(selector).evaluate(node => [...node.children].map(child => {const r = child.getBoundingClientRect();return {top:r.top,bottom:r.bottom};}));
      assert.ok(Math.max(...edges.map(r=>r.top))-Math.min(...edges.map(r=>r.top)) <= 1, selector+' top edges');
      assert.ok(Math.max(...edges.map(r=>r.bottom))-Math.min(...edges.map(r=>r.bottom)) <= 1, selector+' bottom edges');
    }
    fs.mkdirSync('artifacts/fp-sample', {recursive:true});
    await page.screenshot({path:'artifacts/fp-sample/sales.png',fullPage:true});
    await page.getByRole('button',{name:'顧客体験と募集品質',exact:true}).click();
    assert.match(await page.locator('h1').innerText(), /顧客の納得/);
    await page.screenshot({path:'artifacts/fp-sample/quality.png',fullPage:true});
    const quality = await page.getByTestId('quality-charts').evaluate(node => [...node.children].map(child => {const r = child.getBoundingClientRect();return {left:r.left,right:r.right};}));
    assert.ok(Math.abs(quality[0].left-quality[2].left) <= 1);
    assert.ok(Math.abs(quality[1].right-quality[3].right) <= 1);
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:'artifacts/fp-sample/quality-mobile.png',fullPage:true});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth+1), 'Mobile root must not overflow');
    assert.deepEqual(errors, []);
    assert.deepEqual(externalRequests, [], 'The sample must never contact customer services or external providers');
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode=1;});
