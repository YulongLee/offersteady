import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const styles = readFileSync(resolve(__dirname, "styles.css"), "utf8");

describe("appearance styles", () => {
  it("scopes the bright palette to authenticated app surfaces", () => {
    expect(styles).toContain(':root[data-theme="bright"] .app-shell');
    expect(styles).toContain(':root[data-theme="bright"] .live-page');
    expect(styles).not.toContain(':root[data-theme="bright"] .route-loading-page');
    expect(styles).not.toContain(':root[data-theme="bright"] {');
    expect(styles).toContain("--bg: #f6f8fb");
    expect(styles).toContain("--field-bg: #fbfcfd");
    expect(styles).toContain("--answer-text: #1f2933");
    expect(styles).toContain(':root[data-theme="bright"] :is(.app-shell, .live-page) .continue-card');
    expect(styles).toContain(':root[data-theme="bright"] :is(.app-shell, .live-page) .balance-card');
    expect(styles).toContain(':root[data-theme="bright"] :is(.app-shell, .live-page) .global-live-alert');
    expect(styles).not.toMatch(/:root\[data-theme="bright"\]\s+\.button\.ghost/);
  });

  it("uses a single answer-size variable without enlarging transcript controls", () => {
    expect(styles).toContain(':root[data-answer-font-size="large"]');
    expect(styles).toContain("--answer-font-size: 19px");
    expect(styles).toMatch(/\.answer-markdown[^}]*font-size: var\(--answer-font-size\)/);
    expect(styles).toMatch(/\.simple-answer p[^}]*font-size: var\(--answer-font-size\)/);
    expect(styles).toMatch(/\.conversation-turn p[^}]*font-size: 10px/);
  });

  it("keeps destructive and disabled actions visible in the bright theme", () => {
    expect(styles).toMatch(
      /:root\[data-theme="bright"\][^{]*\.button\.danger \{[^}]*color: #9f1239;[^}]*border-color: #f1aeb8;[^}]*background: #fff1f2;/,
    );
    expect(styles).toMatch(
      /:root\[data-theme="bright"\][^{]*\.button\.danger:not\(:disabled\):hover \{[^}]*color: #881337;[^}]*background: #ffe4e6;/,
    );
    expect(styles).toMatch(
      /:root\[data-theme="bright"\][^{]*\.button\.danger:focus-visible \{[^}]*outline-color: rgba\(159,18,57,.42\);/,
    );
    expect(styles).toMatch(
      /:root\[data-theme="bright"\][^{]*\.button:disabled \{[^}]*opacity: \.58;/,
    );
  });

  it("keeps the mobile answer in the page scroll flow without a covering action bar", () => {
    expect(styles).toMatch(/\.focused-live-grid \{[^}]*overflow-y: auto[^}]*-webkit-overflow-scrolling: touch[^}]*touch-action: pan-y/);
    expect(styles).toMatch(/\.answer-workspace, \.answer-workspace\.mobile-answer-expanded \{[^}]*overflow: visible/);
    expect(styles).toMatch(/\.answer-workspace-head \{[^}]*position: static/);
    expect(styles).toMatch(/\.answer-action-bar \{[^}]*position: static/);
    expect(styles).not.toMatch(/\.answer-action-bar \{[^}]*position: sticky/);
  });
});
