import { Suspense, useState } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PrototypeContext, usePrototype } from "./app-context";
import type { WebAppState } from "./domain";
import { LivePage, loadLivePage, preloadLivePage } from "./live-route-loader";
import { fixtureAdapter, syntheticState } from "./test-state";

vi.mock("./app-adapter", async () => {
  const { fixtureAdapter } = await import("./test-state");
  return { interviewAppAdapter: fixtureAdapter };
});

// The ordinary App tests alias this barrel to eager routes. Keep this suite on
// the production barrel, including the nested lazy answer renderer.
vi.mock("./route-components", () => vi.importActual("./route-components.ts"));

const contextTitle = "延迟加载上下文面试（合成）";
const manualQuestion = "请解释这个合成项目的缓存失效策略。";

function SharedStateProbe() {
  const { state } = usePrototype();
  return <output aria-label="共享上下文状态">
    {state.account.displayName} | {state.captureState} | {state.questions[0]?.text} | {state.activeAnswerTask?.status}
  </output>;
}

function LiveHarness() {
  const [state, setState] = useState<WebAppState>(() => {
    const initial = structuredClone(syntheticState);
    return {
      ...initial,
      account: { ...initial.account, displayName: "延迟路由合成用户" },
      interviews: initial.interviews.map(interview => interview.id === "demo"
        ? { ...interview, title: contextTitle, status: "active", autoAnswerEnabled: false }
        : interview),
      captureState: "capturing",
      questions: [],
      activeAnswerTask: null,
      speaker: { ...initial.speaker, transcripts: [], pendingQuestion: null },
    };
  });
  return <PrototypeContext.Provider value={{ authenticated: true, setAuthenticated: () => undefined, state, setState, logout: async () => undefined }}>
    <SharedStateProbe />
    <MemoryRouter initialEntries={["/app/interviews/demo/live"]}>
      <Suspense fallback={<div role="status">正在加载真实面试工作台</div>}>
        <Routes>
          <Route path="/app/interviews/:id/live" element={<LivePage brand={<span>合成品牌插槽</span>} accountMenu={<span>合成账号菜单</span>} />} />
        </Routes>
      </Suspense>
    </MemoryRouter>
  </PrototypeContext.Provider>;
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Network access is disabled in lazy-route tests")));
  // Use the single-page lifecycle, without Node's cross-test BroadcastChannel.
  vi.stubGlobal("BroadcastChannel", undefined);
  Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
  vi.spyOn(fixtureAdapter, "loadInterviewWorkspace").mockResolvedValue({ questions: [], activeAnswerTask: null });
  vi.spyOn(fixtureAdapter, "subscribeRealtimeSession").mockImplementation((_id, _onUpdate, signal) => new Promise<void>(resolve => {
    if (signal?.aborted) resolve();
    else signal?.addEventListener("abort", () => resolve(), { once: true });
  }));
});

afterEach(() => {
  cleanup();
  expect(fetch).not.toHaveBeenCalled();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("real lazy live route", () => {
  it("shares concurrent imports and preloads modules without starting a live session", async () => {
    const businessCalls = [
      "createDraft", "startInterviewSession", "controlInterviewCapture",
      "submitManualAnswer", "submitScreenshotAnswer", "bindDesktopDevice",
      "sendDesktopSessionHeartbeat", "loadRealtimeSession", "getInterviewIdleStatus",
      "loadDesktopShortcutScreenshotUpdates",
    ] as const;
    const spies = businessCalls.map(method => vi.spyOn(fixtureAdapter, method));

    const firstLoad = loadLivePage();
    const concurrentLoad = loadLivePage();
    expect(concurrentLoad).toBe(firstLoad);
    await Promise.all([preloadLivePage(), preloadLivePage()]);
    const loaded = await firstLoad;

    expect(loaded.LivePage).toEqual(expect.any(Function));
    expect(loadLivePage()).toBe(firstLoad);
    for (const spy of spies) expect(spy).not.toHaveBeenCalled();
    expect(fixtureAdapter.loadInterviewWorkspace).not.toHaveBeenCalled();
    expect(fixtureAdapter.subscribeRealtimeSession).not.toHaveBeenCalled();
    expect(screen.queryByRole("main")).not.toBeInTheDocument();
  });

  it("resolves through Suspense and shares context for manual answers and pause/resume controls", async () => {
    const submit = vi.spyOn(fixtureAdapter, "submitManualAnswer");
    const controlCapture = vi.spyOn(fixtureAdapter, "controlInterviewCapture");
    render(<LiveHarness />);

    expect(screen.getByRole("status", { name: "" })).toHaveTextContent("正在加载真实面试工作台");
    expect(await screen.findByText(contextTitle)).toBeInTheDocument();
    expect(screen.queryByText("正在加载真实面试工作台")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "返回面试首页" })).toHaveTextContent("合成品牌插槽");
    expect(screen.getByText("合成账号菜单")).toBeInTheDocument();
    expect(screen.getByLabelText("共享上下文状态")).toHaveTextContent("延迟路由合成用户");
    expect(screen.getByRole("switch", { name: "自动回答" })).not.toBeChecked();
    expect(screen.getByRole("button", { name: "结束面试" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "截屏回答" })).toBeEnabled();
    expect(submit).not.toHaveBeenCalled();

    fireEvent.change(screen.getByRole("textbox", { name: "手动输入面试官的问题" }), { target: { value: manualQuestion } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));

    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));
    expect(submit).toHaveBeenCalledWith(expect.objectContaining({ interviewId: "demo", question: manualQuestion }), expect.any(AbortSignal), expect.any(Function));
    expect(await screen.findByRole("heading", { level: 1, name: manualQuestion })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText("共享上下文状态")).toHaveTextContent("completed"));
    expect(screen.getByLabelText("共享上下文状态")).toHaveTextContent(manualQuestion);
    expect(screen.getByLabelText("回答正文")).toHaveTextContent(manualQuestion);

    fireEvent.click(screen.getByRole("button", { name: "暂停收音" }));
    expect(await screen.findByRole("button", { name: "恢复收音" })).toBeEnabled();
    expect(controlCapture).toHaveBeenNthCalledWith(1, "demo", "pause", expect.any(AbortSignal));
    expect(screen.getByLabelText("共享上下文状态")).toHaveTextContent("paused");
    fireEvent.click(screen.getByRole("button", { name: "恢复收音" }));
    expect(await screen.findByRole("button", { name: "暂停收音" })).toBeEnabled();
    expect(controlCapture).toHaveBeenNthCalledWith(2, "demo", "resume", expect.any(AbortSignal));
    expect(screen.getByLabelText("共享上下文状态")).toHaveTextContent("capturing");
  });

  it("aborts in-flight work, clears polling and removes wake-up handlers when unmounted", async () => {
    const heartbeat = vi.spyOn(fixtureAdapter, "sendDesktopSessionHeartbeat");
    const idleStatus = vi.spyOn(fixtureAdapter, "getInterviewIdleStatus");
    const shortcuts = vi.spyOn(fixtureAdapter, "loadDesktopShortcutScreenshotUpdates");
    const setIntervalSpy = vi.spyOn(window, "setInterval");
    const clearIntervalSpy = vi.spyOn(window, "clearInterval");
    const submit = vi.spyOn(fixtureAdapter, "submitManualAnswer").mockImplementation((_command, signal) => new Promise((_resolve, reject) => {
      signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
    }));
    const { unmount } = render(<LiveHarness />);
    await screen.findByText(contextTitle);
    await waitFor(() => expect(fixtureAdapter.subscribeRealtimeSession).toHaveBeenCalledTimes(1));
    fireEvent.change(screen.getByRole("textbox", { name: "手动输入面试官的问题" }), { target: { value: manualQuestion } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    await waitFor(() => expect(submit).toHaveBeenCalledTimes(1));

    const streamSignal = vi.mocked(fixtureAdapter.subscribeRealtimeSession).mock.calls[0]![2]!;
    const manualSignal = submit.mock.calls[0]![1]!;
    const workspaceSignal = vi.mocked(fixtureAdapter.loadInterviewWorkspace).mock.calls[0]![1]!;
    // Claiming the live lease replaces the initial idle/shortcut controllers.
    // Verify the currently active requests, not those already cleaned up.
    const idleSignal = idleStatus.mock.calls.at(-1)![1]!;
    const shortcutSignal = shortcuts.mock.calls.at(-1)![1]!;
    const signals = [streamSignal, manualSignal, workspaceSignal, idleSignal, shortcutSignal];
    for (const signal of signals) expect(signal.aborted).toBe(false);
    const intervalIds = setIntervalSpy.mock.results.filter(result => result.type === "return").map(result => result.value);
    expect(intervalIds.length).toBeGreaterThanOrEqual(3);

    await act(async () => unmount());

    for (const signal of signals) expect(signal.aborted).toBe(true);
    for (const intervalId of intervalIds) expect(clearIntervalSpy).toHaveBeenCalledWith(intervalId);
    const watchedCalls = [heartbeat, idleStatus, shortcuts, vi.mocked(fixtureAdapter.loadInterviewWorkspace), vi.mocked(fixtureAdapter.subscribeRealtimeSession)];
    const callCounts = watchedCalls.map(spy => spy.mock.calls.length);
    await act(async () => {
      window.dispatchEvent(new Event("focus"));
      window.dispatchEvent(new Event("online"));
      window.dispatchEvent(new Event("pageshow"));
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(watchedCalls.map(spy => spy.mock.calls.length)).toEqual(callCounts);
    expect(screen.queryByRole("main")).not.toBeInTheDocument();
  });
});
