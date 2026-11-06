import { build } from 'esbuild';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
const result = await build({entryPoints: ['main.ts'], bundle: true, write: false, minify: true, format: 'esm', target: 'es2022'});
// Inline the complete SDK: no CDN, remote scripts or browser dependency installs.
const script = result.outputFiles[0].text.replace(/<\/script/gi, '<\\/script');
const template = await readFile('template.html', 'utf8');
await mkdir('dist', {recursive: true});
await writeFile('dist/publish.html', template.replace('/* APP_BUNDLE */', () => script));
console.log('Built dist/publish.html');
