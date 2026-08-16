import { describe, expect, it } from "vitest";

import { ScreenshotCaptureLock } from "./screenshot-capture-lock";

describe("ScreenshotCaptureLock", () => {
  it("blocks concurrent screenshots while one capture is in progress", () => {
    const lock = new ScreenshotCaptureLock();

    expect(lock.tryAcquire()).toBe(true);
    expect(lock.state().locked).toBe(true);
    expect(lock.tryAcquire()).toBe(false);
    expect(lock.state().message).toContain("仍在处理中");

    lock.release();
    expect(lock.state().locked).toBe(false);
    expect(lock.tryAcquire()).toBe(true);
  });
});
