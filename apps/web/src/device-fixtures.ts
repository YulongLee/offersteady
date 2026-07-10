import type { CompanionDeviceStatus } from "@offersteady/protocol";

export const createDeviceFixture = (
  captureState: CompanionDeviceStatus["captureState"] = "ready",
): CompanionDeviceStatus => ({
  deviceId: "desktop-demo-01",
  displayName: "办公室电脑",
  captureState,
  connected: captureState !== "not-connected" && captureState !== "error",
  activeSourceIds: captureState === "capturing" ? ["mic-default", "system-loopback"] : [],
  capabilities: {
    protocolVersion: "1.0.0",
    appVersion: "0.1.0",
    platform: "macos",
    platformVersion: "macOS 14.2+ universal",
    microphone: "granted",
    systemAudio: "granted",
    availableSources: [
      { id: "mic-default", kind: "microphone", label: "默认麦克风", available: true },
      { id: "system-loopback", kind: "system", label: "系统音频", available: true },
    ],
  },
  lastSeenAtMs: Date.now(),
  ...(captureState === "error" ? { errorCode: "network-unavailable" as const } : {}),
});
