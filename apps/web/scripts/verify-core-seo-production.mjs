import { readFile, mkdir, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { loadProductionPricing, assertCurrentPricing } from "../pricing-static.mjs";
const out = process.argv[2];
if (!out) throw new Error("Pass output directory");
await mkdir(out, { recursive: true });
const origin = "https://mianshiwen.cn";
const dist = new URL("../dist/", import.meta.url);
const uas = { normal: "Mozilla/5.0 (compatible; OfferSteady-Release-Verification/1.0)", baidu: "Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)" };
const fileFor = path => path === "/" ? "index.html" : path === "/guide" ? "guide.html" : "seo/" + path.split("/").pop() + ".html";
const core = new Set(["/", "/pricing", "/features/realtime-interview", "/features/ai-interview-assistant"]);
function parse(html) {
  const d = new JSDOM(html).window.document;
  return { title: d.title, description: d.querySelector('meta[name="description"]')?.content,
    h1: [...d.querySelectorAll("h1")].map(n => n.textContent), canonical: d.querySelector('link[rel="canonical"]')?.href,
    robots: d.querySelector('meta[name="robots"]')?.content ?? "",
    body: d.querySelector("main")?.textContent,
    links: [...d.querySelectorAll("a[href]")].map(a => ({ href: a.getAttribute("href"), text: a.textContent })),
    scriptHashes: [...d.querySelectorAll('script[type="application/ld+json"]')].map(n => "sha256-" + createHash("sha256").update(n.textContent).digest("base64")) };
}
const expectedSitemap = await readFile(new URL("sitemap.xml", dist), "utf8");
const paths = [...expectedSitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => new URL(m[1]).pathname);
assert.equal(paths.length, 30);
const results = { capturedAt: new Date().toISOString(), version: "", pages: [], sitemap: [], smoke: [], links: [] };
const relevantLinks = new Set();
for (const [agent, ua] of Object.entries(uas)) {
  const s = await fetch(origin + "/sitemap.xml", { headers: { "User-Agent": ua }, signal: AbortSignal.timeout(15000) });
  const xml = await s.text(); assert.equal(s.status, 200); assert.equal(xml, expectedSitemap);
  results.sitemap.push({ agent, status: s.status, count: paths.length, equalsBuild: true });
  await writeFile(out + "/sitemap-" + agent + ".xml", xml);
  for (const path of paths) {
    const r = await fetch(origin + path, { headers: { "User-Agent": ua }, signal: AbortSignal.timeout(15000) });
    const html = await r.text();
    const actual = parse(html), expected = parse(await readFile(new URL(fileFor(path), dist), "utf8"));
    assert.equal(r.status, 200, path);
    for (const key of ["title", "description", "h1", "canonical", "body", "links"]) assert.deepEqual(actual[key], expected[key], path + " " + key);
    assert.equal(actual.h1.length, 1); assert.ok(actual.body.length > 200);
    assert.ok(!/noindex/i.test(actual.robots + r.headers.get("x-robots-tag")));
    const csp = r.headers.get("content-security-policy");
    for (const hash of actual.scriptHashes) assert.ok(csp.includes(hash), path + " CSP");
    if (core.has(path)) for (const link of actual.links) if (link.href?.startsWith("/") && !link.href.startsWith("//")) relevantLinks.add(link.href.split("#")[0] || "/");
    if (path === "/pricing") assertCurrentPricing(html, await loadProductionPricing());
    await writeFile(out + "/" + agent + "-" + path.replaceAll("/", "_") + ".html", html);
    results.pages.push({ agent, path, status: r.status, title: actual.title, description: actual.description, h1: actual.h1, canonical: actual.canonical, robots: actual.robots || "indexable (not set)", xRobotsTag: r.headers.get("x-robots-tag"), matchesBuild: true, core: core.has(path) });
  }
}
for (const path of relevantLinks) {
  const r = await fetch(origin + path, { method: "HEAD", signal: AbortSignal.timeout(15000) });
  assert.equal(r.status, 200, "Link " + path); results.links.push({ path, status: r.status });
}
for (const path of ["/login", "/app", "/app/billing", "/app/interviews/new", "/app/devices", "/download", "/healthz", "/api/v1/billing/status", "/assets/main-D8GtcuCK.js", "/assets/main-DLJpquzR.js"]) {
  const r = await fetch(origin + path, { signal: AbortSignal.timeout(15000) }); assert.equal(r.status, 200, path);
  const text = await r.text(); if (path.endsWith(".js")) assert.ok(!text.startsWith("<"));
  results.smoke.push({ path, status: r.status, contentType: r.headers.get("content-type"), bytes: Buffer.byteLength(text) });
}
const manifest = await (await fetch(origin + "/offersteady-build.json")).json();
assert.equal(manifest.appVersion, "cn-core-seo-20260908.1"); results.version = manifest.appVersion;
await writeFile(out + "/production-verification.json", JSON.stringify(results, null, 2));
console.log("PASS: " + results.version + "; 30 URLs x 2 UAs match build (Title/H1/Description/canonical/body/links); sitemap x2; pricing live; " + results.links.length + " links; read-only business routes and legacy assets.");
