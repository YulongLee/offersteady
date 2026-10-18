// Contract captured from the actual running CN Web image, not Git HEAD.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
const publicRoot = join(dirname(fileURLToPath(import.meta.url)), "public");
const preserved = [
  {
    "path": "llms-full.txt",
    "sha256": "571f42120eb35e4c33183bf86fe4d1468c177562168c3c75367a697a373bddd8"
  },
  {
    "path": "public-facts.json",
    "sha256": "325a702023158a87d4caf61b3119f7fc0ccd1f29bad6e91546dd326c1d22c7ad"
  },
  {
    "path": "seo/features.html",
    "sha256": "8ce1f44e24e1d18887c5b4485ca834112771db113da58683e66609efe63b8731"
  },
  {
    "path": "seo/realtime-interview.html",
    "sha256": "108cf9afce41c7ffe3235b09fe6876378ba16b52becbe4d3b6d5a913f84b89b9"
  },
  {
    "path": "sitemap.xml",
    "sha256": "10ceb2ad257aaf46cd7a0590bacbbf0363461773e9b566fea299c2a5a2a84384"
  }
];
describe("resume addition preserves unrelated published public content", () => {
  it.each(preserved)("retains actual online $path", ({ path, sha256 }) => {
    const bytes = readFileSync(join(publicRoot, path));
    expect(createHash("sha256").update(bytes).digest("hex")).toBe(sha256);
  });
});
