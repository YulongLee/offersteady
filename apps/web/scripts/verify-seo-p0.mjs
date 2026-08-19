import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const webRoot = resolve(import.meta.dirname, "..");
const repoRoot = resolve(webRoot, "../..");
const [indexHtml, guideHtml, robots, sitemap, notFound, nginx, shareCard, viteConfig] = await Promise.all([
  readFile(resolve(webRoot, "index.html"), "utf8"),
  readFile(resolve(webRoot, "guide.html"), "utf8"),
  readFile(resolve(webRoot, "public/robots.txt"), "utf8"),
  readFile(resolve(webRoot, "public/sitemap.xml"), "utf8"),
  readFile(resolve(webRoot, "public/404.html"), "utf8"),
  readFile(resolve(repoRoot, "infra/nginx/default.conf"), "utf8"),
  readFile(resolve(webRoot, "public/assets/brand/share-card.png")),
  readFile(resolve(webRoot, "vite.config.ts"), "utf8"),
]);

assert.match(indexHtml, /<link rel="canonical" href="https:\/\/mianshiwen\.cn\/"\s*\/>/);
assert.match(indexHtml, /<title>AI面试助手｜实时语音识别、截图解题与个性化回答 - 面试稳<\/title>/);
assert.match(indexHtml, /<h1>AI 面试助手，助你更从容地冲刺 Offer。<\/h1>/);
assert.match(indexHtml, /<a href="\/login">登录或免费体验<\/a>/);
assert.match(indexHtml, /<a href="\/guide">使用手册<\/a>/);
const schemas = [...indexHtml.matchAll(/<script type="application\/ld\+json">(.+?)<\/script>/g)]
  .map((match) => JSON.parse(match[1]));
assert.equal(schemas.length, 3);
assert.ok(schemas.every((schema) => schema["@context"] === "https://schema.org"));
assert.deepEqual(schemas.map((schema) => schema["@type"]), [
  "Organization",
  "WebSite",
  "SoftwareApplication",
]);

assert.match(guideHtml, /<link rel="canonical" href="https:\/\/mianshiwen\.cn\/guide"\s*\/>/);
assert.match(guideHtml, /<title>面试稳AI助手使用手册｜安装、收音、截图回答与支付说明<\/title>/);
assert.match(guideHtml, /<h1>从准备资料到面试现场，按步骤完成设置<\/h1>/);
assert.match(guideHtml, /<a href="\/">返回首页<\/a>/);
assert.match(guideHtml, /<a href="\/login">登录或免费体验<\/a>/);
assert.doesNotMatch(guideHtml, /<link rel="canonical" href="https:\/\/mianshiwen\.cn\/"\s*\/>/);
const guideSchemas = [...guideHtml.matchAll(/<script type="application\/ld\+json">(.+?)<\/script>/g)]
  .map((match) => JSON.parse(match[1]));
assert.deepEqual(guideSchemas.map((schema) => schema["@type"]), ["WebPage", "BreadcrumbList"]);
assert.ok(guideSchemas.every((schema) => schema["@context"] === "https://schema.org"));
assert.notEqual(
  indexHtml.match(/<meta\s+name="description"\s+content="([^"]+)"/s)?.[1],
  guideHtml.match(/<meta\s+name="description"\s+content="([^"]+)"/s)?.[1],
);
assert.match(indexHtml, /<meta property="og:image" content="https:\/\/mianshiwen\.cn\/assets\/brand\/share-card\.png"\s*\/>/);
assert.match(indexHtml, /<meta name="twitter:card" content="summary_large_image"\s*\/>/);
assert.equal(shareCard.subarray(1, 4).toString("ascii"), "PNG");
assert.equal(shareCard.readUInt32BE(16), 1200);
assert.equal(shareCard.readUInt32BE(20), 630);

assert.equal(
  robots.trim(),
  "User-agent: *\nAllow: /\n\nSitemap: https://mianshiwen.cn/sitemap.xml",
);
assert.match(sitemap, /^<\?xml version="1\.0" encoding="UTF-8"\?>/);
assert.match(sitemap, /<loc>https:\/\/mianshiwen\.cn\/<\/loc>/);
assert.match(sitemap, /<loc>https:\/\/mianshiwen\.cn\/guide<\/loc>/);
assert.doesNotMatch(sitemap, /\/login|\/app/);
const sitemapUrls = [...sitemap.matchAll(/<loc>(https:\/\/mianshiwen\.cn(?:\/[^<]*)?)<\/loc>/g)]
  .map((match) => new URL(match[1]));
const publicEntries = new Map([
  ["/", indexHtml],
  ["/guide", guideHtml],
]);
assert.deepEqual(sitemapUrls.map((url) => url.pathname), [...publicEntries.keys()]);
for (const url of sitemapUrls) {
  const html = publicEntries.get(url.pathname);
  assert.ok(html, `Missing public entry document for sitemap URL ${url.href}`);
  assert.ok(html.includes(`<link rel="canonical" href="${url.href}" />`), `Non-self-canonical sitemap URL ${url.href}`);
  assert.match(html, /<title>[^<]+<\/title>/);
  assert.match(html, /<meta\s+name="description"\s+content="[^"]+"/s);
  assert.match(html, /<h1>[^<]+<\/h1>/);
}
assert.match(notFound, /<meta name="robots" content="noindex, follow"\s*\/>/);
assert.match(nginx, /if \(\$host = www\.mianshiwen\.cn\)\s*\{\s*return 308 https:\/\/mianshiwen\.cn\$request_uri;/);
assert.match(nginx, /location = \/robots\.txt[\s\S]*?try_files \$uri =404;/);
assert.match(nginx, /location = \/sitemap\.xml[\s\S]*?try_files \$uri =404;/);
assert.match(nginx, /location ~ \^\/guide\/\?\$[\s\S]*?try_files \/guide\.html =404;/);
assert.match(nginx, /location ~ \^\/\(\?:login\|terms\|privacy\|error\|invite\/\[\^\/\]\+\|app/);
assert.ok(nginx.includes('location ~* "^/assets/.+-[A-Za-z0-9_-]{8}\\.(?:js|css)$"'));
assert.match(nginx, /location ~\* "\^\/assets\/[\s\S]*?Cache-Control "public, max-age=31536000, immutable"/);
assert.match(nginx, /location \/assets\/\s*\{\s*try_files \$uri =404;/);
assert.match(nginx, /location ~ \^\/\(\?:login\|terms\|privacy\|error\|invite\/\[\^\/\]\+\|app[\s\S]*?X-Robots-Tag "noindex, follow"/);
assert.match(nginx, /location = \/\s*\{[\s\S]*?Cache-Control "public, max-age=0, must-revalidate"/);
assert.match(nginx, /location ~ \^\/guide\/\?\$[\s\S]*?Cache-Control "public, max-age=0, must-revalidate"/);
assert.match(nginx, /location ~ \^\/\(\?:login\|terms\|privacy\|error\|invite\/\[\^\/\]\+\|app[\s\S]*?Cache-Control "no-store"/);
assert.match(viteConfig, /main:\s*resolve\(import\.meta\.dirname, "index\.html"\)/);
assert.match(viteConfig, /guide:\s*resolve\(import\.meta\.dirname, "guide\.html"\)/);

for (const html of [indexHtml, guideHtml]) {
  for (const match of html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)) {
    const hash = createHash("sha256").update(match[1]).digest("base64");
    assert.ok(nginx.includes(`'sha256-${hash}'`), `CSP is missing JSON-LD hash ${hash}`);
  }
}
assert.match(indexHtml, /<a href="\/terms">用户协议<\/a>/);
assert.match(indexHtml, /<a href="\/privacy">隐私政策<\/a>/);
assert.match(nginx, /location \/\s*\{\s*return 404;/);
assert.doesNotMatch(nginx, /try_files \$uri \$uri\/ \/index\.html/);

console.log("SEO P0 regression checks passed.");
