#!/usr/bin/env node
// Package the existing synthetic sample as one authenticated Vercel Function.
// No static object is published outside the function's private filesystem.
import { readFile, writeFile, mkdir, copyFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
if (!process.argv[2]) throw new Error('Pass a dedicated Vercel deployment directory.');
const output = resolve(process.argv[2], '.vercel/output');
const fn = resolve(output, 'functions/sample.func');
const guard = await readFile(resolve(root, 'infra/cloudfront-functions/fp-sample-auth.js'), 'utf8');
const digest = guard.match(/SAMPLE_AUTH_SHA256 = '([a-f0-9]{64})'/)?.[1];
if (!digest) throw new Error('Missing sample credential digest.');
await mkdir(fn, {recursive:true});
await writeFile(resolve(output, 'config.json'), JSON.stringify({version:3,routes:[{src:'/.*',dest:'/sample'}]},null,2));
await writeFile(resolve(fn, '.vc-config.json'), JSON.stringify({runtime:'nodejs22.x',handler:'serve.cjs',launcherType:'Nodejs',maxDuration:10},null,2));
for (const file of ['index.html', 'app.js', 'app.css'])
  await copyFile(resolve(root, 'samples/fp-management', file), resolve(fn, file));
const source = await readFile(resolve(root, 'scripts/fp-sample-vercel-handler.cjs'), 'utf8');
await writeFile(resolve(fn, 'serve.cjs'), source.replace('__SAMPLE_AUTH_DIGEST__', digest));
console.log('Packaged the three private sample assets behind a single authentication handler.');
