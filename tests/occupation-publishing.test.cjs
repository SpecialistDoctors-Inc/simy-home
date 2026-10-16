const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const vm = require('node:vm');
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

test('new locale pages remain reachable through the older edge redirects', () => fixture((dir, env) => {
  for (const locale of ['es', 'fr', 'hi', 'zh-hans']) {
    const page = path.join(dir, 'site/for', locale, 'engineers/index.html');
    fs.mkdirSync(path.dirname(page), { recursive: true });
    fs.writeFileSync(page, `<html lang="${locale}"><h1>${locale}</h1></html>`);
  }
  const result = spawnSync('bash', [script, 'test-site-bucket'], { cwd: dir, env, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  const calls = fs.readFileSync(env.UPLOAD_LOG, 'utf8').trim().split('\n').map(JSON.parse);
  const value = (args, flag) => args[args.indexOf(flag) + 1];
  const source = fs.readFileSync(path.resolve(__dirname, '../infra/cloudfront-functions/redirect-prod.js'), 'utf8');
  const context = {};
  vm.runInNewContext(source.replace('(?:en|es|fr|hi|zh-hans)', 'en'), context);
  for (const locale of ['es', 'fr', 'hi', 'zh-hans']) {
    const response = context.handler({ request: { uri: `/for/${locale}/engineers/`, headers: { host: { value: 'simy.one' } }, querystring: {} } });
    assert.equal(response.statusCode, 301);
    const key = new URL(response.headers.location.value).pathname.slice(1);
    const alias = calls.find(args => value(args, '--key') === key);
    assert.ok(alias, `old edge destination must be published: ${key}`);
    assert.equal(value(alias, '--body'), `site/for/${locale}/engineers/index.html`);
    assert.match(fs.readFileSync(path.join(dir, value(alias, '--body')), 'utf8'), new RegExp(`<html lang="${locale}">`));
  }
  const workflow = fs.readFileSync(path.resolve(__dirname, '../.github/workflows/deploy-site.yml'), 'utf8');
  const htmlSync = workflow.split('- name: Sync HTML files (short cache)')[1].split('- name:')[0];
  assert.match(htmlSync, /--exclude "for\/\*\/engineers\.html"/, 'later deleting HTML sync must retain compatibility aliases');
  const preparation = workflow.split('- name: Prepare occupation pages and assets')[1].split('- name:')[0];
  assert.match(preparation, /aws s3 sync site\/assets\/engineer-experience\//);
  assert.match(preparation, /engineers-experience\.css engineers-experience\.js/);
  const pageUpload = preparation.indexOf('aws s3 sync site/for/');
  assert.ok(preparation.indexOf('aws s3 sync site/assets/engineer-experience/') < pageUpload);
  for (const dir of ['engineer-manga', 'engineer-mechanism']) {
    assert.ok(preparation.indexOf(`aws s3 sync site/assets/${dir}/`) >= 0);
    assert.ok(preparation.indexOf(`aws s3 sync site/assets/${dir}/`) < pageUpload);
  }
  assert.match(preparation, /engineers-manga\.css/);
  assert.ok(preparation.indexOf('done') < pageUpload, 'all CSS/JS uploads must finish before existing pages change');
}));

test('FP locale compatibility keys survive publication under the live older router', () => fixture((dir, env) => {
  const locales=['es','fr','hi','zh-hans'];
  for (const locale of locales) {
    const page=path.join(dir,'site/for',locale,'financial-planners/index.html');
    fs.mkdirSync(path.dirname(page),{recursive:true});
    fs.writeFileSync(page,`<html lang="${locale}"><h1>${locale} FP</h1></html>`);
  }
  const result=spawnSync('bash',[script,'test-site-bucket'],{cwd:dir,env,encoding:'utf8'});
  assert.equal(result.status,0,result.stderr);
  const calls=fs.readFileSync(env.UPLOAD_LOG,'utf8').trim().split('\n').map(JSON.parse);
  const value=(args,flag)=>args[args.indexOf(flag)+1];
  const source=fs.readFileSync(path.resolve(__dirname,'../infra/cloudfront-functions/redirect-prod.js'),'utf8');
  const context={};vm.runInNewContext(source.replace('(?:en|es|fr|hi|zh-hans)','en'),context);
  for (const locale of locales) {
    const response=context.handler({request:{uri:`/for/${locale}/financial-planners/`,headers:{host:{value:'simy.one'}},querystring:{}}});
    const key=new URL(response.headers.location.value).pathname.slice(1);
    const upload=calls.find(args=>value(args,'--key')===key);
    assert.ok(upload,`live redirect destination is published: ${key}`);
    assert.equal(value(upload,'--body'),`site/for/${locale}/financial-planners/index.html`);
  }
  const workflow=fs.readFileSync(path.resolve(__dirname,'../.github/workflows/deploy-site.yml'),'utf8');
  const htmlSync=workflow.split('- name: Sync HTML files (short cache)')[1].split('- name:')[0];
  assert.match(htmlSync,/--exclude "for\/\*\/financial-planners\.html"/);
  const preparation=workflow.split('- name: Prepare occupation pages and assets')[1].split('- name:')[0];
  assert.ok(preparation.indexOf('aws s3 sync site/assets/fp-experience/')<preparation.indexOf('aws s3 sync site/for/'));
  assert.match(preparation,/financial-planners\.css financial-planners\.js site-header\.css site-header\.js/);
}));

test('deleting HTML sync executes with both locale compatibility exclusions', () => fixture((dir, env) => {
  const workflow=fs.readFileSync(path.resolve(__dirname,'../.github/workflows/deploy-site.yml'),'utf8');
  const step=workflow.split('- name: Sync HTML files (short cache)')[1].split('- name:')[0];
  const commands=step.split('run: |\n')[1].replace(/^          /gm,'').replace(/\$\{\{ secrets\.SITE_S3_BUCKET \}\}/g,'test-site-bucket');
  const result=spawnSync('bash',['-e','-u','-o','pipefail','-c',commands],{cwd:dir,env,encoding:'utf8'});
  assert.equal(result.status,0,result.stderr);
  const calls=fs.readFileSync(env.UPLOAD_LOG,'utf8').trim().split('\n').map(JSON.parse);
  assert.equal(calls.length,1);
  const args=calls[0];
  const exclusions=args.flatMap((arg,i)=>arg==='--exclude'?[args[i+1]]:[]);
  assert.ok(exclusions.includes('for/*/engineers.html'));
  assert.ok(exclusions.includes('for/*/financial-planners.html'));
}));

test('the later deleting asset sync preserves the root hub slash object too', () => {
  const workflow = fs.readFileSync(path.resolve(__dirname, '../.github/workflows/deploy-site.yml'), 'utf8');
  const assets = workflow.split('- name: Sync static assets (long cache)')[1].split('- name:')[0];
  assert.match(assets, /--delete/);
  assert.match(assets, /--exclude "for\/"/); // for/*/ does not match for/ itself.
  assert.match(assets, /--exclude "for\/\*\/"/);
});
