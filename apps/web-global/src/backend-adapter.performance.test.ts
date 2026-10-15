import { describe, expect, it, vi } from "vitest";

import { BackendPreviewInterviewAdapter, WEB_STATE_CACHE_TTL_MS } from "./backend-adapter";
import type { WebAppState } from "./domain";

const state = { account: null, interviews: [] } as unknown as WebAppState;
const envelope = (data: unknown) => ({
  success: true,
  data,
  error: null,
  requestId: "test-request",
  meta: { apiVersion: "v1", timestamp: new Date().toISOString() },
});

const stateResponse = (data: WebAppState = state) => new Response(JSON.stringify(envelope(data)), {
  status: 200,
  headers: { "Content-Type": "application/json" },
});

describe("Global Web performance coordinator", () => {
  it("coalesces concurrent state reads and returns independent values", async () => {
    let resolveResponse!: (response: Response) => void;
    const response = new Promise<Response>(resolve => { resolveResponse = resolve; });
    const fetchImpl = vi.fn(async () => response);
    const adapter = new BackendPreviewInterviewAdapter("https://offersteady.com", fetchImpl as typeof fetch);

    const first = adapter.loadState();
    const second = adapter.loadState();
    expect(fetchImpl).toHaveBeenCalledTimes(1);

    resolveResponse(stateResponse());
    const [firstState, secondState] = await Promise.all([first, second]);
    expect(firstState).not.toBe(secondState);
    firstState.interviews.push({} as never);
    expect(secondState.interviews).toHaveLength(0);
  });

  it("keeps public and authenticated caches isolated and honors forced refresh", async () => {
    window.localStorage.setItem("offersteady.auth.access_token", "access-token");
    window.localStorage.setItem("offersteady.auth.refresh_token", "refresh-token");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user-1", displayName: "Test user", createdAtMs: 1, bindings: [] }));
    const fetchImpl = vi.fn(async () => stateResponse());
    const adapter = new BackendPreviewInterviewAdapter("https://offersteady.com", fetchImpl as typeof fetch);

    await Promise.all([
      adapter.loadState(undefined, { auth: false }),
      adapter.loadState(),
    ]);
    expect(fetchImpl).toHaveBeenCalledTimes(2);
    const headers = fetchImpl.mock.calls.map(call => new Headers((call[1] as RequestInit | undefined)?.headers));
    expect(headers.some(item => item.has("Authorization"))).toBe(true);
    expect(headers.some(item => !item.has("Authorization"))).toBe(true);

    vi.useFakeTimers();
    try {
      await adapter.loadState(undefined, { force: true });
      vi.advanceTimersByTime(WEB_STATE_CACHE_TTL_MS - 1);
      await adapter.loadState();
      expect(fetchImpl).toHaveBeenCalledTimes(3);
      vi.advanceTimersByTime(1);
      await adapter.loadState();
      expect(fetchImpl).toHaveBeenCalledTimes(4);
    } finally {
      vi.useRealTimers();
    }
  });

  it("starts an authoritative refresh independently and never caches a late older response", async () => {
    const complete: Array<(value: Response) => void> = [];
    const fetchImpl = vi.fn(() => new Promise<Response>(resolve => complete.push(resolve)));
    const adapter = new BackendPreviewInterviewAdapter("https://offersteady.com", fetchImpl as typeof fetch);
    const earlier = adapter.loadState();
    const refreshed = adapter.loadState(undefined, { force: true });
    expect(fetchImpl).toHaveBeenCalledTimes(2);
    const latest = { ...state, interviews: [{ id: "after-mutation" }] } as WebAppState;
    complete[1]!(stateResponse(latest));
    expect((await refreshed).interviews[0]?.id).toBe("after-mutation");
    complete[0]!(stateResponse());
    await earlier;
    expect((await adapter.loadState()).interviews[0]?.id).toBe("after-mutation");
    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });

  it("does not share a cached authenticated value across a changed login", async () => {
    window.localStorage.setItem("offersteady.auth.access_token", "synthetic-owner-a");
    window.localStorage.setItem("offersteady.auth.refresh_token", "synthetic-refresh");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "owner-a", displayName: "Synthetic A", createdAtMs: 1, bindings: [] }));
    const fetchImpl = vi.fn(async (_input: unknown, init?: RequestInit) => stateResponse({
      ...state,
      account: { id: new Headers(init?.headers).get("Authorization")?.endsWith("owner-a") ? "owner-a" : "owner-b" },
    } as WebAppState));
    const adapter = new BackendPreviewInterviewAdapter("https://offersteady.com", fetchImpl as typeof fetch);
    expect((await adapter.loadState()).account.id).toBe("owner-a");
    window.localStorage.setItem("offersteady.auth.access_token", "synthetic-owner-b");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "owner-b", displayName: "Synthetic B", createdAtMs: 1, bindings: [] }));
    expect((await adapter.loadState()).account.id).toBe("owner-b");
    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });

  it("lets an aborted caller leave without cancelling the other shared caller", async () => {
    let complete!: (value: Response) => void;
    const fetchImpl = vi.fn((_input: RequestInfo | URL, _init?: RequestInit) => new Promise<Response>(resolve => { complete = resolve; }));
    const adapter = new BackendPreviewInterviewAdapter("https://offersteady.com", fetchImpl as typeof fetch);
    const controller = new AbortController();
    const first = adapter.loadState(controller.signal).catch(error => error);
    const second = adapter.loadState();
    controller.abort();
    expect((await first).name).toBe("AbortError");
    expect((fetchImpl.mock.calls[0]?.[1] as RequestInit).signal?.aborted).toBe(false);
    complete(stateResponse());
    expect(await second).toEqual(state);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  it("does not cache a failed state read", async () => {
    const fetchImpl = vi.fn().mockRejectedValueOnce(new Error("synthetic-network-failure")).mockResolvedValueOnce(stateResponse());
    const adapter = new BackendPreviewInterviewAdapter("https://offersteady.com", fetchImpl as typeof fetch);
    await expect(adapter.loadState()).rejects.toThrow();
    expect(await adapter.loadState()).toEqual(state);
    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });

  it("samples non-final transcript telemetry per session and keeps final revisions", async () => {
    window.localStorage.setItem("offersteady.auth.access_token", "access-token");
    window.localStorage.setItem("offersteady.auth.refresh_token", "refresh-token");
    window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user-1", displayName: "Test user", createdAtMs: 1, bindings: [] }));
    const fetchImpl = vi.fn(async () => new Response(JSON.stringify(envelope({ accepted: true })), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    const adapter = new BackendPreviewInterviewAdapter("https://offersteady.com", fetchImpl as typeof fetch);
    const acknowledge = (adapter as unknown as {
      acknowledgeRuntimePerformance: (
        interviewId: string,
        traceId: string,
        stage: "transcript-render",
        startedAtMs: number,
        taskId: undefined,
        delivery: { eventId: string; segmentId: string; isFinal: boolean; browserRenderAtMs: number },
      ) => void;
    }).acknowledgeRuntimePerformance.bind(adapter);
    let now = 1_000;
    const nowSpy = vi.spyOn(Date, "now").mockImplementation(() => now);

    acknowledge("session-1", "trace-1", "transcript-render", now, undefined, { eventId: "event-1", segmentId: "segment-1", isFinal: false, browserRenderAtMs: now });
    now += 4_999;
    acknowledge("session-1", "trace-2", "transcript-render", now, undefined, { eventId: "event-2", segmentId: "segment-2", isFinal: false, browserRenderAtMs: now });
    now += 1;
    acknowledge("session-1", "trace-3", "transcript-render", now, undefined, { eventId: "event-3", segmentId: "segment-2", isFinal: false, browserRenderAtMs: now });
    acknowledge("session-1", "trace-4", "transcript-render", now, undefined, { eventId: "event-4", segmentId: "segment-2", isFinal: true, browserRenderAtMs: now });

    await vi.waitFor(() => expect(fetchImpl).toHaveBeenCalledTimes(3));
    const bodies = fetchImpl.mock.calls.map(call => JSON.parse(String((call[1] as RequestInit).body)) as { traceId: string });
    expect(bodies.map(body => body.traceId)).toEqual(["trace-1", "trace-3", "trace-4"]);
    nowSpy.mockRestore();
  });
});
