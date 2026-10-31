import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MockInterviewPage, MockReportView } from "./MockInterviewPage";
import { mockRequest, MockPlaybackError, MockVoicePlayer, type MockSession } from "./mock-interview-client";
import { authClient } from "./auth-client";
import { downloadMockInterviewWord } from "./mock-interview-word-export";

vi.mock("./mock-interview-word-export", () => ({ downloadMockInterviewWord: vi.fn() }));

vi.mock("./mock-interview-client", async importOriginal => ({
  ...await importOriginal<typeof import("./mock-interview-client")>(), mockRequest: vi.fn(),
}));

const quote = { activeTimeMember: true, dailyFreeRemaining: 1, entryPoints: 0, minutePoints: 0,
  billingClass: "daily_pass_free", savedCount: 0, savedLimit: 2, dailyFreeLimit: 1, durationLimitMinutes: 60, quotaDay: "2026-10-18", timezone: "Asia/Shanghai", nowMs: Date.now() };
const session: MockSession = { sessionId: "mock-synthetic", title: "合成模拟面试", targetRole: "后端开发",
  billingClass: "points", refunded: false, createdAtMs: 1, resumeId: "resume", resumeVersion: "v1",
  error: null, billableMs: 10000, billedMinutes: 1, interacting: false, partial: true,
  state: { phase: "completed", version: 5, capture_epoch: null,
    rounds: [{ question_id: "q1", question: "如何防止重复写入？", answer: "使用唯一约束", submission_id: "a1" }] },
  report: { summary: "回答方向正确，可以补充并发场景。", overall_score: 80,
    dimensions: { relevance: 80, clarity: 80, depth: 80, evidence: 80 },
    feedback: [{ question_id: "q1", answer_quote: "使用唯一约束", strength: "切题", improvement: "补充冲突处理",
      suggestion: "结合真实项目说明重试策略。" }], practice_priorities: ["练习接口幂等"] } };

describe("CN mock interviews", () => {
  beforeEach(() => { vi.resetAllMocks(); });
  afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
  it("hides paid creation when rollout is disabled", async () => {
    vi.mocked(mockRequest).mockResolvedValue({ enabled: false });
    render(<MemoryRouter><MockInterviewPage /></MemoryRouter>);
    expect(await screen.findByText("模拟面试尚未开放")).toBeInTheDocument();
    expect(screen.queryByText("创建模拟面试 →")).not.toBeInTheDocument();
  });
  it("shows free entitlement and explicit retention/billing rules", async () => {
    vi.mocked(mockRequest).mockImplementation(async path => path.endsWith("capabilities") ? { enabled: true } : { sessions: [], quote });
    render(<MemoryRouter><MockInterviewPage /></MemoryRouter>);
    expect(await screen.findByText("本场免费")).toBeInTheDocument();
    expect(screen.getByText(/今日剩余 1 场/)).toBeInTheDocument();
    expect(screen.getByText(/最多 2 场；不保存原始音频/)).toBeInTheDocument();
  });
  it("blocks creation when both saved slots are occupied", async () => {
    vi.mocked(mockRequest).mockImplementation(async path => path.endsWith("capabilities") ? { enabled: true } : { sessions: [session], quote: { ...quote, savedCount: 2 } });
    render(<MemoryRouter><MockInterviewPage /></MemoryRouter>);
    expect(await screen.findByRole("button", { name: "请先手动删除旧记录" })).toBeDisabled();
    expect(screen.getByRole("link", { name: "查看报告" })).toBeInTheDocument();
  });
  it("uses the renamed default title while preserving the AI interviewer disclosure", async () => {
    vi.mocked(mockRequest).mockImplementation(async (path, body) => path.endsWith("capabilities")
      ? { enabled: true } : body ? session : { sessions: [], quote });
    render(<MemoryRouter><MockInterviewPage /></MemoryRouter>);
    await screen.findByText("本场免费");
    expect(screen.getByText("AI 模拟面试官")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "创建模拟面试 →" }));
    await waitFor(() => expect(mockRequest).toHaveBeenCalledWith("/mock-interviews", expect.objectContaining({
      title: "模拟面试", expectedBillingClass: "daily_pass_free",
    })));
  });
  it("second member creation requires paid confirmation; cancel sends no creation request", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    vi.mocked(mockRequest).mockImplementation(async path => path.endsWith("capabilities") ? { enabled: true } : { sessions: [], quote: { ...quote, dailyFreeRemaining: 0, entryPoints: 100, minutePoints: 5, billingClass: "points" } });
    render(<MemoryRouter><MockInterviewPage /></MemoryRouter>);
    const button = await screen.findByRole("button", { name: "创建模拟面试 →" });
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button);
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining("本场一次性扣 100 积分"));
    expect(vi.mocked(mockRequest).mock.calls.filter(([, body]) => body !== undefined)).toHaveLength(0);
  });
  it("report includes per-question evidence and partial-session label", () => {
    render(<MemoryRouter><MockReportView session={session} /></MemoryRouter>);
    expect(screen.getByText("部分练习报告")).toBeInTheDocument();
    expect(screen.getByText("结合真实项目说明重试策略。")).toBeInTheDocument();
    expect(screen.getAllByText("使用唯一约束")).toHaveLength(2);
  });
  it("empty answers do not invent a score", () => {
    render(<MemoryRouter><MockReportView session={{ ...session, state: { ...session.state, rounds: [] }, report: { summary: "本场未完成作答", overall_score: null, dimensions: null, feedback: [], practice_priorities: [] } }} /></MemoryRouter>);
    expect(screen.getByText("有效回答不足，不评分")).toBeInTheDocument();
    expect(screen.queryByRole("meter")).not.toBeInTheDocument();
  });
  it("downloads the loaded report once and disables repeated clicks during generation without API calls", async () => {
    let finish!: () => void;
    vi.mocked(downloadMockInterviewWord).mockImplementation(() => new Promise<void>(resolve => { finish = resolve; }));
    render(<MemoryRouter><MockReportView session={session} /></MemoryRouter>);
    const button = screen.getByRole("button", { name: "下载 Word" });
    expect(downloadMockInterviewWord).not.toHaveBeenCalled();
    fireEvent.click(button);
    fireEvent.click(button);
    expect(screen.getByRole("button", { name: "正在生成 Word…" })).toBeDisabled();
    await waitFor(() => expect(downloadMockInterviewWord).toHaveBeenCalledExactlyOnceWith(session));
    await act(async () => finish());
    expect(screen.getByRole("button", { name: "下载 Word" })).toBeEnabled();
    expect(mockRequest).not.toHaveBeenCalled();
  });
  it("keeps the report intact and allows retry after Word download failure", async () => {
    vi.mocked(downloadMockInterviewWord).mockRejectedValueOnce(new Error("synthetic failure")).mockResolvedValueOnce();
    render(<MemoryRouter><MockReportView session={session} /></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: "下载 Word" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Word 下载失败，请重试");
    expect(screen.getByText(session.report!.summary)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "下载 Word" }));
    await waitFor(() => expect(downloadMockInterviewWord).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByRole("button", { name: "下载 Word" })).toBeEnabled());
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(mockRequest).not.toHaveBeenCalled();
  });
  it("does not offer download until a completed report exists", () => {
    const { rerender } = render(<MemoryRouter><MockReportView session={{ ...session, report: null }} /></MemoryRouter>);
    expect(screen.queryByRole("button", { name: "下载 Word" })).not.toBeInTheDocument();
    rerender(<MemoryRouter><MockReportView session={{ ...session, state: { ...session.state, phase: "generating_report" } }} /></MemoryRouter>);
    expect(screen.queryByRole("button", { name: "下载 Word" })).not.toBeInTheDocument();
    rerender(<MemoryRouter><MockReportView session={session} /></MemoryRouter>);
    expect(screen.getByRole("button", { name: "下载 Word" })).toBeEnabled();
  });
  it("allows existing assistant preparation before its live audio socket connects", async () => {
    const sockets: any[] = [];
    vi.stubGlobal("WebSocket", class {
      static OPEN = 1; readyState = 1; onmessage: any; onopen: any; onclose: any;
      send = vi.fn(); close = vi.fn(); constructor() { sockets.push(this); }
    });
    vi.spyOn(authClient, "readStoredSession").mockReturnValue({ accessToken: "synthetic-owner", account: { id: "synthetic" } } as ReturnType<typeof authClient.readStoredSession>);
    const row = { ...session, report: null, state: { ...session.state, phase: "preparing", rounds: [] } };
    vi.mocked(mockRequest).mockImplementation(async path => path.endsWith("capabilities") ? { enabled: true } : path.startsWith("/documents") ? [] : row);
    render(<MemoryRouter initialEntries={["/app/mock-interviews/mock-synthetic"]}><Routes><Route path="/app/mock-interviews/:id" element={<MockInterviewPage />} /></Routes></MemoryRouter>);
    await waitFor(() => expect(sockets).toHaveLength(1));
    act(() => sockets[0].onmessage({ data: JSON.stringify({ type: "state", session: row, desktopConnected: true, microphoneConnected: false }) }));
    expect(screen.getByRole("button", { name: "开始模拟面试 →" })).toBeEnabled();
    expect(screen.getByText(/现有正式版助手即可，仅使用麦克风/)).toBeInTheDocument();
    expect(screen.getByText(/服务器会丢弃非回答时段/)).toBeInTheDocument();
  });
  it("waits without listen/billing commands and starts once when legacy audio becomes ready", async () => {
    const sockets: any[] = [];
    vi.stubGlobal("WebSocket", class {
      static OPEN = 1; readyState = 1; onmessage: any; onopen: any; onclose: any;
      send = vi.fn(); close = vi.fn(); constructor() { sockets.push(this); }
    });
    vi.spyOn(authClient, "readStoredSession").mockReturnValue({ accessToken: "synthetic-owner", account: { id: "synthetic" } } as ReturnType<typeof authClient.readStoredSession>);
    const row = { ...session, report: null, state: { ...session.state, phase: "speaking" } };
    vi.mocked(mockRequest).mockImplementation(async path => path.endsWith("capabilities") ? { enabled: true } : row);
    render(<MemoryRouter initialEntries={["/app/mock-interviews/mock-synthetic"]}><Routes><Route path="/app/mock-interviews/:id" element={<MockInterviewPage />} /></Routes></MemoryRouter>);
    await waitFor(() => expect(sockets).toHaveLength(1));
    const emit = (mic: boolean) => act(() => sockets[0].onmessage({ data: JSON.stringify({ type: "state", session: row, desktopConnected: mic, microphoneConnected: mic }) }));
    emit(false);
    vi.useFakeTimers();
    fireEvent.click(screen.getByRole("button", { name: "我已读完，开始回答" }));
    expect(screen.getByText(/正在准备收音/)).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(1500));
    expect(screen.getByText(/正在等待助手收音通道连接/)).toBeInTheDocument();
    expect(sockets[0].send).not.toHaveBeenCalled();
    emit(true); emit(true);
    expect(sockets[0].send).toHaveBeenCalledTimes(1);
    expect(JSON.parse(sockets[0].send.mock.calls[0][0]).action).toBe("listen");
  });
  it("shows the real readiness reason and clears binding notice after legacy readiness recovers", async () => {
    const sockets: any[] = [];
    vi.stubGlobal("WebSocket", class {
      static OPEN = 1; readyState = 1; onmessage: any; onopen: any; onclose: any;
      send = vi.fn(); close = vi.fn(); constructor() { sockets.push(this); }
    });
    vi.spyOn(authClient, "readStoredSession").mockReturnValue({ accessToken: "synthetic-owner", account: { id: "synthetic" } } as ReturnType<typeof authClient.readStoredSession>);
    const row = { ...session, report: null, billedMinutes: 0, state: { ...session.state, phase: "preparing", rounds: [] } };
    vi.mocked(mockRequest).mockImplementation(async path => path.endsWith("capabilities") ? { enabled: true } : path.startsWith("/documents") ? [] : row);
    render(<MemoryRouter initialEntries={["/app/mock-interviews/mock-synthetic"]}><Routes><Route path="/app/mock-interviews/:id" element={<MockInterviewPage />} /></Routes></MemoryRouter>);
    await waitFor(() => expect(sockets).toHaveLength(1));
    const emit = (ready: boolean, message: string) => act(() => sockets[0].onmessage({ data: JSON.stringify({
      type: "state", session: row, desktopConnected: ready, microphoneConnected: false,
      preparation: { ready, code: ready ? "mock_permission_deferred" : "mock_microphone_required", message },
    }) }));
    emit(false, "请在助手中开启麦克风权限。");
    expect(screen.getByRole("button", { name: "开始模拟面试 →" })).toBeDisabled();
    expect(screen.getByRole("status", { name: "助手连接状态" })).toHaveTextContent("请在助手中开启麦克风权限。");
    fireEvent.change(screen.getByLabelText("桌面助手机器码"), { target: { value: "000000" } });
    fireEvent.click(screen.getByRole("button", { name: "验证并连接" }));
    await waitFor(() => expect(screen.getByRole("status", { name: "助手连接状态" })).toHaveTextContent("机器码已绑定，正在检查助手状态"));
    expect(sockets[0].send).toHaveBeenCalledWith(JSON.stringify({ action: "heartbeat" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    emit(true, "助手已连接，可开始面试。现有助手不回报实时权限状态。");
    expect(screen.getByRole("button", { name: "开始模拟面试 →" })).toBeEnabled();
    expect(screen.getByRole("status", { name: "助手连接状态" })).toHaveTextContent("现有助手不回报实时权限状态");
    expect(screen.queryByText(/正在检查助手状态/)).not.toBeInTheDocument();
    expect(sockets[0].send.mock.calls.map(([payload]: [string]) => JSON.parse(payload).action)).toEqual(["heartbeat"]);
    expect(vi.mocked(mockRequest).mock.calls.filter(([path, body]) => path === "/mock-interviews" && body)).toHaveLength(0);
    emit(false, "请先连接在线的桌面助手。");
    expect(screen.getByRole("button", { name: "开始模拟面试 →" })).toBeDisabled();
    expect(screen.getByRole("status", { name: "助手连接状态" })).toHaveTextContent("请先连接在线的桌面助手。");
  });
  it("preserves pre-pause answers, replaces same-epoch partials, and rejects stale transcripts", async () => {
    const sockets: any[] = [];
    vi.stubGlobal("WebSocket", class {
      static OPEN = 1; readyState = 1; onmessage: any; onopen: any; onclose: any;
      send = vi.fn(); close = vi.fn(); constructor() { sockets.push(this); }
    });
    vi.spyOn(authClient, "readStoredSession").mockReturnValue({ accessToken: "synthetic-owner", account: { id: "synthetic" } } as ReturnType<typeof authClient.readStoredSession>);
    let row = { ...session, report: null, state: { ...session.state, phase: "listening" as const, capture_epoch: "a".repeat(32) } };
    vi.mocked(mockRequest).mockImplementation(async path => path.endsWith("capabilities") ? { enabled: true } : row);
    render(<MemoryRouter initialEntries={["/app/mock-interviews/mock-synthetic"]}><Routes><Route path="/app/mock-interviews/:id" element={<MockInterviewPage />} /></Routes></MemoryRouter>);
    await waitFor(() => expect(sockets).toHaveLength(1));
    const emit = (message: object) => act(() => sockets[0].onmessage({ data: JSON.stringify(message) }));
    emit({ type: "state", session: row, desktopConnected: true });
    emit({ type: "transcript", epoch: row.state.capture_epoch, text: "先检查错误率。" });
    emit({ type: "state", session: { ...row, state: { ...row.state, phase: "paused", capture_epoch: null } }, desktopConnected: true });
    row = { ...row, state: { ...row.state, capture_epoch: "b".repeat(32) } };
    emit({ type: "state", session: row, desktopConnected: true });
    emit({ type: "transcript", epoch: row.state.capture_epoch, text: "再看延迟" });
    emit({ type: "transcript", epoch: row.state.capture_epoch, text: "再看接口延迟。" });
    emit({ type: "transcript", epoch: "a".repeat(32), text: "旧轮内容" });
    expect(screen.getByRole("textbox", { name: "你的回答" })).toHaveValue("先检查错误率。 再看接口延迟。");
    fireEvent.change(screen.getByRole("textbox", { name: "你的回答" }), { target: { value: "人工校正后的回答" } });
    emit({ type: "transcript", epoch: row.state.capture_epoch, text: "新的转写" });
    expect(screen.getByRole("textbox", { name: "你的回答" })).toHaveValue("人工校正后的回答");
  });
});


describe("mock permission recovery without a companion update", () => {
  beforeEach(() => { vi.resetAllMocks(); });
  afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
  const rowFor = (phase: MockSession["state"]["phase"]): MockSession => ({ ...session, report: null,
    state: { ...session.state, phase, rounds: phase === "preparing" ? [] : session.state.rounds } });
  const deferred = () => {
    let resolve!: () => void; let reject!: (cause: Error) => void;
    const promise = new Promise<void>((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
  };
  async function open(row: MockSession) {
    const sockets: any[] = [];
    vi.stubGlobal("WebSocket", class {
      static OPEN = 1; readyState = 1; onmessage: any; onopen: any; onclose: any;
      send = vi.fn(); close = vi.fn(); constructor() { sockets.push(this); }
    });
    vi.spyOn(authClient, "readStoredSession").mockReturnValue({ accessToken: "synthetic-owner", account: { id: "synthetic" } } as ReturnType<typeof authClient.readStoredSession>);
    vi.mocked(mockRequest).mockImplementation(async path => path.endsWith("capabilities") ? { enabled: true } : path.startsWith("/documents") ? [] : row);
    const rendered = render(<MemoryRouter initialEntries={["/app/mock-interviews/mock-synthetic"]}><Routes><Route path="/app/mock-interviews/:id" element={<MockInterviewPage />} /></Routes></MemoryRouter>);
    await waitFor(() => expect(sockets).toHaveLength(1));
    const socket = sockets[0];
    const emit = (message: object) => act(() => socket.onmessage({ data: JSON.stringify(message) }));
    const state = (preparation?: object, next = row, desktopConnected = true) => emit({ type: "state", session: next, desktopConnected, microphoneConnected: false, preparation });
    const commands = () => socket.send.mock.calls.map(([payload]: [string]) => JSON.parse(payload).action);
    return { ...rendered, socket, emit, state, commands };
  }
  const checking = { ready: false, code: "mock_microphone_checking", message: "正在检查麦克风，请保持助手运行。" };
  const ready = { ready: true, code: "mock_ready", message: "助手已连接，可开始面试。" };

  it("bounds unknown guidance without extra polling and throttles same-session rechecks", async () => {
    const app = await open(rowFor("preparing"));
    vi.useFakeTimers();
    app.state(checking, rowFor("preparing"), false);
    expect(screen.getByRole("status", { name: "助手连接状态" })).toHaveTextContent("正在检查麦克风");
    expect(screen.getByRole("button", { name: "开始模拟面试 →" })).toBeDisabled();
    act(() => vi.advanceTimersByTime(20_000));
    app.state(checking, rowFor("preparing"), false);
    act(() => vi.advanceTimersByTime(10_000));
    expect(screen.getByRole("status", { name: "助手连接状态" })).toHaveTextContent("麦克风状态尚未确认");
    expect(app.commands()).toEqual([]);
    fireEvent.click(screen.getByRole("button", { name: "重新检查麦克风" }));
    fireEvent.click(screen.getByRole("button", { name: "正在重新检查…" }));
    expect(app.commands()).toEqual(["heartbeat"]);
    expect(screen.getByRole("button", { name: "正在重新检查…" })).toBeDisabled();
    act(() => vi.advanceTimersByTime(2000));
    expect(screen.getByRole("status", { name: "助手连接状态" })).toHaveTextContent("麦克风状态尚未确认");
    fireEvent.click(screen.getByRole("button", { name: "重新检查麦克风" }));
    expect(app.commands()).toEqual(["heartbeat", "heartbeat"]);
    app.state(ready);
    expect(screen.getByRole("button", { name: "开始模拟面试 →" })).toBeEnabled();
    expect(screen.getByRole("status", { name: "助手连接状态" })).toHaveTextContent(ready.message);
    expect(vi.mocked(mockRequest).mock.calls.every(([, body]) => body === undefined)).toBe(true);
    app.unmount();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("uses the existing five-second heartbeat while checking and clears timers on disconnect", async () => {
    const app = await open(rowFor("preparing"));
    vi.useFakeTimers();
    act(() => app.socket.onopen());
    app.state(checking, rowFor("preparing"), false);
    act(() => vi.advanceTimersByTime(15_000));
    expect(app.commands()).toEqual([undefined, "heartbeat", "heartbeat", "heartbeat"]);
    act(() => { app.socket.readyState = 3; app.socket.onclose(); });
    expect(screen.queryByRole("button", { name: "重新检查麦克风" })).toBeDisabled();
    expect(vi.getTimerCount()).toBe(0);
    act(() => vi.advanceTimersByTime(30_000));
    expect(screen.queryByText(/麦克风状态尚未确认/)).not.toBeInTheDocument();
  });

  it("clears only stale microphone start errors after authoritative recovery", async () => {
    const app = await open(rowFor("preparing"));
    app.state(checking, rowFor("preparing"), false);
    app.emit({ type: "error", code: "mock_microphone_checking", message: "正在检查麦克风，请稍候重试。" });
    expect(screen.getByRole("alert")).toHaveTextContent("正在检查麦克风");
    app.state(ready);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    app.emit({ type: "error", code: "mock_generation_unavailable", message: "合成服务暂时不可用。" });
    app.state(ready);
    expect(screen.getByRole("alert")).toHaveTextContent("合成服务暂时不可用");
    expect(app.commands()).toEqual([]);
  });

  it("keeps explicit denial blocked and allows a check without rebinding or losing the resume", async () => {
    const app = await open(rowFor("preparing"));
    app.state({ ready: false, code: "mock_microphone_required", message: "助手当前上报麦克风未授权，请检查后重新检查。" }, rowFor("preparing"), false);
    expect(screen.getByRole("button", { name: "开始模拟面试 →" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "重新检查麦克风" }));
    expect(app.commands()).toEqual(["heartbeat"]);
    expect(vi.mocked(mockRequest).mock.calls.some(([, body]) => body !== undefined)).toBe(false);
  });

  it.each(["automatic-first", "manual-first"])("sends one speak when auto/manual unlock race: %s", async order => {
    const automatic = deferred(); const manual = deferred();
    const unlock = vi.spyOn(MockVoicePlayer.prototype, "unlock").mockReturnValueOnce(automatic.promise).mockReturnValueOnce(manual.promise);
    const app = await open(rowFor("speaking"));
    // Restore via the authoritative state rather than starting a new session.
    app.state(ready, rowFor("paused")); app.state(ready);
    expect(unlock).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("status", { name: "网页声音状态" })).toHaveTextContent("正在准备网页声音");
    fireEvent.click(screen.getByRole("button", { name: "朗读问题" }));
    fireEvent.click(screen.getByRole("button", { name: "朗读问题" }));
    expect(unlock).toHaveBeenCalledTimes(2);
    if (order === "automatic-first") {
      await act(async () => automatic.resolve()); expect(app.commands()).toEqual([]);
      await act(async () => manual.resolve());
    } else {
      await act(async () => manual.resolve()); await act(async () => automatic.resolve());
    }
    expect(app.commands()).toEqual(["speak"]);
  });

  it("offers browser-sound retry after unlock rejection without reporting microphone denial", async () => {
    const unlock = vi.spyOn(MockVoicePlayer.prototype, "unlock").mockRejectedValueOnce(new Error("synthetic resume failure")).mockResolvedValueOnce();
    const app = await open(rowFor("speaking"));
    app.state(ready, rowFor("paused")); app.state(ready);
    expect(await screen.findByRole("status", { name: "网页声音状态" })).toHaveTextContent("网页声音尚未就绪");
    expect(screen.getByRole("button", { name: "朗读问题" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "朗读问题" }));
    await waitFor(() => expect(app.commands()).toEqual(["speak"]));
    expect(unlock).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole("status", { name: "网页声音状态" })).not.toBeInTheDocument();
  });

  it.each(["skip", "pause", "disconnect", "end", "unmount"])("ignores a late automatic unlock after %s", async change => {
    const pending = deferred(); vi.spyOn(MockVoicePlayer.prototype, "unlock").mockReturnValue(pending.promise);
    const app = await open(rowFor("speaking"));
    app.state(ready, rowFor("paused")); app.state(ready);
    if (change === "skip") fireEvent.click(screen.getByRole("button", { name: "我已读完，开始回答" }));
    if (change === "pause") app.state(ready, rowFor("paused"));
    if (change === "disconnect") act(() => { app.socket.readyState = 3; app.socket.onclose(); });
    if (change === "end") { vi.spyOn(window, "confirm").mockReturnValue(true); fireEvent.click(screen.getByRole("button", { name: "结束面试" })); }
    if (change === "unmount") app.unmount();
    await act(async () => pending.resolve());
    expect(app.commands().filter((action: string) => ["speak", "listen", "start"].includes(action))).toEqual([]);
  });


  it("gives an available start retry after browser unlock fails in preparation", async () => {
    const unlock = vi.spyOn(MockVoicePlayer.prototype, "unlock").mockRejectedValueOnce(new Error("synthetic blocked resume")).mockResolvedValueOnce();
    const app = await open(rowFor("preparing")); app.state(ready);
    fireEvent.click(screen.getByRole("button", { name: "开始模拟面试 →" }));
    expect(await screen.findByRole("status", { name: "网页声音状态" })).toHaveTextContent("请再次点击开始模拟面试重试");
    expect(screen.getByRole("button", { name: "开始模拟面试 →" })).toBeEnabled();
    expect(app.commands()).toEqual([]);
    fireEvent.click(screen.getByRole("button", { name: "开始模拟面试 →" }));
    await waitFor(() => expect(app.commands()).toEqual(["start"]));
    expect(unlock).toHaveBeenCalledTimes(2);
  });

  it("retains an available resume instruction after browser playback suspension pauses the question", async () => {
    vi.spyOn(MockVoicePlayer.prototype, "unlock").mockResolvedValue();
    vi.spyOn(MockVoicePlayer.prototype, "append").mockImplementation(() => { throw new MockPlaybackError(); });
    const app = await open(rowFor("speaking")); app.state(ready, rowFor("paused")); app.state(ready);
    await act(async () => {});
    app.emit({ type: "audio", questionId: "q1", pcm: "AAA=" });
    expect(app.commands()).toContain("pause");
    app.state(ready, rowFor("paused"));
    expect(screen.getByRole("status", { name: "网页声音状态" })).toHaveTextContent("请点击继续本题后恢复朗读");
    expect(screen.getByRole("button", { name: "继续本题" })).toBeEnabled();
  });


  it("tries restoring the first received speaking state and fences a replaced question", async () => {
    const stale = deferred(); const fresh = deferred();
    vi.spyOn(MockVoicePlayer.prototype, "unlock").mockReturnValueOnce(stale.promise).mockReturnValueOnce(fresh.promise);
    const app = await open(rowFor("speaking")); app.state(ready);
    expect(screen.getByRole("status", { name: "网页声音状态" })).toHaveTextContent("正在准备网页声音");
    const next = { ...rowFor("speaking"), state: { ...rowFor("speaking").state, rounds: [{ ...session.state.rounds[0]!, question_id: "synthetic-q2" }] } };
    app.state(ready, next);
    await act(async () => stale.resolve()); expect(app.commands()).toEqual([]);
    await act(async () => fresh.resolve()); expect(app.commands()).toEqual(["speak"]);
    expect(JSON.parse(app.socket.send.mock.calls[0][0]).questionId).toBe("synthetic-q2");
  });

  it.each(["unmount", "reconnect"])("ignores a late socket open after %s without authenticating or leaking heartbeats", async change => {
    const app = await open(rowFor("preparing"));
    vi.useFakeTimers();
    if (change === "unmount") app.unmount();
    else fireEvent.click(screen.getByRole("button", { name: "重新连接" }));
    act(() => app.socket.onopen());
    act(() => vi.advanceTimersByTime(15_000));
    expect(app.commands()).toEqual([]);
    expect(vi.getTimerCount()).toBe(0);
  });


  it("cancels a pending start when the confirmed resume changes and keeps retry available", async () => {
    const pending = deferred(); vi.spyOn(MockVoicePlayer.prototype, "unlock").mockReturnValue(pending.promise);
    const app = await open(rowFor("preparing")); app.state(ready);
    fireEvent.click(screen.getByRole("button", { name: "开始模拟面试 →" }));
    app.state(ready, { ...rowFor("preparing"), resumeId: "synthetic-other-resume", resumeVersion: "v2" });
    await act(async () => pending.resolve());
    expect(app.commands()).toEqual([]);
    expect(screen.getByRole("button", { name: "开始模拟面试 →" })).toBeEnabled();
  });

  it("does not start when readiness is lost during a user-gesture unlock", async () => {
    const pending = deferred(); vi.spyOn(MockVoicePlayer.prototype, "unlock").mockReturnValue(pending.promise);
    const app = await open(rowFor("preparing")); app.state(ready);
    fireEvent.click(screen.getByRole("button", { name: "开始模拟面试 →" }));
    app.state(checking, rowFor("preparing"), false);
    await act(async () => pending.resolve());
    expect(app.commands()).toEqual([]);
    expect(screen.getByRole("button", { name: "开始模拟面试 →" })).toBeDisabled();
  });
});

describe("mock session action lifecycle fences", () => {
  beforeEach(() => { vi.resetAllMocks(); });
  afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
  const row = (suffix: string, phase: MockSession["state"]["phase"] = "preparing"): MockSession => ({
    ...session, sessionId: `synthetic-${suffix}`, title: `合成场次 ${suffix}`, report: null,
    resumeId: `resume-${suffix}`, state: { ...session.state, phase, rounds: phase === "preparing" ? [] : session.state.rounds },
  });
  function pending<T>() {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>(yes => { resolve = yes; });
    return { promise, resolve };
  }
  function Navigation() {
    const navigate = useNavigate();
    return <><button onClick={() => navigate("/app/mock-interviews/synthetic-A")}>前往 A</button><button onClick={() => navigate("/app/mock-interviews/synthetic-B")}>前往 B</button></>;
  }
  async function open(phase: MockSession["state"]["phase"] = "preparing") {
    const selection = pending<MockSession>(); const binding = pending<unknown>();
    const sockets: any[] = [];
    vi.stubGlobal("WebSocket", class {
      static OPEN = 1; readyState = 1; onmessage: any; onopen: any; onclose: any;
      send = vi.fn(); close = vi.fn(); constructor() { sockets.push(this); }
    });
    vi.spyOn(authClient, "readStoredSession").mockReturnValue({ accessToken: "synthetic-owner", account: { id: "synthetic" } } as ReturnType<typeof authClient.readStoredSession>);
    const docs = ["A", "B", "selected"].map(id => ({ documentId: `resume-${id}`, displayName: `合成简历 ${id}`, documentVersionId: "v1", status: "ready", indexState: "indexed" }));
    vi.mocked(mockRequest).mockImplementation(async path => {
      if (path.endsWith("capabilities")) return { enabled: true };
      if (path.startsWith("/documents")) return docs;
      if (path.endsWith("/resume")) return selection.promise;
      if (path.endsWith("/desktop-binding")) return binding.promise;
      return row(path.endsWith("synthetic-B") ? "B" : "A", phase);
    });
    const rendered = render(<MemoryRouter initialEntries={["/app/mock-interviews/synthetic-A"]}><Navigation /><Routes><Route path="/app/mock-interviews/:id" element={<MockInterviewPage />} /></Routes></MemoryRouter>);
    await waitFor(() => expect(sockets).toHaveLength(1));
    const state = (socket: any, next: MockSession, microphoneConnected = true) => act(() => socket.onmessage({ data: JSON.stringify({ type: "state", session: next, desktopConnected: true, microphoneConnected,
      preparation: { ready: true, code: "mock_ready", message: "助手已就绪。" } }) }));
    state(sockets[0], row("A", phase));
    if (phase === "preparing") await screen.findByRole("option", { name: "合成简历 selected" });
    const commands = (socket: any) => socket.send.mock.calls.map(([payload]: [string]) => JSON.parse(payload).action);
    return { ...rendered, sockets, selection, binding, state, commands };
  }
  const selected = (): MockSession => ({ ...row("A"), resumeId: "resume-selected", state: { ...row("A").state, version: 6 } });

  it.each([false, true])("ignores a late resume response after changing sessions, including returning to A: %s", async returnToA => {
    const app = await open();
    fireEvent.change(screen.getByLabelText("选择简历"), { target: { value: "resume-selected" } });
    fireEvent.click(screen.getByRole("button", { name: "前往 B" }));
    await screen.findByRole("heading", { name: "合成场次 B" });
    await waitFor(() => expect(app.sockets).toHaveLength(2)); app.state(app.sockets[1], row("B"));
    if (returnToA) {
      fireEvent.click(screen.getByRole("button", { name: "前往 A" }));
      await screen.findByRole("heading", { name: "合成场次 A" });
      await waitFor(() => expect(app.sockets).toHaveLength(3)); app.state(app.sockets[2], row("A"));
    }
    await act(async () => app.selection.resolve(selected()));
    expect(screen.getByRole("heading", { name: `合成场次 ${returnToA ? "A" : "B"}` })).toBeInTheDocument();
    expect(screen.getByLabelText("选择简历")).toHaveValue(`resume-${returnToA ? "A" : "B"}`);
    expect(screen.getByRole("button", { name: "开始模拟面试 →" })).toBeEnabled();
    expect(app.commands(app.sockets.at(-1))).toEqual([]);
  });

  it("accepts the current same-session resume response", async () => {
    const app = await open();
    fireEvent.change(screen.getByLabelText("选择简历"), { target: { value: "resume-selected" } });
    await act(async () => app.selection.resolve(selected()));
    expect(screen.getByLabelText("选择简历")).toHaveValue("resume-selected");
    expect(screen.getByRole("button", { name: "开始模拟面试 →" })).toBeEnabled();
  });

  it("does not rewind an ended session when an older resume response arrives", async () => {
    const app = await open(); vi.spyOn(window, "confirm").mockReturnValue(true);
    fireEvent.change(screen.getByLabelText("选择简历"), { target: { value: "resume-selected" } });
    app.state(app.sockets[0], selected());
    fireEvent.click(screen.getByRole("button", { name: "结束面试" }));
    app.state(app.sockets[0], { ...selected(), state: { ...selected().state, phase: "completed", version: 7 } });
    await act(async () => app.selection.resolve(selected()));
    expect(screen.getByText("本场练习已结束")).toBeInTheDocument();
    expect(screen.queryByLabelText("选择简历")).not.toBeInTheDocument();
  });

  it.each(["another-session", "reconnect"])("ignores a late binding response after %s", async change => {
    const app = await open();
    fireEvent.change(screen.getByLabelText("桌面助手机器码"), { target: { value: "000000" } });
    fireEvent.click(screen.getByRole("button", { name: "验证并连接" }));
    if (change === "another-session") {
      fireEvent.click(screen.getByRole("button", { name: "前往 B" }));
      await screen.findByRole("heading", { name: "合成场次 B" });
    } else {
      act(() => { app.sockets[0].readyState = 3; app.sockets[0].onclose(); });
      fireEvent.click(screen.getByRole("button", { name: "重新连接" }));
    }
    await waitFor(() => expect(app.sockets).toHaveLength(2));
    app.state(app.sockets[1], row(change === "another-session" ? "B" : "A"));
    await act(async () => app.binding.resolve({ bound: true }));
    expect(screen.getByRole("status", { name: "助手连接状态" })).toHaveTextContent("助手已就绪。");
    expect(app.commands(app.sockets[1])).toEqual([]);
    expect(screen.getByRole("button", { name: "开始模拟面试 →" })).toBeEnabled();
  });

  it.each(["settling", "waiting"])("ending immediately fences %s microphone-listen intent before server acknowledgement", async phase => {
    vi.spyOn(MockVoicePlayer.prototype, "unlock").mockResolvedValue(); vi.spyOn(window, "confirm").mockReturnValue(true);
    const app = await open("speaking"); await act(async () => {});
    app.state(app.sockets[0], row("A", "speaking"), phase !== "waiting");
    app.sockets[0].send.mockClear(); vi.useFakeTimers();
    fireEvent.click(screen.getByRole("button", { name: "我已读完，开始回答" }));
    if (phase === "waiting") act(() => vi.advanceTimersByTime(1500));
    fireEvent.click(screen.getByRole("button", { name: "结束面试" }));
    if (phase === "settling") act(() => vi.advanceTimersByTime(1500));
    else app.state(app.sockets[0], row("A", "speaking"));
    expect(app.commands(app.sockets[0])).toEqual(["end"]);
    expect(screen.queryByText(/正在等待助手收音通道连接/)).not.toBeInTheDocument();
  });
});
