import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { authClient } from "./auth-client";

const save = (id: string) => {
  localStorage.setItem("offersteady.auth.access_token", `access-${id}`);
  localStorage.setItem("offersteady.auth.refresh_token", `refresh-${id}`);
  localStorage.setItem("offersteady.auth.account", JSON.stringify({ id, displayName: id, createdAtMs: 1, bindings: [] }));
};
const response = (data: unknown) => new Response(JSON.stringify({ success: true, data, requestId: "synthetic", meta: {} }), { status: 200, headers: { "content-type": "application/json" } });

describe("cancelled authentication restoration", () => {
  beforeEach(() => { localStorage.clear(); save("old"); });
  afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); });

  it("does not refresh when a current-user request was aborted", async () => {
    const controller = new AbortController();
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => {
      controller.abort();
      throw new DOMException("aborted", "AbortError");
    });
    await expect(authClient.restore(controller.signal)).rejects.toHaveProperty("name", "AbortError");
    expect(fetch).toHaveBeenCalledOnce();
  });

  it.each(["aborted", "new-login"])("ignores late current-user data after %s", async reason => {
    const controller = new AbortController();
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => {
      if (reason === "aborted") controller.abort();
      save("new");
      return response({ userId: "old", displayName: "Old account", createdAtMs: 1, bindings: [] });
    });
    await expect(authClient.restore(controller.signal)).rejects.toHaveProperty("name", "AbortError");
    expect(authClient.readStoredSession()?.account.id).toBe("new");
    expect(fetch).toHaveBeenCalledOnce();
  });

  it.each(["aborted", "new-login"])("ignores late refresh credentials after %s", async reason => {
    const controller = new AbortController();
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => {
      if (reason === "aborted") controller.abort();
      save("new");
      return response({ user: { userId: "old", displayName: "Old account", createdAtMs: 1, bindings: [] }, tokens: { accessToken: "stale-access", refreshToken: "stale-refresh" } });
    });
    await expect(authClient.refresh(controller.signal)).rejects.toHaveProperty("name", "AbortError");
    expect(authClient.readStoredSession()?.accessToken).toBe("access-new");
    expect(fetch).toHaveBeenCalledOnce();
  });
});
