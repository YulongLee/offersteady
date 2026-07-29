import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const webRoot = resolve(import.meta.dirname, "..");
const repoRoot = resolve(webRoot, "../..");
const [indexHtml, robots, sitemap, notFound, nginx] = await Promise.all([
  readFile(resolve(webRoot, "index.html"), "utf8"),
  readFile(resolve(webRoot, "public/robots.txt"), "utf8"),
  readFile(resolve(webRoot, "public/sitemap.xml"), "utf8"),
  readFile(resolve(webRoot, "public/404.html"), "utf8"),
  readFile(resolve(repoRoot, "infra/nginx/default.conf"), "utf8"),
]);

assert.match(indexHtml, /<link rel="canonical" href="https:\/\/mianshiwen\.cn\/"\s*\/>/);
assert.match(indexHtml, /<h1>AI 面试助手，助你更从容地冲刺 Offer。<\/h1>/);
assert.match(indexHtml, /<a href="\/login">登录或免费体验<\/a>/);
const schemas = [...indexHtml.matchAll(/<script type="application\/ld\+json">(.+?)<\/script>/g)]
  .map((match) => JSON.parse(match[1]));
assert.equal(schemas.length, 3);
assert.ok(schemas.every((schema) => schema["@context"] === "https://schema.org"));
assert.deepEqual(schemas.map((schema) => schema["@type"]), [
  "Organization",
  "WebSite",
  "SoftwareApplication",
]);

assert.equal(
  robots.trim(),
  "User-agent: *\nAllow: /\n\nSitemap: https://mianshiwen.cn/sitemap.xml",
);
assert.match(sitemap, /^<\?xml version="1\.0" encoding="UTF-8"\?>/);
assert.match(sitemap, /<loc>https:\/\/mianshiwen\.cn\/<\/loc>/);
assert.doesNotMatch(sitemap, /\/login|\/app/);
assert.match(notFound, /<meta name="robots" content="noindex, follow"\s*\/>/);
assert.match(nginx, /if \(\$host = www\.mianshiwen\.cn\)\s*\{\s*return 308 https:\/\/mianshiwen\.cn\$request_uri;/);
assert.match(nginx, /location = \/robots\.txt[\s\S]*?try_files \$uri =404;/);
assert.match(nginx, /location = \/sitemap\.xml[\s\S]*?try_files \$uri =404;/);
assert.match(nginx, /location ~ \^\/\(\?:login\|error\|app/);
assert.match(nginx, /location \/\s*\{\s*return 404;/);
assert.doesNotMatch(nginx, /try_files \$uri \$uri\/ \/index\.html/);

console.log("SEO P0 regression checks passed.");
