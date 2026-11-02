import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BackendPreviewInterviewAdapter } from "./backend-adapter";

const envelope = (data: unknown) => ({ success: true, data, error: null, requestId: "synthetic", meta: { apiVersion: "v1", timestamp: "2026-10-19T00:00:00Z" } });
const json = (data: unknown) => new Response(JSON.stringify(envelope(data)), { headers: { "Content-Type": "application/json" } });
const request = (fields: Record<string, unknown> = {}) => ({
  requestId: "capture-1", sessionId: "written-1", ownerUserId: "user-1", deviceId: "device-1", manualCode: "000000",
  instruction: "", status: "requested", stage: "requested", createdAtMs: 1, updatedAtMs: 1, captureOnly: true, ...fields,
});
const answerTask = (fields: Record<string, unknown> = {}) => ({
  taskId: "batch-task-1", sessionId: "written-1", ownerUserId: "user-1", instruction: "请综合截图回答", answerText: "根据两张截图给出的建议。",
  status: "completed", streamMode: true, imageIds: ["image-2", "image-1"], imageCount: 2, createdAtMs: 1, updatedAtMs: 2,
  retryCount: 0, chunks: [], materialContextStatus: "unused", fixedSourceCount: 0, retrievedSourceCount: 0,
  materialProvenance: {}, unavailableMaterialSources: [], ...fields,
});

function harness(initial = request()) {
  let events: readonly unknown[] = [];
  const fetchImpl = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/remote-capture-requests") || url.endsWith("/batch-answer-requests")) return json(initial);
    if (url.endsWith("/cancel")) return json(request({ status: "cancelled" }));
    if (url.includes("/snapshot?")) return json({
      sessionId: "written-1", cursor: 1,
      transcripts: { sessionId: "written-1", transcripts: [] }, candidates: { sessionId: "written-1", candidates: [] },
      events: { sessionId: "written-1", events }, runtime: null,
    });
    if (url.endsWith("/delivery-metrics") || url.endsWith("/performance-ack")) return json({ accepted: true });
    throw new Error(`Unexpected request ${url}`);
  });
  const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", fetchImpl as typeof fetch);
  return {
    adapter, fetchImpl,
    async push(payload: Record<string, unknown>) {
      events = [{ eventId: "event-1", kind: "screenshot-capture-updated", payload: { requestId: initial.requestId, ...payload }, createdAtMs: 2 }];
      return adapter.loadRealtimeSession("written-1");
    },
  };
}

describe("written multi-screen backend adapter", () => {
  beforeEach(() => {
    const values = new Map<string, string>();
    Object.defineProperty(window, "localStorage", { configurable: true, value: {
      getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => values.set(key, value), removeItem: (key: string) => values.delete(key),
    } });
    window.localStorage.setItem("offersteady.auth.access_token", "synthetic-token");
    window.localStorage.setItem("offersteady.auth.refresh_token", "synthetic-refresh");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user-1", displayName: "合成用户", createdAtMs: 1, bindings: [] }));
  });
  afterEach(() => vi.useRealTimers());

  it("requires explicit capture-only support before enabling collection", async () => {
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", vi.fn(async () => json({ maxImagesPerTask: 4 })) as typeof fetch);
    await expect(adapter.getScreenshotCapturePolicy()).rejects.toThrow("暂不支持多屏回答");
    const supported = new BackendPreviewInterviewAdapter("http://localhost:8000", vi.fn(async () => json({ maxImagesPerTask: 8, supportsCaptureOnly: true })) as typeof fetch);
    await expect(supported.getScreenshotCapturePolicy()).resolves.toEqual({ maxImagesPerTask: 4 });
  });

  it("collects a pushed image without answer generation or task polling", async () => {
    const h = harness();
    const onStage = vi.fn();
    const result = h.adapter.captureScreenshot({ interviewId: "written-1" }, undefined, onStage);
    await vi.waitUntil(() => onStage.mock.calls.length > 0);
    const state = await h.push({ captureOnly: true, status: "completed", stage: "completed", capturedImageId: "image-1", capturedFilename: "screen-1.jpg" });
    await expect(result).resolves.toEqual({ requestId: "capture-1", imageId: "image-1", name: "screen-1.jpg" });
    expect(state.shortcutScreenshotUpdate).toBeUndefined();
    const posted = JSON.parse(String(h.fetchImpl.mock.calls[0]?.[1]?.body));
    expect(posted).toEqual({ userId: "user-1", captureOnly: true, instruction: "" });
    expect(h.fetchImpl.mock.calls.some(([url]) => String(url).includes("/capture-requests/"))).toBe(false);
  });

  it("submits ordered capture identities once and receives partial and final answers", async () => {
    const h = harness(request({ requestId: "batch-1", captureOnly: false, status: "processing", stage: "vision-running" }));
    const onAnswer = vi.fn();
    const result = h.adapter.submitScreenshotBatch({ interviewId: "written-1", captureRequestIds: ["capture-2", "capture-1"], instruction: "请综合截图回答" }, undefined, undefined, onAnswer);
    await vi.waitUntil(() => h.fetchImpl.mock.calls.length > 0);
    const state = await h.push({ status: "processing", stage: "vision-running", captureRequestIds: ["capture-2", "capture-1"], answerTask: answerTask({ status: "streaming", answerText: "先给出部分建议" }) });
    expect(state.shortcutScreenshotUpdate).toBeUndefined();
    await vi.waitUntil(() => onAnswer.mock.calls.length > 0);
    await h.push({ status: "completed", stage: "completed", answerTask: answerTask() });
    await expect(result).resolves.toMatchObject({ question: { advice: { detail: "根据两张截图给出的建议。" } } });
    const creates = h.fetchImpl.mock.calls.filter(([url]) => String(url).endsWith("/batch-answer-requests"));
    expect(creates).toHaveLength(1);
    expect(JSON.parse(String(creates[0]?.[1]?.body))).toEqual({ userId: "user-1", captureRequestIds: ["capture-2", "capture-1"], instruction: "请综合截图回答" });
    expect(h.fetchImpl.mock.calls.some(([url]) => String(url).includes("/remote-capture-requests"))).toBe(false);
  });

  it("returns an already completed idempotent batch without waiting for another event", async () => {
    const h = harness(request({ captureOnly: false, status: "completed", stage: "completed", answerTask: answerTask() }));
    await expect(h.adapter.submitScreenshotBatch({ interviewId: "written-1", captureRequestIds: ["a", "b"], instruction: "请综合截图回答" })).resolves.toMatchObject({ task: { status: "completed" } });
    expect(h.fetchImpl.mock.calls.filter(([url]) => !String(url).endsWith("/performance-ack"))).toHaveLength(1);
  });

  it.each(["capture", "batch"])("aborts %s and cancels its server request", async mode => {
    const h = harness(request({ captureOnly: mode === "capture" }));
    const controller = new AbortController();
    const pending = mode === "capture"
      ? h.adapter.captureScreenshot({ interviewId: "written-1" }, controller.signal)
      : h.adapter.submitScreenshotBatch({ interviewId: "written-1", captureRequestIds: ["a"], instruction: "answer" }, controller.signal);
    const settled = pending.then(() => ({ name: "unexpected-success" }), (error: unknown) => error);
    await vi.waitUntil(() => h.fetchImpl.mock.calls.length > 0);
    controller.abort();
    expect(await settled).toMatchObject({ name: "AbortError" });
    expect(h.fetchImpl.mock.calls.filter(([url]) => String(url).endsWith("/capture-1/cancel"))).toHaveLength(1);
  });

  it("uses bounded recovery polling when a completed capture event was missed", async () => {
    vi.useFakeTimers();
    const fetchImpl = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => json(init?.method === "POST" ? request() : request({ status: "completed", stage: "completed", capturedImageId: "image-1" })));
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", fetchImpl as typeof fetch);
    const pending = adapter.captureScreenshot({ interviewId: "written-1" });
    await vi.advanceTimersByTimeAsync(1001);
    await expect(pending).resolves.toMatchObject({ imageId: "image-1" });
    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });

  it("rejects an older backend that silently ignores captureOnly and cancels it", async () => {
    const h = harness(request({ captureOnly: false }));
    await expect(h.adapter.captureScreenshot({ interviewId: "written-1" })).rejects.toThrow("暂不支持仅截屏");
    expect(h.fetchImpl.mock.calls.some(([url]) => String(url).endsWith("/cancel"))).toBe(true);
  });

  it("cancels a late accepted capture after leaving instead of publishing it", async () => {
    let accept!: (value: Response) => void;
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => String(input).endsWith("/cancel")
      ? json(request({ status: "cancelled" }))
      : new Promise<Response>(resolve => { accept = resolve; }));
    const adapter = new BackendPreviewInterviewAdapter("http://localhost:8000", fetchImpl as typeof fetch);
    const controller = new AbortController();
    const stage = vi.fn();
    const pending = adapter.captureScreenshot({ interviewId: "written-1" }, controller.signal, stage);
    const settled = pending.then(() => ({ name: "unexpected-success" }), (error: unknown) => error);
    controller.abort();
    accept(json(request({ status: "completed", capturedImageId: "image-late" })));
    expect(await settled).toMatchObject({ name: "AbortError" });
    expect(stage).not.toHaveBeenCalled();
    expect(fetchImpl.mock.calls.filter(([url]) => String(url).endsWith("/cancel"))).toHaveLength(1);
  });

  it("rejects incomplete completed capture results rather than waiting indefinitely", async () => {
    const h = harness(request({ status: "completed", stage: "completed" }));
    await expect(h.adapter.captureScreenshot({ interviewId: "written-1" })).rejects.toThrow("未返回完整结果");
    expect(h.fetchImpl.mock.calls.some(([url]) => String(url).endsWith("/cancel"))).toBe(true);
  });

  it("does not revive a cancelled batch through late desktop-shortcut recovery events", async () => {
    const h = harness(request({ requestId: "batch-cancelled", captureOnly: false, status: "processing", captureRequestIds: ["source-1"] }));
    const controller = new AbortController();
    const onAnswer = vi.fn();
    const pending = h.adapter.submitScreenshotBatch({ interviewId: "written-1", captureRequestIds: ["source-1"], instruction: "answer" }, controller.signal, undefined, onAnswer);
    const settled = pending.then(() => ({ name: "unexpected-success" }), (error: unknown) => error);
    await vi.waitUntil(() => h.fetchImpl.mock.calls.length > 0);
    controller.abort();
    expect(await settled).toMatchObject({ name: "AbortError" });
    const state = await h.push({ captureOnly: false, captureRequestIds: ["source-1"], status: "completed", stage: "completed", answerTask: answerTask() });
    expect(onAnswer).not.toHaveBeenCalled();
    expect(state.shortcutScreenshotUpdate).toBeUndefined();
    expect(state.answerUpdate).toBeUndefined();
  });

  it("surfaces a real batch failure and cancels rather than automatically resubmitting images", async () => {
    const h = harness(request({ captureOnly: false, status: "failed", stage: "failed", errorMessage: "截图已过期，请重新截屏。" }));
    await expect(h.adapter.submitScreenshotBatch({ interviewId: "written-1", captureRequestIds: ["a"], instruction: "answer" })).rejects.toThrow("截图已过期");
    expect(h.fetchImpl.mock.calls.filter(([url]) => String(url).endsWith("/batch-answer-requests"))).toHaveLength(1);
  });

  it.each(["capture-failed", "upload-failed"])("retains existing %s metadata for written feedback without changing raw errors", async stage => {
    const h = harness(request({ status: "failed", stage, errorMessage: "request timed out" }));
    const onStage = vi.fn();
    await expect(h.adapter.captureScreenshot({ interviewId: "written-1" }, undefined, onStage)).rejects.toThrow(`截图阶段 ${stage} 失败：request timed out`);
    expect(onStage).toHaveBeenCalledWith({ name: "共享屏幕截取", stage: "failed", errorMessage: "request timed out", failureStage: stage });
    const pushed = await h.push({ captureOnly: false, status: "failed", stage, errorMessage: "request timed out" });
    expect(pushed.shortcutScreenshotUpdate?.screenshotTask).toMatchObject({ stage: "failed", failureStage: stage, errorMessage: "request timed out" });
  });

  it("keeps older responses without a failure stage usable", async () => {
    const h = harness(request({ status: "failed", stage: undefined, errorMessage: "合成失败" }));
    const onStage = vi.fn();
    await expect(h.adapter.captureScreenshot({ interviewId: "written-1" }, undefined, onStage)).rejects.toThrow("合成失败");
    expect(onStage).toHaveBeenCalledWith({ name: "共享屏幕截取", stage: "failed", errorMessage: "合成失败" });
  });
});
