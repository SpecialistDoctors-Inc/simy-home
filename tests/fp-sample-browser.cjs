// Standalone sample in an isolated CI browser, never production customer data.
const { chromium, expect } = require(process.env.FP_SAMPLE_PLAYWRIGHT);
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000}});
    const baseline = await browser.newPage({viewport:{width:1440,height:1000}});
    await baseline.goto('http://127.0.0.1:8348/samples/fp-management/');
    await baseline.locator('[data-testid="sony-workbench"][data-ready="true"]').waitFor();
    await baseline.waitForTimeout(2000);
    const baselineSales = await baseline.screenshot({fullPage:true,animations:'disabled'});
    const baselineText = await baseline.getByTestId('sony-workbench').innerText();
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
    await page.waitForTimeout(2000);
    const sales = await page.screenshot({path:'artifacts/fp-sample/sales.png',fullPage:true,animations:'disabled'});
    assert.equal(await page.getByTestId('sony-workbench').innerText(), baselineText, 'Sales text/numbers must match approved baseline');
    fs.writeFileSync('artifacts/fp-sample/sales-baseline.png',baselineSales);
    assert.ok(sales.equals(baselineSales), 'Sales screenshot must exactly match approved baseline');
    for (const target of [baseline,page]) {
      await target.getByRole('combobox',{name:'表示する支社'}).selectOption({index:1});
      await target.mouse.move(0,0);
      await target.waitForTimeout(2000);
    }
    assert.equal(await page.getByTestId('sony-workbench').innerText(),await baseline.getByTestId('sony-workbench').innerText(),'Sales branch filtering must match baseline');
    assert.ok((await page.screenshot({path:'artifacts/fp-sample/sales-branch.png',fullPage:true,animations:'disabled'})).equals(await baseline.screenshot({path:'artifacts/fp-sample/sales-branch-baseline.png',fullPage:true,animations:'disabled'})),'Filtered sales charts must match baseline');
    for (const target of [baseline,page]) await target.getByRole('combobox',{name:'表示する支社'}).selectOption({index:0});
    const salesActions = page.getByRole('button',{name:'内容を見て対応する',exact:true});
    const baselineActions = baseline.getByRole('button',{name:'内容を見て対応する',exact:true});
    const salesActionCount = await salesActions.count();
    assert.ok(salesActionCount>0);
    assert.equal(salesActionCount,await baselineActions.count());
    for (let index=0; index<salesActionCount; index++) {
      await baselineActions.nth(index).click();
      await salesActions.nth(index).click();
      const currentDetail = await page.getByRole('dialog').innerText();
      const baselineDetail = await baseline.getByRole('dialog').innerText();
      fs.writeFileSync(`artifacts/fp-sample/sales-case-${index}.json`,JSON.stringify({baseline:baselineDetail,current:currentDetail},null,2));
      assert.equal(currentDetail,baselineDetail,'Sales case details must match baseline');
      const fields = target=>target.getByRole('dialog').locator('input,textarea,select').evaluateAll(nodes=>nodes.map(n=>({tag:n.tagName,type:n.type,value:n.value})));
      assert.deepEqual(await fields(page),await fields(baseline),'Sales form defaults and options must match baseline');
      await baseline.keyboard.press('Escape');
      await page.keyboard.press('Escape');
    }
    await page.getByRole('button',{name:'顧客体験と募集品質',exact:true}).click();
    assert.match(await page.locator('h1').innerText(), /顧客の納得/);
    await page.screenshot({path:'artifacts/fp-sample/quality.png',fullPage:true});
    await checkCharts('quality-charts');
    const board = page.getByTestId('quality-review-board');
    await expect(board).toBeVisible();
    assert.ok(await board.getByLabel('品質の論点').locator('option').count() >= 17, 'At least 16 quality topics plus all');
    const feedback = page.getByTestId('quality-execution-overview');
    await expect(board.getByTestId('quality-support-queue')).toBeVisible();
    await expect(feedback).toContainText('判定済み項目数');
    await expect(feedback).toContainText('人数率ではありません');
    await expect(page.getByTestId('quality-risk-overview')).toBeVisible();
    await expect(page.getByTestId('quality-sales-overview')).toContainText('新規・更新');
    await page.getByTestId('quality-risk-overview').getByLabel('偏りを確認する対象').selectOption('product');
    await expect(page.getByTestId('quality-risk-overview')).toContainText('最多の商品');
    await board.getByLabel('品質レビューの支社').selectOption({index:1});
    await expect(board.getByTestId('quality-risk-overview')).toHaveCount(1);
    await expect(board.getByTestId('quality-execution-overview')).toHaveCount(1);
    await expect(board.getByTestId('quality-risk-overview')).toContainText('集計対象の相談 50');
    await board.getByLabel('品質レビューの支社').selectOption('all');
    await expect(board.getByTestId('quality-risk-overview')).toHaveCount(1);
    await expect(board.getByTestId('quality-execution-overview')).toHaveCount(1);
    await expect(board.getByTestId('quality-risk-overview')).toContainText('集計対象の相談 6000');
    await page.reload();
    await page.getByRole('button',{name:'顧客体験と募集品質',exact:true}).click();
    await expect(feedback).toBeVisible();
    await page.screenshot({path:'artifacts/fp-sample/feedback-implementation.png',fullPage:true});
    async function openReview(topic) {
      await board.getByLabel('品質レビューの支社').selectOption({label:'東京中央LPC第1支社'});
      await board.getByLabel('品質の論点').selectOption(topic);
      await board.getByRole('button',{name:'面談と判断を開く'}).first().click();
      return page.getByRole('dialog');
    }
    async function support(topic) {
      const dialog = await openReview(topic);
      for (const [label,value] of [
        ['元の面談日時（記録で確認）','2026-10-01T09:00'],
        ['事実：記録から分かること','選び方について質問した。'],
        ['判断に用いた規程名','面談支援基準（架空・デモ専用）'],
        ['規程の版','デモ1版'], ['条項・参照箇所','選択の支援'],
        ['今回の適用条件・面談段階','初回相談。説明前の希望確認。'],
        ['判断理由・まだ不確かなこと','本人の希望と選ぶ理由を次回確認する。'],
        ['品質対応の担当','サンプル担当者'], ['品質の再確認期限','2026-10-20'],
        ['次の支援・調べること','選択肢を図で説明し顧客の返答を聞く。']
      ]) await dialog.getByLabel(label,{exact:true}).fill(value);
      await dialog.getByLabel('今回の判断',{exact:true}).selectOption('support');
      await dialog.getByRole('button',{name:'品質レビューを保存',exact:true}).click();
      await expect(board.getByRole('status')).toContainText('このブラウザーに保存');
    }
    await support('delegation');
    await page.reload();
    await page.getByRole('button',{name:'顧客体験と募集品質',exact:true}).click();
    let dialog = await openReview('delegation');
    await expect(dialog.getByLabel('次の支援・調べること',{exact:true})).toHaveValue('選択肢を図で説明し顧客の返答を聞く。');
    await dialog.getByLabel('今回の判断',{exact:true}).selectOption('improved');
    await dialog.getByLabel('再面談記録',{exact:true}).selectOption('');
    await dialog.getByLabel('顧客の返答・残る不安',{exact:true}).fill('');
    await dialog.getByRole('button',{name:'品質レビューを保存',exact:true}).click();
    await expect(dialog.getByRole('alert')).toContainText('別の面談記録');
    await dialog.getByLabel('再面談記録',{exact:true}).selectOption({index:1});
    await dialog.getByLabel('再面談日時（記録で確認）',{exact:true}).fill('2026-10-12T09:00');
    await dialog.getByLabel('顧客の返答・残る不安',{exact:true}).fill('選ぶ理由が分かった。費用は引き続き確認する。');
    await dialog.getByRole('button',{name:'品質レビューを保存',exact:true}).click();
    await expect(board.getByRole('status')).toContainText('このブラウザーに保存');
    await page.reload();
    await page.getByRole('button',{name:'顧客体験と募集品質',exact:true}).click();
    dialog = await openReview('delegation');
    await expect(dialog.getByLabel('今回の判断',{exact:true})).toHaveValue('improved');
    await dialog.getByText(/これまでの判断と改善の履歴/).click();
    await dialog.getByText('当時の根拠と対応を確認',{exact:true}).last().click();
    await expect(dialog.getByText('選択の支援',{exact:false}).last()).toBeVisible();
    await page.screenshot({path:'artifacts/fp-sample/quality-history.png',fullPage:true});
    await page.keyboard.press('Escape');
    // A separate issue remains recurring; improvement of one issue must not overwrite it.
    await support('intent-before-product');
    dialog = await openReview('intent-before-product');
    await dialog.getByLabel('今回の判断',{exact:true}).selectOption('recurring');
    await dialog.getByLabel('再面談記録',{exact:true}).selectOption({index:1});
    await dialog.getByLabel('再面談日時（記録で確認）',{exact:true}).fill('2026-10-12T09:00');
    await dialog.getByLabel('顧客の返答・残る不安',{exact:true}).fill('費用の違いがまだ分からない。');
    await dialog.getByRole('button',{name:'品質レビューを保存',exact:true}).click();
    await expect(board.getByRole('status')).toContainText('このブラウザーに保存');
    await page.reload();
    await page.getByRole('button',{name:'顧客体験と募集品質',exact:true}).click();
    dialog = await openReview('intent-before-product');
    await expect(dialog.getByLabel('今回の判断',{exact:true})).toHaveValue('recurring');
    await expect(dialog.getByLabel('顧客の返答・残る不安',{exact:true})).toHaveValue('費用の違いがまだ分からない。');
    await page.keyboard.press('Escape');
    await page.getByRole('button',{name:'営業を前に進める',exact:true}).click();
    await page.mouse.move(0,0);
    await page.evaluate(()=>scrollTo(0,0));
    await page.waitForTimeout(2000);
    assert.equal(await page.getByTestId('sony-workbench').innerText(),baselineText);
    assert.ok((await page.screenshot({path:'artifacts/fp-sample/sales-after-quality.png',fullPage:true,animations:'disabled'})).equals(baselineSales),'Quality saves must preserve sales display');
    for (const target of [baseline,page]) {
      await target.getByRole('button',{name:'内容を見て対応する',exact:true}).first().click();
      await target.getByLabel('対応結果',{exact:true}).fill('架空の営業検証：全体像を説明し次回の確認を約束した。');
      await target.getByRole('button',{name:'対応の実施を記録',exact:true}).click();
      await expect(target.getByRole('status')).toContainText('このブラウザーに保存');
      await target.reload();
      await target.locator('[data-testid="sony-workbench"][data-ready="true"]').waitFor();
      await target.mouse.move(0,0);
      await target.evaluate(()=>scrollTo(0,0));
      await target.waitForTimeout(2000);
    }
    assert.equal(await page.getByTestId('sony-workbench').innerText(),await baseline.getByTestId('sony-workbench').innerText(),'Sales save/reload must match baseline');
    assert.ok((await page.screenshot({path:'artifacts/fp-sample/sales-after-save.png',fullPage:true,animations:'disabled'})).equals(await baseline.screenshot({path:'artifacts/fp-sample/sales-after-save-baseline.png',fullPage:true,animations:'disabled'})),'Sales save/reload charts must match baseline');
    await page.getByRole('button',{name:'顧客体験と募集品質',exact:true}).click();
    for (const width of [1440,390]) {
      await page.setViewportSize({width,height:1000});
      const boxes = await board.getByTestId('quality-review-metrics').locator(':scope > *').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom};}));
      assert.equal(boxes.length,3);
      for (const edge of width===1440?['top','bottom']:['left','right']) assert.ok(Math.max(...boxes.map(b=>b[edge]))-Math.min(...boxes.map(b=>b[edge]))<=1);
      const topicEdges = await board.getByTestId('quality-topic-bars').locator('button > div:first-child').evaluateAll(nodes=>nodes.map(n=>({labelRight:n.children[0].getBoundingClientRect().right,countLeft:n.children[1].getBoundingClientRect().left})));
      assert.ok(topicEdges.length>=16);
      for (const edge of topicEdges) assert.ok(edge.labelRight<=edge.countLeft-1,'Quality topic labels and counts must not overlap');
    }
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:'artifacts/fp-sample/quality-mobile.png',fullPage:true});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth+1), 'Mobile root must not overflow');
    await page.goto('http://127.0.0.1:8347/samples/fp-management/?view=quality');
    await expect(page.getByTestId('quality-review-board')).toBeVisible();
    assert.match(await page.locator('h1').innerText(), /顧客の納得/);
    assert.deepEqual(errors, []);
    assert.deepEqual(externalRequests, [], 'The sample must never contact customer services or external providers');
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode=1;});
