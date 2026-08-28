import { describe, expect, it } from "vitest";

import { BINDING_STATUS_POLL_MS, captureStateForReliability, captureStateForSourceHealth, desktopActiveConnectionQuery, desktopBindingLeaseIdentity, hasPublisherTakenOver, mergeDisplayedSourceHealth } from "../src/renderer/CompanionApp";
import { AUDIO_READINESS_TTL_MS, readinessFields, signalEvidenceIsFresh, sourceHealthIsAudioReady } from "../src/renderer/audio/audio-readiness";
import { productionAudioTransportPolicy, publisherCaptureStateForTransport, publisherFailureDiagnostic, publisherFailureIsTerminal } from "../src/renderer/audio/realtime-publisher";

describe("companion displayed source health", () => {
  it("requires fresh real-signal evidence instead of treating an open silent track as checked", () => {
    const nowMs = 200_000;
    const silent = { sourceId: "system", sourceKind: "system", label: "电脑输出", state: "silent", stage: "track-live", level: 0 } as const;
    const checked = { ...silent, lastSignalAtMs: nowMs - 1_000 };

    expect(sourceHealthIsAudioReady(silent, nowMs)).toBe(false);
    expect(sourceHealthIsAudioReady(checked, nowMs)).toBe(true);
    expect(sourceHealthIsAudioReady(checked, nowMs + AUDIO_READINESS_TTL_MS + 1)).toBe(false);
    expect(signalEvidenceIsFresh(undefined, nowMs)).toBe(false);
    expect(readinessFields(nowMs - 1_000, nowMs)).toMatchObject({ readinessState: "ready", readinessExpiresAtMs: nowMs - 1_000 + AUDIO_READINESS_TTL_MS });
    expect(readinessFields(nowMs - AUDIO_READINESS_TTL_MS - 1, nowMs)).toMatchObject({ readinessState: "stale" });
  });
  it("never falls back to the disabled legacy HTTP frame endpoint", () => {
    expect(productionAudioTransportPolicy).toEqual({
      protocol: "websocket-v2",
      automaticLegacyHttpFallback: false,
    });
  });

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

  it("keeps microphone and system readiness independent instead of claiming global capture", () => {
    expect(captureStateForSourceHealth([
      { sourceId: "mic-live", sourceKind: "microphone", label: "麦克风", state: "receiving", stage: "signal-detected", level: 0.02 },
      { sourceId: "sys-live", sourceKind: "system", label: "电脑输出", state: "unavailable", stage: "failed", level: 0 },
    ], "capturing")).toBe("error");

    expect(captureStateForSourceHealth([
      { sourceId: "mic-live", sourceKind: "microphone", label: "麦克风", state: "silent", stage: "track-live", level: 0 },
      { sourceId: "sys-live", sourceKind: "system", label: "电脑输出", state: "silent", stage: "track-live", level: 0 },
    ], "reconnecting")).toBe("capturing");

    expect(captureStateForSourceHealth([
      { sourceId: "mic-live", sourceKind: "microphone", label: "麦克风", state: "silent", stage: "track-live", level: 0 },
    ], "capturing")).toBe("capturing");

    expect(captureStateForSourceHealth([
      { sourceId: "mic-live", sourceKind: "microphone", label: "麦克风", state: "reconnecting", stage: "stream-opened", level: 0 },
      { sourceId: "sys-live", sourceKind: "system", label: "电脑输出", state: "silent", stage: "track-live", level: 0 },
    ], "capturing")).toBe("reconnecting");
  });

  it("reserves reconnecting for recovery after the publisher was healthy", () => {
    expect(publisherCaptureStateForTransport("reconnecting", false, false)).toBeNull();
    expect(publisherCaptureStateForTransport("connected", false, false)).toBe("capturing");
    expect(publisherCaptureStateForTransport("reconnecting", true, false)).toBe("reconnecting");
    expect(publisherCaptureStateForTransport("reconnecting", true, true)).toBe("reconnecting");

    expect(captureStateForReliability(["STARTING"], false, "capturing")).toBe("capturing");
    expect(captureStateForReliability(["RECOVERING"], false, "capturing")).toBe("capturing");
    expect(captureStateForReliability(["RECOVERING"], true, "capturing")).toBe("reconnecting");
    expect(captureStateForReliability(["HEALTHY", "HEALTHY"], true, "reconnecting")).toBe("capturing");
  });

  it("pins active-connection polls to the established live binding", () => {
    expect(desktopActiveConnectionQuery(
      { deviceId: "device-1", manualCode: "123456" },
      {
        bindingId: "binding-live",
        sessionId: "session-live",
      },
    )).toBe("manualCode=123456&pinnedSessionId=session-live&pinnedBindingId=binding-live");
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

    expect(publisherFailureDiagnostic("system", new Error("screen-capture-permission-required"))).toMatchObject({
      state: "permission-denied",
      stage: "permission-denied",
      errorCode: "permission-denied",
    });
  });

  it("stops retrying publisher creation after permanent session failures", () => {
    expect(publisherFailureIsTerminal(new Error("publisher_create_failed_microphone_410"))).toBe(true);
    expect(publisherFailureIsTerminal(new Error("publisher_create_failed_microphone_401"))).toBe(true);
    expect(publisherFailureIsTerminal(new Error("publisher_websocket_failed"))).toBe(false);
  });

  it("follows backend binding leases on a realtime cadence", () => {
    expect(BINDING_STATUS_POLL_MS).toBeLessThanOrEqual(2_000);
    expect(desktopBindingLeaseIdentity({
      bindingId: "binding-new",
      bindingGeneration: 4,
      sessionId: "session-new",
      ownerUserId: "user",
      deviceId: "device",
      manualCode: "123456",
      displayName: "Mac",
      capabilities: {},
      status: "bound",
      boundAtMs: 1,
      lastSeenAtMs: 1,
    })).toBe("binding-new:4");
  });
});
