import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { cp, lstat, mkdir, mkdtemp, readFile, readdir, rename, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

function text(value, field, maximum = 1000) {
  if (typeof value !== 'string' || !value.trim() || value.length > maximum) throw new Error(`Invalid ${field}`);
}

export function validateContent(content) {
  if (!content || typeof content !== 'object') throw new Error('Invalid clinic content');
  if (content.changeRequest && (!/^[a-f0-9-]{36}$/.test(content.changeRequest.id) || !Number.isSafeInteger(content.changeRequest.revision) || content.changeRequest.revision < 1)) throw new Error('Invalid changeRequest');
  for (const key of ['name', 'englishName', 'description', 'heroImageAlt']) text(content[key], key);
  if (!Array.isArray(content.tagline) || content.tagline.length !== 2) throw new Error('tagline requires two lines');
  content.tagline.forEach((line) => text(line, 'tagline', 60));
  if (!/^assets\/[a-z0-9][a-z0-9-]*\.(png|jpg|webp)$/.test(content.heroImage)) throw new Error('heroImage must be a local image');
  for (const key of ['morning', 'afternoon', 'note']) text(content.hours?.[key], `hours.${key}`, 160);
  for (const key of ['morningDays', 'afternoonDays']) {
    const days = content.hours?.[key];
    if (!Array.isArray(days) || days.length !== 7 || days.some((day) => typeof day !== 'boolean')) throw new Error(`Invalid hours.${key}`);
  }
  if (!Array.isArray(content.notices) || content.notices.length > 30) throw new Error('Invalid notices');
  const ids = new Set();
  for (const notice of content.notices) {
    if (!notice || !/^[a-z0-9][a-z0-9-]{0,79}$/.test(notice.id) || ids.has(notice.id)) throw new Error('Invalid or duplicate notice id');
    ids.add(notice.id);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(notice.date) || !Number.isFinite(Date.parse(notice.date)) || new Date(notice.date).toISOString().slice(0, 10) !== notice.date) throw new Error('Invalid notice date');
    for (const key of ['category', 'title', 'body']) text(notice[key], `notice.${key}`, key === 'body' ? 4000 : 200);
  }
  return content;
}

export function renderPage(template, content) {
  validateContent(content);
  const lines = (value) => escapeHtml(value).replaceAll('\n', '<br>');
  const row = (time, days) => `<tr><th scope="row">${escapeHtml(time)}</th>${days.map((open) => `<td><span aria-label="${open ? '診療' : '休診'}">${open ? '●' : '—'}</span></td>`).join('')}</tr>`;
  const values = {
    NAME: escapeHtml(content.name), ENGLISH_NAME: escapeHtml(content.englishName),
    TAGLINE: content.tagline.map(escapeHtml).join('<br>'), DESCRIPTION: lines(content.description),
    HERO_IMAGE: escapeHtml(content.heroImage), HERO_IMAGE_ALT: escapeHtml(content.heroImageAlt),
    HOURS: row(content.hours.morning, content.hours.morningDays) + row(content.hours.afternoon, content.hours.afternoonDays),
    HOURS_NOTE: escapeHtml(content.hours.note),
    NOTICES: content.notices.map((notice) => `<details class="notice" id="notice-${notice.id}"><summary><time datetime="${notice.date}">${notice.date.replaceAll('-', '.')}</time><span>${escapeHtml(notice.title)}</span><span class="notice-arrow" aria-hidden="true">+</span></summary><p>${lines(notice.body)}</p></details>`).join('\n'),
  };
  return template.replace(/\{\{([A-Z_]+)\}\}/g, (_, key) => {
    if (!(key in values)) throw new Error(`Unknown template field ${key}`);
    return values[key];
  });
}

async function listFiles(directory, prefix = '') {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const relative = path.posix.join(prefix, entry.name);
    if (entry.isDirectory()) files.push(...await listFiles(path.join(directory, entry.name), relative));
    else if (entry.isFile()) files.push(relative);
    else throw new Error('Symlinks and special files are not allowed in a static release');
  }
  return files.sort();
}

export async function artifactHash(directory) {
  const hash = createHash('sha256');
  for (const file of await listFiles(directory)) {
    if (file === 'version.json') continue;
    const data = await readFile(path.join(directory, file));
    hash.update(`${file}\0${data.length}\0`); hash.update(data);
  }
  return hash.digest('hex');
}

export async function build({ output = path.join(root, 'dist'), contentPath = path.join(root, 'content/clinic.json'), environment = process.env.SITE_ENV || 'local', revision = process.env.SOURCE_REVISION } = {}) {
  if (!['local', 'dev', 'prod'].includes(environment)) throw new Error('Invalid SITE_ENV');
  if (!revision) revision = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim();
  if (!/^[a-f0-9]{40}$/.test(revision)) throw new Error('SOURCE_REVISION must be a full Git SHA');
  const content = validateContent(JSON.parse(await readFile(contentPath, 'utf8')));
  // Verify assets before touching the task-owned build output.
  await readFile(path.join(root, 'site', content.heroImage));
  const html = renderPage(await readFile(path.join(root, 'site/index.html'), 'utf8'), content);
  await mkdir(path.dirname(output), { recursive: true });
  const existing = await lstat(output).catch((error) => { if (error.code === 'ENOENT') return null; throw error; });
  if (existing) {
    if (!existing.isDirectory()) throw new Error('Output must be a directory, not a symlink');
    if ((await readdir(output)).length) {
      const previous = JSON.parse(await readFile(path.join(output, 'version.json'), 'utf8'));
      if (previous.schemaVersion !== 1 || previous.siteId !== 'sample-clinic') throw new Error('Output is not a generated sample-clinic release');
    }
  }
  // Finish a complete release before replacing the previous one. Both temporary
  // paths are created by this invocation; a failed build preserves the old site.
  const temporary = await mkdtemp(path.join(path.dirname(output), '.sample-clinic-build-'));
  const candidate = path.join(temporary, 'candidate');
  const backup = path.join(temporary, 'previous');
  let previousMoved = false;
  let installed = false;
  try {
    await mkdir(candidate);
    for (const name of ['styles.css', 'site.js', 'robots.txt']) await cp(path.join(root, 'site', name), path.join(candidate, name));
    await cp(path.join(root, 'site/assets'), path.join(candidate, 'assets'), { recursive: true });
    await writeFile(path.join(candidate, 'index.html'), html);
    await writeFile(path.join(candidate, 'error.html'), '<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>ページが見つかりません｜SIMY サンプルクリニック</title><link rel="stylesheet" href="/styles.css"><main class="container section-space"><p class="eyebrow">404 / SAMPLE CLINIC</p><h1>ページが見つかりません。</h1><p>架空のクリニックのサンプルサイトです。</p><a class="button" href="/">トップページへ戻る</a></main></html>');
    const manifest = { schemaVersion: 1, siteId: 'sample-clinic', environment, sourceRevision: revision, artifactHash: await artifactHash(candidate), ...(content.changeRequest ? { requestId: content.changeRequest.id, requestRevision: content.changeRequest.revision } : {}) };
    await writeFile(path.join(candidate, 'version.json'), JSON.stringify(manifest, null, 2) + '\n');
    if (existing) { await rename(output, backup); previousMoved = true; }
    await rename(candidate, output);
    installed = true;
    return manifest;
  } finally {
    if (previousMoved && !installed) await rename(backup, output);
    await rm(temporary, { recursive: true, force: true });
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = await build();
  console.log(JSON.stringify(result));
}
