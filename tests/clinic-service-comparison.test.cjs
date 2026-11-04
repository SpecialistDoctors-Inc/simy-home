const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');

test('both comparison addresses forward to the production page with the original section', () => {
  for (const name of ['clinic-service.html','clinic-service-v2.html']) {
    const html = fs.readFileSync('site/hp-management/' + name, 'utf8');
    assert.ok(html.includes("location.replace('/hp-management/clinic.html'+location.search+location.hash)"));
    assert.doesNotMatch(html, /<form\b/);
  }
  const page = fs.readFileSync('site/hp-management/clinic/index.html','utf8');
  for (const id of ['diagnosis-form','rebuild-form','rebuild-editor','preview-application']) {
    assert.equal(page.split('id="' + id + '"').length, 2);
  }
});
