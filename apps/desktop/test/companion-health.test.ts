import { describe, expect, it } from "vitest";

import { hasPublisherTakenOver, mergeDisplayedSourceHealth } from "../src/renderer/CompanionApp";
import { publisherFailureDiagnostic } from "../src/renderer/audio/realtime-publisher";

describe("companion displayed source health", () => {
  it("falls back to monitor health when live health is present but not active", () => {
    const merged = mergeDisplayedSourceHealth(
      [
        { sourceId: "mic-live", sourceKind: "microphone", label: "麦克风", state: "unavailable", stage: "failed", level: 0, errorCode: "source-unavailable" },
        { sourceId: "sys-live", sourceKind: "system", label: "电脑输出", state: "unavailable", stage: "failed", level: 0, errorCode: "adapter-required" },
      ],
      [
        { sourceId: "mic-monitor", sourceKind: "microphone", label: "麦克风", state: "receiving", stage: "signal-detected", level: 0.021, lastSignalAtMs: Date.now() },
        { sourceId: "sys-monitor", sourceKind: "system", label: "电脑输出", state: "silent", stage: "track-live", level: 0 },
      ],
    );

    expect(merged.find((item) => item.sourceKind === "microphone")?.sourceId).toBe("mic-monitor");
    expect(merged.find((item) => item.sourceKind === "system")?.sourceId).toBe("sys-monitor");
  });

  it("prefers live health after frames or signal appear", () => {
    const merged = mergeDisplayedSourceHealth(
      [
        { sourceId: "mic-live", sourceKind: "microphone", label: "麦克风", state: "receiving", stage: "frames-produced", level: 0.03, frameCount: 3, lastFrameAtMs: Date.now() },
        { sourceId: "sys-live", sourceKind: "system", label: "电脑输出", state: "silent", stage: "track-live", level: 0 },
      ],
      [
        { sourceId: "mic-monitor", sourceKind: "microphone", label: "麦克风", state: "receiving", stage: "signal-detected", level: 0.01, lastSignalAtMs: Date.now() },
        { sourceId: "sys-monitor", sourceKind: "system", label: "电脑输出", state: "receiving", stage: "signal-detected", level: 0.02, lastSignalAtMs: Date.now() },
      ],
    );

    expect(merged.find((item) => item.sourceKind === "microphone")?.sourceId).toBe("mic-live");
    expect(merged.find((item) => item.sourceKind === "system")?.sourceId).toBe("sys-live");
  });

  it("does not treat failed or placeholder publisher health as takeover", () => {
    expect(hasPublisherTakenOver([
      { sourceId: "mic-live", sourceKind: "microphone", label: "麦克风", state: "unavailable", stage: "failed", level: 0, errorCode: "source-unavailable" },
      { sourceId: "sys-live", sourceKind: "system", label: "电脑输出", state: "silent", stage: "track-live", level: 0 },
    ])).toBe(false);

    expect(hasPublisherTakenOver([
      { sourceId: "mic-live", sourceKind: "microphone", label: "麦克风", state: "receiving", stage: "signal-detected", level: 0.025, lastSignalAtMs: Date.now() },
    ])).toBe(true);
  });

  it("classifies publisher transport failures separately from capture failures", () => {
    expect(publisherFailureDiagnostic("microphone", new Error("publisher_create_failed_microphone"))).toMatchObject({
      state: "error",
      stage: "failed",
      errorCode: "publisher-create-failed",
    });

    expect(publisherFailureDiagnostic("microphone", new Error("publisher_websocket_failed"))).toMatchObject({
      state: "reconnecting",
      stage: "failed",
      errorCode: "publisher-websocket-failed",
    });

    expect(publisherFailureDiagnostic("system", new Error("system-audio-unavailable"))).toMatchObject({
      state: "unavailable",
      stage: "unsupported",
      errorCode: "adapter-required",
    });
  });
});
