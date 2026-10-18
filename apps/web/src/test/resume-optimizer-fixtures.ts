import { syntheticState } from "../test-state";
import type { WebAppState } from "../domain";
import type { ResumeOptimization, ResumeOptimizerCapabilities } from "../resume-optimizer-client";

export function optimizerCaps(patch: Partial<ResumeOptimizerCapabilities> = {}): ResumeOptimizerCapabilities {
  return { enabled: true, eligible: true, activeTimeMember: true, dailyLimit: 3, dailyRemaining: 3, quotaDay: "2026-10-18", timezone: "Asia/Shanghai", nowMs: Date.parse("2026-10-18T12:00:00+08:00"), resetAtMs: Date.parse("2026-10-19T00:00:00+08:00"), memberRequired: false, exhausted: false, activeJobId: null, billingClass: "daily_pass_free", entryPoints: 0, availablePoints: 250, canStart: true, limits: { resumeCharacters: 40000, jdCharacters: 12000, targetRoleCharacters: 120, draftCharacters: 60000 }, exports: ["docx", "pdf"], ...patch };
}
export const optimizerCompleted: ResumeOptimization = { jobId: "synthetic-review", status: "completed", revision: 1, sourceDocumentId: "synthetic-resume", sourceVersionId: "synthetic-version", sourceDisplayName: "合成简历.pdf", targetRole: "后端工程师", hasJd: false, quotaDay: "2026-10-18", allowanceStatus: "settled", billingClass: "daily_pass_free", pointsCharged: 0, billingStatus: "settled", createdAtMs: Date.parse("2026-10-18T12:00:00+08:00"), updatedAtMs: Date.parse("2026-10-18T12:00:00+08:00"), completedAtMs: Date.parse("2026-10-18T12:00:00+08:00"), errorCode: null, errorMessage: null, savedDocumentId: null, savedVersionId: null, sourceText: "# 合成候选人\n负责使用Python开发数据接口。\n联系：synthetic@example.invalid", jdText: "", jdDocumentId: null, jdVersionId: null, initialDraftMarkdown: "# 合成候选人\n使用Python实现数据接口开发。\n联系：synthetic@example.invalid", draftMarkdown: "# 合成候选人\n使用Python实现数据接口开发。\n联系：synthetic@example.invalid", promptVersion: "resume-optimizer-zh-v1", scoreVersion: "resume-reference-v1", review: { overallScore: 75, roleMatchingAssessed: false, dimensions: [{ key: "impact", score: 75, reason: "有具体工作内容，尚缺少可核实的成果。", evidence: [{ source: "resume", quote: "负责使用Python开发数据接口。" }] }], suggestions: [{ priority: "high", title: "说明个人贡献", explanation: "可以更清楚地描述具体工作。", recommendation: "补充你实际完成的工作范围。", evidence: [{ source: "resume", quote: "负责使用Python开发数据接口。" }] }], missingFacts: ["仅在能够核实时补充成果指标。"], disclaimer: "参考评分不代表录用概率，使用前请核实事实。" } };
export const optimizerQueued: ResumeOptimization = { ...optimizerCompleted, status: "queued", review: null, draftMarkdown: null, initialDraftMarkdown: null, allowanceStatus: "reserved", billingStatus: "reserved", completedAtMs: null };
export const optimizerCompletedWithSummary: ResumeOptimization = { ...optimizerCompleted, promptVersion: "resume-optimizer-zh-CN-v2", review: { ...optimizerCompleted.review!, editSummary: { proposedCount: 1, appliedCount: 1, retainedCount: 0, retainedReasonCounts: { factCheck: 0, sourceQuote: 0, overlap: 0, unchanged: 0 } } } };
export const optimizerPartialCompleted: ResumeOptimization = {
  ...optimizerCompletedWithSummary,
  sourceText: optimizerCompleted.sourceText + "\n参与Redis缓存维护。",
  initialDraftMarkdown: optimizerCompleted.initialDraftMarkdown + "\n参与Redis缓存维护。",
  draftMarkdown: optimizerCompleted.draftMarkdown + "\n参与Redis缓存维护。",
  review: { ...optimizerCompleted.review!, editSummary: { proposedCount: 2, appliedCount: 1, retainedCount: 1, retainedReasonCounts: { factCheck: 1, sourceQuote: 0, overlap: 0, unchanged: 0 } } },
};
export const optimizerFactsFailed: ResumeOptimization = { ...optimizerQueued, status: "failed", billingClass: "points", pointsCharged: 100, allowanceStatus: "released", billingStatus: "released", errorCode: "invalid_output", errorMessage: "AI 改写未通过原文事实检查，已停止生成。原简历无需重新上传，请稍后重试。本次积分或免费次数已退还。" };
export const optimizerNoEditsFailed: ResumeOptimization = { ...optimizerQueued, status: "failed", allowanceStatus: "released", billingStatus: "released", errorCode: "invalid_output", errorMessage: "本次未生成可安全应用的有效修改，原简历已保留。本次积分或免费次数已退还。" };
export function optimizerState(): WebAppState {
  const state = structuredClone(syntheticState);
  state.librarySources = [
    { id: "synthetic-resume", documentId: "synthetic-resume", documentVersionId: "synthetic-version", kind: "resume", ownerUserId: state.account.id, displayName: "合成简历.pdf", version: "v1", status: "ready", updatedAtMs: 1 },
    { id: "processing", documentVersionId: "processing-version", kind: "resume", ownerUserId: state.account.id, displayName: "尚在解析.pdf", version: "v1", status: "processing", updatedAtMs: 1 },
    { id: "foreign", documentVersionId: "foreign-version", kind: "resume", ownerUserId: "another-owner", displayName: "他人不可见资料", version: "v1", status: "ready", updatedAtMs: 1 },
    { id: "synthetic-jd", documentId: "synthetic-jd", documentVersionId: "synthetic-jd-version", kind: "jd", ownerUserId: state.account.id, displayName: "合成岗位描述", version: "v2", status: "ready", updatedAtMs: 1 },
  ]; return state;
}
