#!/usr/bin/env node
'use strict';

// Local evidence consumer only: never executes commands or changes source receipts.
const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const { parseArgs } = require('node:util');
const REQUIRED = ['AC-1', 'AC-2', 'AC-3'];
const ALIASES = new Map([['AC-2.work/language/layout/account', 'AC-2']]);
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const inside = (root, file) => file === root || (!path.relative(root, file).startsWith(`..${path.sep}`) && path.relative(root, file) !== '..' && !path.isAbsolute(path.relative(root, file)));

async function reconcileEvidence({ matrix, roots, recover, maxFiles = 10000 }) {
  if (!matrix || !Array.isArray(matrix.results)) throw new Error('Expected existing matrix.results array');
  if (!Array.isArray(roots) || !roots.length) throw new Error('Explicit evidence roots required');
  const allowed = await Promise.all(roots.map(root => fs.realpath(root)));
  const files = new Map();
  const hashes = new Map();
  let count = 0;
  // No symlink traversal. Only explicitly supplied evidence directories are indexed.
  async function walk(directory) {
    for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
      const file = path.join(directory, entry.name);
      if (entry.isSymbolicLink()) continue;
      if (++count > maxFiles) throw new Error('Evidence scan limit reached');
      if (entry.isDirectory()) await walk(file);
      else if (entry.isFile()) {
        const real = await fs.realpath(file);
        if (!allowed.some(root => inside(root, real))) continue;
        const hash = digest(await fs.readFile(real));
        files.set(real, hash);
        if (!hashes.has(hash)) hashes.set(hash, []);
        hashes.get(hash).push(real);
      }
    }
  }
  for (const root of allowed) await walk(root);
  const output = structuredClone(matrix);
  const artifacts = [];
  const accepted = new Map();
  const attempted = new Map();
  const ids = new Map();
  for (const row of output.results) {
    const id = ALIASES.get(row.id) || row.id;
    ids.set(id, (ids.get(id) || 0) + 1);
  }
  for (const row of output.results) {
    const originalId = row.id;
    const id = ALIASES.get(originalId) || originalId;
    // Unknown or duplicate acceptance IDs are never silently coalesced.
    const known = REQUIRED.includes(id) && ids.get(id) === 1;
    if (known) row.id = id;
    for (const [layer, value] of Object.entries(row.layers || {})) {
      for (const evidence of value.evidence || []) {
        const originalPath = evidence.path;
        const expected = evidence.sha256;
        const item = { id, layer, originalPath, expected, status: 'unverified' };
        artifacts.push(item);
        if (!known || typeof originalPath !== 'string' || !/^[a-f0-9]{64}$/.test(expected || '')) {
          item.reason = 'unknown_or_duplicate_acceptance_or_invalid_reference';
          continue;
        }
        const candidates = allowed.map(root => path.resolve(root, originalPath));
        const validPaths = candidates.filter(file => allowed.some(root => inside(root, file)));
        let selected = validPaths.find(file => files.get(file) === expected);
        const wrongContent = validPaths.some(file => files.has(file) && files.get(file) !== expected);
        if (selected) item.status = 'verified';
        else if (hashes.has(expected)) {
          selected = [...hashes.get(expected)].sort()[0];
          item.status = 'relocated_by_hash';
        } else if (accepted.has(expected)) {
          selected = accepted.get(expected);
          item.status = 'reused_recovered_receipt';
        } else if (recover) {
          // A caller-owned adapter can collect a completed job or reacquire this
          // artifact. One call per expected content, even when several rows use it.
          if (!attempted.has(expected)) {
            attempted.set(expected, Promise.resolve().then(() => recover({
              id, layer, originalPath, expected,
              sourceRevisions: structuredClone(matrix.context?.source_revisions || {}),
              reason: wrongContent ? 'content_mismatch' : 'missing',
            })).catch(error => ({ error: String(error?.message || error) })));
          }
          const receipt = await attempted.get(expected);
          if (receipt?.error) item.recoveryError = receipt.error;
          if (receipt?.path && receipt?.jobId && receipt?.sourceRevisions &&
              JSON.stringify(Object.entries(receipt.sourceRevisions).sort()) === JSON.stringify(Object.entries(matrix.context?.source_revisions || {}).sort())) {
            try {
              const real = await fs.realpath(receipt.path);
              if (allowed.some(root => inside(root, real)) && digest(await fs.readFile(real)) === expected) {
                selected = real;
                accepted.set(expected, real);
                item.jobId = receipt.jobId;
                item.status = 'collected_recovery_receipt';
              }
            } catch (error) { item.recoveryError = String(error?.message || error); }
          }
        }
        if (selected) {
          evidence.path = selected;
          item.path = selected;
        } else {
          item.status = wrongContent ? 'content_mismatch' : 'missing';
        }
      }
    }
  }
  const criteria = REQUIRED.map(id => ({
    id,
    status: ids.get(id) !== 1 ? 'missing_or_duplicate_acceptance' :
      artifacts.some(item => item.id === id && !item.path) ? 'evidence_incomplete' :
      !artifacts.some(item => item.id === id) ? 'no_evidence' : 'references_verified',
    // Reference integrity never promotes failed/unknown acceptance into passed.
    observedLayerStatuses: output.results.filter(row => row.id === id).flatMap(row => Object.values(row.layers || {}).map(layer => layer.status)),
  }));
  return { sourceRevisions: structuredClone(matrix.context?.source_revisions || {}),
    criteria, artifacts, reconciledMatrix: output,
    scopeComplete: false,
    limitation: 'Reference integrity only. Original acceptance statuses, risks and source revision remain unchanged; not current-candidate, visual-review, SQM or whole-purpose approval.' };
}

async function main() {
  const { values } = parseArgs({ options: { matrix: { type: 'string' }, root: { type: 'string', multiple: true }, output: { type: 'string' }, receipts: { type: 'string' } } });
  if (!values.matrix || !values.output) throw new Error('--matrix, --root and separate --output required');
  const source = await fs.realpath(values.matrix);
  const destination = path.resolve(values.output);
  if (destination === source) throw new Error('Do not overwrite source matrix');
  const matrix = JSON.parse(await fs.readFile(source, 'utf8'));
  const receipts = values.receipts ? JSON.parse(await fs.readFile(values.receipts, 'utf8')) : {};
  const report = await reconcileEvidence({ matrix, roots: values.root,
    recover: values.receipts ? async request => receipts[request.expected] : undefined });
  // Exclusive create keeps previous results/receipts immutable too.
  await fs.writeFile(destination, JSON.stringify(report, null, 2) + '\n', { flag: 'wx' });
  console.log(JSON.stringify({ output: destination, criteria: report.criteria }));
  if (report.criteria.some(row => row.status !== 'references_verified')) process.exitCode = 2;
}
if (require.main === module) main().catch(error => { console.error(error.message); process.exitCode = 1; });
module.exports = { reconcileEvidence };
