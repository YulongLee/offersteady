import { describe, expect, it } from "vitest";

import { captureEnabledForBinding, companionStatusCopy, desktopBindingLeaseIdentity } from "../src/renderer/CompanionApp";
import { desktopCaptureArchitecture, sessionCapturePermissionPolicy } from "../src/renderer/audio/realtime-publisher";

describe("desktop permission and interview connection states", () => {
  it("keeps an idle registered device distinct from a missing permission", () => {
    expect(companionStatusCopy.ready.title).toBe("设备在线");
    expect(companionStatusCopy.ready.detail).toContain("系统授权与本场连接相互独立");
    expect(companionStatusCopy["permission-required"].title).toBe("需要系统权限");
  });

  it("uses the session lease identity only for active interview capture", () => {
    expect(desktopBindingLeaseIdentity(null)).toBe("");
    expect(desktopBindingLeaseIdentity({
      bindingId: "binding-1",
      bindingGeneration: 3,
      sessionId: "session-1",
      ownerUserId: "user-1",
      deviceId: "device-1",
      manualCode: "123456",
      displayName: "Mac",
      capabilities: {},
      status: "bound",
      boundAtMs: 1,
      lastSeenAtMs: 1,
    })).toBe("binding-1:3");
  });

  it("reuses assistant-owned permissions instead of requesting them when a session starts", () => {
    expect(sessionCapturePermissionPolicy.requestPermissionOnSessionStart).toBe(false);
    expect(sessionCapturePermissionPolicy.systemAudioCapture).toBe("electron-display-loopback");
    expect(sessionCapturePermissionPolicy.captureOwner).toBe("electron-single-owner");
    expect(desktopCaptureArchitecture).toBe("electron-single-owner");
  });

  it("never resumes capture while the authoritative binding remains paused", () => {
    expect(captureEnabledForBinding("live", "capturing")).toBe(true);
    expect(captureEnabledForBinding("live", "paused")).toBe(false);
    expect(captureEnabledForBinding("preparing", "capturing")).toBe(false);
  });
});
