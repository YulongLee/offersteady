import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { interviewAppAdapter } from "./app-adapter";
import type { WebAppState } from "./domain";
import { mockSuccessfulMaterialUploadAdapter } from "./test-adapter-builders";
import { syntheticState } from "./test-state";

const open = (path: string, mutate?: (state: WebAppState) => void) => {
  mockSuccessfulMaterialUploadAdapter();
  if (!vi.isMockFunction(interviewAppAdapter.startInterviewSession)) {
    vi.spyOn(interviewAppAdapter, "startInterviewSession").mockImplementation(async id => ({
      ...(syntheticState.interviews.find(item => item.id === id) ?? syntheticState.interviews[0]!),
      id,
      status: "active",
      updatedAt: "刚刚",
    }));
  }
  if (!vi.isMockFunction(interviewAppAdapter.getDesktopDeviceBinding)) {
    vi.spyOn(interviewAppAdapter, "getDesktopDeviceBinding").mockResolvedValue(null);
  }
  if (!vi.isMockFunction(interviewAppAdapter.bindDesktopDevice)) {
    vi.spyOn(interviewAppAdapter, "bindDesktopDevice").mockImplementation(async command => ({
      bindingId: `fixture-binding-${command.manualCode}`,
      sessionId: command.interviewId,
      deviceId: `fixture-device-${command.manualCode}`,
      manualCode: command.manualCode,
      displayName: "面试稳伴随程序 · Mac",
      capabilities: { microphone: true, systemAudio: true, screenCapture: true },
      status: "bound",
      boundAtMs: Date.now(),
      lastSeenAtMs: Date.now(),
    }));
  }
  if (!vi.isMockFunction(interviewAppAdapter.confirmInterviewMaterials)) {
    vi.spyOn(interviewAppAdapter, "confirmInterviewMaterials").mockImplementation(async selection => structuredClone(selection));
  }
  if (!vi.isMockFunction(interviewAppAdapter.submitManualAnswer)) {
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
            detail: "不对候选人的公司、项目、职责或结果作具体推断，只基于本场已确认资料与用户输入回答。",
            sourceTypes: [],
            inference: "",
            uncertain: true,
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
          completedText: "不对候选人的公司、项目、职责或结果作具体推断，只基于本场已确认资料与用户输入回答。",
          updatedAtMs: Date.now(),
        },
      };
    });
  }
  const state = structuredClone(syntheticState); mutate?.(state);
  window.history.pushState({}, "", path);
  return render(<App initialAuthenticated initialState={state} />);
};

describe("categorized materials and reachable live actions", () => {
  it("separates resume, JD and knowledge management without authorizing a new resume", async () => {
    open("/app/library");
    const tabs = screen.getByRole("navigation", { name: "资料类型" });
    expect(within(tabs).getByRole("button", { name: /简历/ })).toBeInTheDocument();
    expect(within(tabs).getByRole("button", { name: /职位 JD/ })).toBeInTheDocument();
    expect(within(tabs).getByRole("button", { name: /知识库/ })).toBeInTheDocument();
    fireEvent.click(within(tabs).getByRole("button", { name: /简历/ }));
    expect(screen.getAllByText(/支持上传 PDF、DOCX、DOC、TXT、MD/).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "＋ 添加简历" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/支持上传 PDF、DOCX、DOC、TXT、MD/)).toBeInTheDocument();
    const file = new File(["synthetic"], "新增合成简历.pdf", { type: "application/pdf" });
    fireEvent.change(within(dialog).getByLabelText("选择简历文件"), { target: { files: [file] } });
    fireEvent.click(within(dialog).getByRole("button", { name: "添加并解析" }));
    expect(await screen.findByText(/尚未授权给任何面试/)).toBeInTheDocument();
    expect(screen.getByText("新增合成简历.pdf")).toBeInTheDocument();
    window.history.pushState({}, "", "/app/interviews/demo/prepare"); window.dispatchEvent(new PopStateEvent("popstate"));
    const uploadedResume = await screen.findByRole("radio", { name: /新增合成简历.pdf/ });
    expect(uploadedResume).not.toBeChecked();
    expect(uploadedResume).toBeDisabled();
  });

  it("hides foreign material sources from categorized management", () => {
    open("/app/library", state => { state.librarySources.push({ id: "foreign-resume", ownerUserId: "another-user", kind: "resume", displayName: "不应展示的外部简历", version: "v1", status: "ready", updatedAtMs: 1 }); });
    const tabs = screen.getByRole("navigation", { name: "资料类型" }); fireEvent.click(within(tabs).getByRole("button", { name: /简历/ }));
    expect(screen.queryByText("不应展示的外部简历")).not.toBeInTheDocument();
  });

  it("shows consistent format guidance for JD on page and in dialog", () => {
    open("/app/library");
    const tabs = screen.getByRole("navigation", { name: "资料类型" });
    fireEvent.click(within(tabs).getByRole("button", { name: /职位 JD/ }));
    expect(screen.getAllByText(/支持上传 PDF、DOCX、DOC、TXT、MD，也支持直接粘贴 JD 文本/).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "＋ 添加 JD" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/支持上传 PDF、DOCX、DOC、TXT、MD，也支持直接粘贴 JD 文本/)).toBeInTheDocument();
    expect(within(dialog).getByLabelText("选择 JD 文件")).toHaveAttribute("accept", ".pdf,.docx,.doc,.txt,.md");
  });

  it("rejects unsupported resume formats before upload starts", async () => {
    open("/app/library");
    const tabs = screen.getByRole("navigation", { name: "资料类型" });
    fireEvent.click(within(tabs).getByRole("button", { name: /简历/ }));
    fireEvent.click(screen.getByRole("button", { name: "＋ 添加简历" }));
    const dialog = screen.getByRole("dialog");
    const file = new File(["synthetic"], "avatar.png", { type: "image/png" });
    fireEvent.change(within(dialog).getByLabelText("选择简历文件"), { target: { files: [file] } });
    fireEvent.click(within(dialog).getByRole("button", { name: "添加并解析" }));
    expect(await screen.findByText(/仅支持 PDF、DOCX、DOC、TXT、MD/)).toBeInTheDocument();
    const failedUpload = screen.getByText("avatar.png").closest("article")!;
    expect(within(failedUpload).getByText("资料暂不可用，请刷新状态。")).toBeInTheDocument();
  });

  it("keeps newly uploaded knowledge materials unavailable in preparation until processing is complete", async () => {
    open("/app/library");
    fireEvent.click(screen.getByRole("button", { name: "＋ 添加资料" }));
    const dialog = screen.getByRole("dialog");
    const file = new File(["synthetic"], "新知识.md", { type: "text/markdown" });
    fireEvent.change(within(dialog).getByLabelText("选择资料文件"), { target: { files: [file] } });
    fireEvent.click(within(dialog).getByRole("button", { name: "确认报价并建立索引" }));
    expect(await screen.findByText(/等待服务端建立索引/)).toBeInTheDocument();
    window.history.pushState({}, "", "/app/interviews/demo/prepare"); window.dispatchEvent(new PopStateEvent("popstate"));
    expect(await screen.findByRole("checkbox", { name: /新知识.md/ })).toBeDisabled();
  });

  it("uses the managed library list and flags a deleted saved selection", () => {
    open("/app/interviews/demo/prepare", state => {
      state.librarySources = state.librarySources.map(source => source.id === "resume-frontend" ? { ...source, status: "deleted" } : source);
    });
    expect(screen.queryByText("高级前端工程师简历（合成）")).not.toBeInTheDocument();
    expect(screen.getByText(/已选资料已失效/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /开始面试/ })).toBeDisabled();
    expect(screen.getByRole("link", { name: "前往面试资料处理" })).toHaveAttribute("href", "/app/library");
  });

  it("keeps a reusable resume when backend deletion fails and exposes no prototype replacement actions", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    open("/app/library"); const tabs = screen.getByRole("navigation", { name: "资料类型" }); fireEvent.click(within(tabs).getByRole("button", { name: /简历/ }));
    const row = screen.getByText("高级前端工程师简历（合成）").closest("article")!;
    expect(within(row).queryByRole("button", { name: "替换" })).not.toBeInTheDocument();
    expect(within(row).queryByRole("button", { name: "完成模拟解析" })).not.toBeInTheDocument();
    fireEvent.click(within(row).getByRole("button", { name: "删除" }));
    expect(await screen.findByText("无法连接后端基础服务")).toBeInTheDocument();
    expect(screen.getByText("高级前端工程师简历（合成）")).toBeInTheDocument();
  });

  it("allows an explicitly confirmed empty selection to start", async () => {
    open("/app/interviews/demo/prepare");
    fireEvent.click(screen.getByRole("button", { name: "本场不使用资料" }));
    fireEvent.click(screen.getByRole("button", { name: "确认空资料并继续" }));
    expect(await screen.findByText("已确认不使用个人资料")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /开始面试/ })).toBeEnabled();
    expect(screen.queryByRole("checkbox", { name: /数据用途/ })).not.toBeInTheDocument();
  });

  it("enters live workspace without audio readiness and keeps capture stopped", async () => {
    open("/app/interviews/demo/prepare", state => {
      const device = state.preparation.device!;
      state.preparation = { ...state.preparation, device: { ...device, capabilities: { ...device.capabilities, systemAudio: "denied" } } };
    });
    expect(screen.getByText("本地端会继续检查收音、系统音频和问题检测")).toBeInTheDocument();
    const start = screen.getByRole("button", { name: /开始面试/ });
    expect(start).toBeEnabled();
    fireEvent.click(start);
    expect(await screen.findByText("等待开始面试")).toBeInTheDocument();
    expect(screen.getByText("这台 Mac · 已连接，未采集")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "手动输入面试官的问题" })).toBeInTheDocument();
  });

  it("requires a machine code before starting when no companion is connected", async () => {
    open("/app/interviews/demo/prepare", state => {
      const device = state.preparation.device!;
      state.preparation = { ...state.preparation, device: { ...device, connected: false, captureState: "not-connected" } };
    });
    expect(screen.getByText("请输入桌面伴随程序中的 6 位机器码，绑定本场收音机器")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /开始面试/ })).toBeDisabled();
    fireEvent.change(screen.getByPlaceholderText("输入 6 位机器码"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "验证并绑定" }));
    expect(await screen.findByText(/已绑定：面试稳伴随程序 · Mac/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /开始面试/ }));
    expect(await screen.findByText("等待开始面试")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "手动输入面试官的问题" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /截屏回答/ })).toBeInTheDocument();
  });

  it("keeps confirmation, screenshot and manual input in the focused workspace", () => {
    open("/app/interviews/demo/live");
    const actions = screen.getByRole("region", { name: "面试操作" });
    const inputRegion = screen.getByRole("region", { name: "手动问题输入" });
    expect(screen.getByRole("button", { name: "确认问题" })).toBeInTheDocument();
    expect(within(actions).getByRole("button", { name: /截屏回答/ })).toBeInTheDocument();
    expect(within(actions).getByRole("button", { name: /快答/ })).toBeInTheDocument();
    expect(within(inputRegion).getByRole("textbox", { name: "手动输入面试官的问题" })).toBeInTheDocument();
    const sidebars = screen.queryAllByRole("complementary");
    sidebars.forEach(sidebar => expect(within(sidebar).queryByRole("button", { name: /截屏回答|确认问题|快答/ })).not.toBeInTheDocument());
  });

  it("dismisses a pending question from the main region without charging", () => {
    open("/app/interviews/demo/live");
    fireEvent.click(screen.getByRole("button", { name: "忽略" }));
    expect(screen.queryByText("可能是面试官的问题")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "积分" })).toBeInTheDocument();
  });

  it.each([390, 900, 1280])("keeps primary actions mounted at %ipx", width => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: width }); open("/app/interviews/demo/live");
    expect(screen.getByRole("region", { name: "面试操作" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /截屏回答/ })).toBeInTheDocument();
  });

  it("keeps primary actions without rendering a material rail", () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 }); open("/app/interviews/demo/live");
    expect(screen.queryByText(/面试资料 · v/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /收起资料|展开资料|调整/ })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "面试操作" })).toBeInTheDocument();
  });

  it("preserves the manual draft across viewport changes", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 390 });
    open("/app/interviews/demo/live");
    const input = screen.getByRole("textbox", { name: "手动输入面试官的问题" });
    fireEvent.change(input, { target: { value: "不会因响应式重排丢失的合成问题" } });
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
    fireEvent(window, new Event("resize"));
    expect(screen.getByRole("textbox", { name: "手动输入面试官的问题" })).toHaveValue("不会因响应式重排丢失的合成问题");
    await waitFor(() => expect(screen.getByRole("separator", { name: "调整实时对话与回答宽度" })).toBeInTheDocument());
  });

  it("preserves answer history, draft and screenshot preview across breakpoints", async () => {
    vi.spyOn(interviewAppAdapter, "submitScreenshotAnswer").mockImplementation(() => new Promise(() => undefined));
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
    open("/app/interviews/demo/live");
    fireEvent.click(screen.getByRole("button", { name: /上一条/ }));
    const input = screen.getByRole("textbox", { name: "手动输入面试官的问题" });
    fireEvent.change(input, { target: { value: "跨断点保留的合成草稿" } });
    fireEvent.click(screen.getByRole("button", { name: "截屏回答" }));
    expect(screen.getByRole("dialog", { name: "正在截取当前屏幕" })).toBeInTheDocument();
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 390 });
    fireEvent(window, new Event("resize"));
    await waitFor(() => expect(screen.queryByRole("separator")).not.toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "请做一个简短的自我介绍。" })).toBeInTheDocument();
    expect(input).toHaveValue("跨断点保留的合成草稿");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("labels newly generated answers when the confirmed allowlist is empty", async () => {
    open("/app/interviews/demo/live", state => { state.contextSelections.demo = { sessionId: "demo", resumeSourceId: null, jobDescriptionSourceId: null, knowledgeSourceIds: [], revision: 2, confirmedAtMs: 10 }; });
    const input = screen.getByRole("textbox", { name: "手动输入面试官的问题" });
    fireEvent.change(input, { target: { value: "空资料问题" } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    expect(screen.getAllByText("未使用个人资料").length).toBeGreaterThan(0);
    expect(await screen.findByText(/不对候选人的公司、项目、职责或结果作具体推断/)).toBeInTheDocument();
  });
});
