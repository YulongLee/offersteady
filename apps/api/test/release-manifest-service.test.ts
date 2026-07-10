import { describe, expect, it } from "vitest";
import type { DesktopReleaseEntry } from "@offersteady/protocol";
import { ReleaseManifestService } from "../src/release-manifest-service.js";
const release: DesktopReleaseEntry = { id: "mac-arm", platform: "macos", architecture: "arm64", displayName: "macOS Apple Silicon", version: "0.1.0", minimumOs: "14.2", fileSizeBytes: 10, sha256: "a".repeat(64), signingStatus: "verified", notarized: true, publishedAtMs: 1, protocolVersion: "1.0.0", downloadUrl: "/mac.dmg", capabilities: { microphone: true, systemAudio: true, manualInputFallback: true, screenshotFallback: true } };
describe("ReleaseManifestService", () => {
  it("publishes verified releases and withdraws URLs", () => { const service = new ReleaseManifestService(); expect(service.publish("release-manager", release).entries).toHaveLength(1); expect(service.withdraw("release-manager", release.id).entries).toHaveLength(0); });
  it("enforces role and signing/notarization", () => { const service = new ReleaseManifestService(); expect(() => service.publish("support", release)).toThrowError(expect.objectContaining({ code: "forbidden" })); expect(() => service.publish("release-manager", { ...release, notarized: false })).toThrowError(expect.objectContaining({ code: "invalid-release" })); });
  it("rejects malformed checksums", () => { expect(() => new ReleaseManifestService().publish("release-manager", { ...release, sha256: "bad" })).toThrowError(expect.objectContaining({ code: "invalid-release" })); });
});
