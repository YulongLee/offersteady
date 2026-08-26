import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { interviewAppAdapter } from "./app-adapter";
import { authClient } from "./auth-client";
import { syntheticState } from "./test-state";
import { AppError, type RealtimeSessionUpdate, type WebAppState } from "./domain";

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
  it("keeps reconnect backoff after an aggregate recovery snapshot succeeds", async () => {
    vi.spyOn(interviewAppAdapter, "sendDesktopSessionHeartbeat").mockImplementation(async command => ({
      pageInstanceId: command.pageInstanceId ?? null,
      leaseGeneration: 1,
      leaseExpiresAtMs: Date.now() + 30_000,
    }));
    vi.spyOn(interviewAppAdapter, "loadRealtimeSession").mockResolvedValue({
      speaker: structuredClone(syntheticState.speaker),
    });
    let attempts = 0;
    const subscribe = vi.spyOn(interviewAppAdapter, "subscribeRealtimeSession").mockImplementation(async (_id, _onUpdate, signal) => {
      attempts += 1;
      if (attempts <= 3) throw new AppError("network", "first snapshot timeout");
      await new Promise<void>((_resolve, reject) => signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true }));
    });

    openLive();

    await waitFor(() => expect(subscribe).toHaveBeenCalledTimes(2), { timeout: 500 });
    expect(interviewAppAdapter.loadRealtimeSession).toHaveBeenCalledTimes(2);
    await new Promise(resolve => window.setTimeout(resolve, 250));
    expect(subscribe).toHaveBeenCalledTimes(2);
  });

  it("offers account switching and logout from the focused interview page", async () => {
    const logout = vi.spyOn(authClient, "logout").mockResolvedValue();
    openLive();

    fireEvent.click(screen.getByRole("button", { name: "账号菜单" }));
    expect(screen.getByText("当前账号")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "切换账号" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "退出登录" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "切换账号" }));

    await waitFor(() => expect(logout).toHaveBeenCalledOnce());
    await waitFor(() => expect(window.location.pathname).toBe("/login"));
  });

  it("hydrates backend answer history when the same interview opens on another device", async () => {
    vi.spyOn(interviewAppAdapter, "loadInterviewWorkspace").mockResolvedValueOnce({
      questions: [{
        id: "cross-device-answer",
        askedAt: "刚刚",
        text: "电脑端已经回答的问题",
        input: "manual",
        status: "confirmed",
        advice: { outline: [], detail: "这是从服务端恢复的完整回答。", sourceTypes: [], inference: "", uncertain: false, provenance: { selectionRevision: 0, usedSources: [] } },
      }],
      activeAnswerTask: null,
    });

    openLive(state => { state.questions = []; });

    expect(await screen.findByText("电脑端已经回答的问题")).toBeInTheDocument();
    expect(screen.getByLabelText("回答正文")).toHaveTextContent("这是从服务端恢复的完整回答。");
  });

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

  it("keeps compact desktop windows side by side and resizable", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 840 });
    openLive();
    const input = screen.getByRole("textbox", { name: "手动输入面试官的问题" });
    fireEvent.change(input, { target: { value: "紧凑窗口草稿" } });
    const divider = screen.getByRole("separator", { name: "调整实时对话与回答宽度" });
    expect(document.querySelector(".focused-live-grid")).toHaveStyle({ gridTemplateColumns: "minmax(240px, 42fr) 12px minmax(300px, 58fr)" });
    fireEvent.keyDown(divider, { key: "ArrowRight", code: "ArrowRight", keyCode: 39 });
    await waitFor(() => expect(divider).toHaveAttribute("aria-valuenow", "44"));
    expect(input).toHaveValue("紧凑窗口草稿");
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

  it("shows an explicitly requested answer immediately instead of staying on history", async () => {
    openLive();
    fireEvent.click(screen.getByRole("button", { name: /上一条/ }));
    expect(screen.getByRole("heading", { name: "请做一个简短的自我介绍。" })).toBeInTheDocument();
    const input = screen.getByRole("textbox", { name: "手动输入面试官的问题" });
    fireEvent.change(input, { target: { value: "新到达的合成问题" } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    expect(await screen.findByRole("heading", { name: "新到达的合成问题" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "有新答案 · 回到最新" })).not.toBeInTheDocument();
  });

  it("renders the completed answer body as the primary content", () => {
    openLive();
    expect(screen.getByLabelText("回答正文")).toHaveTextContent("可以按照 STAR 结构回答");
    expect(screen.queryByText("展开完整回答思路")).not.toBeInTheDocument();
    expect(screen.queryByText("模型推断")).not.toBeInTheDocument();
  });

  it("keeps the complete mobile answer in one continuous scroll flow", () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 390 });
    openLive();
    const workspace = document.querySelector(".answer-workspace");
    const expand = screen.getByRole("button", { name: "扩大回答框" });
    expect(workspace).not.toHaveClass("mobile-answer-expanded");
    fireEvent.click(expand);
    expect(workspace).toHaveClass("mobile-answer-expanded");
    expect(screen.getByRole("button", { name: "恢复回答框高度" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByLabelText("回答正文")).toHaveTextContent("可以按照 STAR 结构回答");
    fireEvent.click(screen.getByRole("button", { name: "恢复回答框高度" }));
    expect(workspace).not.toHaveClass("mobile-answer-expanded");
  });

  it("uses an answer-first tab workspace on phones instead of stacking the full page", () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 390 });
    openLive();

    expect(screen.getByRole("tab", { name: "回答" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "回答" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "实时对话" })).not.toBeInTheDocument();
    expect(screen.queryByText("面试进行中")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /对话/ }));
    expect(screen.getByRole("heading", { name: "实时对话" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "回答" })).not.toBeInTheDocument();
  });

  it("keeps phone actions in one compact region and returns to the answer for quick replies", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 390 });
    openLive();
    fireEvent.click(screen.getByRole("tab", { name: /对话/ }));

    const actions = screen.getByRole("region", { name: "面试操作" });
    const input = within(actions).getByRole("textbox", { name: "手动输入面试官的问题" });
    fireEvent.change(input, { target: { value: "手机端合成测试问题" } });
    fireEvent.click(within(actions).getByRole("button", { name: "快答" }));

    expect(screen.getByRole("tab", { name: /回答/ })).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByRole("heading", { name: "手机端合成测试问题" })).toBeInTheDocument();
    expect(interviewAppAdapter.submitManualAnswer).toHaveBeenCalledOnce();
  });

  it("keeps the phone header compact and exposes low-frequency actions from more", () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 390 });
    openLive();

    expect(screen.getByRole("button", { name: "开始面试" })).toBeInTheDocument();
    const more = document.querySelector(".mobile-live-more");
    expect(more).not.toHaveAttribute("open");
    fireEvent.click(screen.getByLabelText("更多面试操作"));
    expect(more).toHaveAttribute("open");
    expect(screen.getByRole("link", { name: "积分与会员" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "用户设置" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "结束面试" })).toBeInTheDocument();
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
    expect(screen.getByRole("button", { name: "快答" })).toBeDisabled();
    expect(screen.getByText("正在生成回答，请稍候")).toBeInTheDocument();
    expect(await screen.findByText("流式首段已经出现。")).toBeInTheDocument();
    expect(screen.queryByText("流式首段已经出现。最终回答也完成。")).not.toBeInTheDocument();
    finishStream();
    expect(await screen.findByText("流式首段已经出现。最终回答也完成。")).toBeInTheDocument();
    expect(await screen.findByText("快答已完成")).toBeInTheDocument();
  });

  it("does not let workspace polling shorten a visible streamed quick answer", async () => {
    let finishStream!: () => void;
    const completion = new Promise<void>(resolve => { finishStream = resolve; });
    let staleWorkspace: Awaited<ReturnType<typeof interviewAppAdapter.loadInterviewWorkspace>> | null = null;
    vi.spyOn(interviewAppAdapter, "loadInterviewWorkspace").mockImplementation(async () => staleWorkspace ?? {
      questions: structuredClone(syntheticState.questions),
      activeAnswerTask: null,
    });
    vi.spyOn(interviewAppAdapter, "submitManualAnswer").mockImplementation(async (command, _signal, onStreamUpdate) => {
      const streamed = {
        question: {
          id: "stream-race-task",
          askedAt: "刚刚",
          text: command.question,
          input: "manual" as const,
          status: "streaming" as const,
          advice: { outline: [], detail: "这是已经稳定展示的较长合成回答。", sourceTypes: [], inference: "", uncertain: false, provenance: { selectionRevision: 0, usedSources: [] } },
        },
        task: {
          id: "stream-race-task",
          interviewId: command.interviewId,
          userId: "prototype-user",
          billingUsageId: "live-answer:stream-race-task",
          questionId: "stream-race-task",
          revision: 1,
          status: "generating" as const,
          question: command.question,
          partialText: "这是已经稳定展示的较长合成回答。",
          updatedAtMs: 300,
        },
      };
      staleWorkspace = {
        questions: [{ ...streamed.question, advice: { ...streamed.question.advice, detail: "较短旧快照" } }],
        activeAnswerTask: { ...streamed.task, partialText: "较短旧快照", updatedAtMs: 200 },
      };
      onStreamUpdate?.({ result: streamed, event: { type: "chunk", task: {}, chunk: { sequence: 1, text: streamed.task.partialText, isFinal: false } } });
      await completion;
      return {
        question: { ...streamed.question, status: "confirmed" as const },
        task: { ...streamed.task, status: "completed" as const, completedText: streamed.task.partialText },
      };
    });

    openLive();
    fireEvent.change(screen.getByRole("textbox", { name: "手动输入面试官的问题" }), { target: { value: "验证轮询竞态的合成问题" } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));

    expect(await screen.findByText("这是已经稳定展示的较长合成回答。")).toBeInTheDocument();
    window.dispatchEvent(new Event("focus"));
    await waitFor(() => expect(interviewAppAdapter.loadInterviewWorkspace).toHaveBeenCalledTimes(2));
    expect(screen.getByLabelText("回答正文")).toHaveTextContent("这是已经稳定展示的较长合成回答。");
    expect(screen.queryByText("较短旧快照")).not.toBeInTheDocument();
    finishStream();
    expect(await screen.findByText("快答已完成")).toBeInTheDocument();
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
    fireEvent.click(screen.getByRole("link", { name: "积分与会员" }));
    expect(await screen.findByText("200 点", { selector: ".balance-card strong" })).toBeInTheDocument();
  });

  it("moves an explicit answer off history and can re-answer after cancellation", async () => {
    openLive();
    fireEvent.click(screen.getByRole("button", { name: /上一条/ }));
    const input = screen.getByRole("textbox", { name: "手动输入面试官的问题" });
    fireEvent.change(input, { target: { value: "后台生成的合成问题" } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    expect(await screen.findByText("当前回答正在生成")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "后台生成的合成问题" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "终止回答" }));
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
    const submitScreenshot = vi.mocked(interviewAppAdapter.submitScreenshotAnswer);
    fireEvent.click(screen.getByRole("button", { name: "截屏回答" }));
    const screenshotButton = screen.getByRole("button", { name: "截屏回答" });
    expect(screenshotButton).toBeDisabled();
    expect(screenshotButton).toHaveTextContent("截屏回答");
    expect(screenshotButton).toHaveTextContent("直接截取共享屏幕并进入回答");
    expect(screenshotButton).not.toHaveTextContent(/处理中|已回答/);
    expect((await screen.findAllByText("请设计一个支持实时协作的 Web 系统。")).length).toBeGreaterThan(0);
    expect(await screen.findByText("截屏回答已完成，答案已显示")).toBeInTheDocument();
    expect(screen.queryByText("上传并识别")).not.toBeInTheDocument();
    const instruction = submitScreenshot.mock.calls.at(-1)?.[0].instruction ?? "";
    expect(instruction).toContain("只依据当前截图");
    expect(instruction).toContain("不要使用实时对话");
    expect(instruction).not.toContain("面试官最近的问题是");
    expect(instruction).not.toContain("还有一个细节，具体怎么监控");
  });

  it("hides model implementation copy while generating a screenshot answer", async () => {
    vi.spyOn(interviewAppAdapter, "submitScreenshotAnswer").mockImplementation(async (_command, signal, onStage) => {
      onStage?.({ name: "共享屏幕截取", stage: "generating" });
      await new Promise<void>((_resolve, reject) => {
        signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
      });
      return {} as never;
    });
    openLive();

    fireEvent.click(screen.getByRole("button", { name: "截屏回答" }));

    const dialog = await screen.findByRole("dialog", { name: "正在生成答案" });
    expect(within(dialog).queryByText(/视觉模型|模型 API/)).not.toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "取消" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("shows and cancels desktop shortcut screenshots with the same feedback as the screenshot button", async () => {
    vi.spyOn(interviewAppAdapter, "loadDesktopShortcutScreenshotUpdates").mockResolvedValue([{
      requestId: "shortcut-shot-1",
      status: "processing",
      screenshotTask: { name: "共享屏幕截取", stage: "generating" },
    }]);
    const cancelShortcut = vi.spyOn(interviewAppAdapter, "cancelDesktopShortcutScreenshot").mockResolvedValue();
    openLive();

    const dialog = await screen.findByRole("dialog", { name: "正在生成答案" });
    expect(within(dialog).queryByText(/视觉模型|模型 API/)).not.toBeInTheDocument();
    const screenshotButton = screen.getByRole("button", { name: "截屏回答" });
    expect(screenshotButton).toBeDisabled();
    expect(screenshotButton).toHaveTextContent("截屏回答");
    expect(screenshotButton).not.toHaveTextContent("正在生成截图答案");
    expect(screen.getAllByText("正在生成截图答案")).toHaveLength(1);

    fireEvent.click(within(dialog).getByRole("button", { name: "取消" }));

    await waitFor(() => expect(cancelShortcut).toHaveBeenCalledWith("shortcut-shot-1", expect.any(AbortSignal)));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByText("截屏回答已取消")).toBeInTheDocument();
  });

  it("shows shortcut feedback as soon as realtime acceptance arrives instead of waiting for recovery polling", async () => {
    vi.spyOn(interviewAppAdapter, "loadDesktopShortcutScreenshotUpdates").mockResolvedValue([]);
    vi.spyOn(interviewAppAdapter, "sendDesktopSessionHeartbeat").mockImplementation(async command => ({
      pageInstanceId: command.pageInstanceId ?? null,
      leaseGeneration: 1,
      leaseExpiresAtMs: Date.now() + 30_000,
    }));
    let publishRealtime: ((update: RealtimeSessionUpdate) => void) | null = null;
    vi.spyOn(interviewAppAdapter, "subscribeRealtimeSession").mockImplementation(async (_id, onUpdate, signal) => {
      publishRealtime = onUpdate;
      await new Promise<void>((_resolve, reject) => signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true }));
    });

    openLive();
    await waitFor(() => expect(publishRealtime).not.toBeNull());
    act(() => publishRealtime?.({
        speaker: structuredClone(syntheticState.speaker),
        shortcutScreenshotUpdate: {
          requestId: "shortcut-instant-1",
          status: "requested",
          screenshotTask: { name: "共享屏幕截取", stage: "waiting-desktop" },
          notificationId: "shortcut-notice-1",
          acceptedAtMs: Date.now(),
        },
      }));

    const dialog = await screen.findByRole("dialog", { name: "等待本地助手" });
    expect(within(dialog).getByText("网页端已创建截屏任务，正在等待本地助手接收。")).toBeInTheDocument();
    const screenshotButton = screen.getByRole("button", { name: "截屏回答" });
    expect(screenshotButton).toBeDisabled();
    expect(screenshotButton).toHaveTextContent("截屏回答");
    expect(screenshotButton).not.toHaveTextContent(/处理中|已回答/);
  });

  it("keeps the mobile screenshot button label stable while capture is active", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 390 });
    vi.spyOn(interviewAppAdapter, "submitScreenshotAnswer").mockImplementation(async (_command, signal, onStage) => {
      onStage?.({ name: "共享屏幕截取", stage: "waiting-desktop" });
      await new Promise<void>((_resolve, reject) => {
        signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
      });
      return {} as never;
    });
    openLive();

    const screenshotButton = screen.getByRole("button", { name: "截屏回答" });
    fireEvent.click(screenshotButton);

    expect(screenshotButton).toBeDisabled();
    expect(screenshotButton).toHaveTextContent("截屏回答");
    expect(screenshotButton).not.toHaveTextContent(/截屏中|处理中|已回答/);
    fireEvent.click(await screen.findByRole("button", { name: "取消" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("keeps a completed screenshot current when an older speech answer arrives in the same realtime update", async () => {
    vi.spyOn(interviewAppAdapter, "loadDesktopShortcutScreenshotUpdates").mockResolvedValue([]);
    vi.spyOn(interviewAppAdapter, "sendDesktopSessionHeartbeat").mockImplementation(async command => ({
      pageInstanceId: command.pageInstanceId ?? null,
      leaseGeneration: 1,
      leaseExpiresAtMs: Date.now() + 30_000,
    }));
    let publishRealtime: ((update: RealtimeSessionUpdate) => void) | null = null;
    vi.spyOn(interviewAppAdapter, "subscribeRealtimeSession").mockImplementation(async (_id, onUpdate, signal) => {
      publishRealtime = onUpdate;
      await new Promise<void>((_resolve, reject) => signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true }));
    });
    const speaker = { ...structuredClone(syntheticState.speaker), pendingQuestion: null };
    const oldSpeechResult = {
      question: {
        id: "speech-answer-old",
        askedAt: "刚刚",
        text: "旧的面试官问题",
        input: "manual" as const,
        status: "confirmed" as const,
        advice: { outline: [], detail: "旧的语音回答", sourceTypes: [], inference: "", uncertain: false, provenance: { selectionRevision: 0, usedSources: [] } },
      },
      task: {
        id: "speech-answer-old",
        interviewId: "demo",
        userId: "prototype-user",
        billingUsageId: "live-answer:speech-answer-old",
        questionId: "speech-answer-old",
        revision: 1,
        status: "completed" as const,
        question: "旧的面试官问题",
        completedText: "旧的语音回答",
        updatedAtMs: 100,
      },
    };
    const screenshotResult = {
      question: {
        id: "screenshot-answer-new",
        askedAt: "刚刚",
        text: "截图中的算法题",
        input: "screenshot" as const,
        status: "confirmed" as const,
        advice: { outline: [], detail: "新的截图回答", sourceTypes: [], inference: "", uncertain: false, provenance: { selectionRevision: 0, usedSources: [] } },
      },
      task: {
        id: "screenshot-answer-new",
        interviewId: "demo",
        userId: "prototype-user",
        billingUsageId: "screenshot-answer:screenshot-answer-new",
        questionId: "screenshot-answer-new",
        revision: 1,
        status: "completed" as const,
        question: "截图中的算法题",
        completedText: "新的截图回答",
        updatedAtMs: 200,
      },
    };

    openLive();
    await waitFor(() => expect(publishRealtime).not.toBeNull());
    act(() => publishRealtime?.({
      speaker,
      answerUpdate: oldSpeechResult,
      shortcutScreenshotUpdate: {
        requestId: "screenshot-request-new",
        status: "completed",
        screenshotTask: { name: "共享屏幕截取", stage: "completed" },
        result: screenshotResult,
      },
    }));

    expect(await screen.findByText("新的截图回答")).toBeInTheDocument();
    expect(screen.getByText("截屏回答已完成，答案已显示")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    act(() => publishRealtime?.({
      speaker,
      shortcutScreenshotUpdate: {
        requestId: "screenshot-request-new",
        status: "processing",
        screenshotTask: { name: "共享屏幕截取", stage: "recognizing" },
      },
    }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByText("截屏回答已完成，答案已显示")).toBeInTheDocument();
  });

  it("confirms detected question text without creating an answer before quick answer is clicked", () => {
    const submitManual = vi.spyOn(interviewAppAdapter, "submitManualAnswer");
    const currentQuestion = syntheticState.questions[0]!.text;
    openLive();

    fireEvent.click(screen.getByRole("button", { name: "确认问题" }));

    expect(screen.queryByRole("button", { name: "确认问题" })).not.toBeInTheDocument();
    expect(screen.getAllByText(currentQuestion).length).toBeGreaterThan(0);
    expect(submitManual).not.toHaveBeenCalled();
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
