const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const base = process.env.PREVIEW_TEST_URL || 'http://127.0.0.1:8936';
const catalog = require('../scripts/hp-management-industries.json').industries;
const sites = [
  {host: 'clinic.example', title: 'サンプルクリニック', category: '休診情報', heading: '休診のお知らせ'},
  {host: 'law.example', title: 'サンプル法律事務所', category: '新着情報', heading: '休業のお知らせ'},
  {host: 'property.example', title: 'サンプル不動産', category: '更新情報', heading: '営業時間のお知らせ'},
];

async function submit(page, message) {
  await page.locator('#preview-edit-message').fill(message);
  await page.locator('#preview-send').click();
  await page.locator('#preview-send:enabled').waitFor();
}

async function checkEntry(browser, industry) {
  const page = await browser.newPage({viewport: {width: 1280, height: 900}});
  page.setDefaultTimeout(15000);
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  const requests = [];
  let selected;
  let releasePendingEdit;
  const pendingEdit = new Promise(resolve => {releasePendingEdit = resolve;});
  try {
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.origin === base) return route.continue();
      if (url.pathname === '/api/scan') {
        const {url} = route.request().postDataJSON();
        return route.fulfill({json: {url, checkedAt: new Date().toISOString(), findings: [{
          id: 'preview-fixture', title: '表示確認', state: 'review', summary: '合成サイトの診断です。',
          evidence: '', fix: '', reference: '',
        }], technologies: [], scripts: {libraries: [], resources: []}}});
      }
      if (url.pathname === '/api/report-registration') {
        const {id} = route.request().postDataJSON();
        return route.fulfill({status: 202, json: {status: 'registered', receiptId: id}});
      }
      if (url.pathname === '/api/rebuild') {
        const payload = route.request().postDataJSON();
        const hostname = new URL(payload.url).hostname;
        selected = sites.find(site => site.host === hostname)
          || (hostname === 'property-next.example' ? sites.at(-1) : null);
        assert.ok(selected);
        assert.equal(payload.rightsConfirmed, true);
        return route.fulfill({json: {mode: 'static-html5-preview', html:
          '<title>' + selected.title + '</title><main><h1>' + selected.title +
          '</h1><section data-test-notice' + (selected.category === '休診情報' ? '' : ' class="news"') + '><h2>' + selected.category + '</h2><dl><dt>2026/11/18</dt>' +
          '<dd>既存のお知らせです。</dd></dl></section>' +
          '<section><h2>受付枠</h2><dl><dt>2026/11/20</dt><dd>受付時間を選ぶ</dd></dl></section></main>'}});
      }
      if (url.pathname === '/api/preview-edit') {
        const payload = route.request().postDataJSON();
        requests.push(payload);
        if (payload.request === '前のサイトへの依頼') {
          await pendingEdit;
          try {
            await route.fulfill({json: {status: 'clarify', question: '前のサイトについての質問',
              context: {goal: '前のサイトの編集', target: '', decisions: '', pending: ''}}});
          } catch {
            // Changing sites aborts the browser request while its server work is still pending.
          }
          return;
        }
        if (payload.request === '接続エラーの確認') return route.fulfill({status: 503, json: {error: '変更案を作成できませんでした。'}});
        const news = payload.nodes.filter(node => node.kind === 'news');
        assert.equal(news.length, 1);
        if (payload.request === '明日は休み') {
          return route.fulfill({json: {status: 'clarify', question: '終日のお休みですか？'}});
        }
        return route.fulfill({json: {status: 'edit', summary: 'お知らせを追加しました。', operations: [{
          type: 'insert_notice', target: news[0].id, date: '2026-11-19',
          title: selected.heading, body: '11月20日はお休みです。',
        }]}});
      }
      return route.abort();
    });

    const frame = page.frameLocator('#rebuild-preview');
    await page.goto(base + '/' + industry.source, {waitUntil: 'domcontentloaded'});
    const input = page.locator('#preview-edit-message');
    if (industry.id === 'law-firm') {
      await page.locator('#jump-update').click();
      await frame.locator('[data-sample-notices]').waitFor();
      assert.equal(requests.length, 0);
      const photo = await page.evaluate(() => {
        const canvas = document.createElement('canvas');
        canvas.width = canvas.height = 64;
        canvas.getContext('2d').fillRect(0, 0, 64, 64);
        return canvas.toDataURL('image/png').split(',')[1];
      });
      assert.equal(await input.inputValue(), 'お知らせ：ホームページを更新しました。');
      await page.locator('#preview-photo').setInputFiles({
        name: 'sample.png', mimeType: 'image/png', buffer: Buffer.from(photo, 'base64'),
      });
      await page.locator('#preview-photo-status').getByText('添付：sample.png').waitFor();
      assert.equal(await input.inputValue(), '写真を変更');
      await page.locator('#preview-send').click();
      await frame.locator('[data-sample-photo] img').waitFor();
      const content = '写真付きのご案内を更新しました。';
      await submit(page, 'お知らせ：' + content);
      await frame.getByText(content, {exact: true}).waitFor();
      await submit(page, 'この文章をお知らせに追加');
      await page.getByText(/操作例を選ぶか/).waitFor();
      assert.equal(await frame.locator('[data-sample-notices] li').count(), 2);

      assert.equal(requests.length, 0);
      await page.locator('#rebuild-editor-close').click();
      await page.locator('#try-article').click();
      await frame.getByRole('heading', {name: '初めて相続をご相談される方へ'}).waitFor();
      await page.locator('#preview-send').click();
      await frame.getByText(/初回相談にお持ちいただく資料について/).waitFor();
      await page.locator('[popovertarget=preview-tools]').click();
      await page.locator('[data-sample-action=rewrite]').click();
      await page.locator('#preview-send').click();
      await frame.getByText(/相続の初回相談では、まず状況を伺います/).waitFor();
      assert.equal(requests.length, 0);
      await page.locator('#rebuild-editor-close').click();
    }

    for (const site of sites) {
      requests.length = 0;
      await page.locator('#rebuild-url').fill('https://' + site.host);
      await page.locator('#rebuild-form [name=rights]').check();
      await page.locator('#rebuild-form [type=submit]').click();
      await frame.getByRole('heading', {name: site.title}).waitFor();
      assert.match(await page.locator('#preview-source').innerText(), new RegExp(site.host.replace('.', '\\.')));
      assert.equal(await input.inputValue(), '');
      const enquiry = new URL(await page.locator('#preview-enquiry').getAttribute('href'));
      assert.match(enquiry.searchParams.get('body'), /事業者・団体名/);
      assert.ok(enquiry.searchParams.get('body').includes('https://' + site.host + '/'));

      await page.locator('#preview-notice-prompt').click();
      assert.equal(await input.inputValue(), 'お知らせ：ホームページを更新しました。');
      assert.equal(requests.length, 0);
      await page.locator('[popovertarget=preview-tools]').click();
      await page.locator('#preview-edit-example').click();
      assert.equal(await input.inputValue(), 'お知らせ：ホームページを更新しました。');
      assert.equal(requests.length, 0);

      await submit(page, '明日は休み');
      assert.equal(requests[0].request, '明日は休み');
      assert.equal(requests[0].siteUrl, 'https://' + site.host + '/');
      assert.match(requests[0].nodes.find(node => node.id === 'e0').context, new RegExp(site.title));
      assert.match(requests[0].nodes.find(node => node.kind === 'news').context, new RegExp(site.category));
      await page.getByText('終日のお休みですか？', {exact: true}).waitFor();
      assert.equal(await frame.locator('[data-test-notice] dd').count(), 1);

      await submit(page, 'はい、終日です。');
      assert.deepEqual(requests[1].history.map(turn => turn.text), ['明日は休み', '終日のお休みですか？']);
      await frame.getByText(/11月20日はお休みです。/).waitFor();
      assert.equal(await frame.locator('[data-test-notice] dd').count(), 2);

      if (process.env.PREVIEW_SCREENSHOTS && site.host === 'property.example') {
        const directory = process.env.PREVIEW_SCREENSHOTS;
        fs.mkdirSync(directory, {recursive: true});
        await page.screenshot({path: path.join(directory, industry.id + '-desktop.png')});
        await page.setViewportSize({width: 390, height: 844});
        await page.screenshot({path: path.join(directory, industry.id + '-mobile.png')});
        await page.setViewportSize({width: 1280, height: 900});
      }

      await submit(page, '接続エラーの確認');
      await page.getByText('変更案を作成できませんでした。', {exact: true}).waitFor();
      assert.equal(await frame.locator('[data-test-notice] dd').count(), 2);

      await page.locator('[popovertarget=preview-tools]').click();
      await page.locator('#preview-edit-undo').click();
      await frame.getByText(/11月20日はお休みです。/).waitFor({state: 'detached'});
      assert.equal(await frame.locator('[data-test-notice] dd').count(), 1);
      await page.locator('#rebuild-editor-close').click();
      console.log(industry.id, site.host, 'passed prompt, context, clarification, edit, failure and undo');
    }

    await page.locator('#rebuild-editor-open').click();
    const oldRequest = page.waitForRequest(request => request.url().endsWith('/api/preview-edit') &&
      request.method() === 'POST');
    await input.fill('前のサイトへの依頼');
    await page.locator('#preview-send').click();
    await oldRequest;
    await page.locator('#rebuild-editor-close').click();
    await page.locator('#rebuild-url').fill('https://property-next.example/');
    await page.locator('#rebuild-form [type=submit]').click();
    await frame.getByRole('heading', {name: 'サンプル不動産'}).waitFor();
    releasePendingEdit();
    await submit(page, '明日は休み');
    assert.equal(requests.at(-1).siteUrl, 'https://property-next.example/');
    assert.deepEqual(requests.at(-1).history, []);
    assert.equal(requests.at(-1).context.goal, '');
    assert.doesNotMatch(await page.locator('#preview-conversation').innerText(), /前のサイト/);
    await page.locator('#rebuild-editor-close').click();
    console.log(industry.id, 'opening a second URL isolates the in-flight edit');

    const reportUrl = 'https://property.example/';
    await page.goto(base + '/' + industry.source, {waitUntil: 'domcontentloaded'});
    await page.locator('#diagnosis-url').fill(reportUrl);
    await page.locator('#diagnosis-form button[type=submit]').click();
    await page.locator('#report-email-address').fill('tester@example.com');
    await page.locator('#report-clinic-name').fill('サンプル不動産');
    await page.locator('#report-contact-name').fill('確認担当');
    await page.locator('.report-email-consent input').check();
    await page.locator('.report-email-form button').click();
    await page.locator('.report-unlocked').waitFor();
    const inline = page.locator('[data-report-rebuild]');
    assert.equal(await inline.locator('[name=url]').inputValue(), reportUrl);
    await inline.locator('[name=rights]').check();
    const trigger = inline.locator('[type=submit]');
    await trigger.click();
    await frame.getByRole('heading', {name: 'サンプル不動産'}).waitFor();
    await page.locator('#rebuild-editor-close').click();
    await trigger.click();
    await page.locator('#rebuild-editor[open]').waitFor();
    console.log(industry.id, 'diagnosis-to-editor URL and reopen passed');
  } catch (error) {
    const state = await page.evaluate(() => ({
      editorOpen: document.querySelector('#rebuild-editor')?.open,
      previewApi: typeof window.SimyPreviewEdit,
      lawSample: typeof window.SimyLawOfficeExample,
      rebuildStatus: document.querySelector('#rebuild-status')?.textContent,
      reportStatus: document.querySelector('[data-report-rebuild] .rebuild-status')?.textContent,
      frameTitle: document.querySelector('#rebuild-preview')?.contentDocument?.title,
    }));
    console.error(industry.id, state, pageErrors);
    throw error;
  } finally {
    await page.close();
  }
}

(async () => {
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  try {
    for (const industry of catalog.filter(entry => entry.status === 'published')) {
      await checkEntry(browser, industry);
    }
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
