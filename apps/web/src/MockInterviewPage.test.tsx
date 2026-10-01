import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MockInterviewPage, MockReportView } from "./MockInterviewPage";
import { mockRequest, type MockSession } from "./mock-interview-client";
import { authClient } from "./auth-client";
import { downloadMockInterviewWord } from "./mock-interview-word-export";

vi.mock("./mock-interview-word-export", () => ({ downloadMockInterviewWord: vi.fn() }));

vi.mock("./mock-interview-client", async importOriginal => ({
  ...await importOriginal<typeof import("./mock-interview-client")>(), mockRequest: vi.fn(),
}));

const quote = { activeTimeMember: true, dailyFreeRemaining: 2, entryPoints: 0, minutePoints: 0,
  billingClass: "daily_pass_free", savedCount: 0, savedLimit: 2 };
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
    expect(screen.getByText(/今日剩余 2 次/)).toBeInTheDocument();
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
  it("fourth member creation requires paid confirmation; cancel sends no creation request", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    vi.mocked(mockRequest).mockImplementation(async path => path.endsWith("capabilities") ? { enabled: true } : { sessions: [], quote: { ...quote, dailyFreeRemaining: 0, entryPoints: 100, minutePoints: 5, billingClass: "points" } });
    render(<MemoryRouter><MockInterviewPage /></MemoryRouter>);
    const button = await screen.findByRole("button", { name: "创建模拟面试 →" });
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button);
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining("每开始一分钟扣 5 积分"));
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
    expect(screen.getByText(/无需为模拟面试升级/)).toBeInTheDocument();
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
