import { describe, expect, it } from "vitest";

import {
  INVALID_REALTIME_SESSION_RETRY_MS,
  isInvalidRealtimeSessionStatus,
  realtimeFallbackDelayMs,
  realtimeRetryDelayMs,
} from "./realtime-recovery";

describe("realtime recovery policy", () => {
  it("circuit-breaks invalid or unauthorized sessions instead of rapidly reconnecting", () => {
    expect(realtimeRetryDelayMs(404, 0)).toBe(INVALID_REALTIME_SESSION_RETRY_MS);
    expect(realtimeRetryDelayMs(401, 8)).toBe(INVALID_REALTIME_SESSION_RETRY_MS);
    expect(isInvalidRealtimeSessionStatus(403)).toBe(true);
    expect(isInvalidRealtimeSessionStatus(409)).toBe(true);
    expect(isInvalidRealtimeSessionStatus(410)).toBe(true);
  });

  it("keeps bounded exponential recovery for transient network failures", () => {
    expect(realtimeRetryDelayMs(null, 0)).toBe(1_000);
    expect(realtimeRetryDelayMs(500, 2)).toBe(4_000);
    expect(realtimeRetryDelayMs(500, 20)).toBe(15_000);
  });

  it("uses a slower bounded fallback snapshot cadence", () => {
    expect(realtimeFallbackDelayMs(0)).toBe(5_000);
    expect(realtimeFallbackDelayMs(1)).toBe(10_000);
    expect(realtimeFallbackDelayMs(2)).toBe(15_000);
    expect(realtimeFallbackDelayMs(20)).toBe(15_000);
  });
});
