import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { legalStaticHtml } from "./legal-static";
import { privacySections, termsSections } from "./src/legal-content";

describe("legal raw HTML", () => {
  for (const kind of ["terms", "privacy"] as const) it(`renders existing ${kind} paragraphs with route metadata`, () => {
    const source = readFileSync("index.html", "utf8");
    const result = legalStaticHtml(source, kind);
    const doc = new DOMParser().parseFromString(result, "text/html");
    expect(doc.querySelector('link[rel="canonical"]')?.getAttribute("href")).toBe(`https://mianshiwen.cn/${kind}`);
    expect(doc.querySelectorAll("h1")).toHaveLength(1);
    expect(doc.querySelector("h1")?.textContent).toBe(kind === "terms" ? "用户协议" : "隐私政策");
    for (const [,paragraphs] of kind === "terms" ? termsSections : privacySections) for (const p of paragraphs) expect(doc.body.textContent).toContain(p);
    expect(result).not.toContain("让你的经历更好表达");
    expect(result).not.toContain("noindex");
    expect(doc.querySelector('script[type="module"]')).not.toBeNull();
    expect(result).toContain("contact@oneshowailab.com");
  });
});
