// Fingerprints of the authorized public source after the 2026-10-27 SEO update.
// Release assembly rewrites links/dates; production byte verification is recorded
// separately in docs/releases/cn-search-content-20261027.1/production-verification.json.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
const publicRoot = join(dirname(fileURLToPath(import.meta.url)), "public");
const preserved = [
  {
    "path": "llms-full.txt",
    "sha256": "bdf2922b0ffcf027dc0c13f25228eb0fe57f46f6cd815568671d08fcbdbbb8b8"
  },
  {
    "path": "public-facts.json",
    "sha256": "9807119acd473f7c26c7f4699aa24087a2a193ad50a0d648b0096c018ce37384"
  },
  {
    "path": "seo/features.html",
    "sha256": "8ce1f44e24e1d18887c5b4485ca834112771db113da58683e66609efe63b8731"
  },
  {
    "path": "seo/realtime-interview.html",
    "sha256": "72aa5c665bba3bb6c33dfcf1b3f9fd5d3d3def599734c2cffdea230d4331eca2"
  },
  {
    "path": "sitemap.xml",
    "sha256": "10ceb2ad257aaf46cd7a0590bacbbf0363461773e9b566fea299c2a5a2a84384"
  }
];
describe("runtime optimization preserves authorized public source content", () => {
  it.each(preserved)("retains approved source $path", ({ path, sha256 }) => {
    const bytes = readFileSync(join(publicRoot, path));
    expect(createHash("sha256").update(bytes).digest("hex")).toBe(sha256);
  });
});
