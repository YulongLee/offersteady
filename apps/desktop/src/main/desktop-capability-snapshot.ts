const permissionValues = new Set(["unknown", "prompt", "granted", "denied", "unavailable"]);
const reportedKeys = ["microphone", "systemAudio", "availableSources", "screenCapture", "nativeRuntimeReady"] as const;

/** In-memory, device-scoped capture capabilities, refreshed only after a successful report. */
export class DesktopCapabilitySnapshot {
  private deviceId: string | null = null;
  private reported: Record<string, unknown> = {};

  remember(deviceId: string, capabilities: Record<string, unknown>) {
    if (this.deviceId !== deviceId) this.reported = {};
    this.deviceId = deviceId;
    for (const key of reportedKeys) {
      const value = capabilities[key];
      if ((key === "microphone" || key === "systemAudio") && typeof value === "string" && permissionValues.has(value)
        || key === "availableSources" && Array.isArray(value)
        || (key === "screenCapture" || key === "nativeRuntimeReady") && typeof value === "boolean") {
        this.reported[key] = value;
      }
    }
  }

  forDevice(deviceId: string, runtime: Record<string, unknown>, microphoneOsStatus?: string): Record<string, unknown> {
    const capabilities = {
      microphone: "unknown", systemAudio: "unknown", availableSources: [], screenCapture: true,
      ...(this.deviceId === deviceId ? this.reported : {}),
      ...runtime,
      mockInterviewProtocol: 1,
    };
    // Current OS consent wins over a renderer snapshot that may have become stale.
    if (microphoneOsStatus !== undefined) {
      capabilities.microphone = microphoneOsStatus === "granted" ? "granted"
        : microphoneOsStatus === "denied" || microphoneOsStatus === "restricted" ? "denied" : "unknown";
    }
    return capabilities;
  }
}
