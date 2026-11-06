import { build } from 'esbuild';
import { mkdir, copyFile } from 'node:fs/promises';
await mkdir('output/playwright', {recursive: true});
await build({entryPoints:['preview-host.ts'], bundle:true, format:'esm', target:'es2022', outfile:'output/playwright/harness.js'});
await copyFile('preview-host.html','output/playwright/host.html');
