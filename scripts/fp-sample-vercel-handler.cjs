const { createHash, timingSafeEqual } = require('node:crypto');
const { readFile } = require('node:fs/promises');
const { join } = require('node:path');
const expected = Buffer.from('__SAMPLE_AUTH_DIGEST__', 'hex');
module.exports = async function handler(req, res) {
  res.setHeader('Cache-Control', 'private, no-store, max-age=0');
  res.setHeader('X-Robots-Tag', 'noindex, nofollow, noarchive');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  const actual = createHash('sha256').update(req.headers.authorization || '').digest();
  if (expected.length !== actual.length || !timingSafeEqual(actual, expected)) {
    res.setHeader('WWW-Authenticate', 'Basic realm="SIMY sample", charset="UTF-8"');
    res.statusCode = 401;
    res.end('ID and password are required.');
    return;
  }
  if (!['GET', 'HEAD'].includes(req.method)) {
    res.statusCode = 405;
    res.setHeader('Allow', 'GET, HEAD');
    res.end();
    return;
  }
  const path = new URL(req.url, 'https://sample.invalid').pathname;
  let asset;
  if (['/', '/sample', '/samples/fp-management', '/samples/fp-management/', '/samples/fp-management/index.html'].includes(path))
    asset = ['index.html', 'text/html; charset=utf-8'];
  else if (path === '/samples/fp-management/app.js')
    asset = ['app.js', 'application/javascript; charset=utf-8'];
  else if (path === '/samples/fp-management/app.css')
    asset = ['app.css', 'text/css; charset=utf-8'];
  if (!asset) {
    res.statusCode = 404;
    res.end('Not found');
    return;
  }
  res.setHeader('Content-Type', asset[1]);
  res.statusCode = 200;
  res.end(req.method === 'HEAD' ? undefined : await readFile(join(__dirname, asset[0])));
};
