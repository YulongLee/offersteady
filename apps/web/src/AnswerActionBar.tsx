import type { ScreenshotTask } from "./domain";

interface Props {
  readonly manualDraft: string;
  readonly latestInterviewerQuestion?: string;
  readonly screenshotTask: ScreenshotTask | null;
  readonly onQuickAnswer: () => void;
  readonly onScreenshot: () => void;
}

const screenshotStatus = (task: ScreenshotTask | null) => {
  if (!task) return "";
  if (task.stage === "capturing") return "正在截取你选择的共享屏幕";
  if (task.stage === "waiting-desktop") return "等待本地助手接收截屏任务";
  if (task.stage === "uploading") return "本地助手正在上传压缩截图";
  if (task.stage === "uploaded") return "截图已上传，正在准备识别";
  if (task.stage === "recognizing") return "正在识别截图题目";
  if (task.stage === "generating") return "正在生成截图答案";
  if (task.stage === "completed") return "截图回答已完成";
  if (task.stage === "cancelled") return "截图回答已取消";
  return task.errorMessage || "截屏回答失败，可重新发起";
};

export function AnswerActionBar({ manualDraft, latestInterviewerQuestion = "", screenshotTask, onQuickAnswer, onScreenshot }: Props) {
  const canQuickAnswer = Boolean(manualDraft.trim() || latestInterviewerQuestion.trim());
  return <section className="answer-action-bar" aria-label="面试操作">
    <div className="answer-action-buttons">
      <button
        className="button primary action-tile"
        aria-label="快答"
        disabled={!canQuickAnswer}
        title={manualDraft.trim() ? "根据左侧输入的问题立即回答" : latestInterviewerQuestion.trim() ? "根据最近一条面试官问题立即回答" : "请先输入问题或等待面试官对话同步"}
        onClick={onQuickAnswer}
      >
        <strong>快答</strong>
        <small>{manualDraft.trim() ? "根据左侧问题直接生成回答" : "根据最近面试官问题回答"}</small>
      </button>
      <button
        className="button ghost action-tile"
        aria-label="截屏回答"
        title="直接截取你选择的共享屏幕并回答"
        onClick={onScreenshot}
      >
        <strong>截屏回答</strong>
        <small>直接截取共享屏幕并进入回答</small>
      </button>
    </div>
    <small className="compact-action-status" aria-live="polite">{screenshotStatus(screenshotTask)}</small>
  </section>;
}
