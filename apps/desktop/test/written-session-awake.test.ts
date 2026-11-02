import { afterEach, expect, it, vi } from "vitest";
import { WrittenSessionAwakeGuard } from "../src/main/written-session-awake";
import { ScreenshotCaptureLock } from "../src/main/screenshot-capture-lock";
afterEach(() => vi.useRealTimers());
it("keeps only a renewable active-written power lease, including blocker ID zero", async () => {
  vi.useFakeTimers(); const start = vi.fn(() => 0), stop = vi.fn();
  const guard = new WrittenSessionAwakeGuard({ start, stop });
  guard.refresh(true); await vi.advanceTimersByTimeAsync(30_000); guard.refresh(true);
  expect(start).toHaveBeenCalledOnce(); await vi.advanceTimersByTimeAsync(44_999); expect(stop).not.toHaveBeenCalled();
  await vi.advanceTimersByTimeAsync(1); expect(stop).toHaveBeenCalledWith(0);
  guard.refresh(true); guard.refresh(false); expect(stop).toHaveBeenCalledTimes(2);
  guard.dispose(); guard.refresh(true); expect(start).toHaveBeenCalledTimes(2);
});
it("does not leak a power timer when the OS rejects protection", () => {
  vi.useFakeTimers(); const guard = new WrittenSessionAwakeGuard({ start: () => { throw new Error("synthetic"); }, stop: vi.fn() });
  expect(() => guard.refresh(true)).not.toThrow(); expect(vi.getTimerCount()).toBe(0); guard.dispose();
});
it("an old screenshot owner cannot release a newer screenshot lock", () => {
  const lock = new ScreenshotCaptureLock(); expect(lock.tryAcquire()).toBe(true); const old = lock.ownerToken();
  expect(lock.release(old)).toBe(true); expect(lock.tryAcquire()).toBe(true); const next = lock.ownerToken();
  expect(next).not.toBe(old); expect(lock.release(old)).toBe(false); expect(lock.state().locked).toBe(true);
  expect(lock.release(next)).toBe(true); expect(lock.state().locked).toBe(false);
});
