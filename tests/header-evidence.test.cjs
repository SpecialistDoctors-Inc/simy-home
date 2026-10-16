'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { spawnSync } = require('node:child_process');
const { reconcileEvidence } = require('../scripts/reconcile-header-evidence.cjs');
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
async function fixture(t) {
  const parent = await fs.mkdtemp(path.join(os.tmpdir(), 'header-evidence-'));
  t.after(() => fs.rm(parent, { recursive: true, force: true }));
  const root = path.join(parent, 'allowed'); await fs.mkdir(root);
  const bytes = ['image-one', 'image-two', 'image-three', 'image-four'].map(Buffer.from);
  const refs = bytes.map((value, index) => ({ path: `image-${index}.png`, sha256: hash(value) }));
  const matrix = { context: { source_revisions: { 'simy-home': 'historical-head' } }, residual_risks: ['physical iPhone not observed'], results: [
    { id: 'AC-1', layers: { user: { status: 'passed', evidence: refs.slice(0, 2) } } },
    { id: 'AC-2.work/language/layout/account', layers: { user: { status: 'unknown', evidence: refs.slice(2) } } },
    { id: 'AC-3', layers: { system: { status: 'failed', evidence: [structuredClone(refs[0])] } } },
  ] };
  return { parent, root, bytes, refs, matrix };
}
test('old path-only access fails; proven alternate content repairs only separate report', async t => {
  const f = await fixture(t); const original = structuredClone(f.matrix);
  for (let i = 0; i < 4; i++) await fs.writeFile(path.join(f.root, `moved-${i}.png`), f.bytes[i]);
  await assert.rejects(fs.readFile(path.join(f.root, f.refs[0].path)), { code: 'ENOENT' });
  const report = await reconcileEvidence({ matrix: f.matrix, roots: [f.root] });
  assert.equal(report.artifacts.every(a => a.status === 'relocated_by_hash'), true);
  assert.deepEqual(f.matrix, original); assert.deepEqual(report.sourceRevisions, original.context.source_revisions);
  assert.deepEqual(report.reconciledMatrix.residual_risks, original.residual_risks);
  assert.equal(report.reconciledMatrix.results[1].layers.user.status, 'unknown');
  assert.equal(report.reconciledMatrix.results[2].layers.system.status, 'failed');
  assert.equal(report.scopeComplete, false);
});
test('one of four missing triggers actual recovery only for affected artifact; valid independent evidence retained', async t => {
  const f = await fixture(t);
  for (let i = 0; i < 3; i++) await fs.writeFile(path.join(f.root, f.refs[i].path), f.bytes[i]);
  const calls = [];
  const report = await reconcileEvidence({ matrix: f.matrix, roots: [f.root], recover: async request => {
    calls.push(request); const file = path.join(f.root, 'collected-job-image.png');
    await fs.writeFile(file, f.bytes[3]);
    return { path: file, jobId: 'already-completed-job-4', sourceRevisions: request.sourceRevisions };
  } });
  assert.equal(calls.length, 1); assert.equal(calls[0].expected, f.refs[3].sha256);
  assert.equal(report.artifacts.filter(a => a.status === 'collected_recovery_receipt').length, 1);
  assert.equal(report.criteria.every(c => c.status === 'references_verified'), true);
  // A second collection finds preserved output; no worker/recovery is dispatched.
  await reconcileEvidence({ matrix: f.matrix, roots: [f.root], recover: () => assert.fail('duplicate dispatch') });
});
test('re-injected wrong image is not accepted; receipt must match bytes and source revision', async t => {
  const f = await fixture(t); await fs.writeFile(path.join(f.root, f.refs[0].path), f.bytes[1]);
  const report = await reconcileEvidence({ matrix: f.matrix, roots: [f.root], recover: async request => ({
    path: path.join(f.root, f.refs[0].path), jobId: 'wrong-image', sourceRevisions: request.sourceRevisions,
  }) });
  assert.equal(report.artifacts[0].status, 'content_mismatch'); assert.equal(report.artifacts[0].path, undefined);
  assert.equal(report.criteria[0].status, 'evidence_incomplete');
});
test('shared missing content collects one job once across acceptance rows, then adopts once per reference', async t => {
  const f = await fixture(t); let calls = 0;
  const report = await reconcileEvidence({ matrix: f.matrix, roots: [f.root], recover: async request => {
    if (request.expected !== f.refs[0].sha256) return null;
    calls++; const file = path.join(f.root, 'recovered.png'); await fs.writeFile(file, f.bytes[0]);
    return { path: file, jobId: 'one-job', sourceRevisions: request.sourceRevisions };
  } });
  assert.equal(calls, 1);
  assert.equal(report.artifacts[0].status, 'collected_recovery_receipt');
  assert.equal(report.artifacts.at(-1).status, 'reused_recovered_receipt');
});
test('adapter failure remains local and independent existing evidence is still processed', async t => {
  const f = await fixture(t); await fs.writeFile(path.join(f.root, f.refs[3].path), f.bytes[3]);
  const report = await reconcileEvidence({ matrix: f.matrix, roots: [f.root], recover: () => { throw new Error('collector offline'); } });
  assert.equal(report.artifacts[0].recoveryError, 'collector offline');
  assert.equal(report.artifacts.find(a => a.originalPath === 'image-3.png').status, 'verified');
});
test('wrong source receipt rejected without promoting acceptance; later verified bytes can be relocated', async t => {
  const f = await fixture(t); const file = path.join(f.root, 'later.png');
  let calls = 0;
  const recover = async request => { if (request.expected !== f.refs[0].sha256) return null; calls++; await fs.writeFile(file, f.bytes[0]); return {
    path: file, jobId: 'same-completed-job', sourceRevisions: { 'simy-home': 'wrong-head' },
  }; };
  const report = await reconcileEvidence({ matrix: f.matrix, roots: [f.root], recover });
  assert.equal(report.artifacts[0].path, undefined);
  // Existing bytes are now verifiable as content, but do not claim the wrong receipt matched.
  const next = await reconcileEvidence({ matrix: f.matrix, roots: [f.root] });
  assert.equal(next.artifacts[0].status, 'relocated_by_hash'); assert.equal(calls, 1);
});
test('unknown and duplicate IDs do not become accepted requirements; missing risks not fabricated', async t => {
  const f = await fixture(t); delete f.matrix.residual_risks;
  f.matrix.results[1].id = 'AC-2.other';
  f.matrix.results.push(structuredClone(f.matrix.results[0]));
  const report = await reconcileEvidence({ matrix: f.matrix, roots: [f.root] });
  assert.equal(report.criteria[0].status, 'missing_or_duplicate_acceptance');
  assert.equal(report.criteria[1].status, 'missing_or_duplicate_acceptance');
  assert.equal(Object.hasOwn(report.reconciledMatrix, 'residual_risks'), false);
});
test('symlink and traversal cannot read unapproved evidence roots or adopt an external receipt', async t => {
  const f = await fixture(t); const outside = path.join(f.parent, 'private.png'); await fs.writeFile(outside, f.bytes[0]);
  await fs.symlink(outside, path.join(f.root, f.refs[0].path));
  f.matrix.results[0].layers.user.evidence[1].path = '../private.png';
  const report = await reconcileEvidence({ matrix: f.matrix, roots: [f.root], recover: request => ({
    path: outside, jobId: 'external', sourceRevisions: request.sourceRevisions,
  }) });
  assert.equal(report.artifacts.every(a => !a.path), true);
});
test('CLI consumes real matrix format without starting commands or overwriting evidence', async t => {
  const f = await fixture(t); const source = path.join(f.parent, 'matrix.json');
  await fs.writeFile(source, JSON.stringify(f.matrix));
  for (let i = 0; i < 4; i++) await fs.writeFile(path.join(f.root, f.refs[i].path), f.bytes[i]);
  const output = path.join(f.parent, 'output.json');
  const script = path.resolve(__dirname, '../scripts/reconcile-header-evidence.cjs');
  const run = spawnSync(process.execPath, [script, '--matrix', source, '--root', f.root, '--output', output], { encoding: 'utf8' });
  assert.equal(run.status, 0, run.stderr); assert.equal(JSON.parse(await fs.readFile(output)).scopeComplete, false);
  const repeated = spawnSync(process.execPath, [script, '--matrix', source, '--root', f.root, '--output', output], { encoding: 'utf8' });
  assert.equal(repeated.status, 1); assert.match(repeated.stderr, /EEXIST/);
  assert.deepEqual(JSON.parse(await fs.readFile(source)), f.matrix);
});

test('non-Error adapter rejection cannot abort independent evidence collection', async t => {
  const f = await fixture(t); await fs.writeFile(path.join(f.root, f.refs[3].path), f.bytes[3]);
  for (const rejection of [null, undefined]) {
    const report = await reconcileEvidence({ matrix: f.matrix, roots: [f.root], recover: () => Promise.reject(rejection) });
    assert.equal(report.artifacts[0].recoveryError, String(rejection));
    assert.equal(report.artifacts.find(a => a.originalPath === 'image-3.png').status, 'verified');
  }
});
