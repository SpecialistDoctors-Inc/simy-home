import assert from 'node:assert/strict';
import { cp, mkdtemp, readFile, readdir, rm, symlink, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { pathToFileURL } from 'node:url';
import { build, renderPage, validateContent } from '../build.mjs';

const fixture = JSON.parse(await readFile(new URL('../content/clinic.json', import.meta.url), 'utf8'));
const template = await readFile(new URL('../site/index.html', import.meta.url), 'utf8');

test('content supplied by a request is escaped in both text and attributes', () => {
  const content = structuredClone(fixture);
  content.name = '<script>alert(1)</script>';
  content.heroImageAlt = '\" onerror=\"alert(1)';
  content.notices[0].body = '<img src=x onerror=alert(1)>';
  const html = renderPage(template, content);
  assert.ok(html.includes('&lt;script&gt;alert(1)&lt;/script&gt;'));
  assert.ok(html.includes('alt="&quot; onerror=&quot;alert(1)"'));
  assert.ok(html.includes('&lt;img src=x onerror=alert(1)&gt;'));
  assert.ok(!html.includes('<script>alert'));
});

test('unsafe images, invalid calendar dates and duplicated request-derived ids fail before build', () => {
  for (const url of ['https://example.com/image.png', '../secret.png', 'assets/../../secret.png', 'javascript:alert(1)']) {
    const content = structuredClone(fixture); content.heroImage = url;
    assert.throws(() => validateContent(content), /local image/);
  }
  const content = structuredClone(fixture); content.notices[0].date = '2026-02-30';
  assert.throws(() => validateContent(content), /notice date/);
  content.notices[0].date = '2026-02-28'; content.notices.push(content.notices[0]);
  assert.throws(() => validateContent(content), /duplicate/);
});

test('content changes update static HTML and release identity without modifying the original', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'sample-clinic-build-'));
  try {
    const before = await build({ output: path.join(directory, 'before'), revision: 'a'.repeat(40) });
    const content = structuredClone(fixture);
    content.notices.unshift({ id: 'december-closure', date: '2026-11-10', category: '休診', title: '12月の臨時休診', body: '12月12日は終日休診です。' });
    const contentPath = path.join(directory, 'updated.json'); await writeFile(contentPath, JSON.stringify(content));
    const after = await build({ output: path.join(directory, 'after'), contentPath, environment: 'dev', revision: 'b'.repeat(40) });
    const original = await readFile(path.join(directory, 'before/index.html'), 'utf8');
    const updated = await readFile(path.join(directory, 'after/index.html'), 'utf8');
    assert.ok(!original.includes('12月の臨時休診'));
    assert.ok(updated.includes('12月の臨時休診'));
    assert.notEqual(before.artifactHash, after.artifactHash);
    assert.equal(after.sourceRevision, 'b'.repeat(40));
    assert.equal(after.environment, 'dev');
    assert.ok(updated.includes('noindex, nofollow, noarchive'));
    assert.ok(!updated.includes('{{'));
    await writeFile(path.join(directory, 'after/assets/retired-photo.png'), 'obsolete asset');
    const again = await build({ output: path.join(directory, 'after'), contentPath, environment: 'dev', revision: 'b'.repeat(40) });
    assert.deepEqual(again, after);
    await assert.rejects(readFile(path.join(directory, 'after/assets/retired-photo.png')), { code: 'ENOENT' });
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('building refuses to erase an unrelated nonempty directory', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'sample-clinic-unowned-'));
  try {
    await writeFile(path.join(directory, 'keep.txt'), 'user content');
    await assert.rejects(build({ output: directory, revision: 'a'.repeat(40) }));
    assert.equal(await readFile(path.join(directory, 'keep.txt'), 'utf8'), 'user content');
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('a failed asset build preserves the previous release and permits a corrected retry', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'sample-clinic-recovery-'));
  try {
    const output = path.join(directory, 'release');
    const before = await build({ output, revision: 'a'.repeat(40) });
    const beforeHtml = await readFile(path.join(output, 'index.html'), 'utf8');
    // Use an isolated source copy so this failure never alters the real site.
    const source = path.join(directory, 'source');
    for (const name of ['build.mjs', 'site', 'content']) {
      await cp(new URL(`../${name}`, import.meta.url), path.join(source, name), { recursive: true });
    }
    const marker = path.join(directory, 'private.txt');
    await writeFile(marker, 'must not enter the static release');
    const badAsset = path.join(source, 'site/assets/invalid.txt');
    await symlink(marker, badAsset);
    const isolated = await import(pathToFileURL(path.join(source, 'build.mjs')).href);
    await assert.rejects(isolated.build({ output, revision: 'b'.repeat(40) }), /Symlinks and special files/);
    assert.deepEqual(JSON.parse(await readFile(path.join(output, 'version.json'), 'utf8')), before);
    assert.equal(await readFile(path.join(output, 'index.html'), 'utf8'), beforeHtml);
    assert.ok(!(await readdir(directory)).some((name) => name.startsWith('.sample-clinic-build-')));
    await rm(badAsset);
    const retried = await isolated.build({ output, revision: 'b'.repeat(40) });
    assert.equal(retried.artifactHash, before.artifactHash);
    assert.equal(retried.sourceRevision, 'b'.repeat(40));
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('unknown environments and incomplete revision identifiers cannot be published', async () => {
  await assert.rejects(build({ environment: 'production' }), /SITE_ENV/);
  await assert.rejects(build({ revision: 'main' }), /full Git SHA/);
});
