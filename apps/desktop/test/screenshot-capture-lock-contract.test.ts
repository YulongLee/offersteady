import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("desktop screenshot lock wiring", () => {
  it("guards main-process manual, remote, and shortcut capture entry points", () => {
    const source = readFileSync(new URL("../src/main/index.ts", import.meta.url), "utf8");

    expect(source).toContain("captureCurrentScreen = async");
    expect(source).toContain("screenshotCaptureLock.tryAcquire()");
    expect(source).toContain("screenshotCaptureLock.state().locked && !lockAlreadyHeld");
    expect(source).toContain("releaseAfterCapture");
    expect(source).toContain("if (screenshotCaptureLock.state().locked) releaseScreenshotCaptureLock()");
    expect(source).toContain("await pollRemoteScreenshotRequest(true)");
  });

  it("exposes authoritative lock synchronization through preload", () => {
    const source = readFileSync(new URL("../src/main/preload.ts", import.meta.url), "utf8");

    expect(source).toContain("getScreenshotCaptureLock");
    expect(source).toContain("onScreenshotCaptureLockChanged");
    expect(source).not.toContain("cancelScreenshotCapture");
  });
});
