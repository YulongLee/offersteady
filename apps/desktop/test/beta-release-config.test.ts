import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const desktopRoot = path.resolve(import.meta.dirname, "..");
const readDesktop = (relativePath: string) => readFileSync(path.join(desktopRoot, relativePath), "utf8");

describe("isolated desktop Beta release", () => {
  it("uses a separate application identity and still requires hardened Developer ID notarization", () => {
    const config = readDesktop("electron-builder.beta.mac.yml");
    expect(config).toContain("appId: com.offersteady.companion.beta");
    expect(config).toContain("productName: 面试稳伴随程序 Beta");
    expect(config).toContain('identity: "Yulong li (8Y5FAR3TF3)"');
    expect(config).toContain("hardenedRuntime: true");
    expect(config).toContain("forceCodeSigning: true");
    expect(config).toContain("notarize: true");
  });

  it("pins a packaged Beta application to the Beta Web and API origins", () => {
    const main = readDesktop("src/main/index.ts");
    expect(main).toContain('app.getName()');
    expect(main).toContain('"https://beta.mianshiwen.cn/app"');
    expect(main).toContain('"https://beta.mianshiwen.cn/api/v1"');
    expect(main).toContain('releaseChannel: isBetaRelease() ? "beta" : "production"');
  });

  it("creates a Beta-only manifest that is ineligible for production publication", () => {
    const generator = readDesktop("scripts/generate-beta-mac-metadata.mjs");
    expect(generator).toContain('bundleId: "com.offersteady.companion.beta"');
    expect(generator).toContain('apiOrigin: "https://beta.mianshiwen.cn/api/v1"');
    expect(generator).toContain('productionManifestEligible: false');
    expect(generator).toContain('signingStatus: "verified-developer-id"');
    expect(generator).toContain('notarized: true');
  });

  it("supports an explicit verified Electron distribution for cross-architecture releases", () => {
    const releaseScript = readDesktop("scripts/package-release-mac.mjs");
    expect(releaseScript).toContain("OFFERSTEADY_ELECTRON_DIST");
    expect(releaseScript).toContain("does not contain a ${arch} Electron.app");
    expect(releaseScript).toContain("--config.electronDist=${electronDistForTarget}");
  });
});
