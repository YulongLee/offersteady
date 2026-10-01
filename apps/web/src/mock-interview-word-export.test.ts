import JSZip from "jszip";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { MockSession } from "./mock-interview-client";
import { createMockInterviewWordBlob, downloadMockInterviewWord, mockInterviewWordFilename } from "./mock-interview-word-export";

const session: MockSession = {
  sessionId: "private-session-id", title: "后端开发练习", targetRole: "后端工程师",
  createdAtMs: 1, resumeId: "private-resume-id", resumeVersion: "private-resume-version",
  billingClass: "points", refunded: false, error: null, billableMs: 60000, billedMinutes: 1,
  interacting: false, partial: true,
  state: { phase: "completed", version: 5, capture_epoch: null, rounds: [
    { question_id: "private-question-id", question: "如何保证幂等？", answer: "使用唯一约束。\n重试时返回已有结果。", submission_id: "private-submission-id" },
    { question_id: "unanswered", question: "如何进行故障演练？", answer: null, submission_id: null },
  ] },
  report: { summary: "思路清晰，可补充异常处理。", overall_score: 82,
    dimensions: { relevance: 90, clarity: 85, depth: 78, evidence: 75 },
    feedback: [
      { question_id: "private-question-id", answer_quote: "使用唯一约束。", strength: "说明了防重机制。", improvement: "补充并发冲突处理。", suggestion: "用真实案例说明冲突后的返回策略。" },
      { question_id: "unanswered", answer_quote: "错误证据", strength: "错误评价", improvement: "错误改进", suggestion: "错误建议" },
    ], practice_priorities: ["练习接口幂等", "补充异常分支"] },
};

async function readWord(blob: Blob) {
  const zip = await JSZip.loadAsync(await blob.arrayBuffer());
  const xml = await zip.file("word/document.xml")!.async("string");
  const parsed = new DOMParser().parseFromString(xml, "application/xml");
  expect(parsed.querySelector("parsererror")).toBeNull();
  return { zip, xml, paragraphs: Array.from(parsed.getElementsByTagName("w:p"), p => p.textContent) };
}

describe("mock interview Word reports", () => {
  afterEach(() => vi.restoreAllMocks());

  it("exports editable scores and complete feedback without private identifiers or fabricated unanswered feedback", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("export must be local"));
    const before = JSON.stringify(session);
    const blob = await createMockInterviewWordBlob(session);
    const { xml, zip, paragraphs } = await readWord(blob);
    expect(blob.type).toBe("application/vnd.openxmlformats-officedocument.wordprocessingml.document");
    expect(await zip.file("[Content_Types].xml")!.async("string")).toContain("wordprocessingml.document.main+xml");
    expect(xml).toContain('<w:pStyle w:val="Title"');
    for (const text of ["模拟面试报告", "后端开发练习", "后端工程师", "部分练习报告", "总体评分：82 / 100", "切题程度：90 / 100",
      "思路清晰，可补充异常处理。", "回答中的证据", "说明了防重机制。", "补充并发冲突处理。", "用真实案例说明冲突后的返回策略。",
      "练习接口幂等", "补充异常分支", "本题未提交回答，不计分。", "不代表真实面试结果"]) expect(xml).toContain(text);
    expect(paragraphs).toContain("使用唯一约束。");
    expect(paragraphs).toContain("重试时返回已有结果。");
    expect(xml.indexOf("如何保证幂等")).toBeLessThan(xml.indexOf("如何进行故障演练"));
    expect(xml).not.toMatch(/private-|错误证据|错误评价|错误改进|错误建议/);
    expect(JSON.stringify(session)).toBe(before);
    expect(request).not.toHaveBeenCalled();
  });

  it("preserves insufficient-evidence reports without inventing scores or answers", async () => {
    const { xml } = await readWord(await createMockInterviewWordBlob({ ...session,
      state: { ...session.state, rounds: [] }, report: { summary: "本场没有完成回答。", overall_score: null, dimensions: null, feedback: [], practice_priorities: [] },
    }));
    expect(xml).toContain("有效回答不足，不评分");
    expect(xml).toContain("本场没有已发布的问题。");
    expect(xml).not.toMatch(/0 \/ 100|分项评分|下一次练习重点/);
  });

  it("retains a genuine zero score and the complete-report label", async () => {
    const { xml } = await readWord(await createMockInterviewWordBlob({ ...session, partial: false,
      report: { ...session.report!, overall_score: 0, dimensions: { relevance: 0 } },
    }));
    expect(xml).toContain("完整练习报告");
    expect(xml).toContain("总体评分：0 / 100");
    expect(xml).toContain("切题程度：0 / 100");
    expect(xml).not.toContain("有效回答不足");
  });

  it("preserves ten long Unicode answers and safely escapes XML without clipping text", async () => {
    const rounds = Array.from({ length: 10 }, (_, index) => ({
      question_id: `q${index}`, question: `问题${index + 1}`, submission_id: `a${index}`,
      answer: `开头${index + 1} <条件> & 判断\u0000\ud800\r\n${"这是需要保留的长回答。".repeat(300)}\n末尾${index + 1} 中文 English 🚀`,
    }));
    const { xml, paragraphs } = await readWord(await createMockInterviewWordBlob({ ...session, state: { ...session.state, rounds } }));
    expect(xml).toContain("&lt;条件&gt; &amp; 判断");
    expect(xml).not.toMatch(/[\u0000\ud800]/u);
    for (let i = 1; i <= 10; i += 1) {
      expect(paragraphs).toContain(`末尾${i} 中文 English 🚀`);
      expect(paragraphs).toContain(`第 ${i} 题`);
    }
    expect(xml.match(/这是需要保留的长回答。/g)).toHaveLength(3000);
  });

  it.each(["preparing", "generating_question", "speaking", "listening", "paused", "generating_report"] as const)("rejects %s sessions even if a report is present", async phase => {
    await expect(createMockInterviewWordBlob({ ...session, state: { ...session.state, phase } })).rejects.toThrow("报告尚未生成完成");
  });

  it("rejects completed sessions with no report", async () => {
    await expect(createMockInterviewWordBlob({ ...session, report: null })).rejects.toThrow("报告尚未生成完成");
  });

  it("bounds and sanitizes filenames including control and directional characters", () => {
    expect(mockInterviewWordFilename(' ..后端/测试:\n"文档"\u0000\u202e ')).toBe("模拟面试报告-后端-测试- -文档--.docx");
    expect(mockInterviewWordFilename("...")).toBe("模拟面试报告.docx");
    expect(mockInterviewWordFilename("🚀".repeat(90))).toBe(`模拟面试报告-${"🚀".repeat(60)}.docx`);
  });

  it("downloads a local DOCX and releases its temporary URL and anchor", async () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    const create = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock-report-local");
    const revoke = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    await downloadMockInterviewWord(session);
    expect(create).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    const anchor = click.mock.instances[0] as HTMLAnchorElement;
    expect(anchor.download).toBe("模拟面试报告-后端开发练习.docx");
    expect(anchor.isConnected).toBe(false);
    expect(revoke).toHaveBeenCalledWith("blob:mock-report-local");
  });
});
