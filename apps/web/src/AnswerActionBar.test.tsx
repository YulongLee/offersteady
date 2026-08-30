import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AnswerActionBar } from "./AnswerActionBar";
import { MobileInterviewControls } from "./MobileInterviewControls";

describe("quiet live answer actions", () => {
  it("lets desktop users request quick-answer guidance before a question is available", () => {
    const onQuickAnswer = vi.fn();
    render(<AnswerActionBar
      manualDraft=""
      latestInterviewerQuestion=""
      screenshotTask={null}
      onQuickAnswer={onQuickAnswer}
      onScreenshot={vi.fn()}
    />);

    const button = screen.getByRole("button", { name: "快答" });
    expect(button).not.toBeDisabled();
    fireEvent.click(button);
    expect(onQuickAnswer).toHaveBeenCalledOnce();
  });

  it("lets mobile users request quick-answer guidance before a question is available", () => {
    const onQuickAnswer = vi.fn();
    render(<MobileInterviewControls
      manualDraft=""
      latestInterviewerQuestion=""
      screenshotTask={null}
      onChange={vi.fn()}
      onQuickAnswer={onQuickAnswer}
      onScreenshot={vi.fn()}
    />);

    const button = screen.getByRole("button", { name: "快答" });
    expect(button).not.toBeDisabled();
    fireEvent.click(button);
    expect(onQuickAnswer).toHaveBeenCalledOnce();
  });

  it("keeps desktop action labels stable and hides task status copy", () => {
    const { rerender } = render(<AnswerActionBar
      manualDraft="合成面试问题"
      screenshotTask={null}
      quickAnswerStatus="processing"
      screenshotAnswerStatus="processing"
      onQuickAnswer={vi.fn()}
      onScreenshot={vi.fn()}
    />);

    expect(screen.getByRole("button", { name: "快答" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "快答" })).toHaveTextContent("快答");
    expect(screen.getByRole("button", { name: "截屏回答" })).toBeDisabled();
    expect(screen.queryByText(/正在生成回答|快答已完成|截屏回答已完成/)).not.toBeInTheDocument();

    rerender(<AnswerActionBar
      manualDraft="合成面试问题"
      screenshotTask={null}
      quickAnswerStatus="success"
      screenshotAnswerStatus="success"
      onQuickAnswer={vi.fn()}
      onScreenshot={vi.fn()}
    />);

    expect(screen.getByRole("button", { name: "快答" })).toHaveTextContent("快答");
    expect(screen.getByRole("button", { name: "快答" })).not.toHaveTextContent("已回答");
    expect(screen.queryByText(/快答已完成|截屏回答已完成/)).not.toBeInTheDocument();
  });

  it("keeps mobile action labels stable and hides task status copy", () => {
    render(<MobileInterviewControls
      manualDraft="合成面试问题"
      screenshotTask={null}
      quickAnswerStatus="processing"
      screenshotAnswerStatus="processing"
      onChange={vi.fn()}
      onQuickAnswer={vi.fn()}
      onScreenshot={vi.fn()}
    />);

    expect(screen.getByRole("button", { name: "快答" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "快答" })).toHaveTextContent("快答");
    expect(screen.getByRole("button", { name: "快答" })).not.toHaveTextContent("生成中");
    expect(screen.getByRole("button", { name: "截屏回答" })).toBeDisabled();
    expect(screen.queryByText(/正在生成回答|回答已生成|正在生成截图答案/)).not.toBeInTheDocument();
  });
});
