import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

describe("Windows installer identity", () => {
  it("keeps the packaged executable and NSIS shortcut target aligned", () => {
    const desktopRoot = path.resolve(import.meta.dirname, "..");
    const packageScript = readFileSync(
      path.join(desktopRoot, "scripts/package-local-windows.mjs"),
      "utf8",
    );
    const builderConfig = readFileSync(
      path.join(desktopRoot, "electron-builder.yml"),
      "utf8",
    );

    const configuredExecutable = builderConfig.match(
      /^\s*executableName:\s*([^\s#]+)\s*$/m,
    )?.[1];

    expect(packageScript).toContain(
      'renameSync(join(packageDir, "electron.exe"), join(packageDir, "OfferSteady.exe"));',
    );
    expect(configuredExecutable).toBe("OfferSteady");
    expect(`${configuredExecutable}.exe`).toBe("OfferSteady.exe");
  });
});
