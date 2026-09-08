import type { ScreenshotTask } from "./domain";

interface Props {
  readonly manualDraft: string;
  readonly screenshotTask: ScreenshotTask | null;
  readonly onManualChange: (value: string) => void;
  readonly onManualSubmit: () => void;
  readonly onScreenshot: () => void;
}

const screenshotTaskText = (task: Props["screenshotTask"]) => {
  if (!task) return "";
  if (task.stage === "failed") return task.errorMessage || "截屏回答失败，可重试";
  if (task.stage === "waiting-desktop") return "等待本地助手接收截屏任务";
  if (task.stage === "uploading") return "正在上传压缩截图";
  if (task.stage === "uploaded") return "截图已上传，正在准备识别";
  if (task.stage === "recognizing") return "正在识别截图题目";
  if (task.stage === "generating") return "正在生成截图答案";
  if (task.stage === "completed") return "截图回答已完成";
  if (task.stage === "cancelled") return "截图回答已取消";
  return "正在截取你选择的共享屏幕";
};

export function CompactQuestionBar({ manualDraft, screenshotTask, onManualChange, onManualSubmit, onScreenshot }: Props) {
  return <section className="compact-question-bar" aria-label="面试操作"><label><span className="sr-only">手动输入面试官的问题</span><textarea aria-label="手动输入面试官的问题" value={manualDraft} onChange={event => onManualChange(event.target.value)} placeholder="输入面试官的问题" rows={1} /></label><button className="button primary" aria-label="回答问题" disabled={!manualDraft.trim()} title={manualDraft.trim() ? "回答这个问题" : "请先输入问题"} onClick={onManualSubmit}>回答问题</button><button className="button ghost" aria-label="截图回答" onClick={onScreenshot}>▧ 截图回答</button><small className="compact-action-status" aria-live="polite">{screenshotTaskText(screenshotTask)}</small></section>;
}
