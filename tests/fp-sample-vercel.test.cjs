const test = require('node:test');
const assert = require('node:assert/strict');
const {mkdtemp, readFile, writeFile, rm} = require('node:fs/promises');
const {tmpdir} = require('node:os');
const {join} = require('node:path');
const {createHash} = require('node:crypto');
const {createServer} = require('node:http');

test('all Vercel routes and assets require authentication, with no filesystem escape', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'fp-sample-auth-'));
  const authorization = 'Basic '+Buffer.from('test:unique-test-password').toString('base64');
  const digest = createHash('sha256').update(authorization).digest('hex');
  const source = await readFile('scripts/fp-sample-vercel-handler.cjs', 'utf8');
  await writeFile(join(directory, 'serve.cjs'), source.replace('__SAMPLE_AUTH_DIGEST__', digest));
  for (const name of ['index.html', 'app.js', 'app.css']) await writeFile(join(directory,name), 'private-'+name);
  const handler = require(join(directory,'serve.cjs'));
  const server = createServer((req,res)=>handler(req,res).catch(()=>{res.statusCode=500;res.end();}));
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const base = 'http://127.0.0.1:'+server.address().port;
  try {
    for (const path of ['/', '/sample', '/samples/fp-management/', '/samples/fp-management/app.js', '/samples/fp-management/app.css', '/serve.cjs']) {
      for (const headers of [{}, {authorization:'Basic wrong'}]) {
        const response = await fetch(base+path,{headers});
        assert.equal(response.status,401);
        assert.match(response.headers.get('www-authenticate'),/SIMY sample/);
        assert.match(response.headers.get('cache-control'),/no-store/);
      }
    }
    for (const [path,body] of [['/?view=quality','private-index.html'],['/samples/fp-management/app.js','private-app.js'],['/samples/fp-management/app.css','private-app.css']]) {
      const response = await fetch(base+path,{headers:{authorization}});
      assert.equal(response.status,200);
      assert.equal(await response.text(),body);
    }
    assert.equal((await fetch(base+'/serve.cjs',{headers:{authorization}})).status,404);
    assert.equal((await fetch(base+'/.vc-config.json',{headers:{authorization}})).status,404);
    assert.equal((await fetch(base+'/',{method:'POST',headers:{authorization}})).status,405);
    const head = await fetch(base+'/',{method:'HEAD',headers:{authorization}});
    assert.equal(head.status,200);
    assert.equal(await head.text(),'');
  } finally {
    await new Promise(resolve=>server.close(resolve));
    await rm(directory,{recursive:true});
  }
});
