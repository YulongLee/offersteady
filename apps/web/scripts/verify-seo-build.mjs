import assert from "node:assert/strict";
import { readFile, readdir, stat } from "node:fs/promises";
import { resolve } from "node:path";

const webRoot = resolve(import.meta.dirname, "..");
const dist = resolve(webRoot, "dist");
const staticOutputs = [
  "seo/features.html", "seo/guides.html", "seo/interview-questions.html",
  "seo/ai-interview-assistant.html", "seo/realtime-interview.html", "seo/screenshot-answer.html",
  "seo/interview-review.html", "seo/audio-troubleshooting.html", "seo/interview-preparation.html",
  "seo/pricing.html", "seo/download.html", "seo/security.html", "seo/about.html", "seo/contact.html",
  "seo/macos-permissions.html", "seo/feishu-audio-setup.html", "seo/tencent-meeting-audio-setup.html",
  "seo/star-interview-answer.html",
  "seo/self-introduction.html", "seo/project-experience.html", "seo/technical-interview.html",
  "seo/common-interview-questions.html",
  "seo/llm.html", "seo/rag.html", "seo/ai-agent.html",
  "seo/public-search.css", "llms.txt", "llms-full.txt", "public-facts.json", "robots.txt", "sitemap.xml", "404.html",
];
const [homepage, guide] = await Promise.all([readFile(resolve(dist, "index.html"), "utf8"), readFile(resolve(dist, "guide.html"), "utf8")]);
assert.match(homepage, /<link rel="canonical" href="https:\/\/mianshiwen\.cn\/"\s*\/>/);
assert.match(guide, /<link rel="canonical" href="https:\/\/mianshiwen\.cn\/guide"\s*\/>/);
assert.notEqual(homepage, guide);
assert.match(homepage, /<script type="module" crossorigin src="\/assets\/.+-[A-Za-z0-9_-]{8}\.js"><\/script>/);
assert.match(guide, /<script type="module" crossorigin src="\/assets\/.+-[A-Za-z0-9_-]{8}\.js"><\/script>/);
for (const file of staticOutputs) assert.ok((await stat(resolve(dist, file))).size > 0, `Missing or empty build output: ${file}`);
for (const file of staticOutputs.filter((file) => file.endsWith(".html") && file.startsWith("seo/"))) {
  const html = await readFile(resolve(dist, file), "utf8");
  assert.match(html, /<link rel="canonical" href="https:\/\/mianshiwen\.cn\/(?:features(?:\/|\")|guides(?:\/|\")|interview-questions|pricing|download|security|about|contact)/);
  assert.equal((html.match(/<h1(?:\s[^>]*)?>/g) ?? []).length, 1);
  JSON.parse(html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1]);
}
JSON.parse(await readFile(resolve(dist, "public-facts.json"), "utf8"));
const assets = await Promise.all((await readdir(resolve(dist, "assets"))).map(async (file) => ({ file, size: (await stat(resolve(dist, "assets", file))).size })));
const jsBytes = assets.filter(({ file }) => file.endsWith(".js")).reduce((sum, { size }) => sum + size, 0);
const cssBytes = assets.filter(({ file }) => file.endsWith(".css")).reduce((sum, { size }) => sum + size, 0);
const entryJsBytes = assets.find(({ file }) => /^main-.+\.js$/.test(file))?.size ?? 0;
assert.ok(jsBytes <= 1_350_000, `Total built JS budget exceeded: ${jsBytes} bytes`);
assert.ok(entryJsBytes <= 410_000, `Public entry JS budget exceeded: ${entryJsBytes} bytes`);
assert.ok(cssBytes <= 250_000, `Built CSS budget exceeded: ${cssBytes} bytes`);
console.log(`SEO/GEO production checks passed; entry JS ${entryJsBytes} bytes, total JS ${jsBytes} bytes, CSS ${cssBytes} bytes.`);
