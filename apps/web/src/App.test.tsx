import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App, interviewContinuationRoute } from "./App";
import { interviewAppAdapter } from "./app-adapter";
import { authClient } from "./auth-client";
import { syntheticState } from "./test-state";

const clonedState = () => structuredClone(syntheticState);

const openAt = (path: string, authenticated = false) => {
  window.history.pushState({}, "", path);
  return render(<App initialAuthenticated={authenticated} initialState={clonedState()} />);
};

const openAtWithState = (path: string, state = clonedState(), authenticated = false) => {
  window.history.pushState({}, "", path);
  return render(<App initialAuthenticated={authenticated} initialState={state} />);
};

const login = async (destination = "/login") => {
  openAt(destination === "/login" ? "/app" : destination, true);
  await screen.findByRole("heading", { name: "继续这场面试" });
};

describe("OfferSteady web application", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/");
    vi.restoreAllMocks();
    vi.spyOn(interviewAppAdapter, "startInterviewSession").mockImplementation(async id => ({
      ...(syntheticState.interviews.find(item => item.id === id) ?? syntheticState.interviews[0]!),
      id,
      status: "active",
      updatedAt: "刚刚",
    }));
    vi.spyOn(interviewAppAdapter, "getActiveInterviewConflict").mockImplementation(async id => ({ currentInterviewId: id, activeInterview: null }));
    vi.spyOn(interviewAppAdapter, "supersedeActiveInterview").mockResolvedValue([]);
    vi.spyOn(interviewAppAdapter, "controlInterviewCapture").mockImplementation(async (_id, action) => action === "pause" ? "paused" : "capturing");
    vi.spyOn(interviewAppAdapter, "getDesktopDeviceBinding").mockResolvedValue(null);
    vi.spyOn(interviewAppAdapter, "getLastDesktopDevice").mockResolvedValue({
      deviceId: "fixture-last-device",
      displayName: "上次使用的 Mac",
      maskedManualCode: "••••56",
      capabilities: { microphone: true, systemAudio: true },
      online: true,
      lastSeenAtMs: Date.now(),
    });
    vi.spyOn(interviewAppAdapter, "bindDesktopDevice").mockImplementation(async command => ({
      bindingId: `fixture-binding-${command.manualCode}`,
      sessionId: command.interviewId,
      deviceId: `fixture-device-${command.manualCode}`,
      manualCode: command.manualCode ?? "••••56",
      displayName: "面试稳伴随程序 · Mac",
      capabilities: { microphone: true, systemAudio: true, screenCapture: true },
      status: "bound",
      boundAtMs: Date.now(),
      lastSeenAtMs: Date.now(),
    }));
    vi.spyOn(interviewAppAdapter, "submitManualAnswer").mockImplementation(async command => {
      const taskId = `answer-${command.idempotencyKey.replace(/[^a-zA-Z0-9-]/g, "-")}`;
      return {
        question: {
          id: taskId,
          askedAt: "刚刚",
          text: command.question,
          input: "manual",
          status: "confirmed",
          advice: {
            outline: [],
            detail: `这是来自后端模型链路的测试回答：${command.question}`,
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
          status: "completed",
          question: command.question,
          completedText: `这是来自后端模型链路的测试回答：${command.question}`,
          updatedAtMs: Date.now(),
        },
      };
    });
    vi.spyOn(interviewAppAdapter, "submitScreenshotAnswer").mockImplementation(async command => {
      const taskId = `screenshot-${command.interviewId}`;
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
            inference: "测试环境中的远程截屏回答结果。",
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
  });

  it("routes each interview state through one continuation resolver", () => {
    expect(interviewContinuationRoute({ id: "a", status: "preparing" })).toBe("/app/interviews/a/prepare");
    expect(interviewContinuationRoute({ id: "a", status: "ready" })).toBe("/app/interviews/a/prepare");
    expect(interviewContinuationRoute({ id: "a", status: "active" })).toBe("/app/interviews/a/live");
    expect(interviewContinuationRoute({ id: "a", status: "paused" })).toBe("/app/interviews/a/live");
    expect(interviewContinuationRoute({ id: "a", status: "error" })).toBe("/app/interviews/a/live");
    expect(interviewContinuationRoute({ id: "a", status: "ended" })).toBe("/app/interviews/a/review");
  });

  it("leads with product value and keeps boundaries secondary", () => {
    openAt("/");
    expect(screen.getByRole("heading", { name: /更从容地冲刺 Offer/ })).toBeInTheDocument();
    expect(screen.getByText(/结合你的简历、岗位要求和个人资料/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "从听懂问题，到组织答案，现场更从容。" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "实时抓住问题重点" })).toBeInTheDocument();
    expect(screen.getByText(/AI 内容为回答建议/)).toBeInTheDocument();
    expect(screen.queryByText("CLEAR BOUNDARIES")).not.toBeInTheDocument();
  });

  it("protects interview content behind the prototype identity", async () => {
    openAt("/app/interviews/demo/live");
    expect(await screen.findByRole("heading", { name: "开始你的面试准备" })).toBeInTheDocument();
    expect(screen.queryByText("请介绍一个你负责过的、最有挑战的前端项目。")).not.toBeInTheDocument();
  });

  it("shows a user-correctable message when the SMS verification code is wrong", async () => {
    vi.spyOn(authClient, "sendSmsCode").mockResolvedValue({
      challengeId: "sms-challenge-ui-error",
      status: "sent",
      provider: "aliyun-dypnsapi",
      expiresAtMs: Date.now() + 300_000,
      cooldownSeconds: 0,
      maskedPhone: "157****8798",
    });
    vi.spyOn(authClient, "verifySmsLogin").mockRejectedValue(
      new Error("验证码不正确或已过期，请检查后重新输入。"),
    );
    openAt("/login");

    fireEvent.change(screen.getByPlaceholderText("请输入手机号"), {
      target: { value: "15773668798" },
    });
    fireEvent.click(screen.getByRole("button", { name: "获取验证码" }));
    const codeInput = await screen.findByPlaceholderText("请输入验证码");
    fireEvent.change(codeInput, { target: { value: "610368" } });
    fireEvent.click(screen.getByRole("button", { name: "登录 / 注册" }));

    expect(
      await screen.findByText("验证码不正确或已过期，请检查后重新输入。"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/短信校验服务暂时不可用/)).not.toBeInTheDocument();
    expect(codeInput).toHaveValue("610368");
  });

  it("enters the app and shows an action-oriented home", async () => {
    await login();
    expect(screen.getByRole("link", { name: /新建面试/ })).toBeInTheDocument();
    expect(screen.getAllByText("高级前端工程师面试").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "继续这场面试" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "继续面试" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /预览工作台|继续准备/ })).not.toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "应用导航" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "移动端应用导航" })).toBeInTheDocument();
  });

  it("bootstraps prototype account storage for authenticated initial app sessions", async () => {
    const store = new Map<string, string>();
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: {
        getItem: (key: string) => store.get(key) ?? null,
        setItem: (key: string, value: string) => void store.set(key, value),
        removeItem: (key: string) => void store.delete(key),
      },
    });
    authClient.clear();
    window.history.pushState({}, "", "/app");
    render(<App initialAuthenticated initialState={clonedState()} />);
    await screen.findByRole("heading", { name: "继续这场面试" });
    expect(authClient.readStoredAccount()).toMatchObject({
      id: syntheticState.account.id,
      displayName: syntheticState.account.displayName,
    });
  });

  it("validates and creates an interview draft", async () => {
    vi.spyOn(interviewAppAdapter, "createDraft").mockResolvedValue({
      id: "draft",
      title: "前端架构师终面",
      role: "前端架构师",
      status: "preparing",
      updatedAt: "刚刚",
      readiness: 0,
    });
    const firstUseState = clonedState();
    firstUseState.interviews = [];
    openAtWithState("/app/interviews/new", firstUseState, true);
    expect(screen.getByLabelText("面试名称")).toHaveValue("");
    expect(screen.getByLabelText("目标岗位")).toHaveValue("");
    expect(screen.getByLabelText("公司（可选）")).toHaveValue("");
    fireEvent.click(screen.getByRole("button", { name: /保存并准备/ }));
    expect(screen.getByRole("alert")).toHaveTextContent("请填写面试名称和目标岗位");
    fireEvent.change(screen.getByLabelText("面试名称"), { target: { value: "前端架构师终面" } });
    fireEvent.change(screen.getByLabelText("目标岗位"), { target: { value: "前端架构师" } });
    fireEvent.click(screen.getByRole("button", { name: /保存并准备/ }));
    expect(await screen.findByRole("heading", { name: "前端架构师终面" })).toBeInTheDocument();
    expect(screen.getByText("输入机器码连接本场")).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "一键连接上次设备" }));
    await waitFor(() => expect(interviewAppAdapter.bindDesktopDevice).toHaveBeenCalledWith({
      interviewId: "draft",
      reuseLastDevice: true,
    }, expect.any(AbortSignal)));
    expect(screen.getByText("本场已连接：面试稳伴随程序 · Mac")).toBeInTheDocument();
  });

  it("prefills a new interview from the current account latest interview and keeps it editable", async () => {
    const createDraft = vi.spyOn(interviewAppAdapter, "createDraft").mockImplementation(async input => ({
      id: "prefilled-draft",
      title: input.title,
      role: input.role,
      ...(input.company ? { company: input.company } : {}),
      status: "preparing",
      updatedAt: "刚刚",
      readiness: 0,
    }));
    const state = clonedState();
    state.interviews = [
      { id: "latest", title: "算法工程师二面", role: "算法工程师", company: "示例智能", status: "ended", updatedAt: "刚刚", readiness: 100 },
      { id: "older", title: "前端工程师一面", role: "前端工程师", company: "示例科技", status: "ended", updatedAt: "昨天", readiness: 100 },
    ];
    openAtWithState("/app/interviews/new", state, true);

    expect(screen.getByLabelText("面试名称")).toHaveValue("算法工程师二面");
    expect(screen.getByLabelText("目标岗位")).toHaveValue("算法工程师");
    expect(screen.getByLabelText("公司（可选）")).toHaveValue("示例智能");
    fireEvent.change(screen.getByLabelText("面试名称"), { target: { value: "算法工程师终面" } });
    fireEvent.change(screen.getByLabelText("公司（可选）"), { target: { value: "新公司" } });
    fireEvent.click(screen.getByRole("button", { name: /保存并准备/ }));

    await waitFor(() => expect(createDraft).toHaveBeenCalledWith({
      title: "算法工程师终面",
      role: "算法工程师",
      company: "新公司",
    }, expect.any(AbortSignal)));
  });

  it("shows the backend reason when creating an interview draft fails", async () => {
    vi.spyOn(interviewAppAdapter, "createDraft").mockRejectedValueOnce(new Error("面试创建失败，请稍后重试"));
    await login();
    fireEvent.click(screen.getByRole("link", { name: /新建面试/ }));
    fireEvent.change(screen.getByLabelText("面试名称"), { target: { value: "失败草稿" } });
    fireEvent.change(screen.getByLabelText("目标岗位"), { target: { value: "高级前端工程师" } });
    fireEvent.click(screen.getByRole("button", { name: /保存并准备/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("面试创建失败，请稍后重试");
    expect(screen.getByRole("heading", { name: "创建一场面试" })).toBeInTheDocument();
  });

  it("shows at most five recent interviews and allows deleting one safely", async () => {
    const state = clonedState();
    state.interviews = [
      { id: "i-1", title: "面试 1", role: "前端", status: "active", updatedAt: "刚刚", readiness: 100 },
      { id: "i-2", title: "面试 2", role: "前端", status: "preparing", updatedAt: "刚刚", readiness: 80 },
      { id: "i-3", title: "面试 3", role: "前端", status: "ended", updatedAt: "刚刚", readiness: 100 },
      { id: "i-4", title: "面试 4", role: "前端", status: "ended", updatedAt: "刚刚", readiness: 100 },
      { id: "i-5", title: "面试 5", role: "前端", status: "ended", updatedAt: "刚刚", readiness: 100 },
      { id: "i-6", title: "面试 6", role: "前端", status: "ended", updatedAt: "刚刚", readiness: 100 },
    ];
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(interviewAppAdapter, "deleteInterview").mockResolvedValue(undefined);
    vi.spyOn(interviewAppAdapter, "loadState").mockResolvedValue({
      ...state,
      interviews: state.interviews.filter(item => item.id !== "i-1").slice(0, 5),
    });
    openAtWithState("/app", state, true);
    await screen.findByRole("heading", { name: "继续这场面试" });
    expect(screen.getByText("5 / 5 场")).toBeInTheDocument();
    expect(screen.queryByText("面试 6")).not.toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "删除" })[0]!);
    await waitFor(() => expect(interviewAppAdapter.deleteInterview).toHaveBeenCalledWith("i-1", expect.any(AbortSignal)));
    await waitFor(() => expect(screen.queryByText("面试 1")).not.toBeInTheDocument());
  });

  it("enters the live workspace after materials are confirmed without a generic privacy checkbox", async () => {
    await login();
    window.history.pushState({}, "", "/app/interviews/demo/prepare");
    window.dispatchEvent(new PopStateEvent("popstate"));
    fireEvent.click(await screen.findByRole("button", { name: "一键连接上次设备" }));
    const start = await screen.findByRole("button", { name: /开始面试/ });
    expect(start).toBeEnabled();
    expect(screen.queryByRole("checkbox", { name: /数据用途/ })).not.toBeInTheDocument();
    expect(screen.getByText(/本地端会沿用首次授权并检查音频与问题检测/)).toBeInTheDocument();
    expect(screen.getByText(/麦克风和屏幕权限只由桌面助手首次申请/)).toBeInTheDocument();
    fireEvent.click(start);
    await waitFor(() => expect(interviewAppAdapter.startInterviewSession).toHaveBeenCalledWith("demo", expect.any(AbortSignal)));
    expect((await screen.findAllByText("请介绍一个你负责过的、最有挑战的前端项目。")).length).toBeGreaterThan(0);
    expect(screen.getByText("等待开始面试")).toBeInTheDocument();
    expect(screen.getByText("这台设备 · 已连接，未采集")).toBeInTheDocument();
  });

  it("keeps the user on preparation when backend session start fails", async () => {
    vi.spyOn(interviewAppAdapter, "startInterviewSession").mockRejectedValueOnce(new Error("后端会话启动失败，请重试"));
    await login();
    window.history.pushState({}, "", "/app/interviews/demo/prepare");
    window.dispatchEvent(new PopStateEvent("popstate"));
    fireEvent.click(await screen.findByRole("button", { name: "一键连接上次设备" }));
    fireEvent.click(await screen.findByRole("button", { name: /开始面试/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("后端会话启动失败，请重试");
    expect(screen.getByRole("heading", { name: "高级前端工程师面试" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "实时对话" })).not.toBeInTheDocument();
  });

  it("requires explicit takeover before binding a new interview to the desktop device", async () => {
    vi.mocked(interviewAppAdapter.getActiveInterviewConflict).mockResolvedValueOnce({
      currentInterviewId: "demo",
      activeInterview: { ...syntheticState.interviews[0]!, id: "previous-live", title: "上一场算法面试", status: "active" },
    });
    vi.mocked(interviewAppAdapter.supersedeActiveInterview).mockResolvedValueOnce(["previous-live"]);
    await login();
    window.history.pushState({}, "", "/app/interviews/demo/prepare");
    window.dispatchEvent(new PopStateEvent("popstate"));
    const dialog = await screen.findByRole("dialog", { name: "已有一场面试正在进行" });
    expect(within(dialog).getByText("上一场算法面试")).toBeInTheDocument();
    expect(interviewAppAdapter.bindDesktopDevice).not.toHaveBeenCalled();
    fireEvent.click(within(dialog).getByRole("button", { name: "结束上一场，准备当前面试" }));
    await waitFor(() => expect(interviewAppAdapter.supersedeActiveInterview).toHaveBeenCalledWith({
      interviewId: "demo",
      expectedPreviousInterviewId: "previous-live",
    }, expect.any(AbortSignal)));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "已有一场面试正在进行" })).not.toBeInTheDocument());
    expect(screen.getByRole("button", { name: "一键连接上次设备" })).toBeEnabled();
  });

  it("shows a manually submitted question as the latest answer", async () => {
    await login();
    window.history.pushState({}, "", "/app/interviews/demo/live");
    window.dispatchEvent(new PopStateEvent("popstate"));
    const input = await screen.findByPlaceholderText("输入面试官的问题");
    fireEvent.change(input, { target: { value: "如何设计前端监控系统？" } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "如何设计前端监控系统？" })).toBeInTheDocument());
  });

  it("shows the backend reason when manual answer is rejected by session state", async () => {
    vi.spyOn(interviewAppAdapter, "submitManualAnswer").mockRejectedValueOnce(new Error("只有进行中的面试会话才能发起实时回答。"));
    await login();
    window.history.pushState({}, "", "/app/interviews/demo/live");
    window.dispatchEvent(new PopStateEvent("popstate"));
    const input = await screen.findByPlaceholderText("输入面试官的问题");
    fireEvent.change(input, { target: { value: "为什么刚进入面试无法回答？" } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    expect((await screen.findAllByText("只有进行中的面试会话才能发起实时回答。")).length).toBeGreaterThan(0);
    expect(screen.queryByText("当前任务未启动，请检查积分或会员权益。")).not.toBeInTheDocument();
  });

  it("keeps the question visible when the backend reports a model runtime failure", async () => {
    vi.spyOn(interviewAppAdapter, "submitManualAnswer").mockRejectedValueOnce(new Error("当前对话模型鉴权失败，请检查服务配置。"));
    await login();
    window.history.pushState({}, "", "/app/interviews/demo/live");
    window.dispatchEvent(new PopStateEvent("popstate"));
    const input = await screen.findByPlaceholderText("输入面试官的问题");
    fireEvent.change(input, { target: { value: "模型不可用时如何保留问题？" } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    expect(await screen.findByRole("heading", { name: "模型不可用时如何保留问题？" })).toBeInTheDocument();
    expect((await screen.findAllByText("当前对话模型鉴权失败，请检查服务配置。")).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
  });


  it("keeps screenshot input inside the live workspace", async () => {
    await login();
    window.history.pushState({}, "", "/app/interviews/demo/live");
    window.dispatchEvent(new PopStateEvent("popstate"));
    fireEvent.click(await screen.findByRole("button", { name: /截屏回答/ }));
    expect((await screen.findAllByText("请设计一个支持实时协作的 Web 系统。")).length).toBeGreaterThan(0);
    expect(screen.queryByText("上传并识别")).not.toBeInTheDocument();
  });

  it("pauses and ends a session explicitly", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const captureControl = vi.mocked(interviewAppAdapter.controlInterviewCapture);
    await login();
    window.history.pushState({}, "", "/app/interviews/demo/live");
    window.dispatchEvent(new PopStateEvent("popstate"));
    fireEvent.click(await screen.findByRole("button", { name: "开始面试" }));
    expect(screen.getByText("这台设备 · 正在收音")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "暂停收音" }));
    expect(await screen.findByText("面试已暂停")).toBeInTheDocument();
    expect(captureControl).toHaveBeenCalledWith("demo", "pause", expect.any(AbortSignal));
    fireEvent.click(screen.getByRole("button", { name: "结束面试" }));
    expect(await screen.findByRole("heading", { name: "本场面试复盘" })).toBeInTheDocument();
  });

  it("separates generated review from original records and deletes screenshots after confirmation", async () => {
    vi.spyOn(interviewAppAdapter, "deleteScreenshot").mockResolvedValue(undefined);
    await login();
    window.history.pushState({}, "", "/app/interviews/review/review");
    window.dispatchEvent(new PopStateEvent("popstate"));
    expect(await screen.findByRole("heading", { name: "真实对话记录" })).toBeInTheDocument();
    expect(await screen.findByText("请介绍一下你如何推动跨团队协作。")).toBeInTheDocument();
    expect(await screen.findByText("我会先统一目标和交付边界，再建立固定同步机制。")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "问题与 AI 回答建议" })).toBeInTheDocument();
    expect(screen.getByText("生成建议，不代表实际作答")).toBeInTheDocument();
    expect(screen.getByText("AI 整理摘要")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "删除截图" }));
    await waitFor(() => expect(screen.queryByText("系统设计题（合成）.png")).not.toBeInTheDocument());
  });

  it("downloads the review locally and keeps the mobile transcript readable", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 390 });
    await login();
    window.history.pushState({}, "", "/app/interviews/review/review");
    window.dispatchEvent(new PopStateEvent("popstate"));

    const download = await screen.findByRole("button", { name: "下载 Word" });
    await waitFor(() => expect(download).toBeEnabled());
    expect(screen.getByText(/仅在你的浏览器本地生成/)).toBeInTheDocument();
    const click = vi.fn();
    const anchor = document.createElement("a");
    anchor.click = click;
    vi.spyOn(document, "createElement").mockReturnValue(anchor);
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:review");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    fireEvent.click(download);

    await waitFor(() => expect(URL.createObjectURL).toHaveBeenCalledOnce());
    expect(click).toHaveBeenCalledOnce();
    expect(screen.getByText(/Word 已生成并开始下载/)).toBeInTheDocument();
  });

  it("offers explicit macOS architectures and a truthful Windows preview", async () => {
    vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue("Mozilla/5.0 (Macintosh; Apple Silicon Mac OS X) arm64");
    vi.spyOn(window.navigator, "platform", "get").mockReturnValue("MacARM");
    await login();
    fireEvent.click(screen.getAllByRole("link", { name: /设备/ })[0]!);
    expect(await screen.findByRole("button", { name: /macOS Apple Silicon/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /macOS Intel/ })).toBeInTheDocument();
    expect(screen.getByText("这台 Mac")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Windows 10\/11/ }));
    expect(screen.getByRole("button", { name: "暂未开放下载" })).toBeDisabled();
    expect(screen.getByText(/系统音频：不可用/)).toBeInTheDocument();
  });

  it("completes the desktop prototype journey from home through review", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    window.history.pushState({}, "", "/app");
    render(<App initialAuthenticated initialState={clonedState()} />);
    fireEvent.click(await screen.findByRole("link", { name: "继续面试" }));
    fireEvent.click(await screen.findByRole("button", { name: "一键连接上次设备" }));
    const startInterview = screen.getByRole("button", { name: /开始面试/ });
    await waitFor(() => expect(startInterview).toBeEnabled());
    fireEvent.click(startInterview);
    fireEvent.click(await screen.findByRole("button", { name: "开始面试" }));
    const input = await screen.findByPlaceholderText("输入面试官的问题");
    fireEvent.change(input, { target: { value: "完整旅程测试问题" } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    fireEvent.click(screen.getByRole("button", { name: "结束面试" }));
    expect(await screen.findByRole("heading", { name: "本场面试复盘" })).toBeInTheDocument();
    expect(screen.getByText("完整旅程测试问题")).toBeInTheDocument();
  });

  it("uses one mobile workspace without a material drawer or desktop divider", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 390 });
    window.history.pushState({}, "", "/app/interviews/demo/live");
    render(<App initialAuthenticated initialState={clonedState()} />);
    expect(await screen.findByRole("heading", { name: "实时对话" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "回答" })).toBeInTheDocument();
    expect(screen.queryByRole("separator")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /资料/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "开始面试" }));
    fireEvent.click(screen.getByRole("button", { name: "暂停收音" }));
    expect(await screen.findByText("面试已暂停")).toBeInTheDocument();
  });
});
