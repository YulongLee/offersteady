import type { ScreenshotTask } from "./domain";

interface Props {
  readonly manualDraft: string;
  readonly latestInterviewerQuestion?: string;
  readonly screenshotTask: ScreenshotTask | null;
  readonly quickAnswerStatus?: "idle" | "processing" | "success" | "failed" | "cancelled";
  readonly quickAnswerMessage?: string;
  readonly screenshotAnswerStatus?: "idle" | "processing" | "success" | "failed" | "cancelled";
  readonly disabled?: boolean;
  readonly onChange: (value: string) => void;
  readonly onQuickAnswer: () => void;
  readonly onScreenshot: () => void;
}

const screenshotStageText = (task: ScreenshotTask | null) => {
  if (!task) return "";
  if (task.stage === "waiting-desktop") return "等待助手接收截屏";
  if (task.stage === "capturing") return "正在截取屏幕";
  if (task.stage === "uploading" || task.stage === "uploaded") return "正在上传截图";
  if (task.stage === "recognizing") return "正在识别截图";
  if (task.stage === "generating") return "正在生成截图答案";
  if (task.stage === "completed") return "截图回答已完成";
  if (task.stage === "cancelled") return "截图回答已取消";
  return task.errorMessage || "截图回答失败，可重试";
};

export function MobileInterviewControls({
  manualDraft,
  latestInterviewerQuestion = "",
  screenshotTask,
  quickAnswerStatus = "idle",
  quickAnswerMessage = "",
  screenshotAnswerStatus = "idle",
  disabled = false,
  onChange,
  onQuickAnswer,
  onScreenshot,
}: Props) {
  const canQuickAnswer = Boolean(manualDraft.trim() || latestInterviewerQuestion.trim());
  const quickBusy = quickAnswerStatus === "processing";
  const screenshotBusy = screenshotAnswerStatus === "processing" || Boolean(screenshotTask && !["completed", "failed", "cancelled"].includes(screenshotTask.stage));
  const statusText = quickBusy
    ? "正在生成回答"
    : quickAnswerStatus === "failed"
      ? quickAnswerMessage || "快答失败，可重试"
      : quickAnswerStatus === "success"
        ? "回答已生成"
        : screenshotStageText(screenshotTask);

  return <section className="mobile-interview-controls" aria-label="面试操作">
    <label>
      <span className="sr-only">手动输入面试官的问题</span>
      <textarea
        aria-label="手动输入面试官的问题"
        value={manualDraft}
        disabled={disabled}
        onChange={event => onChange(event.target.value)}
        placeholder="输入问题，或直接使用最近的面试官问题"
        rows={1}
      />
    </label>
    <div className="mobile-interview-actions">
      <button className="button primary" aria-label="快答" disabled={disabled || !canQuickAnswer || quickBusy} onClick={onQuickAnswer}>
        {quickBusy ? "生成中…" : "快答"}
      </button>
      <button className="button ghost" aria-label="截屏回答" disabled={disabled || screenshotBusy} onClick={onScreenshot}>
        截屏回答
      </button>
    </div>
    <small className="mobile-interview-status" aria-live="polite">{statusText}</small>
  </section>;
}
