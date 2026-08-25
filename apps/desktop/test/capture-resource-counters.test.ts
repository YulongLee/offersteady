import { describe, expect, it } from "vitest";

import { CaptureResourceCounters } from "../src/renderer/audio/capture-resource-counters";

describe("capture resource counters", () => {
  it("tracks bounded counters without retaining audio payloads", () => {
    const counters = new CaptureResourceCounters();
    counters.addAudioContext();
    counters.addAudioNodes(4);
    counters.addMediaTracks(1);
    counters.addListeners(2);
    counters.addTimer();
    for (let index = 0; index < 100; index += 1) {
      counters.recordWorkletBatch("system", {
        callbackCount: 8,
        postMessageCount: 1,
        audioBytes: 4_096,
        float32ArrayAllocations: 1,
      });
    }
    counters.setOwnedArrayBufferBytes(32_000);
    expect(counters.snapshot(10_000)).toMatchObject({
      audioWorkletCallbackCount: 800,
      workletPostMessageCount: 100,
      audioBytes: 409_600,
      float32ArrayAllocations: 100,
      ownedArrayBufferBytes: 32_000,
      activeAudioContexts: 1,
      activeAudioNodes: 4,
      activeMediaStreamTracks: 1,
      activeListeners: 2,
      activeTimers: 1,
    });
    counters.removeTimer();
    counters.removeListeners(2);
    counters.removeMediaTracks(1);
    counters.removeAudioNodes(4);
    counters.removeAudioContext();
    expect(counters.snapshot().activeAudioContexts).toBe(0);
    expect(counters.snapshot().activeAudioNodes).toBe(0);
    expect(counters.snapshot().activeMediaStreamTracks).toBe(0);
    expect(counters.snapshot().activeListeners).toBe(0);
    expect(counters.snapshot().activeTimers).toBe(0);
  });
});
