import assert from "node:assert/strict";
import { writeFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { gzipSync } from "node:zlib";
import { build } from "vite";

// Inspect module membership, not just filenames: moving synchronous code into a
// renamed vendor chunk must not count as a public startup improvement.
const result = await build({ build: { write: false }, logLevel: "silent" });
const chunks = new Map(result.output.filter(item => item.type === "chunk").map(item => [item.fileName, item]));
const homepage = result.output.find(item => item.type === "asset" && item.fileName === "index.html");
const html = String(homepage?.source ?? "");
const entryPaths = [...html.matchAll(/<script[^>]+type="module"[^>]+src="\/([^\"]+\.js)"/g)].map(match => match[1]);
const preloadPaths = [...html.matchAll(/<link[^>]+rel="modulepreload"[^>]+href="\/([^\"]+\.js)"/g)].map(match => match[1]);
const entry = [...entryPaths, ...preloadPaths].map(file => chunks.get(file)).find(chunk => chunk && /^assets\/main-.+\.js$/.test(chunk.fileName));
assert.ok(entry, "Missing public main entry");
const initial = new Set();
function visit(file) {
  if (initial.has(file)) return;
  const chunk = chunks.get(file);
  assert.ok(chunk, `Unresolved synchronous import: ${file}`);
  initial.add(file);
  for (const dependency of chunk.imports) visit(dependency);
}
for (const file of [...entryPaths, ...preloadPaths]) visit(file);
const initialModules = [...initial].flatMap(file => Object.keys(chunks.get(file).modules));
for (const moduleName of ["LivePage.tsx", "ConversationMonitor.tsx", "AnswerMarkdown.tsx", "interview-review-word-export.ts"]) {
  assert.ok(!initialModules.some(id => id.endsWith(`/${moduleName}`)), `${moduleName} leaked into public startup`);
}
assert.ok(!initialModules.some(id => /\/(?:katex|docx)\//.test(id)), "Math or Word export runtime leaked into public startup");
const liveChunk = [...chunks.values()].find(item => Object.keys(item.modules).some(id => id.endsWith("/LivePage.tsx")));
assert.ok(liveChunk && !initial.has(liveChunk.fileName), "Live workspace must be asynchronous");
assert.ok([...chunks.values()].some(item => item.dynamicImports.includes(liveChunk.fileName)), "No dynamic path to live workspace");
assert.ok(Buffer.byteLength(entry.code) <= 410_000, "Original entry budget exceeded");
const output = {
  entry: entry.fileName,
  entryBytes: Buffer.byteLength(entry.code),
  initialJsBytes: [...initial].reduce((sum, file) => sum + Buffer.byteLength(chunks.get(file).code), 0),
  initialJsGzipBytes: [...initial].reduce((sum, file) => sum + gzipSync(chunks.get(file).code).byteLength, 0),
  totalJsBytes: [...chunks.values()].reduce((sum, chunk) => sum + Buffer.byteLength(chunk.code), 0),
  initialChunks: [...initial],
  liveChunk: liveChunk.fileName,
  excludedFromStartup: ["LivePage", "ConversationMonitor", "AnswerMarkdown", "docx"],
};
const reportFlag = process.argv.indexOf("--report");
if (reportFlag >= 0) {
  assert.ok(process.argv[reportFlag + 1], "--report needs a path");
  const report = resolve(process.argv[reportFlag + 1]);
  await mkdir(dirname(report), { recursive: true });
  await writeFile(report, `${JSON.stringify(output, null, 2)}\n`);
}
console.log(JSON.stringify(output, null, 2));
