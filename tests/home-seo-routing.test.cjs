const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const production = fs.readFileSync(path.join(root, 'infra/cloudfront-functions/redirect-prod.js'), 'utf8');
const terraform = fs.readFileSync(path.join(root, 'infra/terraform/main.tf'), 'utf8')
  .split('code    = <<-EOF\n')[1].split('\n  EOF')[0]
  .replace('${local.basic_auth_enabled ? "true" : "false"}', 'false')
  .replace('${local.basic_auth_token}', '');
function handler(source) {
  const context = {};
  vm.runInNewContext(source, context);
  return context.handler;
}
function request(uri, querystring = {}, headers = {}) {
  return { uri, querystring, headers: { host: { value: 'simy.one' }, ...headers } };
}
for (const [name, source] of [['production', production], ['Terraform', terraform]]) {
  const run = handler(source);
  for (const [input, output] of [['ja','ja'], ['en-US','en'], ['hi-IN','hi'], ['es-MX','es'], ['fr-FR','fr'], ['zh-SG','zh-Hans']]) {
    test(`${name}: legacy ${input} goes to crawlable HTML, retaining attribution`, () => {
      const result = run({ request: request('/', {lang:{value:input}, utm_source:{value:'seo campaign'}, region:{value:'gb'}, tag:{multiValue:[{value:'a'},{value:'b'}]}}) });
      assert.equal(result.statusCode, 301);
      assert.equal(result.headers.location.value, `https://simy.one/${output === 'en' ? '' : output + '.html'}?utm_source=seo%20campaign&region=gb&tag=a&tag=b`);
      const destination = new URL(result.headers.location.value);
      const next = request(destination.pathname, Object.fromEntries([...destination.searchParams].map(([k,v])=>[k,{value:v}])));
      assert.equal(run({request:next}), next, 'redirect must terminate');
    });
  }
  test(`${name}: locale URLs and default home ignore viewer language and region`, () => {
    for (const uri of ['/', '/ja.html', '/es.html','/fr.html','/hi.html','/zh-Hans.html']) {
      const req = request(uri, {}, {'accept-language':{value:'ja-JP'}, 'cloudfront-viewer-country':{value:'JP'}});
      assert.equal(run({request:req}), req);
    }
  });
  test(`${name}: index alias keeps query parameters and language redirects happen first`, () => {
    const result = run({request:request('/index.html',{utm_source:{value:'news'}})});
    assert.equal(result.headers.location.value,'https://simy.one/?utm_source=news');
    assert.equal(run({request:request('/index.html',{lang:{value:'ja'}})}).headers.location.value,'https://simy.one/ja.html');
  });
  test(`${name}: Traditional Chinese is never mislabeled as Simplified Chinese`, () => {
    for (const lang of ['zh-TW','zh-Hant','unknown']) {
      const req = request('/',{lang:{value:lang}});
      assert.equal(run({request:req}),req);
    }
  });
  test(`${name}: subpages, downloads and universal links retain their routing`, () => {
    for (const uri of ['/downloads/latest.json', '/.well-known/apple-app-site-association', '/privacy.html']) {
      const req = request(uri,{lang:{value:'ja'}});
      assert.equal(run({request:req}),req);
    }
    assert.equal(run({request:request('/about')}).headers.location.value,'https://simy.one/about.html');
    assert.equal(run({request:request('/old/')}).uri,'/old/index.html');
  });
  test(`${name}: query keys cannot shadow built-in object properties`, () => {
    const query = JSON.parse('{"lang":{"value":"ja"},"hasOwnProperty":{"value":"campaign"},"__proto__":{"value":"source"}}');
    assert.equal(run({request:request('/',query)}).headers.location.value,
      'https://simy.one/ja.html?hasOwnProperty=campaign&__proto__=source');
  });
  test(`${name}: occupation URLs normalize once and preserve campaign parameters`, () => {
    for (const [legacy, canonical] of [
      ['/for', '/for/'], ['/for.html', '/for/'], ['/for/index.html', '/for/'],
      ['/for/en', '/for/en/'], ['/for/en/index.html', '/for/en/'],
      ['/engineers.html', '/for/engineers/'], ['/engineers-en.html', '/for/en/engineers/'],
      ['/for/engineers', '/for/engineers/'], ['/for/engineers.html', '/for/engineers/'],
      ['/for/engineers/index.html', '/for/engineers/'],
      ['/for/en/engineers', '/for/en/engineers/'], ['/for/en/engineers/index.html', '/for/en/engineers/'],
    ]) {
      const query = {utm_source: {value:'release mail'}, tag:{multiValue:[{value:'a'},{value:'b'}]}};
      const result = run({request: request(legacy, query)});
      assert.equal(result.statusCode, 301);
      assert.equal(result.headers.location.value, `https://simy.one${canonical}?utm_source=release%20mail&tag=a&tag=b`);
      const next = request(canonical, query);
      assert.equal(run({request: next}), next);
      assert.equal(next.uri, canonical + 'index.html');
      assert.equal(next.querystring, query);
    }
  });
  test(`${name}: occupation routing preserves assets and dev authentication`, () => {
    for (const uri of ['/for/engineers/screen.png', '/guides/codex.html', '/site-theme.css']) {
      const req = request(uri);
      assert.equal(run({request:req}), req);
      assert.equal(req.uri, uri);
    }
    const protectedRun = handler(source.replace('var BASIC_AUTH_ENABLED = false;', 'var BASIC_AUTH_ENABLED = true;'));
    assert.equal(protectedRun({request:request('/for/engineers/')} ).statusCode, 401);
  });
  test(`${name}: dev authentication still precedes language redirects`, () => {
    const authRun = handler(source.replace('var BASIC_AUTH_ENABLED = false;', 'var BASIC_AUTH_ENABLED = true;'));
    assert.equal(authRun({request:request('/',{lang:{value:'ja'}})}).statusCode,401);
  });
}
