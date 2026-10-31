import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BackendPreviewInterviewAdapter, createAuthRefreshingFetch } from "./backend-adapter";
import { authClient, type AuthResultResponse } from "./auth-client";
import { BackendMaterialUploadAdapter } from "./material-upload-adapter";
import { BackendResumeOptimizerClient } from "./resume-optimizer-client";
import { createJsonClient } from "./api-client";
import { invalidateStateReads } from "./state-read-scope";
import { syntheticState } from "./test-state";

const deferred = <T,>() => {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
const envelope = (data: unknown) => ({ success: true, data, error: null, requestId: "synthetic-request", meta: { apiVersion: "v1", timestamp: "2026-10-28T00:00:00Z" } });
const response = (data: unknown) => new Response(JSON.stringify(envelope(data)), { status: 200, headers: { "Content-Type": "application/json" } });
const state = (points: number) => ({ ...structuredClone(syntheticState), billing: { ...syntheticState.billing, balance: points } });
const tokens = (id = "user-a", token = "token-a"): AuthResultResponse => ({
  user: { userId: id, displayName: "合成账号", createdAtMs: 1, bindings: [] },
  tokens: { accessToken: token, refreshToken: `refresh-${token}` },
});
const store = (id = "user-a", token = "token-a") => {
  window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id, displayName: "合成账号", createdAtMs: 1, bindings: [] }));
  window.localStorage.setItem("offersteady.auth.access_token", token);
  window.localStorage.setItem("offersteady.auth.refresh_token", `refresh-${token}`);
};
const flush = () => new Promise(resolve => window.setTimeout(resolve, 0));

describe("CN state reads coalesce only while in flight", () => {
  beforeEach(() => {
    const values = new Map<string, string>();
    Object.defineProperty(window, "localStorage", { configurable: true, value: {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key),
    } });
    authClient.clear();
    invalidateStateReads();
    vi.stubGlobal("fetch", vi.fn(async () => response({ accepted: true })));
  });
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

  it("coalesces a 24-consumer wave, isolates nested results, and never caches completion", async () => {
    store();
    const controlGate = deferred<void>();
    const controlFetch = vi.fn(() => controlGate.promise.then(() => response(state(500))));
    const directClient = createJsonClient({ baseUrl: "/", fetchImpl: controlFetch });
    // The prior loadState delegates directly to JsonClient for every caller.
    const controlReads = Array.from({ length: 24 }, () => directClient.request("/api/v1/web/state", { headers: { Authorization: "Bearer token-a" } }));
    expect(controlFetch).toHaveBeenCalledTimes(24);
    controlGate.resolve();
    const controlResults = await Promise.all(controlReads);
    const pending = deferred<Response>();
    const fetch = vi.fn().mockReturnValueOnce(pending.promise).mockImplementation(async () => response(state(800)));
    const adapter = new BackendPreviewInterviewAdapter("/", fetch);
    const reads = Array.from({ length: 24 }, () => adapter.loadState());
    expect(fetch).toHaveBeenCalledTimes(1);
    pending.resolve(response(state(500)));
    const results = await Promise.all(reads);
    expect(results).toEqual(controlResults);
    expect(results.every(value => value.billing.balance === 500)).toBe(true);
    expect(new Set(results).size).toBe(24);
    (results[0]!.billing as { balance: number }).balance = 1;
    expect(results[1]!.billing.balance).toBe(500);
    expect((await adapter.loadState()).billing.balance).toBe(800);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("isolates adapters and anonymous/authenticated modes", async () => {
    store();
    const pending = [deferred<Response>(), deferred<Response>(), deferred<Response>()];
    const fetch = vi.fn().mockImplementationOnce(() => pending[0]!.promise).mockImplementationOnce(() => pending[1]!.promise).mockImplementationOnce(() => pending[2]!.promise);
    const adapter = new BackendPreviewInterviewAdapter("/a", fetch);
    const other = new BackendPreviewInterviewAdapter("/b", fetch);
    const reads = [adapter.loadState(), adapter.loadState(undefined, { auth: false }), other.loadState(), adapter.loadState(), adapter.loadState(undefined, { auth: false })];
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(new Headers(fetch.mock.calls[0]?.[1]?.headers).get("Authorization")).toBe("Bearer token-a");
    expect(new Headers(fetch.mock.calls[1]?.[1]?.headers).has("Authorization")).toBe(false);
    pending.forEach(item => item.resolve(response(state(50))));
    await Promise.all(reads);
  });

  it("isolates results on supported browsers without structuredClone", async () => {
    const payload = state(500);
    vi.stubGlobal("structuredClone", undefined);
    const pending = deferred<Response>();
    const fetch = vi.fn(() => pending.promise);
    const adapter = new BackendPreviewInterviewAdapter("/", fetch);
    const first = adapter.loadState();
    const second = adapter.loadState();
    pending.resolve(response(payload));
    const [a, b] = await Promise.all([first, second]);
    expect(a).toEqual(payload);
    expect(b).toEqual(payload);
    (a.billing as { balance: number }).balance = 1;
    expect(b.billing.balance).toBe(500);
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("does not let anonymous 401 responses acquire a stored Bearer", async () => {
    store();
    const refresh = vi.spyOn(authClient, "refresh");
    const fetch = vi.fn(async () => new Response(null, { status: 401 }));
    const adapter = new BackendPreviewInterviewAdapter("/", fetch);
    await expect(adapter.loadState(undefined, { auth: false })).rejects.toMatchObject({ status: 401 });
    expect(refresh).not.toHaveBeenCalled();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it.each(["getter", "getItem"] as const)("can load anonymous state when storage %s is blocked", async kind => {
    if (kind === "getter") Object.defineProperty(window, "localStorage", { configurable: true, get: () => { throw new DOMException("Blocked storage", "SecurityError"); } });
    else Object.defineProperty(window, "localStorage", { configurable: true, value: { getItem: () => { throw new DOMException("Blocked storage", "SecurityError"); } } });
    const fetch = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => response(state(5)));
    expect((await new BackendPreviewInterviewAdapter("/", fetch).loadState()).billing.balance).toBe(5);
    expect(new Headers(fetch.mock.calls[0]?.[1]?.headers).has("Authorization")).toBe(false);
    expect(authClient.readStoredSession()).toBeNull();
  });

  it("cancels one consumer without aborting the other", async () => {
    const pending = deferred<Response>();
    const fetch = vi.fn((_input: RequestInfo | URL, _init?: RequestInit) => pending.promise);
    const adapter = new BackendPreviewInterviewAdapter("/", fetch);
    const a = new AbortController();
    const first = adapter.loadState(a.signal);
    const rejected = expect(first).rejects.toMatchObject({ name: "AbortError" });
    const second = adapter.loadState();
    a.abort();
    await rejected;
    expect(fetch.mock.calls[0]?.[1]?.signal?.aborted).toBe(false);
    pending.resolve(response(state(77)));
    expect((await second).billing.balance).toBe(77);
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("releases an abandoned flight and lets the next read start fresh", async () => {
    const firstTransport = deferred<Response>();
    const secondTransport = deferred<Response>();
    const fetch = vi.fn().mockReturnValueOnce(firstTransport.promise).mockReturnValueOnce(secondTransport.promise);
    const adapter = new BackendPreviewInterviewAdapter("/", fetch);
    const a = new AbortController(); const b = new AbortController();
    const first = adapter.loadState(a.signal); const second = adapter.loadState(b.signal);
    const settled = Promise.allSettled([first, second]);
    a.abort(); b.abort();
    expect((await settled).every(item => item.status === "rejected")).toBe(true);
    expect(fetch.mock.calls[0]?.[1]?.signal?.aborted).toBe(true);
    const next = adapter.loadState();
    firstTransport.resolve(response(state(1)));
    const joined = adapter.loadState();
    expect(fetch).toHaveBeenCalledTimes(2);
    secondTransport.resolve(response(state(99)));
    expect((await Promise.all([next, joined])).map(item => item.billing.balance)).toEqual([99, 99]);
  });

  it("does not send an already cancelled read", async () => {
    const controller = new AbortController(); controller.abort();
    const fetch = vi.fn();
    await expect(new BackendPreviewInterviewAdapter("/", fetch).loadState(controller.signal)).rejects.toMatchObject({ name: "AbortError" });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("shares a failure without retaining it", async () => {
    const pending = deferred<Response>();
    const fetch = vi.fn().mockReturnValueOnce(pending.promise).mockImplementation(async () => response(state(3)));
    const adapter = new BackendPreviewInterviewAdapter("/", fetch);
    const all = Promise.allSettled([adapter.loadState(), adapter.loadState()]);
    pending.reject(new Error("synthetic-network"));
    expect((await all).every(item => item.status === "rejected")).toBe(true);
    expect((await adapter.loadState()).billing.balance).toBe(3);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it.each(["account", "token", "logout-login", "cross-tab"] as const)("rejects late state across %s scope changes", async kind => {
    store();
    const a = deferred<Response>(); const b = deferred<Response>();
    const fetch = vi.fn().mockReturnValueOnce(a.promise).mockReturnValueOnce(b.promise);
    const adapter = new BackendPreviewInterviewAdapter("/", fetch);
    const old = adapter.loadState();
    const oldRejected = expect(old).rejects.toMatchObject({ name: "AbortError" });
    if (kind === "account") store("user-b", "token-b");
    else if (kind === "token") store("user-a", "token-b");
    else if (kind === "logout-login") { authClient.clear(); authClient.acceptAuthorizedResult(tokens()); }
    else window.dispatchEvent(new StorageEvent("storage", { key: "offersteady.auth.access_token" }));
    const fresh = adapter.loadState();
    a.resolve(response(state(1)));
    await oldRejected;
    const join = adapter.loadState();
    expect(fetch).toHaveBeenCalledTimes(2);
    b.resolve(response(state(2)));
    expect((await Promise.all([fresh, join])).map(item => item.billing.balance)).toEqual([2, 2]);
  });

  it("retains legitimate same-session automatic 401 refresh", async () => {
    store();
    const refreshTransport = vi.fn(async (input: RequestInfo | URL) => String(input).includes("/auth/refresh") ? response(tokens("user-a", "fresh-token")) : response({ accepted: true }));
    vi.stubGlobal("fetch", refreshTransport);
    const fetch = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => new Headers(init?.headers).get("Authorization") === "Bearer fresh-token" ? response(state(123)) : new Response(null, { status: 401 }));
    const adapter = new BackendPreviewInterviewAdapter("/", fetch);
    const [a, b] = await Promise.all([adapter.loadState(), adapter.loadState()]);
    expect([a.billing.balance, b.billing.balance]).toEqual([123, 123]);
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(refreshTransport.mock.calls.filter(call => String(call[0]).includes("/auth/refresh"))).toHaveLength(1);
    expect(authClient.readStoredSession()?.accessToken).toBe("fresh-token");
  });

  it("recovers two independent wrappers when one refresh loses a same-session token rotation race", async () => {
    store();
    const refreshReplies = [deferred<Response>(), deferred<Response>()];
    let refreshCount = 0;
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => String(input).includes("/auth/refresh") ? refreshReplies[refreshCount++]!.promise : Promise.resolve(response({ accepted: true }))));
    const apiFetch = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => new Response(null, { status: new Headers(init?.headers).get("Authorization") === "Bearer fresh-token" ? 200 : 401 }));
    const a = createAuthRefreshingFetch(apiFetch); const b = createAuthRefreshingFetch(apiFetch);
    const first = a("/synthetic-a", { headers: { Authorization: "Bearer token-a" } });
    const second = b("/synthetic-b", { headers: { Authorization: "Bearer token-a" } });
    await vi.waitFor(() => expect(refreshCount).toBe(2));
    refreshReplies[0]!.resolve(response(tokens("user-a", "fresh-token")));
    expect((await first).status).toBe(200);
    refreshReplies[1]!.resolve(new Response(JSON.stringify({ success: false, data: null, error: { message: "合成旧刷新令牌失效" }, requestId: "synthetic", meta: {} }), { status: 401, headers: { "Content-Type": "application/json" } }));
    expect((await second).status).toBe(200);
    expect(apiFetch).toHaveBeenCalledTimes(4);
  });

  it("retains the original 401 when refresh fails without a newer token", async () => {
    store();
    const refresh = vi.fn(async () => { throw new Error("synthetic-refresh-failure"); });
    const fetch = vi.fn(async () => new Response(null, { status: 401 }));
    expect((await createAuthRefreshingFetch(fetch, refresh)("/synthetic", { headers: { Authorization: "Bearer token-a" } })).status).toBe(401);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("does not retry an old 401 with a switched identity", async () => {
    store();
    const reply = deferred<Response>();
    const fetch = vi.fn(() => reply.promise); const refresh = vi.fn(async () => undefined);
    const old = createAuthRefreshingFetch(fetch, refresh)("/synthetic", { headers: { Authorization: "Bearer token-a" } });
    const rejected = expect(old).rejects.toMatchObject({ name: "AbortError" });
    authClient.acceptAuthorizedResult(tokens("user-b", "token-b"));
    reply.resolve(new Response(null, { status: 401 }));
    await rejected;
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(refresh).not.toHaveBeenCalled();
  });

  it("does not resurrect a logged-out account when refresh returns late", async () => {
    store();
    const refreshReply = deferred<Response>();
    vi.stubGlobal("fetch", vi.fn(() => refreshReply.promise));
    const refresh = authClient.refresh();
    const rejected = expect(refresh).rejects.toMatchObject({ name: "AbortError" });
    authClient.clear();
    refreshReply.resolve(response(tokens("user-a", "fresh-token")));
    await rejected;
    expect(authClient.readStoredSession()).toBeNull();
  });

  it("does not overwrite a new identity after a late refresh or logout", async () => {
    store();
    const replies = [deferred<Response>(), deferred<Response>()];
    vi.stubGlobal("fetch", vi.fn().mockReturnValueOnce(replies[0]!.promise).mockReturnValueOnce(replies[1]!.promise).mockImplementation(async () => response({ accepted: true })));
    const refresh = authClient.refresh();
    const rejected = expect(refresh).rejects.toMatchObject({ name: "AbortError" });
    const logout = authClient.logout();
    authClient.acceptAuthorizedResult(tokens("user-b", "token-b"));
    replies[0]!.resolve(response(tokens("user-a", "old-refresh")));
    replies[1]!.resolve(response({ accepted: true }));
    await rejected; await logout;
    expect(authClient.readStoredSession()?.account.id).toBe("user-b");
  });

  it("does not write an old current-user response into a new account", async () => {
    store();
    const reply = deferred<Response>();
    vi.stubGlobal("fetch", vi.fn().mockReturnValueOnce(reply.promise).mockImplementation(async () => response({ accepted: true })));
    const old = authClient.currentUser();
    const rejected = expect(old).rejects.toMatchObject({ name: "AbortError" });
    authClient.clear(); authClient.acceptAuthorizedResult(tokens("user-b", "token-b"));
    reply.resolve(response(tokens().user));
    await rejected;
    expect(authClient.readStoredSession()?.account.id).toBe("user-b");
  });

  it("does not invalidate a pending read for a heartbeat or acknowledgement", async () => {
    const reply = deferred<Response>();
    const fetch = vi.fn().mockReturnValue(reply.promise);
    const adapter = new BackendPreviewInterviewAdapter("/", fetch);
    const read = adapter.loadState();
    const telemetry = createJsonClient({ baseUrl: "/", fetchImpl: vi.fn(async () => response({ accepted: true })) });
    await telemetry.request("/api/v1/realtime-speech/sessions/s/performance-ack", { method: "POST" });
    await telemetry.request("/api/v1/realtime-speech/sessions/s/web-heartbeat", { method: "POST" });
    const joined = adapter.loadState();
    expect(fetch).toHaveBeenCalledTimes(1);
    reply.resolve(response(state(8)));
    expect((await Promise.all([read, joined])).map(item => item.billing.balance)).toEqual([8, 8]);
  });

  it("makes explicit refresh bypass old work and keeps its late response from replacing the new flight", async () => {
    const oldReply = deferred<Response>(); const newReply = deferred<Response>();
    const fetch = vi.fn().mockReturnValueOnce(oldReply.promise).mockReturnValueOnce(newReply.promise);
    const adapter = new BackendPreviewInterviewAdapter("/", fetch);
    const old = adapter.loadState();
    const fresh = adapter.loadState(undefined, { forceRefresh: true });
    oldReply.resolve(response(state(1)));
    await flush();
    newReply.resolve(response(state(2)));
    expect((await Promise.all([old, fresh])).map(item => item.billing.balance)).toEqual([2, 2]);
  });

  it("bounds automatic rereads when state keeps changing", async () => {
    const first = deferred<Response>(); const second = deferred<Response>();
    const fetch = vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const adapter = new BackendPreviewInterviewAdapter("/", fetch);
    const read = adapter.loadState();
    const rejected = expect(read).rejects.toMatchObject({ name: "AbortError" });
    invalidateStateReads(); first.resolve(response(state(1)));
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    invalidateStateReads(); second.resolve(response(state(2)));
    await rejected;
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it.each(["document", "resume", "mock", "billing-lookup", "billing-sync"] as const)("keeps %s client updates outside an older flight", async kind => {
    store();
    const oldReply = deferred<Response>(); const freshReply = deferred<Response>();
    const stateFetch = vi.fn().mockReturnValueOnce(oldReply.promise).mockReturnValueOnce(freshReply.promise);
    const adapter = new BackendPreviewInterviewAdapter("/", stateFetch);
    const read = adapter.loadState();
    const mutationFetch = vi.fn(async () => response({ deleted: true }));
    if (kind === "document") await new BackendMaterialUploadAdapter("/", mutationFetch).deleteDocument("user-a", "synthetic-document");
    else if (kind === "resume") await new BackendResumeOptimizerClient("/", mutationFetch).remove("synthetic-job");
    else {
      const client = createJsonClient({ baseUrl: "/", fetchImpl: mutationFetch });
      if (kind === "mock") await client.request("/api/v1/mock-interviews/synthetic-session/end", { method: "POST" });
      if (kind === "billing-lookup") await client.request("/api/v1/billing/checkout-orders/synthetic-order");
      if (kind === "billing-sync") await client.request("/api/v1/billing/state");
    }
    const fresh = adapter.loadState();
    oldReply.resolve(response(state(1))); await flush(); freshReply.resolve(response(state(2)));
    expect((await Promise.all([read, fresh])).map(item => item.billing.balance)).toEqual([2, 2]);
    expect(stateFetch).toHaveBeenCalledTimes(2);
  });

  it("invalidates after an uncertain mutation failure and does not invalidate for telemetry", async () => {
    const oldReply = deferred<Response>(); const freshReply = deferred<Response>();
    const fetch = vi.fn().mockReturnValueOnce(oldReply.promise).mockReturnValueOnce(freshReply.promise);
    const adapter = new BackendPreviewInterviewAdapter("/", fetch);
    const read = adapter.loadState();
    const client = createJsonClient({ baseUrl: "/", fetchImpl: vi.fn(async () => { throw new Error("synthetic-disconnect"); }) });
    await expect(client.request("/api/v1/documents/synthetic-document", { method: "DELETE" })).rejects.toMatchObject({ code: "network" });
    const telemetry = createJsonClient({ baseUrl: "/", fetchImpl: vi.fn(async () => response({ accepted: true })) });
    await telemetry.request("/api/v1/realtime-speech/sessions/synthetic-session/performance-ack", { method: "POST" });
    const fresh = adapter.loadState();
    oldReply.resolve(response(state(1))); await flush(); freshReply.resolve(response(state(2)));
    expect((await Promise.all([read, fresh])).map(item => item.billing.balance)).toEqual([2, 2]);
    expect(fetch).toHaveBeenCalledTimes(2);
  });
});
