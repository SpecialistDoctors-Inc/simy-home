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
const approvedSalesCommit = "f1dad0e6cec0847cf948b37a8508667e1a740916";
const approvedSalesData = execFileSync("git", ["show", `${approvedSalesCommit}:src/app/e2e/fp-dashboard/sony-experience-data.ts`], { cwd: root, encoding: "utf8" });
const exportHead = execFileSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" }).trim();
const trackedChanges = execFileSync("git", ["status", "--porcelain", "--untracked-files=normal"], { cwd: root, encoding: "utf8" }).trim();
if (trackedChanges) throw new Error("Export requires a clean, committed simy-web checkout.");
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
      builder.onResolve({ filter: /^sample-feedback-review$/ }, () => ({ path: "sample-feedback-review", namespace: "sample-feedback" }));
      builder.onLoad({ filter: /.*/, namespace: "sample-feedback" }, async () => ({ contents: await readFile(resolve(home, "scripts/fp-feedback-sample.tsx"), "utf8"), loader: "tsx", resolveDir: root }));
      builder.onLoad({ filter: /quality-review-board\.tsx$/ }, async ({ path }) => {
        const source = await readFile(path, "utf8");
        const marker = '      <div className="grid gap-4 sm:grid-cols-3" data-testid="quality-review-metrics">';
        if (!source.includes(marker)) throw new Error("Review the sample feedback insertion point before exporting.");
        return { contents: 'import { SampleFeedbackReview } from "sample-feedback-review";\n' + source.replace(marker, '      {sample && <SampleFeedbackReview />}\n' + marker), loader: "tsx" };
      });
      builder.onResolve({ filter: /^approved-sales-insight$/ }, () => ({ path: "approved-sales-insight", namespace: "approved-sales" }));
      builder.onLoad({ filter: /.*/, namespace: "approved-sales" }, () => ({ contents: approvedSalesData, loader: "ts" }));
      builder.onLoad({ filter: /sony-experience\.tsx$/ }, async ({ path }) => {
        const source = await readFile(path, "utf8");
        const signature = 'export function CaseExperience({ item }: { item: DemoCase })';
        const selection = 'const s = insight(item),';
        if (!source.includes(signature) || !source.includes(selection)) throw new Error("Review the sales case detail adapter before exporting.");
        return { contents: 'import { insight as approvedSalesInsight } from "approved-sales-insight";\n' + source
          .replace(signature, 'export function CaseExperience({ item, sales = false }: { item: DemoCase; sales?: boolean })')
          .replace(selection, 'const s = sales ? approvedSalesInsight(item) : insight(item),'), loader: "tsx" };
      });
      builder.onLoad({ filter: /sony-workbench\.tsx$/ }, async ({ path }) => {
        const source = await readFile(path, "utf8");
        const archive = /        <Button variant="ghost" className="mt-3 justify-start text-xs lg:mt-7" onClick=\{onArchive\}>[\s\S]*?<\/Button>/;
        if (!archive.test(source)) throw new Error("Review the archive link before exporting.");
        const caseDetail = '<CaseExperience item={selected} />';
        if (!source.includes(caseDetail)) throw new Error("Review the sales/quality case detail boundary before exporting.");
        return { contents: source.replace(archive, "").replace(caseDetail, '<CaseExperience item={selected} sales={mode === "sales"} />').replace("ローカル体験用", "サンプル体験用（このブラウザー内に保存）"), loader: "tsx" };
      });
    },
  }],
});
const javascript = resolve(output, "app.js");
await writeFile(javascript, (await readFile(javascript, "utf8")).split("\n").map(line => line.trimEnd()).join("\n"));
const css = await postcss([tailwind({ base: root, optimize: true })]).process(
  `@source "${resolve(home, "scripts/fp-feedback-sample.tsx")}";\n` + await readFile(resolve(root, "src/app/globals.css"), "utf8"),
  { from: resolve(root, "src/app/globals.css"), to: resolve(output, "app.css") },
);
await writeFile(resolve(output, "app.css"), css.css);
await writeFile(resolve(output, "index.html"), `<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive"><title>営業・品質マネジメント サンプル | SIMY</title><link rel="stylesheet" href="/samples/fp-management/app.css"></head><body><div id="root"></div><script type="module" src="/samples/fp-management/app.js"></script></body></html>\n`);
const finalHead = execFileSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" }).trim();
const finalChanges = execFileSync("git", ["status", "--porcelain", "--untracked-files=normal"], { cwd: root, encoding: "utf8" }).trim();
if (finalHead !== exportHead || finalChanges) throw new Error("Source changed during export; do not publish these assets.");
await writeFile(resolve(output, "source.json"), JSON.stringify({
  repository: "SpecialistDoctors-Inc/simy-web",
  commit: exportHead,
  component: "src/app/e2e/fp-dashboard/sony-workbench.tsx",
  approvedSalesCommit,
  data: "synthetic-only",
  persistence: "browser-local-only",
}, null, 2) + "\n");
console.log(`Exported synthetic sales and quality workbench to ${output}`);
