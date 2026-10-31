import { beforeEach, describe, expect, it, vi } from "vitest";
import { BackendPreviewInterviewAdapter } from "./backend-adapter";
import { authClient } from "./auth-client";
import { syntheticState } from "./test-state";

const deferred = <T,>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(yes => { resolve = yes; });
  return { promise, resolve };
};
const stateResponse = (balance: number) => new Response(JSON.stringify({ success: true, data: { ...structuredClone(syntheticState), billing: { ...syntheticState.billing, balance } }, requestId: "synthetic", meta: {} }), { headers: { "Content-Type": "application/json" } });

describe("state freshness includes the full answer stream lifecycle", () => {
  beforeEach(() => {
    const values = new Map<string, string>();
    Object.defineProperty(window, "localStorage", { configurable: true, value: {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key),
    } });
    authClient.clear();
    window.localStorage.setItem("offersteady.auth.access_token", "synthetic-access");
    window.localStorage.setItem("offersteady.auth.refresh_token", "synthetic-refresh");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "synthetic-user", displayName: "合成账号", createdAtMs: 1, bindings: [] }));
  });

  it.each(["completed", "failed", "cancelled", "eof", "abort"] as const)("invalidates a state read started after headers when the stream ends with %s", async ending => {
    const oldState = deferred<Response>(); const freshState = deferred<Response>();
    const started = deferred<void>();
    const encoder = new TextEncoder();
    const task = { taskId: "synthetic-task", sessionId: "synthetic-session", ownerUserId: "synthetic-user", question: "合成问题", answerText: "", status: "streaming", updatedAtMs: 1, chunks: [] };
    let streamController!: ReadableStreamDefaultController<Uint8Array>;
    const stream = new ReadableStream<Uint8Array>({ start(controller) {
      streamController = controller;
      controller.enqueue(encoder.encode(`event: task-started\ndata: ${JSON.stringify({ type: "task-started", task })}\n\n`));
    } });
    const stateFetch = vi.fn().mockReturnValueOnce(oldState.promise).mockReturnValueOnce(freshState.promise);
    const fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/web/state")) return stateFetch();
      init?.signal?.addEventListener("abort", () => streamController.error(new DOMException("Synthetic abort", "AbortError")), { once: true });
      return new Response(stream, { headers: { "Content-Type": "text/event-stream" } });
    });
    const adapter = new BackendPreviewInterviewAdapter("/", fetch);
    const controller = new AbortController();
    const answer = adapter.submitManualAnswer({ interviewId: "synthetic-session", question: "合成问题", idempotencyKey: "synthetic-answer" }, controller.signal, () => started.resolve());
    const outcome = answer.then(result => ({ result }), error => ({ error }));
    await started.promise; // Parser delivery proves that headers have arrived.
    const old = adapter.loadState();
    expect(stateFetch).toHaveBeenCalledTimes(1);
    if (ending === "abort") controller.abort();
    else {
      if (ending !== "eof") streamController.enqueue(encoder.encode(`event: ${ending}\ndata: ${JSON.stringify({ type: ending, task: { ...task, status: ending, answerText: "合成结果" } })}\n\n`));
      streamController.close();
    }
    const settled = await outcome;
    if (ending === "abort") expect(settled).toMatchObject({ error: { name: "AbortError" } });
    else if (ending === "eof") expect(settled).toMatchObject({ error: { code: "network" } });
    else expect(settled).toMatchObject({ result: { task: { status: ending } } });
    const fresh = adapter.loadState();
    expect(stateFetch).toHaveBeenCalledTimes(2);
    oldState.resolve(stateResponse(100));
    await new Promise(resolve => window.setTimeout(resolve, 0));
    freshState.resolve(stateResponse(200));
    expect((await Promise.all([old, fresh])).map(result => result.billing.balance)).toEqual([200, 200]);
    expect(stateFetch).toHaveBeenCalledTimes(2);
  });
});
