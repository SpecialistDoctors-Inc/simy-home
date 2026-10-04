const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const script = path.resolve(__dirname, '../scripts/publish-occupation-pages.sh');

function fixture(run) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'occupation-publish-'));
  try {
    for (const name of ['', 'en', 'engineers', 'en/engineers', 'future profession']) {
      fs.mkdirSync(path.join(dir, 'site/for', name), { recursive: true });
      fs.writeFileSync(path.join(dir, 'site/for', name, 'index.html'), '<h1>Example</h1>');
    }
    fs.writeFileSync(path.join(dir, 'site/for/asset.png'), 'not a page');
    fs.mkdirSync(path.join(dir, 'bin'));
    fs.writeFileSync(path.join(dir, 'bin/aws'), `#!${process.execPath}\nconst fs=require('node:fs');if(process.env.FAIL_UPLOAD)process.exit(23);fs.appendFileSync(process.env.UPLOAD_LOG,JSON.stringify(process.argv.slice(2))+'\\n');`, { mode: 0o755 });
    run(dir, { ...process.env, PATH: path.join(dir, 'bin') + path.delimiter + process.env.PATH, UPLOAD_LOG: path.join(dir, 'uploads.jsonl') });
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
}

test('publishes each occupation index at its literal slash key, with HTML metadata', () => fixture((dir, env) => {
  const result = spawnSync('bash', [script, 'test-site-bucket'], { cwd: dir, env, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  const calls = fs.readFileSync(env.UPLOAD_LOG, 'utf8').trim().split('\n').map(JSON.parse);
  assert.equal(calls.length, 5);
  const value = (args, flag) => args[args.indexOf(flag) + 1];
  assert.deepEqual(calls.map(c => value(c, '--key')).sort(), ['for/', 'for/en/', 'for/en/engineers/', 'for/engineers/', 'for/future profession/']);
  for (const args of calls) {
    assert.deepEqual(args.slice(0, 2), ['s3api', 'put-object']);
    assert.equal(value(args, '--bucket'), 'test-site-bucket');
    assert.equal(value(args, '--body'), 'site/' + value(args, '--key') + 'index.html');
    assert.equal(value(args, '--content-type'), 'text/html; charset=utf-8');
    assert.equal(value(args, '--cache-control'), 'public, max-age=300');
  }
}));

test('upload failure and missing bucket stop publication', () => fixture((dir, env) => {
  assert.equal(spawnSync('bash', [script, 'test-site-bucket'], { cwd: dir, env: { ...env, FAIL_UPLOAD: '1' } }).status, 23);
  assert.notEqual(spawnSync('bash', [script], { cwd: dir, env }).status, 0);
}));

test('the later deleting asset sync preserves the root hub slash object too', () => {
  const workflow = fs.readFileSync(path.resolve(__dirname, '../.github/workflows/deploy-site.yml'), 'utf8');
  const assets = workflow.split('- name: Sync static assets (long cache)')[1].split('- name:')[0];
  assert.match(assets, /--delete/);
  assert.match(assets, /--exclude "for\/"/); // for/*/ does not match for/ itself.
  assert.match(assets, /--exclude "for\/\*\/"/);
});
