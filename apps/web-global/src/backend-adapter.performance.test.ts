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

const stateResponse = () => new Response(JSON.stringify(envelope(state)), {
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
