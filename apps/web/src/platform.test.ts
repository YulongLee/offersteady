import { describe, expect, it } from "vitest";
import type { DesktopReleaseEntry, DesktopReleaseManifest } from "@offersteady/protocol";

import { companionUpdate, compareDesktopVersions } from "./platform";

const release = (overrides: Partial<DesktopReleaseEntry> = {}): DesktopReleaseEntry => ({
  id: "mac-arm64-1-2-13",
  platform: "macos",
  architecture: "arm64",
  displayName: "macOS Apple Silicon",
  version: "1.2.13",
  minimumOs: "macOS 12+",
  fileSizeBytes: 1,
  sha256: "a".repeat(64),
  signingStatus: "verified",
  distributionStatus: "published",
  notarized: true,
  publishedAtMs: 100,
  protocolVersion: "2.0",
  downloadUrl: "/api/v1/web/downloads/desktop/mac-arm64-1-2-13",
  capabilities: { microphone: true, systemAudio: true, manualInputFallback: true, screenshotFallback: true },
  ...overrides,
});

const manifest = (entries: readonly DesktopReleaseEntry[]): DesktopReleaseManifest => ({ version: 1, generatedAtMs: 100, entries });

describe("companion update selection", () => {
  it("compares numeric versions and treats a suffixed build as older than its stable release", () => {
    expect(compareDesktopVersions("1.2.9", "1.2.10")).toBe(-1);
    expect(compareDesktopVersions("1.2.10a", "1.2.10")).toBe(-1);
    expect(compareDesktopVersions("1.2.13", "1.2.13")).toBe(0);
    expect(compareDesktopVersions("1.3.0", "1.2.13")).toBe(1);
    expect(compareDesktopVersions("not-a-version", "1.2.13")).toBeNull();
  });

  it("selects the newest downloadable release for the exact normalized device target", () => {
    const update = companionUpdate(
      { appVersion: "1.2.10a", platform: "darwin", architecture: "aarch64" },
      manifest([
        release({ id: "older", version: "1.2.12", publishedAtMs: 90 }),
        release(),
        release({ id: "intel", architecture: "x64", version: "2.0.0" }),
        release({ id: "windows", platform: "windows", architecture: "x64", version: "2.0.0" }),
      ]),
    );
    expect(update).toMatchObject({ currentVersion: "1.2.10a", release: { id: "mac-arm64-1-2-13", version: "1.2.13" } });
  });

  it("does not warn for equal, newer, malformed, missing or unmatched device versions", () => {
    const releases = manifest([release()]);
    expect(companionUpdate({ appVersion: "1.2.13", platform: "macos", architecture: "arm64" }, releases)).toBeNull();
    expect(companionUpdate({ appVersion: "1.3.0", platform: "macos", architecture: "arm64" }, releases)).toBeNull();
    expect(companionUpdate({ appVersion: "dev", platform: "macos", architecture: "arm64" }, releases)).toBeNull();
    expect(companionUpdate({ platform: "macos", architecture: "arm64" }, releases)).toBeNull();
    expect(companionUpdate({ appVersion: "1.0.0", platform: "macos", architecture: "x64" }, releases)).toBeNull();
  });

  it("ignores releases that are not downloadable", () => {
    const unavailable = release({ signingStatus: "withdrawn", distributionStatus: "withdrawn" });
    expect(companionUpdate({ appVersion: "1.0.0", platform: "macos", architecture: "arm64" }, manifest([unavailable]))).toBeNull();
  });
});
