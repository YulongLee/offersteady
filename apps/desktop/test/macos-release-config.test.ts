import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const desktopRoot = path.resolve(import.meta.dirname, "..");
const repositoryRoot = path.resolve(desktopRoot, "../..");
const readDesktop = (relativePath: string) => readFileSync(path.join(desktopRoot, relativePath), "utf8");

describe("macOS Developer ID release configuration", () => {
  it("keeps the stable bundle identity and requires Developer ID signing and notarization", () => {
    const config = readDesktop("electron-builder.release.mac.yml");

    expect(config).toContain("appId: com.offersteady.companion");
    expect(config).toContain('identity: "Yulong li (8Y5FAR3TF3)"');
    expect(config).toContain("forceCodeSigning: true");
    expect(config).toContain("hardenedRuntime: true");
    expect(config).toContain("strictVerify: true");
    expect(config).toContain("notarize: true");
    expect(config).toContain("target: dmg");
    expect(config).toContain("Contents/Resources/app/native/macos-capture/OfferSteadyCaptureRuntime");
    expect(config).not.toMatch(/identity:\s*["']?-["']?/);
  });

  it("uses minimal release entitlements and retains all capture usage declarations", () => {
    const config = readDesktop("electron-builder.release.mac.yml");
    const mainEntitlements = readDesktop("build/entitlements.mac.release.plist");
    const inheritedEntitlements = readDesktop("build/entitlements.mac.release.inherit.plist");

    for (const key of ["NSMicrophoneUsageDescription", "NSAudioCaptureUsageDescription", "NSScreenCaptureUsageDescription"]) {
      expect(config).toContain(key);
    }
    for (const entitlements of [mainEntitlements, inheritedEntitlements]) {
      expect(entitlements).toContain("com.apple.security.cs.allow-jit");
      expect(entitlements).not.toContain("com.apple.security.cs.allow-unsigned-executable-memory");
      expect(entitlements).not.toContain("com.apple.security.app-sandbox");
    }
  });

  it("keeps development commands separate and makes production fail closed", () => {
    const packageJson = JSON.parse(readDesktop("package.json")) as { scripts: Record<string, string> };
    const releaseScript = readDesktop("scripts/package-release-mac.mjs");
    const verifier = readDesktop("scripts/verify-release-mac.mjs");

    expect(packageJson.scripts["package:mac:arm64"]).toContain("package-local-mac.mjs");
    expect(packageJson.scripts["package:mac:release:arm64"]).toContain("package-release-mac.mjs arm64");
    expect(packageJson.scripts["package:mac:release:prepare:arm64"]).toContain("--prepare-only");
    expect(releaseScript).toContain("Production notarization credentials are missing");
    expect(releaseScript).toContain('CSC_NAME: SIGNING_QUALIFIER');
    expect(releaseScript).toContain('"notarytool", "submit", dmgPath');
    expect(releaseScript).toContain('submission.status !== "Accepted"');
    expect(releaseScript).toContain('["--sign", EXPECTED_IDENTITY, "--force", "--timestamp", dmgs[0]]');
    expect(releaseScript).toContain('["stapler", "staple", dmgPath]');
    expect(releaseScript).toContain('entry.name.includes(`-macOS-${arch}.`)');
    expect(releaseScript).toContain(".filter(isTargetArchitecture)");
    expect(releaseScript).toContain('path.endsWith(`-macOS-${arch}.dmg`)');
    expect(releaseScript).toContain("generate-production-mac-metadata.mjs");
    expect(releaseScript).not.toContain("rmSync(outputDir");
    expect(releaseScript).not.toContain('CSC_IDENTITY_AUTO_DISCOVERY: "false"');
    expect(verifier).toContain('"--verify", "--deep", "--strict", "--verbose=2"');
    expect(verifier).toContain('"spctl", ["--assess", "--type", "execute", "--verbose"');
    expect(verifier).toContain('"spctl", ["--assess", "--type", "open", "--context", "context:primary-signature", "--verbose"');
    expect(verifier).toContain("assertDeveloperIdSignature(dmgPath)");
    expect(verifier).toContain('"xcrun", ["stapler", "validate"');
    expect(verifier).toContain('"stapler", "validate", dmgPath');
  });

  it("generates verified publication metadata only from production DMGs", () => {
    const generator = readDesktop("scripts/generate-production-mac-metadata.mjs");

    expect(generator).toContain('signingStatus: "verified"');
    expect(generator).toContain("notarized: true");
    expect(generator).toContain('installerType: "dmg"');
    expect(generator).toContain('developmentOnly: false');
    expect(generator).toContain('artifact.endsWith(".dmg")');
  });

  it("ignores Apple signing and notarization secret files", () => {
    const gitignore = readFileSync(path.join(repositoryRoot, ".gitignore"), "utf8");

    for (const pattern of ["*.p8", "*.p12", "*.cer", "*.mobileprovision", "*.keychain-db", "notarytool-credentials*"]) {
      expect(gitignore).toContain(pattern);
    }
  });
});
