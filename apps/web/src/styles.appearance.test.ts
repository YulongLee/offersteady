import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const styles = readFileSync(resolve(__dirname, "styles.css"), "utf8");

describe("appearance styles", () => {
  it("scopes the bright palette to authenticated app surfaces", () => {
    expect(styles).toContain(':root[data-theme="bright"] .app-shell');
    expect(styles).toContain(':root[data-theme="bright"] .live-page');
    expect(styles).toContain(':root[data-theme="bright"] .route-loading-page');
    expect(styles).not.toContain(':root[data-theme="bright"] {');
    expect(styles).toContain("--field-bg: #ffffff");
    expect(styles).toContain("--answer-text: #17242b");
  });

  it("uses a single answer-size variable without enlarging transcript controls", () => {
    expect(styles).toContain(':root[data-answer-font-size="large"]');
    expect(styles).toContain("--answer-font-size: 19px");
    expect(styles).toMatch(/\.answer-markdown[^}]*font-size: var\(--answer-font-size\)/);
    expect(styles).toMatch(/\.simple-answer p[^}]*font-size: var\(--answer-font-size\)/);
    expect(styles).toMatch(/\.conversation-turn p[^}]*font-size: 10px/);
  });
});
