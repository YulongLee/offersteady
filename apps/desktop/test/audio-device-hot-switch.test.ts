import { describe, expect, it, vi } from "vitest";

import {
  createDebouncedDeviceRefresh,
  reconcileMicrophoneSelection,
  SerializedLatestSourceSwitch,
} from "../src/renderer/audio/audio-device-hot-switch";

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
});
