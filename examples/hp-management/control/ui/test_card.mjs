import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { transform } from 'esbuild';
const { code } = await transform(await readFile(new URL('./card.ts', import.meta.url), 'utf8'), { loader: 'ts', format: 'esm', target: 'es2022' });
const { Card, publicHttps } = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
const approval = '11111111-1111-4111-8111-111111111111';
const operation = '22222222-2222-4222-8222-222222222222';
const nonce = 'private-nonce-that-never-enters-context-123456';
function prepared(changes = {}, meta = { confirmation_nonce: nonce }) {
  return { structuredContent: { approval_id: approval, mode: 'publish', site_name: 'Example Site', summary: 'Update opening hours', preview_url: 'https://preview.example.invalid', production_url: 'https://site.example.invalid', expires_at: 1600, ...changes }, _meta: meta };
}
function harness(call = async () => ({ structuredContent: { operation_id: operation, kind: 'publish', status: 'queued' } })) {
  let now = 1000000;
  const calls = [], contexts = [], renders = [];
  const bridge = { callServerTool: async params => { calls.push(params); return call(params); }, updateModelContext: async params => { contexts.push(params); } };
  const card = new Card(bridge, view => renders.push(view), () => now);
  return { card, calls, contexts, renders, advance: milliseconds => { now += milliseconds; } };
}

test('fails closed without private meta and rejects unsafe URLs', async () => {
  for (const result of [prepared({}, {}), { structuredContent: prepared().structuredContent }, prepared({ preview_url: 'javascript:alert(1)' }), prepared({ production_url: 'http://site.example.invalid' }), { structuredContent: { ...prepared().structuredContent, confirmation_nonce: nonce } }]) {
    const h = harness(); h.card.connect(true); h.card.receive(result);
    await h.card.confirm(true);
    assert.equal(h.calls.length, 0); assert.equal(h.card.view.phase, 'error');
  }
  assert.equal(publicHttps('https://user@site.example.invalid'), null);
  assert.equal(publicHttps('not a URL'), null);
});

test('requires host connection and a trusted click, enforces TTL at click', async () => {
  const h = harness(); h.card.receive(prepared());
  await h.card.confirm(true); assert.equal(h.calls.length, 0);
  h.card.connect(true); await h.card.confirm(false); assert.equal(h.calls.length, 0);
  h.advance(600000); await h.card.confirm(true);
  assert.equal(h.card.view.phase, 'expired'); assert.equal(h.calls.length, 0);
});

test('double click and repeated prepared notifications cannot resend confirmation', async () => {
  let resolve;
  const response = new Promise(done => { resolve = done; });
  const h = harness(async () => response);
  h.card.connect(true); h.card.receive(prepared());
  const first = h.card.confirm(true);
  await h.card.confirm(true); h.card.receive(prepared()); await h.card.confirm(true);
  assert.equal(h.calls.length, 1); assert.equal(h.card.view.phase, 'sending');
  resolve({ structuredContent: { operation_id: operation, kind: 'publish', status: 'queued' } }); await first;
  assert.equal(h.card.view.phase, 'queued');
  assert.match(h.card.view.message, /まだ公開は完了していません/);
  assert.deepEqual(h.calls[0].arguments, { approval_id: approval, confirmation_nonce: nonce });
  assert.deepEqual(h.contexts[0], { content: [{ type: 'text', text: JSON.stringify({ operation_id: operation }) }] });
  assert.ok(!JSON.stringify(h.contexts).includes(nonce)); assert.ok(!JSON.stringify(h.renders).includes(nonce));
});

test('ambiguous transport failure and server rejection never allow blind retry', async () => {
  for (const call of [async () => { throw new Error('unknown save outcome'); }, async () => ({ isError: true, structuredContent: { error: 'confirmation_stale' } })]) {
    const h = harness(call); h.card.connect(true); h.card.receive(prepared());
    await h.card.confirm(true); h.card.receive(prepared()); await h.card.confirm(true);
    assert.equal(h.card.view.phase, 'error'); assert.equal(h.calls.length, 1); assert.equal(h.contexts.length, 0);
  }
});

test('explicit read reports running versus completed and never resends publish', async () => {
  let readCount = 0;
  const h = harness(async params => ({ structuredContent: { operation_id: operation, kind: 'publish', status: params.name === 'hp_confirm_publish' ? 'queued' : ++readCount === 1 ? 'running' : 'completed' } }));
  h.card.connect(true); h.card.receive(prepared()); await h.card.confirm(true);
  await h.card.refresh(true); assert.equal(h.card.view.phase, 'queued'); assert.match(h.card.view.message, /まだ完了していません/);
  await h.card.refresh(true); assert.equal(h.card.view.phase, 'completed');
  assert.deepEqual(h.calls.map(call => call.name), ['hp_confirm_publish', 'hp_get_operation', 'hp_get_operation']);
  assert.equal(h.contexts.length, 1);
});

test('malformed operation receipt cannot claim completion or leak raw errors', async () => {
  const h = harness(async () => ({ structuredContent: { operation_id: 'bad', kind: 'publish', status: 'completed', error: 'secret internal text' } }));
  h.card.connect(true); h.card.receive(prepared()); await h.card.confirm(true);
  assert.equal(h.card.view.phase, 'error'); assert.equal(h.contexts.length, 0);
  assert.ok(!JSON.stringify(h.renders).includes('secret internal text'));
});

test('retries, reconciliation and attention never invent publication completion', async () => {
  for (const status of ['retry_wait', 'reconciling', 'needs_attention', 'reporting']) {
    const h = harness(async () => ({ structuredContent: { operation_id: operation, kind: 'publish', status } }));
    h.card.connect(true); h.card.receive(prepared()); await h.card.confirm(true);
    assert.notEqual(h.card.view.phase, 'completed');
    assert.equal(h.card.view.operationId, operation);
    assert.ok(!h.card.view.message.includes('公開は完了しました'));
    await h.card.confirm(true); assert.equal(h.calls.length, 1);
  }
});

test('verified publication completion remains separate from notification trouble', async () => {
  const result = { kind: 'published', receipt: { verified: true } };
  for (const status of ['reporting', 'needs_attention', 'reconciling']) {
    const h = harness(async () => ({ structuredContent: { operation_id: operation, kind: 'publish', status, result } }));
    h.card.connect(true); h.card.receive(prepared()); await h.card.confirm(true);
    assert.match(h.card.view.message, /公開は完了しました/);
    assert.match(h.card.view.message, /記録・通知/);
    assert.notEqual(h.card.view.phase, 'completed');
  }
  const h = harness(async () => ({ structuredContent: { operation_id: operation, kind: 'publish', status: 'published_after_cancel_or_revocation', result } }));
  h.card.connect(true); h.card.receive(prepared()); await h.card.confirm(true);
  assert.match(h.card.view.message, /キャンセルまたは権限変更後/);
  assert.match(h.card.view.message, /公開済み/);
});

test('connection-test card requires private metadata and trusted click, reports only test completion', async () => {
  const h = harness(async () => ({ structuredContent: { kind: 'connection_test', status: 'completed', approval_id: approval } }));
  h.card.receive(prepared({ mode: 'connection_test' }));
  assert.equal(h.card.view.mode, 'connection_test');
  assert.match(h.card.view.message, /接続テスト.*公開は行いません/);
  await h.card.confirm(true); assert.equal(h.calls.length, 0);
  h.card.connect(true); await h.card.confirm(false); assert.equal(h.calls.length, 0);
  await h.card.confirm(true); await h.card.confirm(true);
  assert.equal(h.calls.length, 1); assert.equal(h.contexts.length, 0);
  assert.equal(h.card.view.phase, 'completed'); assert.equal(h.card.view.operationId, null);
  assert.match(h.card.view.message, /接続を確認しました.*公開は行っていません/);
  assert.ok(!JSON.stringify(h.renders).includes(nonce));
});

test('connection test cannot accept publication or another card receipt or missing private nonce', async () => {
  for (const result of [{ operation_id: operation, kind: 'publish', status: 'queued' },
      { kind: 'connection_test', status: 'completed', approval_id: operation }]) {
    const h = harness(async () => ({ structuredContent: result }));
    h.card.connect(true); h.card.receive(prepared({ mode: 'connection_test' })); await h.card.confirm(true);
    assert.equal(h.card.view.phase, 'error'); assert.equal(h.contexts.length, 0);
    assert.equal(h.card.view.operationId, null);
  }
  const h = harness(); h.card.connect(true); h.card.receive(prepared({ mode: 'connection_test' }, {}));
  await h.card.confirm(true); assert.equal(h.calls.length, 0);
  const missingMode = prepared(); delete missingMode.structuredContent.mode;
  h.card.receive(missingMode); await h.card.confirm(true); assert.equal(h.calls.length, 0);
});

test('a replacement card cannot be overwritten by an older confirmation response', async () => {
  for (const failed of [false, true]) {
    let resolve, reject;
    const pending = new Promise((done, fail) => { resolve = done; reject = fail; });
    const h = harness(async () => pending); h.card.connect(true); h.card.receive(prepared());
    const old = h.card.confirm(true);
    h.card.receive(prepared({ approval_id: operation, mode: 'connection_test' }));
    if (failed) reject(new Error('old request failed'));
    else resolve({ structuredContent: { operation_id: operation, kind: 'publish', status: 'queued' } });
    await old;
    assert.equal(h.card.view.mode, 'connection_test'); assert.equal(h.card.view.phase, 'ready');
    assert.match(h.card.view.message, /接続テスト/); assert.equal(h.contexts.length, 0);
  }
});

test('a replacement connection-test card ignores an old publication status read or failure', async () => {
  for (const failed of [false, true, 'server']) {
    let resolve, reject;
    const pending = new Promise((done, fail) => { resolve = done; reject = fail; });
    const h = harness(async params => params.name === 'hp_get_operation' ? pending :
      { structuredContent: { operation_id: operation, kind: 'publish', status: 'queued' } });
    h.card.connect(true); h.card.receive(prepared()); await h.card.confirm(true);
    const old = h.card.refresh(true);
    h.card.receive(prepared({ approval_id: operation, mode: 'connection_test' }));
    if (failed === 'server') resolve({ isError: true });
    else if (failed) reject(new Error('old read failed'));
    else resolve({ structuredContent: { operation_id: operation, kind: 'publish', status: 'completed' } });
    await old;
    assert.equal(h.card.view.mode, 'connection_test'); assert.equal(h.card.view.phase, 'ready');
    assert.equal(h.card.view.operationId, null); assert.match(h.card.view.message, /接続テスト/);
    assert.deepEqual(h.calls.map(call => call.name), ['hp_confirm_publish', 'hp_get_operation']);
  }
});
