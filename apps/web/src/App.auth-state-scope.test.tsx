import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { authClient, type StoredAuthSession } from "./auth-client";
import { interviewAppAdapter } from "./app-adapter";
import { syntheticState } from "./test-state";

describe("application authentication freshness", () => {
  beforeEach(() => {
    const values = new Map<string, string>();
    Object.defineProperty(window, "localStorage", { configurable: true, value: {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key),
    } });
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ success: true, data: { accepted: true }, requestId: "synthetic", meta: {} }), { headers: { "Content-Type": "application/json" } })));
    authClient.clear();
    authClient.acceptAuthorizedResult({ user: { userId: "user-a", displayName: "合成账号A", createdAtMs: 1, bindings: [] }, tokens: { accessToken: "access-a", refreshToken: "refresh-a" } });
    window.history.pushState({}, "", "/app");
  });
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

  it.each(["restore", "loadState"] as const)("does not clear a newer login after a cancelled %s", async stage => {
    let reject!: (error: unknown) => void;
    const pending = new Promise<never>((_resolve, no) => { reject = no; });
    const clear = vi.spyOn(authClient, "clear");
    const restore = vi.spyOn(authClient, "restore").mockImplementation(async () => stage === "restore" ? pending : authClient.readStoredSession() as StoredAuthSession);
    const loadState = vi.spyOn(interviewAppAdapter, "loadState").mockImplementation(() => pending);
    const view = render(<App />);
    await waitFor(() => expect(stage === "restore" ? restore : loadState).toHaveBeenCalledOnce());
    authClient.acceptAuthorizedResult({ user: { userId: "user-b", displayName: "合成账号B", createdAtMs: 1, bindings: [] }, tokens: { accessToken: "access-b", refreshToken: "refresh-b" } });
    await act(async () => { reject(new DOMException("State superseded", "AbortError")); });
    expect(clear).not.toHaveBeenCalled();
    expect(authClient.readStoredSession()?.account.id).toBe("user-b");
    view.unmount();
  });

  it("makes the explicit initial retry request fresh state", async () => {
    vi.spyOn(authClient, "restore").mockImplementation(async () => authClient.readStoredSession() as StoredAuthSession);
    const loadState = vi.spyOn(interviewAppAdapter, "loadState").mockRejectedValueOnce(new Error("合成网络失败")).mockResolvedValue(structuredClone(syntheticState));
    const view = render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "立即重试" }));
    await waitFor(() => expect(loadState).toHaveBeenCalledTimes(2));
    expect(loadState.mock.calls[1]?.[1]).toEqual({ forceRefresh: true });
    view.unmount();
  });

  it("immediately recovers the current identity after one superseded initialization", async () => {
    let reject!: (error: unknown) => void;
    const pending = new Promise<never>((_resolve, no) => { reject = no; });
    const restore = vi.spyOn(authClient, "restore").mockReturnValueOnce(pending).mockImplementation(async () => authClient.readStoredSession() as StoredAuthSession);
    const loadState = vi.spyOn(interviewAppAdapter, "loadState").mockResolvedValue(structuredClone(syntheticState));
    const view = render(<App />);
    await waitFor(() => expect(restore).toHaveBeenCalledOnce());
    authClient.acceptAuthorizedResult({ user: { userId: "user-b", displayName: "合成账号B", createdAtMs: 1, bindings: [] }, tokens: { accessToken: "access-b", refreshToken: "refresh-b" } });
    await act(async () => { reject(new DOMException("Superseded", "AbortError")); });
    await waitFor(() => expect(loadState).toHaveBeenCalledOnce());
    expect(restore).toHaveBeenCalledTimes(2);
    expect(screen.queryByText("后端页面状态暂时无法加载")).not.toBeInTheDocument();
    expect(authClient.readStoredSession()?.account.id).toBe("user-b");
    view.unmount();
  });

  it("does not restart initialization after effect cleanup cancels it", async () => {
    let reject!: (error: unknown) => void;
    const restore = vi.spyOn(authClient, "restore").mockImplementation(() => new Promise<never>((_resolve, no) => { reject = no; }));
    const loadState = vi.spyOn(interviewAppAdapter, "loadState");
    const view = render(<App />);
    await waitFor(() => expect(restore).toHaveBeenCalledOnce());
    view.unmount();
    await act(async () => { reject(new DOMException("Unmounted", "AbortError")); });
    expect(restore).toHaveBeenCalledOnce();
    expect(loadState).not.toHaveBeenCalled();
  });
});
