import type { InterviewQuestion, InterviewReview, InterviewSummary } from "./domain";

const safeLine = (value: string) => value.replace(/\r?\n/g, " ").trim();

export const interviewReviewFilename = (title: string, endedAtMs?: number | null) => {
  const date = endedAtMs ? new Date(endedAtMs) : new Date();
  const stamp = Number.isNaN(date.getTime()) ? "unknown-date" : date.toISOString().slice(0, 10);
  const safeTitle = safeLine(title).replace(/[\\/:*?"<>|]/g, "-").replace(/\s+/g, "-").slice(0, 60) || "面试复盘";
  return `${safeTitle}-${stamp}.md`;
};

const formatTime = (value?: number | null) => value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "未记录";

export const formatInterviewReviewMarkdown = (
  review: InterviewReview,
  questions: readonly InterviewQuestion[],
  interview?: InterviewSummary,
) => {
  const title = review.title || interview?.title || "本场面试复盘";
  const lines = [
    `# ${safeLine(title)}`,
    "",
    `- 开始时间：${formatTime(review.startedAtMs)}`,
    `- 结束时间：${formatTime(review.endedAtMs)}`,
    `- 面试时长：${review.duration}`,
    "- 说明：对话内容来自语音转写，可能存在识别误差；AI 回答建议不代表候选人实际说法。",
    "",
    "## 真实对话记录（语音转写）",
    "",
  ];
  if (review.transcripts.length) {
    review.transcripts.forEach(item => {
      lines.push(`### ${item.speakerLabel} · ${formatTime(item.occurredAtMs)}`, "", item.text.trim(), "");
    });
  } else {
    lines.push("本场没有可用的持久语音转写。", "");
  }
  lines.push("## 问题与 AI 回答建议", "");
  if (questions.length) {
    [...questions].reverse().forEach((question, index) => {
      lines.push(
        `### ${index + 1}. ${safeLine(question.text)}`,
        "",
        `- 时间：${question.askedAt}`,
        `- 来源：${question.input === "screenshot" ? "截图题" : question.input === "manual" ? "手动输入" : "音频转写"}`,
        "",
        question.advice.outline.length ? question.advice.outline.map(item => `- ${safeLine(item)}`).join("\n") : "暂无 AI 回答建议。",
        "",
      );
      if (question.advice.detail.trim()) lines.push(question.advice.detail.trim(), "");
    });
  } else {
    lines.push("本场没有已保存的问题与 AI 回答建议。", "");
  }
  return `${lines.join("\n").trim()}\n`;
};

export const downloadInterviewReviewMarkdown = (filename: string, markdown: string) => {
  const url = URL.createObjectURL(new Blob(["\ufeff", markdown], { type: "text/markdown;charset=utf-8" }));
  try {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.style.display = "none";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
};
