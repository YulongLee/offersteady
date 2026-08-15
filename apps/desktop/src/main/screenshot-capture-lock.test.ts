import { describe, expect, it } from "vitest";

import { ScreenshotCaptureLock } from "./screenshot-capture-lock";

describe("ScreenshotCaptureLock", () => {
  it("keeps a successful screenshot locked until explicit release", () => {
    const lock = new ScreenshotCaptureLock();

    expect(lock.tryAcquire()).toBe(true);
    expect(lock.state().locked).toBe(true);
    expect(lock.tryAcquire()).toBe(false);
    expect(lock.state().message).toContain("取消当前截屏");

    lock.release();
    expect(lock.state().locked).toBe(false);
    expect(lock.tryAcquire()).toBe(true);
  });
});
