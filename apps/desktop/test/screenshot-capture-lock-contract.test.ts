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
    expect(source).toContain("await processRemoteScreenshotRequest(identity, requestId, true)");
    expect(source).toContain("DesktopCaptureEventParser");
  });

  it("exposes authoritative lock synchronization through preload", () => {
    const source = readFileSync(new URL("../src/main/preload.ts", import.meta.url), "utf8");

    expect(source).toContain("getScreenshotCaptureLock");
    expect(source).toContain("onScreenshotCaptureLockChanged");
    expect(source).not.toContain("cancelScreenshotCapture");
  });

  it("uses one cancellable push stream and only polls after that stream fails", () => {
    const source = readFileSync(new URL("../src/main/index.ts", import.meta.url), "utf8");

    expect(source).toContain("await consumeRemoteScreenshotEventStream(state.identity, streamController.signal)");
    expect(source).toContain("if (streamController?.signal.aborted)");
    expect(source).toContain("await pollRemoteScreenshotRequest()");
    expect(source).toContain('schedule(desktopPollDelayMs("failure", remoteScreenshotPollFailureCount))');
    expect(source).toContain("if (state !== previousState) startRemoteScreenshotRequestLoop()");
  });
});
