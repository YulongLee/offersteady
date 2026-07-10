import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const srcRoot = join(process.cwd(), "src");
const readTree = (directory: string): string => readdirSync(directory).map(name => {
  const path = join(directory, name);
  return statSync(path).isDirectory() ? readTree(path) : /\.(ts|tsx)$/.test(path) && !/\.test\.(ts|tsx)$/.test(path) ? readFileSync(path, "utf8") : "";
}).join("\n");

const luminance = (hex: string) => {
  const values = hex.match(/[a-f\d]{2}/gi)!.map(value => Number.parseInt(value, 16) / 255).map(value => value <= .03928 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
  return .2126 * values[0]! + .7152 * values[1]! + .0722 * values[2]!;
};
const contrast = (foreground: string, background: string) => {
  const [bright, dark] = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
  return (bright! + .05) / (dark! + .05);
};

describe("responsive and security contracts", () => {
  const css = readFileSync(join(srcRoot, "styles.css"), "utf8");

  it("defines desktop, tablet and mobile layout contracts", () => {
    expect(css).toContain("grid-template-columns: 230px minmax(420px, 1fr) 240px");
    expect(css).toContain("@media (max-width: 1050px)");
    expect(css).toContain("@media (max-width: 720px)");
  });

  it("defines keyboard focus and 44px mobile targets", () => {
    expect(css).toContain(":focus-visible");
    expect(css).toMatch(/min-height:\s*44px/);
    expect(css).toContain("prefers-reduced-motion");
    expect(contrast("#edf2f8", "#080c13")).toBeGreaterThan(4.5);
    expect(contrast("#06241b", "#6ee7bd")).toBeGreaterThan(4.5);
  });

  it("contains no external provider credentials in browser source", () => {
    const source = readTree(srcRoot);
    expect(source).not.toMatch(/sk-[a-zA-Z0-9]{20,}/);
    expect(source).not.toMatch(/OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY/);
  });
});
