import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { interviewAppAdapter } from "./app-adapter";
import { authClient, type StoredAuthSession } from "./auth-client";
import { syntheticState } from "./test-state";

const session: StoredAuthSession = {
  accessToken: "synthetic-access",
  refreshToken: "synthetic-refresh",
  account: syntheticState.account,
};

const deferred = <T,>() => {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((next, fail) => { resolve = next; reject = fail; });
  return { promise, resolve, reject };
};

afterEach(() => vi.restoreAllMocks());

describe("application initialization", () => {
  it("waits for saved-session restoration before making the sole protected state request", async () => {
    const restoration = deferred<StoredAuthSession>();
    vi.spyOn(authClient, "readStoredSession").mockReturnValue(session);
    vi.spyOn(authClient, "restore").mockReturnValue(restoration.promise);
    const loadState = vi.spyOn(interviewAppAdapter, "loadState").mockResolvedValue(structuredClone(syntheticState));
    window.history.pushState({}, "", "/app");
    render(<App />);

    expect(screen.getByRole("status", { name: "页面加载中" })).toBeEmptyDOMElement();
    expect(screen.queryByText("正在安全加载")).not.toBeInTheDocument();
    expect(screen.queryByText("后端页面状态无法加载")).not.toBeInTheDocument();
    expect(loadState).not.toHaveBeenCalled();

    await act(async () => restoration.resolve(session));
    expect(await screen.findByRole("heading", { name: "继续这场面试" })).toBeInTheDocument();
    expect(loadState).toHaveBeenCalledTimes(1);
  });

  it("loads public state directly when no saved session exists", async () => {
    vi.spyOn(authClient, "readStoredSession").mockReturnValue(null);
    vi.spyOn(authClient, "restore");
    const loadState = vi.spyOn(interviewAppAdapter, "loadState").mockResolvedValue(structuredClone(syntheticState));
    window.history.pushState({}, "", "/");
    render(<App />);

    expect(await screen.findByRole("heading", { name: /AI 面试助手/ })).toBeInTheDocument();
    expect(authClient.restore).not.toHaveBeenCalled();
    expect(loadState).toHaveBeenCalledTimes(1);
    expect(loadState.mock.calls[0]?.[1]).toEqual({ auth: true });
  });

  it("shows the backend error only when the final saved-session initialization fails", async () => {
    const restoration = deferred<StoredAuthSession>();
    vi.spyOn(authClient, "readStoredSession").mockReturnValue(session);
    vi.spyOn(authClient, "restore").mockReturnValue(restoration.promise);
    const loadState = vi.spyOn(interviewAppAdapter, "loadState").mockResolvedValue(structuredClone(syntheticState));
    window.history.pushState({}, "", "/app");
    render(<App />);

    expect(screen.queryByText("后端页面状态无法加载")).not.toBeInTheDocument();
    await act(async () => restoration.reject(new Error("会话恢复失败")));
    expect(await screen.findByText("后端页面状态无法加载")).toBeInTheDocument();
    expect(screen.getByText(/会话恢复失败/)).toBeInTheDocument();
    expect(loadState).not.toHaveBeenCalled();
  });
});
