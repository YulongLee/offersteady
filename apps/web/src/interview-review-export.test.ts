import { describe, expect, it, vi } from "vitest";

import { downloadInterviewReviewMarkdown, formatInterviewReviewMarkdown, interviewReviewFilename } from "./interview-review-export";
import { syntheticState } from "./test-state";


describe("interview review export", () => {
  it("separates real transcript and AI advice in UTF-8 Markdown", () => {
    const markdown = formatInterviewReviewMarkdown(syntheticState.review, syntheticState.questions, syntheticState.interviews[1]);

    expect(markdown).toContain("## 真实对话记录（语音转写）");
    expect(markdown).toContain("### 面试官");
    expect(markdown).toContain("### 我");
    expect(markdown).toContain("我会先统一目标和交付边界");
    expect(markdown).toContain("## 问题与 AI 回答建议");
    expect(markdown).toContain("AI 回答建议不代表候选人实际说法");
  });

  it("keeps available AI review data when transcript history is unavailable", () => {
    const markdown = formatInterviewReviewMarkdown({ ...syntheticState.review, transcripts: [] }, syntheticState.questions);

    expect(markdown).toContain("本场没有可用的持久语音转写");
    expect(markdown).toContain("请介绍一个你负责过的、最有挑战的前端项目");
  });

  it("sanitizes filenames and generates the file entirely through a local Blob", () => {
    const click = vi.fn();
    const remove = vi.fn();
    const anchor = document.createElement("a");
    anchor.click = click;
    anchor.remove = remove;
    vi.spyOn(document, "createElement").mockReturnValue(anchor);
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:review-local");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);

    const filename = interviewReviewFilename('后端/平台:"一面"', Date.UTC(2026, 7, 13));
    downloadInterviewReviewMarkdown(filename, "# 复盘\n");

    expect(filename).toBe("后端-平台--一面--2026-08-13.md");
    expect(URL.createObjectURL).toHaveBeenCalledOnce();
    expect(anchor.download).toBe(filename);
    expect(anchor.href).toContain("blob:review-local");
    expect(click).toHaveBeenCalledOnce();
    expect(remove).toHaveBeenCalledOnce();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:review-local");
  });
});
