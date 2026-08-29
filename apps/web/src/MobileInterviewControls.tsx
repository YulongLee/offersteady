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

export function MobileInterviewControls({
  manualDraft,
  latestInterviewerQuestion = "",
  screenshotTask,
  quickAnswerStatus = "idle",
  screenshotAnswerStatus = "idle",
  disabled = false,
  onChange,
  onQuickAnswer,
  onScreenshot,
}: Props) {
  const canQuickAnswer = Boolean(manualDraft.trim() || latestInterviewerQuestion.trim());
  const quickBusy = quickAnswerStatus === "processing";
  const screenshotBusy = screenshotAnswerStatus === "processing" || Boolean(screenshotTask && !["completed", "failed", "cancelled"].includes(screenshotTask.stage));
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
        快答
      </button>
      <button className="button ghost" aria-label="截屏回答" disabled={disabled || screenshotBusy} onClick={onScreenshot}>
        截屏回答
      </button>
    </div>
  </section>;
}
