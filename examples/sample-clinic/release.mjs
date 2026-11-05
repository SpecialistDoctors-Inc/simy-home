import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { artifactHash } from './build.mjs';

const requireValue = (valid, message) => { if (!valid) throw new Error(message); };

export function validateApproval(input) {
  requireValue(/^[1-9][0-9]*$/.test(input.artifactId), 'A GitHub artifact ID is required');
  requireValue(/^[a-f0-9]{40}$/.test(input.sourceSha), 'A full approved source SHA is required');
  requireValue(/^[a-f0-9]{64}$/.test(input.hash), 'An approved artifact hash is required');
  requireValue(/^[a-f0-9-]{36}$/.test(input.requestId), 'A request UUID is required');
  requireValue(Number.isSafeInteger(Number(input.revision)) && Number(input.revision) > 0, 'A positive request revision is required');
  requireValue(typeof input.approvalRef === 'string' && input.approvalRef.trim().length > 0 && input.approvalRef.length <= 1000, 'An approval record reference is required');
  // The reference is evidence for the human GitHub Environment reviewer, not
  // machine proof that a customer authorized publication.
  return input;
}

export function validateSource(artifact, run, input, repository) {
  validateApproval(input);
  requireValue(String(artifact.id) === input.artifactId && artifact.expired === false, 'Artifact unavailable or expired');
  requireValue(artifact.workflow_run?.id === run.id, 'Artifact run differs');
  requireValue(run.repository?.full_name === repository && run.head_repository?.full_name === repository, 'Source repository differs');
  requireValue(run.head_branch === 'dev' && artifact.workflow_run?.head_branch === 'dev', 'Only dev artifacts can be promoted');
  requireValue(run.path === '.github/workflows/deploy-sample-clinic.yml', 'Unexpected source workflow');
  requireValue(['push', 'workflow_dispatch'].includes(run.event), 'Pull request artifacts cannot be promoted');
  requireValue(run.status === 'completed' && run.conclusion === 'success', 'The dev deployment must have succeeded');
  requireValue(run.head_sha === input.sourceSha && artifact.workflow_run?.head_sha === input.sourceSha, 'Approved source SHA differs');
  requireValue(artifact.name === `sample-clinic-dev-${input.sourceSha}-${run.run_attempt}`, 'Artifact is not from the latest successful attempt');
  return run.id;
}

export async function prepareProduction(directory, input, releaseRevision) {
  validateApproval(input);
  requireValue(/^[a-f0-9]{40}$/.test(releaseRevision), 'A full main release SHA is required');
  const manifestPath = path.join(directory, 'version.json');
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  requireValue(manifest.schemaVersion === 1 && manifest.siteId === 'sample-clinic' && manifest.environment === 'dev', 'Not a sample-clinic dev artifact');
  requireValue(manifest.sourceRevision === input.sourceSha && manifest.artifactHash === input.hash, 'The approved artifact identity differs');
  requireValue(manifest.requestId === input.requestId && manifest.requestRevision === Number(input.revision), 'The approved request revision differs');
  requireValue(await artifactHash(directory) === input.hash, 'Downloaded static bytes differ from the approved artifact');
  const release = { ...manifest, environment: 'prod', releaseRevision, sourceArtifactId: input.artifactId };
  // Static bytes are promoted unchanged; only release metadata is replaced.
  await writeFile(manifestPath, JSON.stringify(release, null, 2) + '\n');
  return release;
}

function approvalFromEnvironment() {
  return { artifactId: process.env.SOURCE_ARTIFACT_ID, sourceSha: process.env.APPROVED_SOURCE_SHA, hash: process.env.APPROVED_ARTIFACT_HASH, requestId: process.env.REQUEST_ID, revision: process.env.REQUEST_REVISION, approvalRef: process.env.APPROVAL_RECORD_REF };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const input = validateApproval(approvalFromEnvironment());
  if (process.argv[2] === 'source') {
    const artifact = JSON.parse(await readFile(process.argv[3], 'utf8'));
    const run = JSON.parse(await readFile(process.argv[4], 'utf8'));
    console.log(validateSource(artifact, run, input, process.env.GITHUB_REPOSITORY));
  } else if (process.argv[2] === 'prepare') {
    console.log(JSON.stringify(await prepareProduction(process.argv[3], input, process.env.GITHUB_SHA)));
  } else if (process.argv[2] !== 'inputs') throw new Error('Expected inputs, source, or prepare');
}
