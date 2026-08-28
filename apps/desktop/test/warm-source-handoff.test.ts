import { describe, expect, it, vi } from "vitest";

import type { OpenAudioSource } from "../src/renderer/audio/audio-source-adapter";
import { WarmSourceHandoff } from "../src/renderer/audio/warm-source-handoff";

const source = (input: { readyState?: MediaStreamTrackState; muted?: boolean } = {}) => {
  const close = vi.fn();
  const audioTrack = {
    readyState: input.readyState ?? "live",
    muted: input.muted ?? false,
  } as MediaStreamTrack;
  const opened = {
    descriptor: { id: "source-1", kind: "microphone", label: "Synthetic", available: true },
    stream: { getAudioTracks: () => [audioTrack] } as unknown as MediaStream,
    close,
  } satisfies OpenAudioSource;
  return { opened, close };
};

describe("warm source handoff", () => {
  it("promotes a healthy preparation stream exactly once without closing it", () => {
    const prepared = source();
    const calibration = { noiseFloor: 0.0003, sampleCount: 20, calibratedAtMs: 9_000 };
    const handoff = new WarmSourceHandoff([{ sourceKind: "microphone", source: prepared.opened, lastSignalAtMs: 9_000, calibration }]);

    expect(handoff.take("microphone", 10_000)).toEqual({ source: prepared.opened, outcome: "promoted", calibration });
    expect(handoff.take("microphone", 10_000)).toEqual({ source: null, outcome: "missing" });
    expect(prepared.close).not.toHaveBeenCalled();
  });

  it.each([
    { readyState: "ended" as const, muted: false },
    { readyState: "live" as const, muted: true },
  ])("rejects and closes a stale preparation stream", state => {
    const prepared = source(state);
    const handoff = new WarmSourceHandoff([{ sourceKind: "system", source: prepared.opened, lastSignalAtMs: 9_000 }]);

    expect(handoff.take("system", 10_000)).toEqual({ source: null, outcome: "stale" });
    expect(prepared.close).toHaveBeenCalledOnce();
  });

  it("closes every unconsumed stream during cancellation", () => {
    const microphone = source();
    const system = source();
    const handoff = new WarmSourceHandoff([
      { sourceKind: "microphone", source: microphone.opened, lastSignalAtMs: 9_000 },
      { sourceKind: "system", source: system.opened, lastSignalAtMs: 9_000 },
    ]);

    handoff.close();
    handoff.close();

    expect(microphone.close).toHaveBeenCalledOnce();
    expect(system.close).toHaveBeenCalledOnce();
    expect(handoff.pendingSourceCount).toBe(0);
  });

  it("rejects an unchecked or expired stream before live promotion", () => {
    const unchecked = source();
    const expired = source();
    const handoff = new WarmSourceHandoff([
      { sourceKind: "microphone", source: unchecked.opened, lastSignalAtMs: undefined },
      { sourceKind: "system", source: expired.opened, lastSignalAtMs: 1_000 },
    ]);

    expect(handoff.take("microphone", 10_000)).toEqual({ source: null, outcome: "stale" });
    expect(handoff.take("system", 122_001)).toEqual({ source: null, outcome: "stale" });
    expect(unchecked.close).toHaveBeenCalledOnce();
    expect(expired.close).toHaveBeenCalledOnce();
  });
});
