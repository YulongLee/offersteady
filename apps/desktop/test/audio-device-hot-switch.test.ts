import { describe, expect, it, vi } from "vitest";

import {
  createDebouncedDeviceRefresh,
  reconcileMicrophoneSelection,
  SerializedLatestSourceSwitch,
} from "../src/renderer/audio/audio-device-hot-switch";
import { BoundedAudioFrameBuffer, SourceFrameSequencer, createAudioFrame } from "../src/renderer/audio/audio-frame-buffer";

const source = (id: string, label = id) => ({ id, label, kind: "microphone" as const, available: true });

describe("audio device hot switching", () => {
  it("retains an available explicit microphone and falls back only after removal", () => {
    const sources = [source("default", "Default - MacBook Microphone"), source("airpods", "AirPods")];
    expect(reconcileMicrophoneSelection(sources, "airpods")).toBe("airpods");
    expect(reconcileMicrophoneSelection([sources[0]!], "airpods")).toBe("default");
    expect(reconcileMicrophoneSelection(sources, "airpods", "default")).toBe("default");
  });

  it("coalesces a burst of macOS devicechange events into one refresh", () => {
    vi.useFakeTimers();
    vi.stubGlobal("window", { setTimeout, clearTimeout });
    const refresh = vi.fn();
    const debounced = createDebouncedDeviceRefresh(refresh);
    debounced.notify();
    debounced.notify();
    debounced.notify();
    vi.advanceTimersByTime(399);
    expect(refresh).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(refresh).toHaveBeenCalledTimes(1);
    debounced.dispose();
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("serializes source-only switches and converges on the newest route", async () => {
    const switcher = new SerializedLatestSourceSwitch("airpods");
    const applied: string[] = [];
    let releaseFirst!: () => void;
    const firstBlocked = new Promise<void>(resolve => { releaseFirst = resolve; });
    const apply = vi.fn(async (sourceId: string) => {
      applied.push(sourceId);
      if (sourceId === "macbook") await firstBlocked;
      return true;
    });
    const first = switcher.request("macbook", apply);
    const latest = switcher.request("usb-mic", apply);
    expect(applied).toEqual(["macbook"]);
    releaseFirst();
    await Promise.all([first, latest]);
    expect(applied).toEqual(["macbook", "usb-mic"]);
    expect(apply).toHaveBeenCalledTimes(2);
  });

  it("clears acknowledged channel frames even when the microphone device identity changed", () => {
    const sequencer = new SourceFrameSequencer();
    const buffer = new BoundedAudioFrameBuffer(64_000);
    const headset = createAudioFrame(sequencer, { sessionId: "s", deviceId: "d", sourceId: "airpods", sourceKind: "microphone", capturedAtMs: 1, durationMs: 20, payload: new Uint8Array(320) });
    const builtIn = createAudioFrame(sequencer, { sessionId: "s", deviceId: "d", sourceId: "macbook", sourceKind: "microphone", capturedAtMs: 2, durationMs: 20, payload: new Uint8Array(320) });
    buffer.push(headset);
    buffer.push(builtIn);
    buffer.acknowledge("macbook", 1);
    expect(buffer.depth()).toBe(0);
  });
});
