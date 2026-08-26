import { describe, expect, it } from "vitest";

import {
  INVALID_REALTIME_SESSION_RETRY_MS,
  isInvalidRealtimeSessionStatus,
  realtimeRetryDelayMs,
  realtimeReconnectAttemptAfterRecovery,
} from "./realtime-recovery";

describe("realtime recovery policy", () => {
  it("circuit-breaks invalid or unauthorized sessions instead of rapidly reconnecting", () => {
    expect(realtimeRetryDelayMs(404, 0)).toBe(INVALID_REALTIME_SESSION_RETRY_MS);
    expect(realtimeRetryDelayMs(401, 8)).toBe(INVALID_REALTIME_SESSION_RETRY_MS);
    expect(isInvalidRealtimeSessionStatus(403)).toBe(true);
    expect(isInvalidRealtimeSessionStatus(409)).toBe(true);
    expect(isInvalidRealtimeSessionStatus(410)).toBe(true);
  });

  it("resets retry backoff only after the SSE stream snapshot recovers", () => {
    expect(realtimeReconnectAttemptAfterRecovery(3, "fallback-snapshot")).toBe(3);
    expect(realtimeReconnectAttemptAfterRecovery(3, "stream-snapshot")).toBe(0);
  });

  it("keeps bounded exponential recovery for transient network failures", () => {
    expect(realtimeRetryDelayMs(null, 0)).toBe(0);
    expect(realtimeRetryDelayMs(500, 1)).toBe(2_000);
    expect(realtimeRetryDelayMs(500, 2)).toBe(4_000);
    expect(realtimeRetryDelayMs(500, 20)).toBe(15_000);
  });
});
