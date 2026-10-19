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

export function WrittenMultiScreenActionBar({ manualDraft, latestInterviewerQuestion = "", screenshotTask, onQuickAnswer, onScreenshot, disabled = false, quickAnswerStatus = "idle", screenshotAnswerStatus = "idle", screenshotOnly = false, multiScreen = false, pendingScreenshots = [], screenshotLimit = 4, captureBusy = false, captureMessage = "", captureUnavailable = false, onBatchAnswer, onRemoveScreenshot }: Props) {
  const quickBusy = quickAnswerStatus === "processing";
  const screenshotBusy = screenshotAnswerStatus === "processing" || Boolean(screenshotTask && !["completed", "failed", "cancelled"].includes(screenshotTask.stage));
  const multiScreenBusy = screenshotBusy || captureBusy;
  return <section className="answer-action-bar" aria-label="Interview controls">
    <div className="answer-action-buttons">
      {!screenshotOnly ? <button
        className="button primary action-tile"
        aria-label="Quick answer"
        disabled={disabled || quickBusy}
        title={manualDraft.trim() ? "Answer the question entered on the left" : latestInterviewerQuestion.trim() ? "Answer the latest interviewer question" : "Enter a question or wait for the conversation to sync"}
        onClick={onQuickAnswer}
      >
        <strong>Quick answer</strong>
        <small>{manualDraft.trim() ? "Answer the entered question" : "Answer the latest interviewer question"}</small>
      </button> : null}
      <button
        className="button ghost action-tile"
        aria-label={multiScreen ? "Capture" : "Screen Assist"}
        disabled={disabled || screenshotBusy || (multiScreen && (captureBusy || captureUnavailable || pendingScreenshots.length >= screenshotLimit))}
        title={multiScreen ? "Capture the current shared screen and answer together later" : "Capture your selected shared screen and answer"}
        onClick={onScreenshot}
      >
        <strong>{multiScreen ? "Capture" : "Screen Assist"}</strong>
        <small>{multiScreen ? "Keep this view, then scroll and capture more" : "Capture the shared screen and generate an answer"}</small>
      </button>
      {multiScreen ? <button
        className="button primary action-tile"
        aria-label="Answer"
        disabled={disabled || multiScreenBusy || pendingScreenshots.length === 0}
        onClick={onBatchAnswer}
      ><strong>Answer</strong><small>Generate one answer from all captures</small></button> : null}
    </div>
    {multiScreen ? <div className="written-screenshot-collection">
      <div className="written-screenshot-summary" role="status" aria-live="polite"><span>{captureMessage || `Captured ${pendingScreenshots.length} / ${screenshotLimit}`}</span>{captureBusy ? <small>Capturing…</small> : null}</div>
      {pendingScreenshots.length > 0 ? <ol className="written-screenshot-list" aria-label="Pending captures">{pendingScreenshots.map((item, index) => <li key={item.requestId}><span title={item.name}>Capture {index + 1}</span><button type="button" aria-label={`Remove capture ${index + 1}`} disabled={disabled || multiScreenBusy} onClick={() => onRemoveScreenshot?.(item.requestId)}>×</button></li>)}</ol> : null}
    </div> : null}
  </section>;
}
