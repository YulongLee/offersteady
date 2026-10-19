import type { CollectedScreenshot, ScreenshotTask } from "./domain";

interface Props {
  readonly manualDraft: string;
  readonly latestInterviewerQuestion?: string;
  readonly screenshotTask: ScreenshotTask | null;
  readonly onQuickAnswer: () => void;
  readonly onScreenshot: () => void;
  readonly disabled?: boolean;
  readonly quickAnswerStatus?: "idle" | "processing" | "success" | "failed" | "cancelled";
  readonly quickAnswerMessage?: string;
  readonly screenshotAnswerStatus?: "idle" | "processing" | "success" | "failed" | "cancelled";
  readonly screenshotOnly?: boolean;
  readonly multiScreen?: boolean;
  readonly pendingScreenshots?: readonly CollectedScreenshot[];
  readonly screenshotLimit?: number;
  readonly captureBusy?: boolean;
  readonly captureMessage?: string;
  readonly captureUnavailable?: boolean;
  readonly onBatchAnswer?: () => void;
  readonly onRemoveScreenshot?: (requestId: string) => void;
}

export function AnswerActionBar({ manualDraft, latestInterviewerQuestion = "", screenshotTask, onQuickAnswer, onScreenshot, disabled = false, quickAnswerStatus = "idle", screenshotAnswerStatus = "idle", screenshotOnly = false, multiScreen = false, pendingScreenshots = [], screenshotLimit = 4, captureBusy = false, captureMessage = "", captureUnavailable = false, onBatchAnswer, onRemoveScreenshot }: Props) {
  const quickBusy = quickAnswerStatus === "processing";
  const screenshotBusy = screenshotAnswerStatus === "processing" || Boolean(screenshotTask && !["completed", "failed", "cancelled"].includes(screenshotTask.stage));
  const multiScreenBusy = screenshotBusy || captureBusy;
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
      <button
        className="button ghost action-tile"
        aria-label={multiScreen ? "截屏" : "截屏回答"}
        disabled={disabled || screenshotBusy || (multiScreen && (captureBusy || captureUnavailable || pendingScreenshots.length >= screenshotLimit))}
        title={multiScreen ? "截取当前共享屏幕，稍后一起回答" : "直接截取你选择的共享屏幕并回答"}
        onClick={onScreenshot}
      >
        <strong>{multiScreen ? "截屏" : "截屏回答"}</strong>
        <small>{multiScreen ? "保存当前画面，可继续翻页截屏" : "直接截取共享屏幕并进入回答"}</small>
      </button>
      {multiScreen ? <button
        className="button primary action-tile"
        aria-label="回答"
        disabled={disabled || multiScreenBusy || pendingScreenshots.length === 0}
        onClick={onBatchAnswer}
      ><strong>回答</strong><small>将已截取的画面一起生成回答</small></button> : null}
    </div>
    {multiScreen ? <div className="written-screenshot-collection">
      <div className="written-screenshot-summary" role="status" aria-live="polite"><span>{captureMessage || `已截取 ${pendingScreenshots.length} / ${screenshotLimit} 张`}</span>{captureBusy ? <small>正在截屏…</small> : null}</div>
      {pendingScreenshots.length > 0 ? <ol className="written-screenshot-list" aria-label="待回答截图">{pendingScreenshots.map((item, index) => <li key={item.requestId}><span title={item.name}>截图 {index + 1}</span><button type="button" aria-label={`移除截图 ${index + 1}`} disabled={disabled || multiScreenBusy} onClick={() => onRemoveScreenshot?.(item.requestId)}>×</button></li>)}</ol> : null}
    </div> : null}
  </section>;
}
