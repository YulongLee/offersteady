import JSZip from "jszip";
import { describe, expect, it, vi } from "vitest";

import {
  createInterviewReviewWordBlob,
  downloadInterviewReviewWord,
  interviewReviewWordFilename,
} from "./interview-review-word-export";
import { syntheticState } from "./test-state";

const documentXml = async (blob: Blob) => {
  const zip = await JSZip.loadAsync(await blob.arrayBuffer());
  return {
    document: await zip.file("word/document.xml")!.async("string"),
    contentTypes: await zip.file("[Content_Types].xml")!.async("string"),
  };
};

describe("Word interview review export", () => {
  it("creates a standards-compliant DOCX with transcript and AI advice separated", async () => {
    const blob = await createInterviewReviewWordBlob(
      syntheticState.review,
      syntheticState.questions,
      syntheticState.interviews[1],
    );
    const xml = await documentXml(blob);

    expect(blob.type).toBe(
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    );
    expect(xml.contentTypes).toContain(
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
    );
    expect(xml.document).toContain("真实对话记录（语音转写）");
    expect(xml.document).toContain("面试官");
    expect(xml.document).toContain("我会先统一目标和交付边界");
    expect(xml.document).toContain("问题与 AI 回答建议");
    expect(xml.document).toContain("AI 回答建议不代表候选人实际说法");
  });

  it("preserves complete long-form detail and truthful empty states", async () => {
    const longDetail = Array.from(
      { length: 80 },
      (_, index) => `第 ${index + 1} 段完整回答内容，不允许因为回答模式或文档分页而截断。`,
    ).join("\n\n");
    const [question] = syntheticState.questions;
    const blob = await createInterviewReviewWordBlob(
      { ...syntheticState.review, transcripts: [] },
      question ? [{ ...question, advice: { ...question.advice, detail: longDetail } }] : [],
    );
    const xml = await documentXml(blob);

    expect(xml.document).toContain("本场没有可用的持久语音转写");
    expect(xml.document).toContain("第 1 段完整回答内容");
    expect(xml.document).toContain("第 80 段完整回答内容");
  });

  it("sanitizes the DOCX filename and downloads through a local Blob URL", () => {
    const click = vi.fn();
    const remove = vi.fn();
    const anchor = document.createElement("a");
    anchor.click = click;
    anchor.remove = remove;
    vi.spyOn(document, "createElement").mockReturnValue(anchor);
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:review-word-local");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);

    const filename = interviewReviewWordFilename(
      '后端/平台:"一面"',
      Date.UTC(2026, 7, 13),
    );
    downloadInterviewReviewWord(filename, new Blob(["synthetic"]));

    expect(filename).toBe("后端-平台--一面--2026-08-13.docx");
    expect(URL.createObjectURL).toHaveBeenCalledOnce();
    expect(anchor.download).toBe(filename);
    expect(anchor.href).toContain("blob:review-word-local");
    expect(click).toHaveBeenCalledOnce();
    expect(remove).toHaveBeenCalledOnce();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:review-word-local");
  });
});
