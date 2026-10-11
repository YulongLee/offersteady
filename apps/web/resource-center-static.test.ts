import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { resourceCenterManifest, resourceReviewDate, resourceCenterUrls } from "./resource-center-manifest.mjs";

const root = resolve(import.meta.dirname);
const read = (path: string) => readFileSync(resolve(root, path), "utf8");
const origin = "https://mianshiwen.cn";

describe("CN technical resource center static delivery", () => {
  it("renders the directory and every published report with indexable metadata", () => {
    const pages = [
      { route: "/resources/", file: "public/resources/index.html", title: "技术报告与资源中心｜面试稳AI助手" },
      ...resourceCenterManifest.map(item => ({ route: `/resources/${item.slug}/`, file: `public/resources/${item.slug}/index.html`, title: item.metaTitle })),
    ];
    expect(pages.map(page => page.route)).toEqual(resourceCenterUrls);
    for (const page of pages) {
      const html = read(page.file);
      expect(html).toContain(`<link rel="canonical" href="${origin}${page.route}" />`);
      expect(html).toContain(`<title>${page.title}</title>`);
      expect(html.match(/<h1(?:\s[^>]*)?>/g) ?? []).toHaveLength(1);
      expect(html).toContain(resourceReviewDate);
      expect(html).toContain("application/ld+json");
      expect(html).toContain('class="conversion-page"');
      expect(html).not.toMatch(/Meta Title:|Meta Description:|URL Slug:|sk-[A-Za-z0-9]/);
      expect(html).not.toMatch(/AccessKey|Secret|BEGIN .* KEY/i);
      expect(html).toContain('href="/resources/"');
    }
  });

  it("keeps each JSON-LD script covered by the shared CSP", () => {
    const nginx = readFileSync(resolve(root, "../../infra/nginx/default.conf"), "utf8");
    for (const file of ["public/resources/index.html", ...resourceCenterManifest.map(item => `public/resources/${item.slug}/index.html`)]) {
      const html = read(file);
      const payload = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)?.[1];
      expect(payload).toBeTruthy();
      const hash = createHash("sha256").update(payload!, "utf8").digest("base64");
      expect(nginx).toContain(`'sha256-${hash}'`);
    }
  });

  it("exposes a crawlable related-report path on every article", () => {
    for (const item of resourceCenterManifest) {
      const html = read(`public/resources/${item.slug}/index.html`);
      expect(html).toContain("相关技术报告");
      for (const relatedSlug of item.relatedSlugs) {
        expect(html).toContain(`href="/resources/${relatedSlug}/"`);
      }
    }
    const directory = read("public/resources/index.html");
    const graph = JSON.parse(directory.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)?.[1] ?? "{}")["@graph"];
    expect(graph.map((node: { [key: string]: unknown }) => node["@type"])).toEqual(["CollectionPage", "ItemList", "BreadcrumbList"]);
    expect(graph.find((node: { [key: string]: unknown }) => node["@type"] === "ItemList").numberOfItems).toBe(resourceCenterManifest.length);
  });
});
