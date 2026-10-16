#!/usr/bin/env node
// Export only the approved synthetic workbench; no Next routes, Auth or DB client.
import { createRequire } from "node:module";
import { readFile, mkdir, writeFile, readdir } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";

const home = resolve(dirname(fileURLToPath(import.meta.url)), "..");
if (!process.argv[2]) throw new Error("Pass the simy-web checkout containing the approved Sony sample.");
const root = resolve(process.argv[2]);
const require = createRequire(resolve(root, "package.json"));
const output = resolve(home, "samples/fp-management");
const modules = resolve(root, "node_modules/.pnpm");
const esbuildDir = (await readdir(modules)).find((name) => name.startsWith("esbuild@0.28."));
const { build } = require(resolve(modules, esbuildDir, "node_modules/esbuild"));
const tailwind = require("@tailwindcss/postcss");
const postcss = createRequire(require.resolve("@tailwindcss/postcss"))("postcss");
await mkdir(output, { recursive: true });
await build({
  absWorkingDir: root,
  stdin: {
    contents: 'import {createRoot} from "react-dom/client"; import {SonyWorkbench} from "./src/app/e2e/fp-dashboard/sony-workbench"; createRoot(document.getElementById("root")).render(<SonyWorkbench onArchive={()=>{}}/>);',
    resolveDir: root,
    loader: "tsx",
  },
  outfile: resolve(output, "app.js"),
  bundle: true,
  minify: true,
  format: "esm",
  jsx: "automatic",
  define: { "process.env.NODE_ENV": '"production"' },
  plugins: [{
    name: "standalone-sample-copy",
    setup(builder) {
      builder.onLoad({ filter: /sony-workbench\.tsx$/ }, async ({ path }) => {
        const source = await readFile(path, "utf8");
        const archive = /        <Button variant="ghost" className="mt-3 justify-start text-xs lg:mt-7" onClick=\{onArchive\}>[\s\S]*?<\/Button>/;
        if (!archive.test(source)) throw new Error("Review the archive link before exporting.");
        return { contents: source.replace(archive, "").replace("ローカル体験用", "サンプル体験用（このブラウザー内に保存）"), loader: "tsx" };
      });
    },
  }],
});
const javascript = resolve(output, "app.js");
await writeFile(javascript, (await readFile(javascript, "utf8")).split("\n").map(line => line.trimEnd()).join("\n"));
const css = await postcss([tailwind({ base: root, optimize: true })]).process(
  await readFile(resolve(root, "src/app/globals.css"), "utf8"),
  { from: resolve(root, "src/app/globals.css"), to: resolve(output, "app.css") },
);
await writeFile(resolve(output, "app.css"), css.css);
await writeFile(resolve(output, "index.html"), `<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive"><title>営業・品質マネジメント サンプル | SIMY</title><link rel="stylesheet" href="/samples/fp-management/app.css"></head><body><div id="root"></div><script type="module" src="/samples/fp-management/app.js"></script></body></html>\n`);
await writeFile(resolve(output, "source.json"), JSON.stringify({
  repository: "SpecialistDoctors-Inc/simy-web",
  commit: execFileSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" }).trim(),
  component: "src/app/e2e/fp-dashboard/sony-workbench.tsx",
  data: "synthetic-only",
  persistence: "browser-local-only",
}, null, 2) + "\n");
console.log(`Exported synthetic sales and quality workbench to ${output}`);
