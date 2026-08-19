import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const webRoot = resolve(import.meta.dirname, "..");
const repoRoot = resolve(webRoot, "../..");
const [homepage, guide, nginx] = await Promise.all([
  readFile(resolve(webRoot, "dist/index.html"), "utf8"),
  readFile(resolve(webRoot, "dist/guide.html"), "utf8"),
  readFile(resolve(repoRoot, "infra/nginx/default.conf"), "utf8"),
]);

assert.match(homepage, /<link rel="canonical" href="https:\/\/mianshiwen\.cn\/"\s*\/>/);
assert.match(guide, /<link rel="canonical" href="https:\/\/mianshiwen\.cn\/guide"\s*\/>/);
assert.notEqual(homepage, guide);
assert.match(homepage, /<script type="module" crossorigin src="\/assets\/.+-[A-Za-z0-9_-]{8}\.js"><\/script>/);
assert.match(guide, /<script type="module" crossorigin src="\/assets\/.+-[A-Za-z0-9_-]{8}\.js"><\/script>/);
for (const html of [homepage, guide]) {
  for (const match of html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)) {
    const hash = createHash("sha256").update(match[1]).digest("base64");
    assert.ok(nginx.includes(`'sha256-${hash}'`), `Production CSP is missing JSON-LD hash ${hash}`);
  }
}

console.log("SEO production build checks passed.");
