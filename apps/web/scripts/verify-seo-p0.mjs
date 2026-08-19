import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";

const webRoot = resolve(import.meta.dirname, "..");
const repoRoot = resolve(webRoot, "../..");
const featureRoutes = new Map([
  ["/features/ai-interview-assistant", "public/seo/ai-interview-assistant.html"],
  ["/features/realtime-interview", "public/seo/realtime-interview.html"],
  ["/features/screenshot-answer", "public/seo/screenshot-answer.html"],
  ["/features/interview-review", "public/seo/interview-review.html"],
]);
const hubRoutes = new Map([
  ["/features", "public/seo/features.html"],
  ["/guides", "public/seo/guides.html"],
  ["/interview-questions", "public/seo/interview-questions.html"],
]);
const commercialRoutes = new Map([
  ["/pricing", "public/seo/pricing.html"],
  ["/download", "public/seo/download.html"],
  ["/security", "public/seo/security.html"],
  ["/about", "public/seo/about.html"],
  ["/contact", "public/seo/contact.html"],
]);
const guideRoutes = new Map([
  ["/guides/audio-troubleshooting", "public/seo/audio-troubleshooting.html"],
  ["/guides/interview-preparation", "public/seo/interview-preparation.html"],
  ["/guides/macos-permissions", "public/seo/macos-permissions.html"],
  ["/guides/feishu-audio-setup", "public/seo/feishu-audio-setup.html"],
  ["/guides/tencent-meeting-audio-setup", "public/seo/tencent-meeting-audio-setup.html"],
  ["/guides/star-interview-answer", "public/seo/star-interview-answer.html"],
  ["/guides/self-introduction", "public/seo/self-introduction.html"],
  ["/guides/project-experience", "public/seo/project-experience.html"],
  ["/guides/technical-interview", "public/seo/technical-interview.html"],
  ["/guides/common-interview-questions", "public/seo/common-interview-questions.html"],
]);
const coreGuideRoutes = new Set(["/guides/self-introduction", "/guides/project-experience", "/guides/technical-interview", "/guides/common-interview-questions"]);
const aiTopicRoutes = new Map([
  ["/interview-questions/llm", "public/seo/llm.html"],
  ["/interview-questions/rag", "public/seo/rag.html"],
  ["/interview-questions/ai-agent", "public/seo/ai-agent.html"],
]);
const articleRoutes = new Set([...guideRoutes.keys(), ...aiTopicRoutes.keys()]);
const deepArticleRoutes = new Set([...coreGuideRoutes, ...aiTopicRoutes.keys()]);
const topicRoutes = new Map([...hubRoutes, ...featureRoutes, ...commercialRoutes, ...guideRoutes, ...aiTopicRoutes]);
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
  const expectedPageType = articleRoutes.has(route) ? "Article" : route === "/about" ? "AboutPage" : route === "/contact" ? "ContactPage" : "WebPage";
  assert.deepEqual(graph.map((node) => node["@type"]), [expectedPageType, "BreadcrumbList"], `Unexpected topic schema for ${route}`);
  assert.doesNotMatch(html, /(?:可以|能够|将|会)保证(?:面试|录用)|百分之百|绝对准确|(?:属于|已经|现为|达成)官方合作|(?:已经|现已|完成)直接集成|真实用户评价/);
  assert.match(html, /class="boundary"/);
  assert.ok(Buffer.byteLength(html) <= (deepArticleRoutes.has(route) ? 20_000 : 12_000), `Topic HTML budget exceeded for ${route}`);
}
for (const route of articleRoutes) {
  const html = topicDocuments.get(route);
  assert.match(html, /面试稳产品与支持团队/);
  assert.match(html, /datePublished|dateModified/);
  assert.match(html, /class="answer-block"/);
  assert.match(html, /class="[^"]*\bsource-note\b[^"]*"/);
}
for (const route of commercialRoutes.keys()) {
  const html = topicDocuments.get(route);
  assert.match(html, /登录|产品内|下载页|联系/);
  assert.match(html, /href="\/(?:login|guide|pricing|download|security|about|contact)/, `Missing crawlable CTA for ${route}`);
}

assert.equal(shareCard.subarray(1, 4).toString("ascii"), "PNG");
assert.equal(shareCard.readUInt32BE(16), 1200);
assert.equal(shareCard.readUInt32BE(20), 630);
assert.ok(shareCard.byteLength <= 100_000, "Share card exceeds 100 KB budget");
assert.ok((await stat(resolve(webRoot, "public/assets/brand/app-icon-96.png"))).size <= 16_000, "Rendered app icon exceeds 16 KB budget");
assert.ok((await stat(resolve(webRoot, "public/seo/public-search.css"))).size <= 8_000, "Topic CSS exceeds 8 KB budget");
assert.match(appSource, /brand\.app-icon[^>]+width="44" height="44"[^>]+decoding="async"/);
assert.match(appSource, /platform\.logoUrl[^>]+width="180" height="48"[^>]+loading="lazy" decoding="async"/);

for (const agent of ["*", "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "PerplexityBot"]) {
  assert.match(robots, new RegExp(`User-agent: ${agent === "*" ? "\\*" : agent}\\nAllow: /`), `Missing allow policy for ${agent}`);
}
assert.match(robots, /Sitemap: https:\/\/mianshiwen\.cn\/sitemap\.xml/);
const sitemapEntries = [...sitemap.matchAll(/<url>\s*<loc>(https:\/\/mianshiwen\.cn(?:\/[^<]*)?)<\/loc>\s*<lastmod>(\d{4}-\d{2}-\d{2})<\/lastmod>/g)].map((match) => ({ url: new URL(match[1]), lastmod: match[2] }));
assert.deepEqual(new Set(sitemapEntries.map(({ url }) => url.pathname)), new Set(publicEntries.keys()));
assert.equal(sitemapEntries.length, publicEntries.size);
assert.ok(sitemapEntries.every(({ lastmod }) => lastmod === "2026-08-19"));
assert.doesNotMatch(sitemap, /\/login|\/app/);

const discoveryHtml = `${indexHtml}\n${guideHtml}\n${[...hubRoutes.keys()].map((route) => topicDocuments.get(route)).join("\n")}`;
for (const route of topicRoutes.keys()) {
  assert.ok(discoveryHtml.includes(`href="${route}"`), `Topic is not linked from homepage or guide: ${route}`);
  assert.ok(llms.includes(canonicalUrl(route)), `llms.txt missing ${route}`);
}
assert.match(llms, /AI 输出仅供参考/);
assert.match(llmsFull, /价格.*积分消耗.*支付渠道.*调整/);
assert.doesNotMatch(`${llms}\n${llmsFull}`, /\/api\/|AccessKey|Secret|private key|BEGIN .* KEY/iu);
const facts = JSON.parse(factsText);
assert.equal(facts.schemaVersion, "1.1");
assert.equal(facts.canonicalSite, "https://mianshiwen.cn/");
assert.equal(facts.product.name, "面试稳AI助手");
assert.equal(facts.dataBoundaries.rawAudioStoredByDefault, false);
assert.equal(facts.dataBoundaries.guaranteesInterviewOutcome, false);
assert.equal(facts.entityBoundaries.registeredLegalOperatorVerified, false);
assert.equal(facts.entityBoundaries.platformNamesIndicateAffiliation, false);
assert.doesNotMatch(factsText, /\/api\/|access.?key|secret|password|token/iu);
for (const url of ["https://mianshiwen.cn/guide", "https://mianshiwen.cn/privacy", "https://mianshiwen.cn/terms"]) {
  assert.ok(llms.includes(url) || llmsFull.includes(url));
  assert.ok(factsText.includes(url));
}

assert.match(notFound, /<meta name="robots" content="noindex, follow"\s*\/>/);
assert.match(nginx, /if \(\$host = www\.mianshiwen\.cn\)[\s\S]*?return 308 https:\/\/mianshiwen\.cn\$request_uri;/);
assert.ok(nginx.includes("location ~ ^/features/(ai-interview-assistant|realtime-interview|screenshot-answer|interview-review)/?$"));
assert.ok(nginx.includes("location ~ ^/(features|guides|interview-questions)/?$"));
assert.ok(nginx.includes("location ~ ^/(pricing|download|security|about|contact)/?$"));
assert.ok(nginx.includes("location ~ ^/guides/(audio-troubleshooting|interview-preparation|macos-permissions|feishu-audio-setup|tencent-meeting-audio-setup|star-interview-answer|self-introduction|project-experience|technical-interview|common-interview-questions)/?$"));
assert.ok(nginx.includes("location ~ ^/interview-questions/(llm|rag|ai-agent)/?$"));
for (const resource of ["llms.txt", "llms-full.txt", "public-facts.json"]) assert.ok(nginx.includes(`location = /${resource}`), `Missing Nginx route for ${resource}`);
assert.match(nginx, /location ~\* "\^\/assets\/[\s\S]*?Cache-Control "public, max-age=31536000, immutable"/);
assert.match(nginx, /location ~ \^\/\(\?:login\|terms\|privacy\|error\|invite\/[\s\S]*?Cache-Control "no-store"[\s\S]*?X-Robots-Tag "noindex, follow"/);
assert.match(nginx, /location \/\s*\{\s*return 404;/);
assert.doesNotMatch(nginx, /try_files \$uri \$uri\/ \/index\.html/);

console.log(`SEO/GEO source checks passed for ${publicEntries.size} public pages.`);
