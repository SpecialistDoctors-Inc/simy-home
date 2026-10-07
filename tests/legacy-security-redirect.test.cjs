const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const legacySecurity = fs.readFileSync(path.join(__dirname, '../site/old/security.html'), 'utf8');

test('legacy security URL sends visitors to current security information without stale claims', () => {
  assert.match(legacySecurity, /<meta http-equiv="refresh" content="0; url=\/security\.html">/);
  assert.match(legacySecurity, /window\.location\.replace\('\/security\.html' \+ window\.location\.search \+ window\.location\.hash\)/);
  assert.match(legacySecurity, /<a href="\/security\.html">current security information<\/a>/);
  assert.doesNotMatch(legacySecurity, /TLS\s*1\.3|AES-256|SOC\s*2|HIPAA|physical database isolation/i);
});
