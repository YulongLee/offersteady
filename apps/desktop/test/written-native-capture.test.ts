import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { expect, it, vi } from "vitest";
import { ScreenshotCaptureLock } from "../src/main/screenshot-capture-lock";
const ts = createRequire(import.meta.url)("typescript") as typeof import("typescript");
const source = readFileSync(new URL("../src/main/index.ts", import.meta.url), "utf8");
const from = source.indexOf("const captureCurrentScreen = async");
const to = source.indexOf("const uploadScreenshotCapture =", from);
const compiled = ts.transpileModule(source.slice(from, to), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText;
it("fences an unabortable timed-out native read without starting overlapping native work", async () => {
  let resolve!: (value: unknown[]) => void;
  const native = vi.fn().mockImplementationOnce(() => new Promise(done => { resolve = done; })).mockResolvedValue([]);
  const lock = new ScreenshotCaptureLock();
  const capture = new Function("desktopCapturer", "screenshotCaptureLock", "releaseScreenshotCaptureLock", `
    let writtenNativeSourceReadInFlight = false;
    let preferredScreenSourceId = null;
    const publishScreenshotCaptureLock = () => undefined;
    ${compiled}
    return captureCurrentScreen;
  `)({ getSources: native }, lock, (owner: number) => lock.release(owner)) as (id: null, held: boolean, release: boolean, lifecycle: {signal: AbortSignal; ownerToken: number}) => Promise<unknown>;
  lock.tryAcquire(); const oldOwner = lock.ownerToken()!; const old = new AbortController();
  const first = capture(null, true, false, { signal: old.signal, ownerToken: oldOwner });
  old.abort(); lock.release(oldOwner);
  lock.tryAcquire(); const nextOwner = lock.ownerToken()!;
  const second = await capture(null, true, false, { signal: new AbortController().signal, ownerToken: nextOwner });
  expect(second).toMatchObject({ errorMessage: expect.stringContaining("仍在恢复") });
  expect(native).toHaveBeenCalledOnce();
  lock.tryAcquire(); const latestOwner = lock.ownerToken()!;
  const late = expect(first).rejects.toThrow("screenshot_operation_obsolete");
  resolve([]); await late;
  expect(lock.ownerToken()).toBe(latestOwner);
  const recovered = await capture(null, true, false, { signal: new AbortController().signal, ownerToken: latestOwner });
  expect(native).toHaveBeenCalledTimes(2);
  expect(recovered).toMatchObject({ errorMessage: expect.stringContaining("没有找到") });
});
