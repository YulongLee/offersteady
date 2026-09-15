import { describe, expect, it } from "vitest";
import indexHtml from "../index.html?raw";

describe("global HTML entry contract", () => {
  it("keeps the public prerender while providing an app-only shell", () => {
    expect(indexHtml).toContain('id="app-entry-shell"');
    expect(indexHtml).toContain('^\\/app(?:\\/|$)');
    expect(indexHtml).toContain('html[data-app-entry] #root > .seo-prerender');
    expect(indexHtml).toContain("AI interview guidance. Built around you.");
  });
});
