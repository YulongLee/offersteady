import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const runtimeFiles = [
  "App.tsx",
  "app-adapter.ts",
  "backend-adapter.ts",
  "material-upload-adapter.ts",
  "runtime-config.ts",
];

describe("product runtime imports", () => {
  it("does not import the removed fixture adapter from runtime modules", () => {
    for (const file of runtimeFiles) {
      const source = readFileSync(resolve(__dirname, file), "utf-8");
      expect(source).not.toContain("fixture-adapter");
      expect(source).not.toContain("syntheticState");
    }
  });
});
