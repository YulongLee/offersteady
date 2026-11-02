import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { describe, expect, it } from "vitest";

const desktopRoot = path.resolve(import.meta.dirname, "..");
const readDesktop = (relativePath: string) => readFileSync(path.join(desktopRoot, relativePath), "utf8");

describe("isolated Global companion release", () => {
  it("uses a distinct application identity, artifact directory, and executable", () => {
    const config = readDesktop("electron-builder.global.yml");
    expect(config).toContain("appId: com.offersteady.companion.global");
    expect(config).toContain("productName: OfferSteady Companion Global");
    expect(config).toContain("output: release/global");
    expect(config).toContain("executableName: OfferSteadyGlobal");
    expect(config).toContain("OfferSteady-Companion-Global-${version}");
  });

  it("requires HTTPS Global endpoints and rejects every domestic hostname", () => {
    const generator = readDesktop("scripts/prepare-global-runtime-config.mjs");
    expect(generator).toContain("OFFERSTEADY_GLOBAL_WEB_URL");
    expect(generator).toContain("OFFERSTEADY_GLOBAL_API_BASE_URL");
    expect(generator).toContain('parsed.protocol !== "https:"');
    expect(generator).toContain('"mianshiwen.cn", "www.mianshiwen.cn", "beta.mianshiwen.cn"');
    expect(generator).toContain('!== "/api/v1"');
  });

  it("does not migrate domestic pairing credentials into the Global profile", () => {
    const main = readDesktop("src/main/index.ts");
    expect(main).toContain("app.isPackaged && existsSync(packagedGlobalRuntimeConfigPath())");
    expect(main).toContain("isGlobalRelease() ? [] : legacyUserDataDirectories");
    expect(main).toContain('releaseChannel: localTestRuntime ? "local-test" : isGlobalRelease() ? "global"');
    expect(main).toContain("global-runtime-config.json");
    expect(main).toContain("companionTrayImages(isGlobalRelease())");
    const trayPresentation = readFileSync(path.join(desktopRoot, "src/main/tray-presentation.ts"), "utf8");
    expect(trayPresentation).toContain('NORMAL_IMAGES[global ? "O" : "稳"]');
    expect(main).toContain("isGlobalRelease()\n    ? defaultWebWorkspaceUrl()");
    expect(main).toContain("isGlobalRelease()\n    ? defaultApiBaseUrl()");
  });

  it("contains only English values in the generated Global companion catalogue", () => {
    const generated = readDesktop("src/renderer/global-copy.generated.ts");
    const values = [...generated.matchAll(/:[ \t]*"([^"]*)"/g)].map((match) => match[1]);
    expect(values.length).toBeGreaterThan(100);
    expect(values.join("\n")).not.toMatch(/[\u3400-\u9fff]/);
    expect(values.join("\n")).not.toContain("Additional companion information is available for this step.");
  });

  it("fails the Global copy build when new Chinese companion copy has no explicit translation", () => {
    const generator = readDesktop("scripts/generate-global-companion-copy.mjs");
    expect(generator).toContain("Global companion copy is incomplete");
    expect(generator).toContain("Missing exact translation");
    expect(generator).toContain("Missing template translation");
  });

  it("leaves the domestic release identity and artifact names intact", () => {
    const domestic = readDesktop("electron-builder.yml");
    expect(domestic).toContain("appId: com.offersteady.companion");
    expect(domestic).toContain("productName: 面试稳伴随程序");
    expect(domestic).not.toContain("com.offersteady.companion.global");
  });

  it("uses the formal Mac release pipeline and validates actual capture signatures", () => {
    const config = readDesktop("electron-builder.global.yml");
    const release = readDesktop("scripts/package-release-mac.mjs");
    const packageJson = JSON.parse(readDesktop("package.json")) as { scripts: Record<string, string> };
    for (const arch of ["arm64", "x64"]) {
      expect(packageJson.scripts[`package:mac:global:${arch}`]).toBe(`OFFERSTEADY_PRODUCT_EDITION=global node scripts/package-release-mac.mjs ${arch}`);
    }
    expect(config).toContain("forceCodeSigning: true");
    expect(config).toContain("notarize: true");
    expect(config).toContain("entitlements: build/entitlements.mac.release.plist");
    expect(config).toContain("entitlementsInherit: build/entitlements.mac.release.inherit.plist");
    expect(config).toContain("Contents/Resources/app/native/macos-capture/OfferSteadyCaptureRuntime");
    expect(config).not.toContain("target: zip");
    expect(release).toContain('isGlobal ? "electron-builder.global.yml"');
    expect(release).toContain('isGlobal ? "build:global" : "build"');
    expect(release).toContain('"scripts/generate-global-release-metadata.mjs"');
    expect(release).toContain('"Global and domestic Beta release editions cannot be combined."');
  });

  it("keeps the native helper permission identity and wording in the Global edition", () => {
    const globalInfo = readDesktop("native/macos-capture/Info.global.plist");
    const domesticInfo = readDesktop("native/macos-capture/Info.plist");
    const builder = readDesktop("scripts/build-native-runtime.mjs");
    expect(builder).toContain('process.env.OFFERSTEADY_PRODUCT_EDITION === "global"');
    expect(builder).toContain('"native/macos-capture/Info.global.plist"');
    expect(globalInfo).toContain("com.offersteady.companion.global");
    expect(globalInfo).not.toMatch(/[\u3400-\u9fff]/);
    for (const usage of ["NSMicrophoneUsageDescription", "NSAudioCaptureUsageDescription", "NSScreenCaptureUsageDescription"]) {
      expect(globalInfo).toContain(usage);
    }
    expect(domesticInfo).toContain("<string>com.offersteady.companion</string>");
    expect(domesticInfo).toContain("面试稳");
  });

  it("does not label an unverified Global Mac artifact as signed or notarized", () => {
    const metadata = readDesktop("scripts/generate-global-release-metadata.mjs");
    expect(metadata).toContain('"scripts/verify-release-mac.mjs"');
    expect(metadata).toContain('"--bundle-id", "com.offersteady.companion.global"');
    expect(metadata).toContain("Global macOS metadata requires the packaged App");
    expect(metadata).toContain('runtime.webWorkspaceUrl !== "https://offersteady.com/app"');
    expect(metadata).toContain('runtime.apiBaseUrl !== "https://offersteady.com/api/v1"');
    expect(metadata).toContain('signingStatus: platform === "macos" ? "verified" : "unsigned"');
  });

  it("rejects an arbitrary DMG instead of publishing verified metadata for its extension", () => {
    const root = mkdtempSync(path.join(tmpdir(), "offersteady-global-metadata-"));
    try {
      mkdirSync(path.join(root, "scripts"));
      mkdirSync(path.join(root, "release/global"), { recursive: true });
      copyFileSync(path.join(desktopRoot, "scripts/generate-global-release-metadata.mjs"), path.join(root, "scripts/generate-global-release-metadata.mjs"));
      writeFileSync(path.join(root, "package.json"), JSON.stringify({ version: "1.3.5", type: "module" }));
      const fakeArtifact = path.join(root, "OfferSteady-Companion-Global-1.3.5-macOS-arm64.dmg");
      writeFileSync(fakeArtifact, "synthetic text that is not a signed or notarized DMG");
      const result = spawnSync(process.execPath, [path.join(root, "scripts/generate-global-release-metadata.mjs"), "macos", "arm64", fakeArtifact], { encoding: "utf8" });
      expect(result.status).not.toBe(0);
      expect(existsSync(path.join(root, "release/global/OfferSteady-Companion-Global-1.3.5-macOS-arm64.json"))).toBe(false);
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
});
