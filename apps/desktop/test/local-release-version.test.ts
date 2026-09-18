import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("local companion 1.3.0 release boundary", () => {
  it("keeps the desktop package and workspace lockfile aligned at 1.3.0", () => {
    const packageJson = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));
    const lockfile = JSON.parse(readFileSync(new URL("../../../package-lock.json", import.meta.url), "utf8"));

    expect(packageJson.version).toBe("1.3.0");
    expect(lockfile.packages["apps/desktop"].version).toBe("1.3.0");
  });

  it("does not opt the local build into a publish command", () => {
    const packageJson = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));
    const scripts = Object.values(packageJson.scripts).join(" ");

    expect(scripts).toContain("npm run build");
    expect(scripts).not.toContain("publish-desktop-release");
  });
});
