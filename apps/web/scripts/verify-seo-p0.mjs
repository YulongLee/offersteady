import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";

const webRoot = resolve(import.meta.dirname, "..");
const repoRoot = resolve(webRoot, "../..");
const topicRoutes = new Map([
  ["/features/ai-interview-assistant", "public/seo/ai-interview-assistant.html"],
  ["/features/realtime-interview", "public/seo/realtime-interview.html"],
  ["/features/screenshot-answer", "public/seo/screenshot-answer.html"],
  ["/features/interview-review", "public/seo/interview-review.html"],
  ["/guides/audio-troubleshooting", "public/seo/audio-troubleshooting.html"],
  ["/guides/interview-preparation", "public/seo/interview-preparation.html"],
]);
const readWeb = (path) => readFile(resolve(webRoot, path), "utf8");
const [indexHtml, guideHtml, robots, sitemap, notFound, nginx, llms, llmsFull, factsText, appSource, shareCard] = await Promise.all([
  readWeb("index.html"), readWeb("guide.html"), readWeb("public/robots.txt"), readWeb("public/sitemap.xml"),
  readWeb("public/404.html"), readFile(resolve(repoRoot, "infra/nginx/default.conf"), "utf8"),
  readWeb("public/llms.txt"), readWeb("public/llms-full.txt"), readWeb("public/public-facts.json"),
  readWeb("src/App.tsx"), readFile(resolve(webRoot, "public/assets/brand/share-card.png")),
]);
const topicDocuments = new Map(await Promise.all([...topicRoutes].map(async ([route, file]) => [route, await readWeb(file)])));
const publicEntries = new Map([["/", indexHtml], ["/guide", guideHtml], ...topicDocuments]);
const canonicalUrl = (route) => `https://mianshiwen.cn${route}`;

const metadata = [];
for (const [route, html] of publicEntries) {
  const canonical = canonicalUrl(route);
  assert.ok(html.includes(`<link rel="canonical" href="${canonical}" />`), `Missing self-canonical for ${route}`);
  const title = html.match(/<title>([^<]+)<\/title>/)?.[1];
  const description = html.match(/<meta\s+name="description"\s+content="([^"]+)"/s)?.[1];
  assert.ok(title && title.length >= 12 && title.length <= 70, `Invalid title for ${route}`);
  assert.ok(description && description.length >= 45 && description.length <= 180, `Invalid description for ${route}`);
  assert.equal((html.match(/<h1(?:\s[^>]*)?>/g) ?? []).length, 1, `Expected one H1 for ${route}`);
  assert.match(html, /<meta property="og:image" content="https:\/\/mianshiwen\.cn\/assets\/brand\/share-card\.png"\s*\/>/);
  assert.match(html, /<meta name="twitter:card" content="summary_large_image"\s*\/>/);
  metadata.push({ route, title, description });
  const schemas = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map((match) => {
    const parsed = JSON.parse(match[1]);
    const hash = createHash("sha256").update(match[1]).digest("base64");
    assert.ok(nginx.includes(`'sha256-${hash}'`), `CSP is missing JSON-LD hash for ${route}: ${hash}`);
    return parsed;
  });
  assert.ok(schemas.length >= 1, `Missing JSON-LD for ${route}`);
  assert.ok(schemas.every((schema) => schema["@context"] === "https://schema.org"), `Invalid schema context for ${route}`);
}
assert.equal(new Set(metadata.map((item) => item.title)).size, metadata.length, "Public titles must be unique");
assert.equal(new Set(metadata.map((item) => item.description)).size, metadata.length, "Public descriptions must be unique");
assert.deepEqual([...indexHtml.matchAll(/<script type="application\/ld\+json">(.+?)<\/script>/g)].map((match) => JSON.parse(match[1])["@type"]), ["Organization", "WebSite", "SoftwareApplication"]);
assert.deepEqual([...guideHtml.matchAll(/<script type="application\/ld\+json">(.+?)<\/script>/g)].map((match) => JSON.parse(match[1])["@type"]), ["WebPage", "BreadcrumbList"]);
for (const [route, html] of topicDocuments) {
  const graph = JSON.parse(html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1])["@graph"];
  assert.deepEqual(graph.map((node) => node["@type"]), ["WebPage", "BreadcrumbList"], `Unexpected topic schema for ${route}`);
  assert.doesNotMatch(html, /(?<!不)保证(?:面试|录用)|百分之百|绝对准确|官方合作|直接集成|真实用户评价/);
  assert.match(html, /class="boundary"/);
  assert.ok(Buffer.byteLength(html) <= 12_000, `Topic HTML budget exceeded for ${route}`);
}

assert.equal(shareCard.subarray(1, 4).toString("ascii"), "PNG");
assert.equal(shareCard.readUInt32BE(16), 1200);
assert.equal(shareCard.readUInt32BE(20), 630);
assert.ok(shareCard.byteLength <= 100_000, "Share card exceeds 100 KB budget");
assert.ok((await stat(resolve(webRoot, "public/assets/brand/app-icon-96.png"))).size <= 16_000, "Rendered app icon exceeds 16 KB budget");
assert.ok((await stat(resolve(webRoot, "public/seo/public-search.css"))).size <= 8_000, "Topic CSS exceeds 8 KB budget");
assert.match(appSource, /brand\.app-icon[^>]+width="44" height="44"[^>]+decoding="async"/);
assert.match(appSource, /platform\.logoUrl[^>]+width="180" height="48"[^>]+loading="lazy" decoding="async"/);

assert.equal(robots.trim(), "User-agent: *\nAllow: /\n\nSitemap: https://mianshiwen.cn/sitemap.xml");
const sitemapEntries = [...sitemap.matchAll(/<url>\s*<loc>(https:\/\/mianshiwen\.cn(?:\/[^<]*)?)<\/loc>\s*<lastmod>(\d{4}-\d{2}-\d{2})<\/lastmod>/g)].map((match) => ({ url: new URL(match[1]), lastmod: match[2] }));
assert.deepEqual(sitemapEntries.map(({ url }) => url.pathname), [...publicEntries.keys()]);
assert.ok(sitemapEntries.every(({ lastmod }) => lastmod === "2026-08-19"));
assert.doesNotMatch(sitemap, /\/login|\/app/);

const discoveryHtml = `${indexHtml}\n${guideHtml}`;
for (const route of topicRoutes.keys()) {
  assert.ok(discoveryHtml.includes(`href="${route}"`), `Topic is not linked from homepage or guide: ${route}`);
  assert.ok(llms.includes(canonicalUrl(route)), `llms.txt missing ${route}`);
}
assert.match(llms, /AI 输出仅供参考/);
assert.match(llmsFull, /价格.*积分消耗.*支付渠道.*调整/);
assert.doesNotMatch(`${llms}\n${llmsFull}`, /\/api\/|AccessKey|Secret|private key|BEGIN .* KEY/iu);
const facts = JSON.parse(factsText);
assert.equal(facts.schemaVersion, "1.0");
assert.equal(facts.canonicalSite, "https://mianshiwen.cn/");
assert.equal(facts.product.name, "面试稳AI助手");
assert.equal(facts.dataBoundaries.rawAudioStoredByDefault, false);
assert.equal(facts.dataBoundaries.guaranteesInterviewOutcome, false);
assert.doesNotMatch(factsText, /\/api\/|access.?key|secret|password|token/iu);
for (const url of ["https://mianshiwen.cn/guide", "https://mianshiwen.cn/privacy", "https://mianshiwen.cn/terms"]) {
  assert.ok(llms.includes(url) || llmsFull.includes(url));
  assert.ok(factsText.includes(url));
}

assert.match(notFound, /<meta name="robots" content="noindex, follow"\s*\/>/);
assert.match(nginx, /if \(\$host = www\.mianshiwen\.cn\)[\s\S]*?return 308 https:\/\/mianshiwen\.cn\$request_uri;/);
assert.ok(nginx.includes("location ~ ^/features/(ai-interview-assistant|realtime-interview|screenshot-answer|interview-review)/?$"));
assert.ok(nginx.includes("location ~ ^/guides/(audio-troubleshooting|interview-preparation)/?$"));
for (const resource of ["llms.txt", "llms-full.txt", "public-facts.json"]) assert.ok(nginx.includes(`location = /${resource}`), `Missing Nginx route for ${resource}`);
assert.match(nginx, /location ~\* "\^\/assets\/[\s\S]*?Cache-Control "public, max-age=31536000, immutable"/);
assert.match(nginx, /location ~ \^\/\(\?:login\|terms\|privacy\|error\|invite\/[\s\S]*?Cache-Control "no-store"[\s\S]*?X-Robots-Tag "noindex, follow"/);
assert.match(nginx, /location \/\s*\{\s*return 404;/);
assert.doesNotMatch(nginx, /try_files \$uri \$uri\/ \/index\.html/);

console.log(`SEO/GEO source checks passed for ${publicEntries.size} public pages.`);
