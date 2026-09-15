import { mkdir, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
const output = process.argv[2];
if (!output) throw new Error("Pass an evidence output directory");
await mkdir(output, { recursive: true });
const local = "http://127.0.0.1:18988";
const origin = "https://mianshiwen.cn";
const paths = ["/", "/pricing", "/features/realtime-interview", "/features/ai-interview-assistant"];
const agents = { ordinary: "Mozilla/5.0 (compatible; SEO-ReadOnly-Check/1.0)", baidu: "Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)" };
function inspect(html, response) {
  const d = new JSDOM(html).window.document;
  const schemas = [...d.querySelectorAll('script[type="application/ld+json"]')];
  return { status: response.status, title: d.title, description: d.querySelector('meta[name="description"]')?.content,
    h1: [...d.querySelectorAll("h1")].map(n => n.textContent), canonical: d.querySelector('link[rel="canonical"]')?.href,
    robots: d.querySelector('meta[name="robots"]')?.content ?? "not set (indexable)",
    xRobotsTag: response.headers.get("x-robots-tag"), body: d.querySelector("main")?.textContent,
    links: [...d.querySelectorAll("a[href]")].map(n => ({ href: n.getAttribute("href"), text: n.textContent })),
    schema: schemas.map(n => JSON.parse(n.textContent)), csp: response.headers.get("content-security-policy"),
    scriptHashes: schemas.map(n => "sha256-" + createHash("sha256").update(n.textContent).digest("base64")) };
}
const evidence = { before: [], after: [], sitemap: [] };
for (const phase of ["before", "after"]) for (const path of paths) for (const [agent, userAgent] of Object.entries(agents)) {
  const response = await fetch((phase === "before" ? origin : local) + path, { headers: { "User-Agent": userAgent } });
  const html = await response.text();
  const record = { path, agent, ...inspect(html, response) };
  evidence[phase].push(record);
  await writeFile(output + "/" + phase + "-" + (path.replaceAll("/", "_") || "home") + "-" + agent + ".html", html);
  if (phase === "after") {
    assert.equal(record.status, 200); assert.equal(record.h1.length, 1);
    assert.equal(record.canonical, origin + path); assert.ok(record.body.length > 300);
    assert.ok(!/noindex/i.test(record.robots + record.xRobotsTag));
    for (const hash of record.scriptHashes) assert.ok(record.csp.includes(hash), "CSP missing " + path + " " + hash);
    for (const link of record.links.filter(l => l.href?.startsWith("/") && !/^\/(app|login)/.test(l.href))) {
      const r = await fetch(local + link.href, { method: "HEAD" }); assert.equal(r.status, 200, path + " -> " + link.href);
    }
  }
}
const sitemapResponse = await fetch(local + "/sitemap.xml");
const sitemap = await sitemapResponse.text();
const urls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1]);
assert.equal(urls.length, 30);
for (const url of urls) {
  const response = await fetch(local + new URL(url).pathname, { headers: { "User-Agent": agents.baidu } });
  const page = inspect(await response.text(), response);
  assert.equal(page.status, 200); assert.equal(page.canonical, url);
  assert.equal(page.h1.length, 1); assert.ok(!/noindex/.test(page.robots + page.xRobotsTag));
  evidence.sitemap.push({ url, status: page.status, canonical: page.canonical, robots: page.robots, xRobotsTag: page.xRobotsTag });
}
assert.equal(new Set(evidence.after.map(p => p.title)).size, 4);
await writeFile(output + "/raw-html-evidence.json", JSON.stringify(evidence, null, 2));
console.log("PASS: 4 pages x 2 agents, raw HTML, schema/CSP, all internal links and 30 sitemap routes.");
