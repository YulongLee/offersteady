import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { interviewAppAdapter } from "./app-adapter";
import { PrototypeContext } from "./app-context";
import type { CollectedScreenshot, SubmitManualAnswerResult, WebAppState } from "./domain";
import { LivePage } from "./LivePage";
import { FixtureInterviewAdapter, syntheticState } from "./test-state";

const deferred = <T,>() => {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((accept, fail) => { resolve = accept; reject = fail; });
  return { promise, resolve, reject };
};
const image = (number: number): CollectedScreenshot => ({ requestId: `capture-${number}`, imageId: `image-${number}`, name: `合成页面 ${number}` });
const result = (): SubmitManualAnswerResult => ({
  question: { ...syntheticState.questions[0]!, id: "batch-answer", text: "合成多图题目", input: "screenshot", status: "confirmed", advice: { ...syntheticState.questions[0]!.advice, detail: "合成多图回答" } },
  task: { id: "batch-answer", interviewId: "demo", userId: "admin", billingUsageId: "screenshot-answer:batch-answer", questionId: "batch-answer", question: "合成多图题目", revision: 1, status: "completed", completedText: "合成多图回答", updatedAtMs: Date.now() },
});
function Workspace({ mode = "written" }: { mode?: "written" | "interview" }) {
  const [state, setState] = useState<WebAppState>(() => {
    const next = structuredClone(syntheticState);
    next.interviews = [{ ...next.interviews.find(item => item.id === "demo")!, sessionMode: mode, status: "active" }];
    next.questions = [];
    return next;
  });
  return <PrototypeContext.Provider value={{ state, setState, authenticated: true, setAuthenticated: () => undefined, logout: async () => undefined }}><MemoryRouter initialEntries={["/app/interviews/demo/live"]}><Routes><Route path="/app/interviews/:id/live" element={<LivePage brand="面试稳" accountMenu={<span>用户</span>} />} /><Route path="*" element={<div>已离开工作台</div>} /></Routes></MemoryRouter></PrototypeContext.Provider>;
}
const enable = async () => {
  fireEvent.click(screen.getByRole("switch", { name: "多屏回答" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "截屏" })).not.toBeDisabled());
};
const capture = async (count: number) => {
  fireEvent.click(screen.getByRole("button", { name: "截屏" }));
  await screen.findByText(`已截取 ${count} / 4 张`);
};

beforeEach(() => {
  const fixture = new FixtureInterviewAdapter();
  for (const method of Object.getOwnPropertyNames(FixtureInterviewAdapter.prototype)) {
    if (method === "constructor") continue;
    const methods = fixture as unknown as Record<string, (...args: never[]) => unknown>;
    const target = interviewAppAdapter as unknown as Record<string, (...args: never[]) => unknown>;
    const implementation = methods[method];
    if (typeof implementation === "function" && typeof target[method] === "function") vi.spyOn(target, method).mockImplementation(implementation.bind(fixture));
  }
  vi.spyOn(interviewAppAdapter, "loadInterviewWorkspace").mockResolvedValue({ questions: [], activeAnswerTask: null });
  vi.spyOn(interviewAppAdapter, "getScreenshotCapturePolicy").mockResolvedValue({ maxImagesPerTask: 4 });
  let count = 0;
  vi.spyOn(interviewAppAdapter, "captureScreenshot").mockImplementation(async () => image(++count));
  vi.spyOn(interviewAppAdapter, "submitScreenshotBatch").mockImplementation(async () => result());
  vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("No network in synthetic tests"))));
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("written multi-screen answering", () => {
  it("starts off and retains the original single-screen answer flow", async () => {
    render(<Workspace />);
    expect(screen.getByRole("switch", { name: "多屏回答" })).not.toBeChecked();
    fireEvent.click(screen.getByRole("button", { name: "截屏回答" }));
    await waitFor(() => expect(interviewAppAdapter.submitScreenshotAnswer).toHaveBeenCalledOnce());
    expect(interviewAppAdapter.captureScreenshot).not.toHaveBeenCalled();
    expect(interviewAppAdapter.submitScreenshotBatch).not.toHaveBeenCalled();
  });

  it("collects in order without answering and submits exactly once", async () => {
    render(<Workspace />);
    await enable();
    expect(screen.getByRole("button", { name: "回答" })).toBeDisabled();
    await capture(1);
    await capture(2);
    expect(interviewAppAdapter.submitScreenshotBatch).not.toHaveBeenCalled();
    expect(interviewAppAdapter.submitScreenshotAnswer).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "回答" }));
    fireEvent.click(screen.getByRole("button", { name: "回答" }));
    await screen.findByText("合成多图回答");
    expect(interviewAppAdapter.submitScreenshotBatch).toHaveBeenCalledOnce();
    expect(interviewAppAdapter.submitScreenshotBatch).toHaveBeenCalledWith(expect.objectContaining({ interviewId: "demo", captureRequestIds: ["capture-1", "capture-2"] }), expect.any(AbortSignal), expect.any(Function), expect.any(Function));
    expect(screen.getByRole("button", { name: "回答" })).toBeDisabled();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("limits captures and removes an item without changing remaining order", async () => {
    render(<Workspace />);
    await enable();
    for (let n = 1; n <= 4; n++) await capture(n);
    expect(screen.getByRole("button", { name: "截屏" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "移除截图 2" }));
    expect(interviewAppAdapter.cancelDesktopShortcutScreenshot).toHaveBeenCalledWith("capture-2");
    expect(screen.getByRole("button", { name: "截屏" })).not.toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "回答" }));
    await waitFor(() => expect(interviewAppAdapter.submitScreenshotBatch).toHaveBeenCalledWith(expect.objectContaining({ captureRequestIds: ["capture-1", "capture-3", "capture-4"] }), expect.anything(), expect.anything(), expect.anything()));
  });

  it("uses the backend policy limit and blocks capture against an unsupported backend", async () => {
    vi.mocked(interviewAppAdapter.getScreenshotCapturePolicy!).mockResolvedValueOnce({ maxImagesPerTask: 2 });
    const view = render(<Workspace />);
    await enable();
    for (let n = 1; n <= 2; n++) { fireEvent.click(screen.getByRole("button", { name: "截屏" })); await screen.findByText(`已截取 ${n} / 2 张`); }
    expect(screen.getByRole("button", { name: "截屏" })).toBeDisabled();
    view.unmount();
    vi.mocked(interviewAppAdapter.getScreenshotCapturePolicy!).mockRejectedValueOnce(new Error("后端尚未支持多屏截屏"));
    render(<Workspace />);
    fireEvent.click(screen.getByRole("switch", { name: "多屏回答" }));
    await screen.findByText("后端尚未支持多屏截屏");
    expect(screen.getByRole("button", { name: "截屏" })).toBeDisabled();
  });

  it("keeps ready captures on capture failure and serializes clicks", async () => {
    render(<Workspace />);
    await enable();
    await capture(1);
    const pending = deferred<CollectedScreenshot>();
    vi.mocked(interviewAppAdapter.captureScreenshot!).mockReturnValueOnce(pending.promise);
    fireEvent.click(screen.getByRole("button", { name: "截屏" }));
    fireEvent.click(screen.getByRole("button", { name: "截屏" }));
    expect(interviewAppAdapter.captureScreenshot).toHaveBeenCalledTimes(2);
    expect(screen.getByRole("button", { name: "回答" })).toBeDisabled();
    await act(async () => pending.reject(new Error("屏幕权限暂不可用")));
    await screen.findByText("屏幕权限暂不可用");
    expect(within(screen.getByRole("list", { name: "待回答截图" })).getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "回答" })).not.toBeDisabled();
  });

  it("releases captures when switching off and ignores a late capture", async () => {
    render(<Workspace />);
    await enable();
    await capture(1);
    const pending = deferred<CollectedScreenshot>();
    vi.mocked(interviewAppAdapter.captureScreenshot!).mockReturnValueOnce(pending.promise);
    fireEvent.click(screen.getByRole("button", { name: "截屏" }));
    const signal = vi.mocked(interviewAppAdapter.captureScreenshot!).mock.calls.at(-1)![1];
    fireEvent.click(screen.getByRole("switch", { name: "多屏回答" }));
    expect(signal?.aborted).toBe(true);
    await act(async () => pending.resolve(image(2)));
    expect(interviewAppAdapter.cancelDesktopShortcutScreenshot).toHaveBeenCalledWith("capture-1");
    expect(interviewAppAdapter.cancelDesktopShortcutScreenshot).toHaveBeenCalledWith("capture-2");
    expect(screen.queryByRole("list", { name: "待回答截图" })).not.toBeInTheDocument();
    await enable();
    expect(screen.getByText("已截取 0 / 4 张")).toBeInTheDocument();
  });

  it("discards submitted captures on failure and explains recapture", async () => {
    vi.mocked(interviewAppAdapter.submitScreenshotBatch!).mockRejectedValueOnce(new Error("截图已过期"));
    render(<Workspace />);
    await enable();
    await capture(1);
    fireEvent.click(screen.getByRole("button", { name: "回答" }));
    await screen.findAllByText("截图已过期 请重新截屏后再回答。");
    expect(screen.getByRole("button", { name: "回答" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "截屏" })).not.toBeDisabled();
    expect(interviewAppAdapter.submitScreenshotBatch).toHaveBeenCalledOnce();
  });

  it("cancels an in-flight batch and prevents late completion from reviving it", async () => {
    const pending = deferred<SubmitManualAnswerResult>();
    vi.mocked(interviewAppAdapter.submitScreenshotBatch!).mockReturnValueOnce(pending.promise);
    render(<Workspace />);
    await enable(); await capture(1);
    fireEvent.click(screen.getByRole("button", { name: "回答" }));
    expect(screen.getByRole("switch", { name: "多屏回答" })).toBeDisabled();
    const signal = vi.mocked(interviewAppAdapter.submitScreenshotBatch!).mock.calls[0]![1];
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "取消" }));
    expect(signal?.aborted).toBe(true);
    await act(async () => pending.resolve(result()));
    expect(screen.queryByText("合成多图回答")).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "回答" })).toBeDisabled();
  });

  it("releases pending captures on unmount and successful ending", async () => {
    const view = render(<Workspace />); await enable(); await capture(1); view.unmount();
    expect(interviewAppAdapter.cancelDesktopShortcutScreenshot).toHaveBeenCalledWith("capture-1");
    vi.mocked(interviewAppAdapter.cancelDesktopShortcutScreenshot).mockClear();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<Workspace />); await enable(); await capture(1);
    fireEvent.click(screen.getByRole("button", { name: "结束笔试" }));
    await screen.findByText("已离开工作台");
    expect(interviewAppAdapter.cancelDesktopShortcutScreenshot).toHaveBeenCalledWith("capture-2");
  });

  it("clears ready captures when the page lease is replaced", async () => {
    const subscription = deferred<void>();
    vi.mocked(interviewAppAdapter.subscribeRealtimeSession).mockReturnValueOnce(subscription.promise);
    render(<Workspace />); await enable(); await capture(1);
    await waitFor(() => expect(interviewAppAdapter.subscribeRealtimeSession).toHaveBeenCalled());
    await act(async () => subscription.reject(new Error("会话已在其他页面继续 (409)")));
    await screen.findByText("本场笔试已在其他页面继续");
    expect(interviewAppAdapter.cancelDesktopShortcutScreenshot).toHaveBeenCalledWith("capture-1");
    expect(screen.queryByRole("list", { name: "待回答截图" })).not.toBeInTheDocument();
    expect(screen.getByRole("switch", { name: "多屏回答" })).toBeDisabled();
  });

  it("keeps pending captures if ending fails", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(interviewAppAdapter.endInterviewSession).mockRejectedValueOnce(new Error("结束暂不可用"));
    render(<Workspace />); await enable(); await capture(1);
    fireEvent.click(screen.getByRole("button", { name: "结束笔试" }));
    await screen.findByText("结束暂不可用");
    expect(screen.getByText("已截取 1 / 4 张")).toBeInTheDocument();
    expect(interviewAppAdapter.cancelDesktopShortcutScreenshot).not.toHaveBeenCalled();
  });

  it("marks a streamed batch failed instead of leaving it generating and does not replay on retry", async () => {
    const pending = deferred<SubmitManualAnswerResult>();
    vi.mocked(interviewAppAdapter.submitScreenshotBatch!).mockImplementationOnce(async (_command, _signal, _stage, onUpdate) => {
      const partial = result();
      onUpdate?.({ ...partial, task: { ...partial.task, status: "generating", partialText: "合成部分回答" } });
      return pending.promise;
    });
    render(<Workspace />); await enable(); await capture(1);
    fireEvent.click(screen.getByRole("button", { name: "回答" }));
    await act(async () => pending.reject(new Error("连接已断开")));
    await screen.findByText("回答生成失败");
    expect(screen.queryByRole("button", { name: "终止回答" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "重试" }));
    await screen.findByText("本次截图已提交，请重新截屏后再回答。");
    expect(interviewAppAdapter.submitScreenshotBatch).toHaveBeenCalledOnce();
    expect(screen.getByText("回答生成失败")).toBeInTheDocument();
  });

  it("routes the page shortcut to collection only while enabled", async () => {
    render(<Workspace />); await enable();
    fireEvent.keyDown(window, { code: "Space", ctrlKey: true, shiftKey: true });
    await screen.findByText("已截取 1 / 4 张");
    expect(interviewAppAdapter.captureScreenshot).toHaveBeenCalledOnce();
    expect(interviewAppAdapter.submitScreenshotAnswer).not.toHaveBeenCalled();
  });

  it("keeps interview controls unchanged", () => {
    render(<Workspace mode="interview" />);
    expect(screen.queryByRole("switch", { name: "多屏回答" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "快答" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "截屏回答" })).toBeInTheDocument();
    expect(interviewAppAdapter.getScreenshotCapturePolicy).not.toHaveBeenCalled();
  });
});
