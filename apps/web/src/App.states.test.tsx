import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { interviewAppAdapter } from "./app-adapter";
import type { QuestionStatus, WebAppState } from "./domain";
import { syntheticState } from "./test-state";

const renderState = (path: string, mutate?: (state: WebAppState) => void) => {
  const state = structuredClone(syntheticState);
  mutate?.(state);
  window.history.pushState({}, "", path);
  return render(<App initialAuthenticated initialState={state} />);
};

describe("web application states", () => {
  it.each([
    ["listening", "正在聆听"],
    ["transcribing", "正在转写"],
    ["generating", "正在思考"],
    ["streaming", "正在生成"],
    ["uncertain", "需要确认"],
    ["failed", "生成失败"],
    ["offline", "连接离线"],
  ] as const)("presents %s question state with text", (status, label) => {
    renderState("/app/interviews/demo/live", state => { state.questions[0] = { ...state.questions[0]!, status: status as QuestionStatus }; });
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("recovers a failed answer without losing the original question", () => {
    renderState("/app/interviews/demo/live", state => { state.questions[0] = { ...state.questions[0]!, status: "failed" }; });
    expect(screen.getByText("回答生成失败")).toBeInTheDocument();
    expect(screen.getByLabelText("回答正文")).toHaveTextContent("可以按照 STAR 结构回答");
    fireEvent.click(screen.getByRole("button", { name: "重试" }));
    expect(screen.getByText("正在思考")).toBeInTheDocument();
    expect(screen.getAllByText("请介绍一个你负责过的、最有挑战的前端项目。").length).toBeGreaterThan(0);
  });

  it("keeps generating answers readable without prototype explanation blocks", () => {
    renderState("/app/interviews/demo/live", state => {
      state.questions[0] = {
        ...state.questions[0]!,
        status: "generating",
        advice: { ...state.questions[0]!.advice, detail: "正在调用当前对话模型生成回答…" },
      };
    });
    expect(screen.getByLabelText("回答正文")).toHaveTextContent("正在调用当前对话模型生成回答…");
    expect(screen.queryByText("展开完整回答思路")).not.toBeInTheDocument();
    expect(screen.queryByText("模型推断")).not.toBeInTheDocument();
  });

  it.each([
    ["reconnecting", "设备正在重连"],
    ["permission-required", "需要麦克风与系统音频权限"],
    ["error", "桌面设备连接异常"],
  ] as const)("provides recovery for desktop state %s", (captureState, message) => {
    renderState("/app/interviews/demo/live", state => { state.captureState = captureState; });
    expect(screen.getAllByText(message).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: captureState === "permission-required" ? "已完成授权" : "重新诊断" }));
    expect(screen.getByText("等待开始面试")).toBeInTheDocument();
  });

  it("shows managed processing and failed sources as unavailable in preparation", () => {
    renderState("/app/interviews/demo/prepare", state => {
      state.librarySources[0] = { ...state.librarySources[0]!, status: "processing" };
      state.librarySources[2] = { ...state.librarySources[2]!, status: "failed" };
    });
    expect(screen.getByRole("radio", { name: /高级前端工程师简历（合成）/ })).toBeDisabled();
    expect(screen.getByRole("radio", { name: /示例科技高级前端 JD/ })).toBeDisabled();
    expect(screen.getByText(/已选资料已失效/)).toBeInTheDocument();
  });

  it("supports screenshot failure, cancellation and retry states", async () => {
    vi.spyOn(interviewAppAdapter, "submitScreenshotAnswer")
      .mockRejectedValueOnce(new Error("当前屏幕暂时无法截取，请重试。"))
      .mockImplementationOnce(() => new Promise(() => undefined));
    renderState("/app/interviews/demo/live");
    fireEvent.click(screen.getByRole("button", { name: /截屏回答/ }));
    let dialog = screen.getByRole("dialog", { name: "正在截取当前屏幕" });
    expect(within(dialog).getByText(/不会跳转到上传页面/)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "取消" })).toBeInTheDocument();
    dialog = await screen.findByRole("dialog", { name: "截屏回答失败" });
    expect(within(dialog).getByText("当前屏幕暂时无法截取，请重试。")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "删除本次失败" })).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "重新截屏" }));
    dialog = screen.getByRole("dialog", { name: "正在截取当前屏幕" });
    fireEvent.click(within(dialog).getByRole("button", { name: "取消" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("deduplicates an identical manual command", () => {
    renderState("/app/interviews/demo/live");
    const input = screen.getByPlaceholderText("输入面试官的问题");
    fireEvent.change(input, { target: { value: "同一个问题" } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    fireEvent.change(input, { target: { value: "同一个问题" } });
    fireEvent.click(screen.getByRole("button", { name: "快答" }));
    expect(screen.getAllByText("同一个问题")).toHaveLength(2);
  });

  it("keeps original records available when AI review generation fails", () => {
    renderState("/app/interviews/review/review", state => { state.review = { ...state.review, status: "failed" }; });
    expect(screen.getByText(/摘要生成失败/)).toBeInTheDocument();
    expect(screen.getByText("问题与回答记录")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "重试" }));
    expect(screen.getByText("这是基于本场记录的生成建议，与原始问题记录分开保存。")).toBeInTheDocument();
  });

  it("handles an empty review without presenting a false success", () => {
    renderState("/app/interviews/review/review", state => { state.questions = []; });
    expect(screen.getByText("没有可复盘的问题")).toBeInTheDocument();
  });

  it("deletes a session only after explicit confirmation", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    vi.spyOn(interviewAppAdapter, "deleteInterview").mockResolvedValue(undefined);
    renderState("/app/interviews/review/review");
    fireEvent.click(screen.getByRole("button", { name: "删除整场面试" }));
    expect(confirm).toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "本场面试复盘" })).toBeInTheDocument();
    confirm.mockReturnValue(true);
    fireEvent.click(screen.getByRole("button", { name: "删除整场面试" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "继续这场面试" })).toBeInTheDocument());
  });

  it("keeps records visible when server-confirmed deletion fails", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(interviewAppAdapter, "deleteScreenshot").mockRejectedValueOnce(new Error("synthetic failure"));
    renderState("/app/interviews/review/review");
    fireEvent.click(screen.getByRole("button", { name: "删除截图" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("截图删除失败");
    expect(screen.getByText("系统设计题（合成）.png")).toBeInTheDocument();
  });

  it("removes the unsupported retention preference while keeping real data controls", () => {
    renderState("/app/settings");
    expect(screen.getByText("默认不保存")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "面试记录保存期限" })).not.toBeInTheDocument();
    expect(screen.queryByText(/^7 天$|^30 天$|^手动删除$/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看数据说明" })).toBeInTheDocument();
  });
});
