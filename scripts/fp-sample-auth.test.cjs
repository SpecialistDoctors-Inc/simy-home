const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');

const source = fs.readFileSync('infra/cloudfront-functions/redirect-prod.js', 'utf8');
assert.ok(source.includes(fs.readFileSync('infra/cloudfront-functions/fp-sample-auth.js', 'utf8').trim()), 'Deployment guard and tested router must match');
const context = { require, SAMPLE_AUTH_SHA256: '' };
vm.createContext(context);
vm.runInContext(source, context);
context.SAMPLE_AUTH_SHA256 = crypto.createHash('sha256').update('Basic test-valid').digest('hex');
function request(uri, auth) {
  return context.handler({request:{uri,querystring:{},headers:{host:{value:'simy.one'},...(auth?{authorization:{value:auth}}:{})}}});
}
test('all sample paths including bundles and encoded paths require authentication', () => {
  for (const path of ['/samples/fp-management/', '/samples/fp-management/app.js', '/samples/fp-management/app.css', '/%73amples/fp-management/', '/samples//fp-management/', '/samples/fp-management/../fp-management/app.js']) {
    assert.equal(request(path).statusCode, 401);
    assert.equal(request(path, 'Basic wrong').statusCode, 401);
  }
});
test('valid credentials resolve only the sample entry and its two bundles', () => {
  assert.equal(request('/samples/fp-management/', 'Basic test-valid').uri, '/samples/fp-management/index.html');
  assert.equal(request('/samples/fp-management/app.js', 'Basic test-valid').uri, '/samples/fp-management/app.js');
  assert.equal(request('/samples/fp-management/source.json', 'Basic test-valid').statusCode, 404);
});
test('public homepage and redirects retain their behavior', () => {
  assert.equal(request('/').uri, '/');
  assert.equal(request('/pricing').headers.location.value, 'https://simy.one/pricing.html');
});
