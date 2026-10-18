import { describe, expect, it } from "vitest";
import { resumeInitialDraftSummary, resumeOptimizationFailureMessage, type ResumeOptimization } from "./resume-optimizer-client";
import { optimizerCompleted, optimizerQueued } from "./test/resume-optimizer-fixtures";
import fixedBackendMessages from "./test/resume-optimizer-safe-messages.json";

const fallback = "未生成可用优化稿，原简历保留。";
const refund = "本次积分或免费次数已退还。";
const factsMessage = "AI 改写未通过原文事实检查，已停止生成。原简历无需重新上传，请稍后重试。";
const failure = (updates: Partial<ResumeOptimization> = {}): ResumeOptimization => ({ ...optimizerQueued, status: "failed", errorCode: "invalid_output", errorMessage: factsMessage + refund, allowanceStatus: "released", billingStatus: "released", ...updates });
const summary = { proposedCount: 4, appliedCount: 1, retainedCount: 3, retainedReasonCounts: { factCheck: 1, sourceQuote: 0, overlap: 2, unchanged: 0 } };
const completed = (editSummary: unknown): ResumeOptimization => ({ ...optimizerCompleted, review: { ...optimizerCompleted.review!, editSummary: editSummary as never } });

describe("安全失败说明与 AI 初稿计数合同", () => {
  it.each(fixedBackendMessages.cases)("后端固定原因 $reason 的原句和合法退款句只映射为本地安全基句", row => {
    expect(fixedBackendMessages.syntheticOnly).toBe(true);
    expect(resumeOptimizationFailureMessage(failure({ errorCode: row.errorCode, errorMessage: row.message }))).toBe(row.message);
    expect(resumeOptimizationFailureMessage(failure({ errorCode: row.errorCode, errorMessage: row.message + refund }))).toBe(row.message);
    expect(resumeOptimizationFailureMessage(failure({ errorCode: row.errorCode, errorMessage: row.message + refund, allowanceStatus: "reserved" }))).toBe(fallback);
  });
  it.each([
    "PRIVATE_PROVIDER_PAYLOAD", factsMessage + " PRIVATE_PROVIDER_PAYLOAD", "PRIVATE_PROVIDER_PAYLOAD " + factsMessage,
    `<p>${factsMessage}</p>`, " " + factsMessage, factsMessage + refund + refund, { private: "PRIVATE_PROVIDER_PAYLOAD" }, null,
  ])("不显示动态、拼接、HTML、空白包装或对象错误 %j", message => {
    const result = resumeOptimizationFailureMessage(failure({ errorMessage: message as never }));
    expect(result).toBe(fallback); expect(result).not.toContain("PRIVATE_PROVIDER_PAYLOAD");
  });
  it.each(["unknown_private_code", "__proto__", "constructor", "toString", "provider_timeout"])("错误类别 %s 不得借用已知事实错误句", errorCode => {
    expect(resumeOptimizationFailureMessage(failure({ errorCode }))).toBe(fallback);
  });
  it.each([{ errorCode: ["invalid_output"] }, { errorCode: { code: "invalid_output" } }, { errorCode: null }])("误形错误类别 %j 不经属性键转换获得可信说明", ({ errorCode }) => {
    expect(resumeOptimizationFailureMessage(failure({ errorCode: errorCode as never }))).toBe(fallback);
  });
  it.each(["queued", "running", "completed", "cancelled"] as const)("状态 %s 不得借用失败说明", status => {
    expect(resumeOptimizationFailureMessage(failure({ status }))).toBe(fallback);
  });
  it("旧任务没有具体原因仍显示原通用提示", () => expect(resumeOptimizationFailureMessage(failure({ errorMessage: null }))).toBe(fallback));
  it("未知费用状态回退且不从消息推断退款", () => expect(resumeOptimizationFailureMessage(failure({ allowanceStatus: "private-unknown" as never }))).toBe(fallback));
  it("合法partial计数明确只指AI初稿与未采用提议", () => {
    expect(resumeInitialDraftSummary(completed(summary))).toBe("AI 初稿：已采用 1 项改写，3 项改写未采用，请核实。");
  });
  it("全部改写被采用时不暗示存在未采用内容", () => {
    expect(resumeInitialDraftSummary(completed({ proposedCount: 24, appliedCount: 24, retainedCount: 0, retainedReasonCounts: { factCheck: 0, sourceQuote: 0, overlap: 0, unchanged: 0 } }))).toBe("AI 初稿：已采用 24 项改写。");
  });
  it.each([
    undefined, null, [], "PRIVATE_SUMMARY", {},
    { ...summary, appliedCount: 0 }, { ...summary, proposedCount: 25 }, { ...summary, appliedCount: 1.5 },
    { ...summary, appliedCount: true }, { ...summary, retainedCount: "3" }, { ...summary, retainedCount: -1 },
    { ...summary, proposedCount: 5 }, { ...summary, retainedReasonCounts: { factCheck: 3 } },
    { ...summary, retainedReasonCounts: { factCheck: 1, sourceQuote: 0, overlap: 1, unchanged: 0 } },
    { ...summary, retainedReasonCounts: { factCheck: 1, sourceQuote: 0, overlap: 2, unchanged: false } },
    { ...summary, retainedReasonCounts: { ...summary.retainedReasonCounts, private: "PRIVATE_SUMMARY" } },
    { ...summary, private: "PRIVATE_SUMMARY" },
  ])("无效或旧版摘要隐藏，不阻断原结果 %j", value => expect(resumeInitialDraftSummary(completed(value))).toBeNull());
  it.each(["queued", "running", "failed", "cancelled"] as const)("非完成状态 %s 不显示AI初稿摘要", status => {
    expect(resumeInitialDraftSummary({ ...completed(summary), status })).toBeNull();
  });
});
