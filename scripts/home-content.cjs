// Share the existing, source-controlled translation dictionaries with static generation.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const site = path.resolve(__dirname, '../site');
const runtime = fs.readFileSync(path.join(site, 'home-i18n.js'), 'utf8');
function literal(startMarker, endMarker) {
  const start = runtime.indexOf(startMarker);
  if (start < 0) throw new Error(`Missing homepage declaration: ${startMarker}`);
  const from = start + startMarker.length;
  const end = runtime.indexOf(endMarker, from);
  if (end < 0) throw new Error(`Missing homepage declaration end: ${endMarker}`);
  return vm.runInNewContext('(' + runtime.slice(from, end) + ')', {}, { timeout: 1000 });
}
const context = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(site, 'home-locales.js'), 'utf8'), context, { timeout: 1000 });
const content = {
  copy: { en: {}, ja: literal('const JA_COPY = Object.freeze(', ');'), ...context.window.SIMY_HOME_LOCALES },
  meta: literal('const PAGE_META = ', ';\n'),
};
module.exports = content;
if (require.main === module) process.stdout.write(JSON.stringify(content));
