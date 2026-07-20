import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { interviewAppAdapter } from "./app-adapter";
import { syntheticState } from "./test-state";
import type { WebAppState } from "./domain";

const openLive = (mutate?: (state: WebAppState) => void) => {
  if (!vi.isMockFunction(interviewAppAdapter.submitManualAnswer)) {
    vi.spyOn(interviewAppAdapter, "submitManualAnswer").mockImplementation(async command => {
      const taskId = `answer-${command.idempotencyKey.replace(/[^a-zA-Z0-9-]/g, "-")}`;
      return {
        question: {
          id: taskId,
          askedAt: "刚刚",
          text: command.question,
          input: "manual",
          status: "generating",
          advice: {
            outline: [],
            detail: "正在调用当前对话模型生成回答…",
            sourceTypes: ["简历", "JD", "知识库"],
            inference: "",
            uncertain: false,
            provenance: { selectionRevision: 0, usedSources: [] },
          },
        },
        task: {
          id: taskId,
          interviewId: command.interviewId,
          userId: "prototype-user",
          billingUsageId: `live-answer:${taskId}`,
          questionId: taskId,
          revision: 1,
          status: "generating",
          question: command.question,
          partialText: "正在调用当前对话模型生成回答…",
          updatedAtMs: Date.now(),
        },
      };
    });
  }
  if (!vi.isMockFunction(interviewAppAdapter.cancelAnswer)) {
    vi.spyOn(interviewAppAdapter, "cancelAnswer").mockImplementation(async (_command, current) => {
      const { partialText: _partialText, ...task } = current;
      return {
        outcome: "cancelled",
        task: { ...task, status: "cancelled", revision: current.revision + 1, updatedAtMs: Date.now() },
        billingReleased: true,
      };
    });
  }
  if (!vi.isMockFunction(interviewAppAdapter.submitScreenshotAnswer)) {
    vi.spyOn(interviewAppAdapter, "submitScreenshotAnswer").mockImplementation(async command => {
      const taskId = `focused-screenshot-${command.interviewId}`;
      return {
        question: {
          id: taskId,
          askedAt: "刚刚",
          text: command.instruction,
          input: "screenshot",
          status: "confirmed",
          advice: {
            outline: ["识别题目", "整理思路", "生成回答"],
            detail: "请设计一个支持实时协作的 Web 系统。",
            sourceTypes: ["简历", "JD", "知识库"],
            inference: "聚焦工作台测试中的远程截屏回答结果。",
            uncertain: false,
            provenance: { selectionRevision: 0, usedSources: [] },
          },
        },
        task: {
          id: taskId,
          interviewId: command.interviewId,
          userId: "prototype-user",
          billingUsageId: `screenshot-answer:${taskId}`,
          questionId: taskId,
          revision: 1,
          status: "completed",
          question: command.instruction,
          completedText: "请设计一个支持实时协作的 Web 系统。",
          updatedAtMs: Date.now(),
        },
      };
    });
  }
  const state = structuredClone(syntheticState);
  mutate?.(state);
  window.history.pushState({}, "", "/app/interviews/demo/live");
  return render(<App initialAuthenticated initialState={state} />);
};

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });
beforeEach(() => Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 }));

describe("focused live interview workspace", () => {
  it("uses conversation and answer regions without a permanent history rail", () => {
    openLive();
    expect(screen.getByRole("heading", { name: "实时对话" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "回答" })).toBeInTheDocument();
    expect(document.querySelector(".live-right")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /历史/ })).not.toBeInTheDocument();
  });

  it("resizes columns by keyboard without losing a manual draft and persists the ratio", async () => {
    openLive();
    const input = screen.getByRole("textbox", { name: "手动输入面试官的问题" });
    fireEvent.change(input, { target: { value: "保留这条合成草稿" } });
    const divider = screen.getByRole("separator", { name: "调整实时对话与回答宽度" });
    expect(divider).toHaveAttribute("aria-valuenow", "42");
    divider.focus();
    fireEvent.keyDown(divider, { key: "ArrowRight", code: "ArrowRight", keyCode: 39 });
    await waitFor(() => expect(divider).toHaveAttribute("aria-valuenow", "44"));
    fireEvent.keyDown(divider, { key: "ArrowLeft", code: "ArrowLeft", keyCode: 37, shiftKey: true });
    expect(divider).toHaveAttribute("aria-valuenow", "34");
    fireEvent.keyDown(divider, { key: "Home", code: "Home", keyCode: 36 });
    expect(divider).toHaveAttribute("aria-valuenow", "25");
    fireEvent.keyDown(divider, { key: "End", code: "End", keyCode: 35 });
    expect(divider).toHaveAttribute("aria-valuenow", "75");
    fireEvent.keyDown(divider, { key: "Enter", code: "Enter", keyCode: 13 });
    expect(divider).toHaveAttribute("aria-valuenow", "42");
    expect(input).toHaveValue("保留这条合成草稿");
    await waitFor(() => expect(window.sessionStorage.getItem("offersteady.live.demo.split.v1")).toContain('"ratio":42'));
  });

  it("clamps pointer resizing and resets the split without duplicating workspace state", async () => {
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => { callback(0); return 1; });
    vi.stubGlobal("cancelAnimationFrame", () => undefined);
    openLive();
    const grid = document.querySelector(".focused-live-grid") as HTMLDivElement;
    vi.spyOn(grid, "getBoundingClientRect").mockReturnValue({ x: 0, y: 0, left: 0, top: 0, right: 1200, bottom: 700, width: 1200, height: 700, toJSON: () => ({}) });
    const divider = screen.getByRole("separator", { name: "调整实时对话与回答宽度" });
    divider.focus();
    fireEvent.pointerDown(divider, { pointerId: 1, clientX: 504 });
    fireEvent.pointerMove(divider, { pointerId: 1, clientX: 1100 });
    fireEvent.pointerUp(divider, { pointerId: 1, clientX: 1100 });
    await waitFor(() => expect(Number(divider.getAttribute("aria-valuenow"))).toBeLessThanOrEqual(Number(divider.getAttribute("aria-valuemax"))));
    const ratioAfterDrag = divider.getAttribute("aria-valuenow");
    fireEvent.pointerDown(divider, { pointerId: 2, clientX: 900 });
    fireEvent.pointerCancel(divider, { pointerId: 2, clientX: 900 });
    fireEvent.pointerMove(divider, { pointerId: 2, clientX: 100 });
    expect(divider).toHaveAttribute("aria-valuenow", ratioAfterDrag!);
    expect(screen.getAllByRole("heading", { name: "实时对话" })).toHaveLength(1);
    expect(screen.getAllByRole("heading", { name: "回答" })).toHaveLength(1);
    fireEvent.keyDown(divider, { key: "Enter", code: "Enter", keyCode: 13 });
    await waitFor(() => expect(divider).toHaveAttribute("aria-valuenow", "42"));
  });

  it("keeps a historical answer visible when a new answer arrives", async () => {
    openLive();
    fireEvent.click(screen.getByRole("button", { name: /上一条/ }));
    expect(screen.getByRole("heading", { name: "请做一个简短的自我介绍。" })).toBeInTheDocument();
    const input = screen.getByRole("textbox", { name: "手动输入面试官的问题" });
    fireEvent.change(input, { target: { value: "新到达的合成问题" } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "有新答案 · 回到最新" })).toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "请做一个简短的自我介绍。" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "有新答案 · 回到最新" }));
    expect(screen.getByRole("heading", { name: "新到达的合成问题" })).toBeInTheDocument();
  });

  it("renders the completed answer body as the primary content", () => {
    openLive();
    expect(screen.getByLabelText("回答正文")).toHaveTextContent("可以按照 STAR 结构回答");
    expect(screen.queryByText("展开完整回答思路")).not.toBeInTheDocument();
    expect(screen.queryByText("模型推断")).not.toBeInTheDocument();
  });

  it("keeps compact actions free of point-price labels", () => {
    openLive();
    const actions = screen.getByRole("region", { name: "面试操作" });
    expect(within(actions).getByRole("button", { name: "快答" })).toBeInTheDocument();
    expect(within(actions).getByRole("button", { name: "截屏回答" })).toBeInTheDocument();
    expect(actions).not.toHaveTextContent(/\d+\s*点/);
  });

  it("uses the latest detected interviewer question when quick answering without manual text", async () => {
    openLive();
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    await waitFor(() => expect(interviewAppAdapter.submitManualAnswer).toHaveBeenCalledWith(
      expect.objectContaining({ question: "还有一个细节，具体怎么监控" }),
      expect.any(AbortSignal),
      expect.any(Function),
    ));
  });

  it("merges recent interviewer segments for quick answer when there is no pending candidate", async () => {
    openLive(state => {
      state.speaker = {
        ...state.speaker,
        pendingQuestion: null,
        transcripts: [
          ...state.speaker.transcripts,
          {
            id: "transcript-q2",
            sessionId: "demo",
            revision: 1,
            sourceId: "system-loopback",
            sourceKind: "system",
            speakerId: "interviewer-3",
            role: "interviewer",
            text: "请你继续讲一下",
            transcriptConfidence: 0.94,
            startedAtMs: 9_000,
            endedAtMs: 10_000,
            isFinal: true,
            overlap: false,
          },
          {
            id: "transcript-q3",
            sessionId: "demo",
            revision: 1,
            sourceId: "system-loopback",
            sourceKind: "system",
            speakerId: "interviewer-3",
            role: "interviewer",
            text: "你当时是怎么做监控闭环的？",
            transcriptConfidence: 0.95,
            startedAtMs: 10_100,
            endedAtMs: 11_500,
            isFinal: true,
            overlap: false,
          },
        ],
      };
    });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    await waitFor(() => expect(interviewAppAdapter.submitManualAnswer).toHaveBeenCalledWith(
      expect.objectContaining({ question: "请你继续讲一下 你当时是怎么做监控闭环的？" }),
      expect.any(AbortSignal),
      expect.any(Function),
    ));
  });

  it("adds the newest partial interviewer fragment without mixing candidate speech into quick answer", async () => {
    openLive(state => {
      state.speaker = {
        ...state.speaker,
        pendingQuestion: null,
        transcripts: [
          ...state.speaker.transcripts,
          { id: "candidate-turn", sessionId: "demo", revision: 1, sourceId: "mic", sourceKind: "microphone", speakerId: "candidate", role: "candidate", text: "这个项目由我负责。", transcriptConfidence: 0.96, startedAtMs: 9_000, endedAtMs: 10_000, isFinal: true, overlap: false },
          { id: "interviewer-final", sessionId: "demo", revision: 1, sourceId: "system", sourceKind: "system", speakerId: "interviewer", role: "interviewer", text: "这个项目最大的难点是什么？", transcriptConfidence: 0.96, startedAtMs: 10_500, endedAtMs: 11_500, isFinal: true, overlap: false },
          { id: "interviewer-partial", sessionId: "demo", revision: 2, sourceId: "system", sourceKind: "system", speakerId: "interviewer", role: "interviewer", text: "你是怎么解决的", transcriptConfidence: 0.82, startedAtMs: 11_600, endedAtMs: 12_200, isFinal: false, overlap: false },
        ],
      };
    });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    await waitFor(() => expect(interviewAppAdapter.submitManualAnswer).toHaveBeenCalledWith(
      expect.objectContaining({ question: "这个项目最大的难点是什么？ 你是怎么解决的" }),
      expect.any(AbortSignal),
      expect.any(Function),
    ));
  });

  it("renders only the newest revision of one transcript segment", () => {
    openLive(state => {
      const original = state.speaker.transcripts[0]!;
      state.speaker = { ...state.speaker, transcripts: [
          ...state.speaker.transcripts,
          { ...original, revision: original.revision + 1, text: "修订后的合成面试官问题" },
        ] };
    });
    expect(screen.getByText("修订后的合成面试官问题")).toBeInTheDocument();
    expect(screen.queryByText("请介绍一个你负责过的、最有挑战的前端项目。", { selector: ".conversation-turn p" })).not.toBeInTheDocument();
  });

  it("does not turn candidate speech into an answer or expose role correction", () => {
    openLive();
    expect(screen.getByText("1 / 2")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /设为我|设为面试官/ })).not.toBeInTheDocument();
    expect(screen.getByText("我")).toBeInTheDocument();
    expect(screen.getByText("1 / 2")).toBeInTheDocument();
  });

  it("does not use local point balance as the authority for manual model answers", async () => {
    openLive(state => { state.billing = { ...state.billing, balance: 0, activePass: null }; });
    const input = screen.getByRole("textbox", { name: "手动输入面试官的问题" });
    fireEvent.change(input, { target: { value: "余额为零时仍交给后端判断的问题" } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    expect(await screen.findByRole("heading", { name: "余额为零时仍交给后端判断的问题" })).toBeInTheDocument();
    expect(screen.queryByText("积分不足，请先购买积分或开通会员")).not.toBeInTheDocument();
  });

  it("shows the first streamed answer chunk before the answer completes", async () => {
    let finishStream!: () => void;
    const completion = new Promise<void>(resolve => { finishStream = resolve; });
    vi.spyOn(interviewAppAdapter, "submitManualAnswer").mockImplementation(async (command, _signal, onStreamUpdate) => {
      const started = {
        question: {
          id: "stream-task-1",
          askedAt: "刚刚",
          text: command.question,
          input: "manual" as const,
          status: "streaming" as const,
          advice: { outline: [], detail: "流式首段已经出现。", sourceTypes: ["简历" as const], inference: "", uncertain: false, provenance: { selectionRevision: 0, usedSources: [] } },
        },
        task: {
          id: "stream-task-1",
          interviewId: command.interviewId,
          userId: "prototype-user",
          billingUsageId: "live-answer:stream-task-1",
          questionId: "stream-task-1",
          revision: 1,
          status: "generating" as const,
          question: command.question,
          partialText: "流式首段已经出现。",
          updatedAtMs: Date.now(),
        },
      };
      onStreamUpdate?.({ result: started, event: { type: "chunk", task: {}, chunk: { sequence: 1, text: "流式首段已经出现。", isFinal: false } } });
      await completion;
      return {
        question: { ...started.question, status: "confirmed" as const, advice: { ...started.question.advice, detail: "流式首段已经出现。最终回答也完成。" } },
        task: { ...started.task, status: "completed" as const, completedText: "流式首段已经出现。最终回答也完成。" },
      };
    });
    openLive();
    const input = screen.getByRole("textbox", { name: "手动输入面试官的问题" });
    fireEvent.change(input, { target: { value: "验证流式首段的问题" } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    expect(await screen.findByText("流式首段已经出现。")).toBeInTheDocument();
    expect(screen.queryByText("流式首段已经出现。最终回答也完成。")).not.toBeInTheDocument();
    finishStream();
    expect(await screen.findByText("流式首段已经出现。最终回答也完成。")).toBeInTheDocument();
  });

  it("stops the active answer without stopping capture and releases reserved points", async () => {
    openLive();
    fireEvent.click(screen.getByRole("button", { name: "开始面试" }));
    const input = screen.getByRole("textbox", { name: "手动输入面试官的问题" });
    fireEvent.change(input, { target: { value: "这条合成问题随后终止" } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    fireEvent.click(await screen.findByRole("button", { name: "终止回答" }));
    expect(await screen.findByText("回答已终止", { selector: ".cancelled-answer strong" })).toBeInTheDocument();
    expect(screen.getByText("面试进行中")).toBeInTheDocument();
    expect(screen.queryByText("AI 回答建议")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "积分" }));
    expect(await screen.findByText("200 点", { selector: ".balance-card strong" })).toBeInTheDocument();
  });

  it("keeps active answer control available while reading history and can re-answer after cancellation", async () => {
    openLive();
    fireEvent.click(screen.getByRole("button", { name: /上一条/ }));
    const input = screen.getByRole("textbox", { name: "手动输入面试官的问题" });
    fireEvent.change(input, { target: { value: "后台生成的合成问题" } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    expect(await screen.findByText("最新回答仍在生成")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "终止回答" }));
    fireEvent.click(await screen.findByRole("button", { name: "有新答案 · 回到最新" }));
    fireEvent.click(await screen.findByRole("button", { name: "重新回答" }));
    expect(await screen.findByRole("button", { name: "终止回答" })).toBeInTheDocument();
  });

  it("keeps the active answer unchanged when cancellation fails", async () => {
    vi.spyOn(interviewAppAdapter, "cancelAnswer").mockRejectedValueOnce(new Error("synthetic cancellation failure"));
    openLive();
    const input = screen.getByRole("textbox", { name: "手动输入面试官的问题" });
    fireEvent.change(input, { target: { value: "取消失败的合成问题" } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    fireEvent.click(await screen.findByRole("button", { name: "终止回答" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("终止回答失败");
    expect(screen.getByRole("button", { name: "终止回答" })).toBeInTheDocument();
  });

  it("keeps manual input on the left and quick actions on the right", () => {
    openLive();
    const inputRegion = screen.getByRole("region", { name: "手动问题输入" });
    const actionRegion = screen.getByRole("region", { name: "面试操作" });
    expect(within(inputRegion).getByRole("textbox", { name: "手动输入面试官的问题" })).toBeInTheDocument();
    expect(within(actionRegion).getByRole("button", { name: "快答" })).toBeInTheDocument();
    expect(within(actionRegion).getByRole("button", { name: "截屏回答" })).toBeInTheDocument();
    expect(within(actionRegion).queryByRole("textbox", { name: "手动输入面试官的问题" })).not.toBeInTheDocument();
  });

  it("captures the current screen without file-upload copy", async () => {
    openLive();
    fireEvent.click(screen.getByRole("button", { name: "截屏回答" }));
    expect((await screen.findAllByText("请设计一个支持实时协作的 Web 系统。")).length).toBeGreaterThan(0);
    expect(screen.queryByText("上传并识别")).not.toBeInTheDocument();
  });

  it("can terminate a pending screenshot answer before the local assistant finishes", async () => {
    vi.spyOn(interviewAppAdapter, "submitScreenshotAnswer").mockImplementation(async (_command, signal) => {
      await new Promise<void>((resolve, reject) => {
        const timer = window.setTimeout(resolve, 30000);
        signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
        signal?.addEventListener("abort", () => window.clearTimeout(timer), { once: true });
      });
      return {} as never;
    });
    openLive();
    fireEvent.click(screen.getByRole("button", { name: "截屏回答" }));
    fireEvent.click(await screen.findByRole("button", { name: "终止回答" }));
    expect(await screen.findByText("回答已终止", { selector: ".cancelled-answer strong" })).toBeInTheDocument();
    expect(screen.queryByText("截图回答已终止，积分预留已释放")).not.toBeInTheDocument();
  });

  it("shows source degradation outside the two-role transcript list", () => {
    openLive(state => { state.speaker = { ...state.speaker, mode: "manual-only", degradation: { id: "degraded-1", sessionId: "demo", reason: "mixed-input", sourceKind: "mixed", detectedAtMs: 10, manualInputAvailable: true }, runtimeNotice: null }; });
    expect(screen.getByText("音频来源无法区分")).toBeInTheDocument();
    expect(screen.getByText("仅手动提问")).toBeInTheDocument();
    expect(screen.queryByText("角色待确认")).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "手动输入面试官的问题" })).toBeInTheDocument();
  });

  it("shows current-session runtime diagnostics when no realtime transcript is available yet", () => {
    openLive(state => {
      state.speaker = {
        ...state.speaker,
        transcripts: [],
        pendingQuestion: null,
        degradation: null,
        runtimeNotice: {
          stage: "publishing",
          message: "当前 session 正在接收音频，等待实时转写同步到对话区。",
        },
      };
    });
    expect(screen.getByText("当前 session 尚未收到实时对话")).toBeInTheDocument();
    expect(screen.getByText("等待当前面试的实时对话")).toBeInTheDocument();
    expect(screen.getAllByText("当前 session 正在接收音频，等待实时转写同步到对话区。")).toHaveLength(2);
  });

  it("shows chain-aware runtime diagnostics for desktop send backlog", () => {
    openLive(state => {
      state.speaker = {
        ...state.speaker,
        transcripts: [],
        pendingQuestion: null,
        degradation: null,
        runtimeNotice: {
          stage: "publishing",
          message: "桌面端正在采集，但发送积压过高，实时字幕会明显变慢。",
        },
      };
    });
    expect(screen.getAllByText("桌面端正在采集，但发送积压过高，实时字幕会明显变慢。")).toHaveLength(2);
  });
});
