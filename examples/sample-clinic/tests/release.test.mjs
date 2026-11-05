import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { artifactHash, build } from '../build.mjs';
import { prepareProduction, validateApproval, validateSource } from '../release.mjs';

const sha = 'a'.repeat(40);
const approval = { artifactId: '123', sourceSha: sha, hash: 'b'.repeat(64), requestId: '3ebf607c-e242-436a-b1cd-0feae476e1ab', revision: '1', approvalRef: 'test-fixture-approval' };
const repository = 'SpecialistDoctors-Inc/simy-home';
const sourceRun = { id: 456, repository: { full_name: repository }, head_repository: { full_name: repository }, head_branch: 'dev', head_sha: sha, path: '.github/workflows/deploy-sample-clinic.yml', event: 'push', status: 'completed', conclusion: 'success', run_attempt: 1 };
const sourceArtifact = { id: 123, expired: false, name: `sample-clinic-dev-${sha}-1`, workflow_run: { id: 456, head_branch: 'dev', head_sha: sha } };

test('promotion requires complete approval inputs and a successful trusted dev artifact', () => {
  assert.equal(validateSource(sourceArtifact, sourceRun, approval, repository), 456);
  for (const key of Object.keys(approval)) assert.throws(() => validateApproval({ ...approval, [key]: '' }));
  for (const patch of [{ conclusion: 'failure' }, { status: 'in_progress' }, { event: 'pull_request' }, { head_branch: 'main' }, { head_sha: 'c'.repeat(40) }, { path: '.github/workflows/other.yml' }, { head_repository: { full_name: 'someone/fork' } }, { repository: { full_name: 'someone/fork' } }, { run_attempt: 2 }]) {
    assert.throws(() => validateSource(sourceArtifact, { ...sourceRun, ...patch }, approval, repository));
  }
  for (const patch of [{ expired: true }, { id: 999 }, { name: 'other' }, { workflow_run: { id: 999, head_branch: 'dev', head_sha: sha } }]) {
    assert.throws(() => validateSource({ ...sourceArtifact, ...patch }, sourceRun, approval, repository));
  }
});

test('production promotes identical static bytes and rejects tampering or a different request', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'clinic-promotion-'));
  try {
    const content = JSON.parse(await readFile(new URL('../content/clinic.json', import.meta.url), 'utf8'));
    content.changeRequest = { id: approval.requestId, revision: 1 };
    const contentPath = path.join(directory, 'input.json');
    await writeFile(contentPath, JSON.stringify(content));
    const output = path.join(directory, 'dist');
    const manifest = await build({ output, contentPath, environment: 'dev', revision: sha });
    const input = { ...approval, hash: manifest.artifactHash };
    const originalHtml = await readFile(path.join(output, 'index.html'), 'utf8');
    await assert.rejects(prepareProduction(output, { ...input, revision: '2' }, 'c'.repeat(40)), /request revision/);
    await assert.rejects(prepareProduction(output, { ...input, hash: 'd'.repeat(64) }, 'c'.repeat(40)), /identity differs/);
    await writeFile(path.join(output, 'index.html'), 'tampered');
    await assert.rejects(prepareProduction(output, input, 'c'.repeat(40)), /static bytes differ/);
    await writeFile(path.join(output, 'index.html'), originalHtml);
    const production = await prepareProduction(output, input, 'c'.repeat(40));
    assert.equal(production.environment, 'prod');
    assert.equal(production.sourceRevision, sha);
    assert.equal(production.releaseRevision, 'c'.repeat(40));
    assert.equal(production.sourceArtifactId, '123');
    assert.equal(production.approvalRecordRef, undefined);
    assert.equal(await artifactHash(output), manifest.artifactHash);
    assert.equal(await readFile(path.join(output, 'index.html'), 'utf8'), originalHtml);
    await assert.rejects(prepareProduction(output, input, 'c'.repeat(40)), /dev artifact/);
  } finally { await rm(directory, { recursive: true, force: true }); }
});
