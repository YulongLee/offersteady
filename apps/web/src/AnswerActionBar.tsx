import type { ScreenshotTask } from "./domain";

interface Props {
  readonly manualDraft: string;
  readonly latestInterviewerQuestion?: string;
  readonly screenshotTask: ScreenshotTask | null;
  readonly onQuickAnswer: () => void;
  readonly onScreenshot: () => void;
  readonly webSearchEnabled?: boolean;
  readonly onToggleWebSearch?: () => void;
  readonly disabled?: boolean;
  readonly quickAnswerStatus?: "idle" | "processing" | "success" | "failed" | "cancelled";
  readonly quickAnswerMessage?: string;
  readonly screenshotAnswerStatus?: "idle" | "processing" | "success" | "failed" | "cancelled";
  readonly screenshotOnly?: boolean;
}

export function AnswerActionBar({ manualDraft, latestInterviewerQuestion = "", screenshotTask, onQuickAnswer, onScreenshot, webSearchEnabled = false, onToggleWebSearch = () => undefined, disabled = false, quickAnswerStatus = "idle", screenshotAnswerStatus = "idle", screenshotOnly = false }: Props) {
  const quickBusy = quickAnswerStatus === "processing";
  const screenshotBusy = screenshotAnswerStatus === "processing" || Boolean(screenshotTask && !["completed", "failed", "cancelled"].includes(screenshotTask.stage));
  return <section className="answer-action-bar" aria-label="面试操作">
    <div className="answer-action-buttons">
      {!screenshotOnly ? <button
        className="button primary action-tile"
        aria-label="快答"
        disabled={disabled || quickBusy}
        title={manualDraft.trim() ? "根据左侧输入的问题立即回答" : latestInterviewerQuestion.trim() ? "根据最近一条面试官问题立即回答" : "请先输入问题或等待面试官对话同步"}
        onClick={onQuickAnswer}
      >
        <strong>快答</strong>
        <small>{manualDraft.trim() ? "根据左侧问题直接生成回答" : "根据最近面试官问题回答"}</small>
      </button> : null}
      {!screenshotOnly ? <button
        className={`button ${webSearchEnabled ? "primary" : "ghost"} action-tile web-search-action-tile`}
        aria-label="联网回答"
        aria-pressed={webSearchEnabled}
        disabled={disabled || quickBusy}
        title="开启后，详细回答会检索公开网页信息并显示来源"
        onClick={onToggleWebSearch}
      >
        <strong>{webSearchEnabled ? "联网回答已开启" : "联网回答"}</strong>
        <small>{webSearchEnabled ? "详细回答会结合实时网页资料" : "详细回答使用实时网页资料 · 20积分 / 7天会员免费"}</small>
      </button> : null}
      <button
        className="button ghost action-tile"
        aria-label="截屏回答"
        disabled={disabled || screenshotBusy}
        title="直接截取你选择的共享屏幕并回答"
        onClick={onScreenshot}
      >
        <strong>截屏回答</strong>
        <small>直接截取共享屏幕并进入回答</small>
      </button>
    </div>
  </section>;
}
