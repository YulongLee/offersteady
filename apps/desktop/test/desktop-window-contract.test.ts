import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("desktop companion window sizing", () => {
  it("uses a compact default height without removing vertical overflow access", () => {
    const mainSource = readFileSync(new URL("../src/main/index.ts", import.meta.url), "utf8");
    const styles = readFileSync(new URL("../src/renderer/styles.css", import.meta.url), "utf8");

    expect(mainSource).toContain("width: 780");
    expect(mainSource).toContain("height: 540");
    expect(mainSource).toContain("minHeight: 500");
    expect(styles).toContain("overflow-y: auto");
  });
});
