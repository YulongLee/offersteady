import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { authClient } from "./auth-client";
import { createAuthRefreshingFetch } from "./backend-adapter";

const storedValues = new Map<string, string>();

beforeAll(() => {
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: {
      clear: () => storedValues.clear(),
      getItem: (key: string) => storedValues.get(key) ?? null,
      key: (index: number) => [...storedValues.keys()][index] ?? null,
      get length() { return storedValues.size; },
      removeItem: (key: string) => storedValues.delete(key),
      setItem: (key: string, value: string) => storedValues.set(key, value),
    } satisfies Storage,
  });
});

const storeSession = (accessToken: string) => {
  window.localStorage.setItem("offersteady.auth.access_token", accessToken);
  window.localStorage.setItem("offersteady.auth.refresh_token", "refresh-token");
  window.localStorage.setItem("offersteady.auth.account", JSON.stringify({
    id: "user-1",
    displayName: "测试用户",
    createdAtMs: 1,
    bindings: [],
  }));
};

describe("auth refreshing fetch", () => {
  beforeEach(() => storedValues.clear());

  it("refreshes once and retries a request with the rotated access token", async () => {
    storeSession("expired-token");
    const fetchImpl = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const authorization = new Headers(init?.headers).get("Authorization");
      return new Response(null, { status: authorization === "Bearer fresh-token" ? 200 : 401 });
    });
    const refresh = vi.fn(async () => {
      storeSession("fresh-token");
    });
    const refreshingFetch = createAuthRefreshingFetch(fetchImpl as typeof fetch, refresh);

    const response = await refreshingFetch("/runtime", {
      headers: { Authorization: "Bearer expired-token" },
    });

    expect(response.status).toBe(200);
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });

  it("shares one refresh across concurrent unauthorized realtime requests", async () => {
    storeSession("expired-token");
    const fetchImpl = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const authorization = new Headers(init?.headers).get("Authorization");
      return new Response(null, { status: authorization === "Bearer fresh-token" ? 200 : 401 });
    });
    let releaseRefresh: (() => void) | undefined;
    const refresh = vi.fn(() => new Promise<void>((resolve) => {
      releaseRefresh = () => {
        storeSession("fresh-token");
        resolve();
      };
    }));
    const refreshingFetch = createAuthRefreshingFetch(fetchImpl as typeof fetch, refresh);
    const requests = [
      refreshingFetch("/runtime", { headers: { Authorization: "Bearer expired-token" } }),
      refreshingFetch("/stream", { headers: { Authorization: "Bearer expired-token" } }),
    ];
    await vi.waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
    releaseRefresh?.();

    const responses = await Promise.all(requests);

    expect(responses.map((response) => response.status)).toEqual([200, 200]);
    expect(authClient.readStoredSession()?.accessToken).toBe("fresh-token");
  });
});
