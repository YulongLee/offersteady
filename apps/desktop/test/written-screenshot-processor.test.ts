import { afterEach, describe, expect, it, vi } from "vitest";

import { WrittenScreenshotProcessor, type WrittenScreenshotJob, type WrittenScreenshotPorts } from "../src/main/written-screenshot-processor";

const deferred = <T>() => {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
};
const flush = async () => { for (let i = 0; i < 60; i++) await Promise.resolve(); };
const job = (requestId: string, generation = 1): WrittenScreenshotJob => ({
  requestId, generation, bindingKey: `synthetic-binding-${generation}`,
  identity: { deviceId: "synthetic-device", manualCode: "synthetic-code" },
});

const harness = (overrides: Partial<WrittenScreenshotPorts<string>> = {}) => {
  let owner: string | null = null;
  const releases: string[] = [];
  const ports: WrittenScreenshotPorts<string> = {
    inspect: vi.fn(async () => ({ current: true, requested: true })),
    capture: vi.fn(async item => `synthetic-image-${item.requestId}`),
    upload: vi.fn(async () => {}),
    report: vi.fn(async () => {}),
    notice: vi.fn(),
    settled: vi.fn(),
    acquire: vi.fn(item => {
      if (owner) return null;
      const lease = `${item.generation}:${item.requestId}`;
      owner = lease;
      return () => { releases.push(lease); if (owner === lease) owner = null; };
    }),
    ...overrides,
  };
  const processor = new WrittenScreenshotProcessor(ports);
  return { ports, processor, releases, owner: () => owner };
};

afterEach(() => { vi.useRealTimers(); });

describe("WrittenScreenshotProcessor", () => {
  it.each(["capture", "upload"] as const)("retains FIFO requests received while %s is busy", async stage => {
    const busy = deferred<string>();
    const captures: string[] = [];
    const uploads: string[] = [];
    const { processor, ports } = harness({
      capture: vi.fn(async item => {
        captures.push(item.requestId);
        return stage === "capture" && item.requestId === "one" ? busy.promise : "synthetic-image";
      }),
      upload: vi.fn(async item => {
        uploads.push(item.requestId);
        if (stage === "upload" && item.requestId === "one") await busy.promise;
      }),
    });
    const one = processor.enqueue(job("one"));
    await flush();
    const two = processor.enqueue(job("two"));
    const three = processor.enqueue(job("three"));
    expect(processor.enqueue(job("two")).status).toBe("duplicate");
    expect(processor.snapshot().pendingCount).toBe(2);
    busy.resolve("synthetic-image");
    expect((await Promise.all([one.completion, two.completion, three.completion])).map(result => result.status)).toEqual(["uploaded", "uploaded", "uploaded"]);
    expect(captures).toEqual(["one", "two", "three"]);
    expect(uploads).toEqual(["one", "two", "three"]);
    expect(ports.report).not.toHaveBeenCalled();
  });

  it("bounds pending requests to four and explicitly rejects overflow without capturing", async () => {
    const busy = deferred<string>();
    const { processor, ports } = harness({ capture: vi.fn(() => busy.promise) });
    processor.enqueue(job("active"));
    for (let index = 0; index < 4; index++) expect(processor.enqueue(job(`pending-${index}`)).status).toBe("accepted");
    const overflow = processor.enqueue(job("overflow"));
    expect(overflow.status).toBe("full");
    expect(await overflow.completion).toMatchObject({ status: "rejected", failure: { code: "queue-full" } });
    expect(ports.notice).toHaveBeenCalledWith(expect.objectContaining({ requestId: "overflow" }), expect.stringContaining("稍候重试"));
    expect(processor.snapshot().pendingCount).toBe(4);
    processor.cancelAll();
    await flush();
    expect(ports.capture).not.toHaveBeenCalled();
  });

  it("deduplicates completed requests and bounds recent metadata to 128", async () => {
    const { processor, ports } = harness();
    for (let index = 0; index < 130; index++) await processor.enqueue(job(`request-${index}`)).completion;
    const duplicate = processor.enqueue(job("request-129", 2));
    expect(duplicate.status).toBe("duplicate");
    expect((await duplicate.completion).status).toBe("uploaded");
    expect(ports.capture).toHaveBeenCalledTimes(130);
    expect(processor.snapshot().recentCount).toBe(128);
  });

  it("does not capture a noncanonical request and allows later explicit canonical rediscovery", async () => {
    let requested = false;
    const { processor, ports } = harness({ inspect: vi.fn(async () => ({ current: true, requested })) });
    expect(await processor.enqueue(job("later")).completion).toEqual({ status: "skipped" });
    expect(ports.capture).not.toHaveBeenCalled();
    requested = true;
    expect((await processor.enqueue(job("later")).completion).status).toBe("uploaded");
    expect(ports.capture).toHaveBeenCalledTimes(1);
  });

  it("checks binding and pending status again after capture and discards a cancelled image", async () => {
    const inspect = vi.fn()
      .mockResolvedValueOnce({ current: true, requested: true })
      .mockResolvedValueOnce({ current: true, requested: false });
    const { processor, ports } = harness({ inspect });
    expect((await processor.enqueue(job("cancelled-on-server")).completion).status).toBe("skipped");
    expect(inspect).toHaveBeenCalledTimes(2);
    expect(ports.capture).toHaveBeenCalledTimes(1);
    expect(ports.upload).not.toHaveBeenCalled();
    expect(ports.report).not.toHaveBeenCalled();
  });

  it.each(["resolve", "reject"] as const)("drops a late native capture %s after cancellation without releasing a newer lease", async lateAction => {
    const old = deferred<string>();
    const next = deferred<string>();
    const { processor, ports, releases, owner } = harness({ capture: vi.fn(item => item.generation === 1 ? old.promise : next.promise) });
    const first = processor.enqueue(job("old", 1));
    processor.enqueue(job("old-queued", 1));
    await flush();
    expect(processor.cancelWhere(item => item.generation === 1)).toBe(2);
    expect(await first.completion).toEqual({ status: "cancelled" });
    const newer = processor.enqueue(job("new", 2));
    await flush();
    expect(owner()).toBe("2:new");
    if (lateAction === "resolve") old.resolve("obsolete-synthetic-image");
    else old.reject(new Error("late synthetic native error"));
    await flush();
    expect(owner()).toBe("2:new");
    expect(releases).toEqual(["1:old"]);
    expect(ports.upload).not.toHaveBeenCalled();
    next.resolve("current-synthetic-image");
    expect((await newer.completion).status).toBe("uploaded");
    expect(ports.capture).toHaveBeenCalledTimes(2);
    expect(releases).toEqual(["1:old", "2:new"]);
  });

  it.each(["capture", "upload"] as const)("does not replay a request cancelled during %s when the same binding recovers with a new generation", async stage => {
    const busy = deferred<string>();
    const { processor, ports } = harness({
      capture: vi.fn(async item => item.requestId === "same-request" && stage === "capture" ? busy.promise : "synthetic-image"),
      upload: vi.fn(async item => {
        if (item.requestId === "same-request" && stage === "upload") await busy.promise;
      }),
    });
    const original = job("same-request");
    const first = processor.enqueue(original);
    await flush();
    expect(ports.capture).toHaveBeenCalledTimes(1);
    expect(ports.upload).toHaveBeenCalledTimes(stage === "upload" ? 1 : 0);
    expect(processor.cancelAll()).toBe(1);

    // Re-enqueue synchronously after cancellation, before any old promise settles.
    const recovered = { ...original, generation: original.generation + 1 };
    const replay = processor.enqueue(recovered);
    expect(replay.status).toBe("duplicate");
    expect(await replay.completion).toEqual({ status: "cancelled" });
    expect(await first.completion).toEqual({ status: "cancelled" });
    expect((await processor.enqueue({ ...recovered, requestId: "fresh-request" }).completion).status).toBe("uploaded");
    expect(ports.capture).toHaveBeenCalledTimes(2);
    expect(ports.upload).toHaveBeenCalledTimes(stage === "upload" ? 2 : 1);
    busy.resolve("obsolete-synthetic-image");
    await flush();
    expect(ports.capture).toHaveBeenCalledTimes(2);
    expect(ports.upload).toHaveBeenCalledTimes(stage === "upload" ? 2 : 1);
    expect(ports.report).not.toHaveBeenCalled();
  });

  it("allows explicit rediscovery after cancellation before capture even if generation changes", async () => {
    const oldInspection = deferred<{ current: boolean; requested: boolean }>();
    const { processor, ports } = harness({
      inspect: vi.fn(item => item.generation === 1 ? oldInspection.promise : Promise.resolve({ current: true, requested: true })),
    });
    const original = job("not-yet-captured");
    const first = processor.enqueue(original);
    await flush();
    expect(ports.capture).not.toHaveBeenCalled();
    processor.cancelAll();
    expect(await first.completion).toEqual({ status: "cancelled" });
    const recovered = processor.enqueue({ ...original, generation: 2 });
    expect(recovered.status).toBe("accepted");
    expect((await recovered.completion).status).toBe("uploaded");
    expect(ports.capture).toHaveBeenCalledTimes(1);
    oldInspection.resolve({ current: true, requested: true });
    await flush();
    expect(ports.capture).toHaveBeenCalledTimes(1);
  });

  it("bounds a hung capture, aborts its signal, and does not await or upload its late result", async () => {
    vi.useFakeTimers();
    const hung = deferred<string>();
    const next = deferred<string>();
    let oldSignal: AbortSignal | undefined;
    const { processor, ports, releases, owner } = harness({ capture: vi.fn((item, signal) => {
      if (item.requestId === "hung") { oldSignal = signal; return hung.promise; }
      return next.promise;
    }) });
    const first = processor.enqueue(job("hung"));
    const newer = processor.enqueue(job("new"));
    await flush();
    await vi.advanceTimersByTimeAsync(10_000);
    expect(await first.completion).toMatchObject({ status: "failed", failure: { stage: "capture", code: "capture-timeout" } });
    expect(oldSignal?.aborted).toBe(true);
    expect(owner()).toBe("1:new");
    hung.resolve("obsolete-synthetic-image");
    await flush();
    expect(releases).toEqual(["1:hung"]);
    expect(ports.upload).not.toHaveBeenCalled();
    next.resolve("current-synthetic-image");
    expect((await newer.completion).status).toBe("uploaded");
    expect(ports.report).toHaveBeenCalledWith(expect.objectContaining({ requestId: "hung" }), expect.objectContaining({ code: "capture-timeout" }), expect.any(AbortSignal));
  });

  it("classifies upload timeout, confirms pending state and never retries upload", async () => {
    vi.useFakeTimers();
    let signal: AbortSignal | undefined;
    const { processor, ports } = harness({ upload: vi.fn(async (_item, _capture, operationSignal) => {
      signal = operationSignal;
      await new Promise<void>(() => {});
    }) });
    const request = processor.enqueue(job("upload-timeout"));
    await flush();
    await vi.advanceTimersByTimeAsync(30_000);
    expect(await request.completion).toMatchObject({ status: "failed", failure: { stage: "upload", code: "upload-timeout" } });
    expect(signal?.aborted).toBe(true);
    expect(ports.inspect).toHaveBeenCalledTimes(3);
    expect(ports.upload).toHaveBeenCalledTimes(1);
    expect(ports.report).toHaveBeenCalledWith(expect.anything(), expect.objectContaining({ stage: "upload", code: "upload-timeout" }), expect.any(AbortSignal));
    expect(processor.enqueue(job("upload-timeout", 2)).status).toBe("duplicate");
  });

  it.each(["resolve", "reject"] as const)("enforces absolute capture deadlines after sleep before timers run (%s)", async lateAction => {
    vi.useFakeTimers();
    const hung = deferred<string>();
    const { processor, ports, owner } = harness({ capture: vi.fn(() => hung.promise) });
    const first = processor.enqueue(job("sleeping"));
    await flush();
    // Jump wall time without executing the scheduled timeout callback.
    vi.setSystemTime(Date.now() + 10_001);
    if (lateAction === "resolve") hung.resolve("obsolete-synthetic-image");
    else hung.reject(new Error("synthetic native failure after sleep"));
    await flush();
    expect(await first.completion).toMatchObject({ status: "failed", failure: { code: "capture-timeout" } });
    expect(ports.upload).not.toHaveBeenCalled();
    expect(owner()).toBeNull();
  });

  it("expires a long-queued explicit request instead of capturing a changed page", async () => {
    vi.useFakeTimers();
    let available = false;
    const release = vi.fn();
    const { processor, ports } = harness({ acquire: vi.fn(() => available ? release : null) });
    const queued = processor.enqueue(job("old-explicit-request"));
    vi.setSystemTime(Date.now() + 60_001);
    available = true;
    processor.resume();
    expect(await queued.completion).toMatchObject({ status: "failed", failure: { stage: "request", code: "request-expired" } });
    expect(ports.capture).not.toHaveBeenCalled();
    expect(ports.report).toHaveBeenCalledWith(expect.anything(), expect.objectContaining({ code: "request-expired" }), expect.any(AbortSignal));
    expect(processor.enqueue(job("old-explicit-request", 2)).status).toBe("duplicate");
    expect(release).toHaveBeenCalledTimes(1);
  });

  it.each(["accepted", "unreadable"])("does not report or repeat an ambiguous upload when server state is %s", async serverState => {
    const inspect = vi.fn()
      .mockResolvedValueOnce({ current: true, requested: true })
      .mockResolvedValueOnce({ current: true, requested: true });
    if (serverState === "accepted") inspect.mockResolvedValue({ current: true, requested: false });
    else inspect.mockRejectedValue(new Error("synthetic offline"));
    const { processor, ports } = harness({ inspect, upload: vi.fn(async () => { throw new Error("synthetic ambiguous transport error"); }) });
    expect(await processor.enqueue(job("ambiguous")).completion).toMatchObject({ status: "unconfirmed", failure: { code: "upload-outcome-unknown" } });
    expect(ports.report).not.toHaveBeenCalled();
    expect(ports.upload).toHaveBeenCalledTimes(1);
    expect(ports.notice).toHaveBeenLastCalledWith(expect.anything(), expect.stringContaining("查看网页状态"));
    expect(processor.snapshot().activeRequestId).toBeNull();
    expect(processor.enqueue(job("ambiguous", 2)).status).toBe("duplicate");
  });

  it("does not turn a late upload error into a failure in a replacement session", async () => {
    const late = deferred<void>();
    const current = deferred<string>();
    const { processor, ports } = harness({
      capture: vi.fn(item => item.generation === 1 ? Promise.resolve("synthetic-image") : current.promise),
      upload: vi.fn(() => late.promise),
    });
    processor.enqueue(job("old"));
    await flush();
    expect(ports.upload).toHaveBeenCalledTimes(1);
    processor.cancelAll();
    const next = processor.enqueue(job("new", 2));
    await flush();
    late.reject(new Error("synthetic cancelled 409"));
    await flush();
    expect(ports.report).not.toHaveBeenCalled();
    expect(processor.snapshot().activeRequestId).toBe("new");
    processor.cancelAll();
    expect((await next.completion).status).toBe("cancelled");
  });

  it("does not publish a late failure report rejection after its request was replaced", async () => {
    const lateReport = deferred<void>();
    const current = deferred<string>();
    const { processor, ports, owner } = harness({
      capture: vi.fn(item => {
        if (item.generation === 1) return Promise.reject(new Error("synthetic capture failure"));
        return current.promise;
      }),
      report: vi.fn(() => lateReport.promise),
    });
    processor.enqueue(job("old"));
    await flush();
    expect(ports.report).toHaveBeenCalledTimes(1);
    processor.cancelAll();
    processor.enqueue(job("new", 2));
    await flush();
    const noticesBeforeLateReport = vi.mocked(ports.notice).mock.calls.length;
    lateReport.reject(new Error("synthetic obsolete 409"));
    await flush();
    expect(ports.notice).toHaveBeenCalledTimes(noticesBeforeLateReport);
    expect(owner()).toBe("2:new");
    processor.cancelAll();
  });

  it("bounds request checks and failure reporting so either stalled port releases the lease", async () => {
    vi.useFakeTimers();
    const never = new Promise<never>(() => {});
    const inspect = vi.fn().mockReturnValueOnce(never).mockResolvedValue({ current: true, requested: true });
    const { processor, ports, owner } = harness({
      inspect,
      capture: vi.fn(async () => { throw new Error("synthetic capture failure"); }),
      report: vi.fn(() => never),
    });
    const checked = processor.enqueue(job("check-hung"));
    await vi.advanceTimersByTimeAsync(5_000);
    expect(await checked.completion).toMatchObject({ status: "failed", failure: { code: "request-check-failed" } });
    expect(ports.capture).not.toHaveBeenCalled();
    expect(owner()).toBeNull();
    const reported = processor.enqueue(job("report-hung"));
    await flush();
    expect(owner()).toBe("1:report-hung");
    await vi.advanceTimersByTimeAsync(5_000);
    expect(await reported.completion).toMatchObject({ status: "failed", failure: { code: "capture-failed" } });
    expect(owner()).toBeNull();
  });

  it("waits for an ordinary capture lease and resumes only when notified", async () => {
    let available = false;
    const release = vi.fn();
    const { processor, ports } = harness({ acquire: vi.fn(() => available ? release : null) });
    const request = processor.enqueue(job("explicit-pending"));
    await flush();
    expect(ports.capture).not.toHaveBeenCalled();
    expect(processor.snapshot().pendingCount).toBe(1);
    available = true;
    processor.resume();
    expect((await request.completion).status).toBe("uploaded");
    expect(release).toHaveBeenCalledTimes(1);
  });

  it("uses and releases an existing shortcut lease without acquiring a second lock", async () => {
    const release = vi.fn();
    const { processor, ports } = harness();
    expect((await processor.enqueue({ ...job("shortcut"), release }).completion).status).toBe("uploaded");
    expect(ports.acquire).not.toHaveBeenCalled();
    expect(release).toHaveBeenCalledTimes(1);
  });
});
