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
    assert.match(await page.getByTestId('sony-workbench').textContent(), /担当者6,000名/);
    assert.match(await page.getByTestId('transition-analysis').textContent(), /30,000/);
    assert.equal(await page.getByRole('combobox',{name:'表示する支社'}).locator('option').count(),121);
    assert.ok(await page.locator('svg').count() > 5);
    const metrics = await page.getByTestId('manager-metrics').evaluate(node => [...node.children].map(child => {const r = child.getBoundingClientRect();return {top:r.top,bottom:r.bottom};}));
    assert.ok(Math.max(...metrics.map(r=>r.top))-Math.min(...metrics.map(r=>r.top)) <= 1);
    assert.ok(Math.max(...metrics.map(r=>r.bottom))-Math.min(...metrics.map(r=>r.bottom)) <= 1);
    async function checkCharts(selector) {
      const edges = await page.getByTestId(selector).evaluate(node => [...node.children].map(child => {const r = child.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom};}));
      assert.ok(Math.abs(edges[0].left-edges[1].left) <= 1);
      if (selector === 'manager-charts') {
        assert.equal(edges.length, 2);
        assert.ok(Math.abs(edges[0].right-edges[1].right) <= 1);
      } else {
        assert.equal(edges.length, 3);
        assert.ok(Math.abs(edges[0].right-edges[2].right) <= 1);
        assert.ok(Math.abs(edges[1].top-edges[2].top) <= 1);
        assert.ok(Math.abs(edges[1].bottom-edges[2].bottom) <= 1);
      }
    }
    await checkCharts('manager-charts');
    fs.mkdirSync('artifacts/fp-sample', {recursive:true});
    await page.screenshot({path:'artifacts/fp-sample/sales.png',fullPage:true});
    await page.getByRole('button',{name:'顧客体験と募集品質',exact:true}).click();
    assert.match(await page.locator('h1').innerText(), /顧客の納得/);
    await page.screenshot({path:'artifacts/fp-sample/quality.png',fullPage:true});
    await checkCharts('quality-charts');
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:'artifacts/fp-sample/quality-mobile.png',fullPage:true});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth+1), 'Mobile root must not overflow');
    assert.deepEqual(errors, []);
    assert.deepEqual(externalRequests, [], 'The sample must never contact customer services or external providers');
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode=1;});
