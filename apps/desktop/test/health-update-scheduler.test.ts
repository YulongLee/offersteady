import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HealthUpdateScheduler } from "../src/renderer/audio/health-update-scheduler";

describe("health update scheduler", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(1_000);
  });

  afterEach(() => vi.useRealTimers());

  it("emits immediately and coalesces display-only updates to 10 Hz", () => {
    const emitted: number[] = [];
    const scheduler = new HealthUpdateScheduler<number>((value) => emitted.push(value), 100);
    scheduler.push(1);
    for (let value = 2; value <= 20; value += 1) scheduler.push(value);
    expect(emitted).toEqual([1]);
    vi.advanceTimersByTime(99);
    expect(emitted).toEqual([1]);
    vi.advanceTimersByTime(1);
    expect(emitted).toEqual([1, 20]);
  });

  it("cancels pending UI work when capture stops", () => {
    const emitted: number[] = [];
    const scheduler = new HealthUpdateScheduler<number>((value) => emitted.push(value), 100);
    scheduler.push(1);
    scheduler.push(2);
    scheduler.dispose();
    vi.advanceTimersByTime(100);
    expect(emitted).toEqual([1]);
  });
});
