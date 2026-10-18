// Synthetic test-only history. No real interview, audio, provider, or wallet operation.
import type { MockQuote, MockSession } from "../src/mock-interview-client";
export const previewMockQuote: MockQuote = {
  activeTimeMember: true, dailyFreeRemaining: 1, entryPoints: 0, minutePoints: 0,
  billingClass: "daily_pass_free", savedCount: 1, savedLimit: 2, dailyFreeLimit: 1,
  durationLimitMinutes: 60, quotaDay: "2026-10-18", timezone: "Asia/Shanghai",
  nowMs: Date.parse("2026-10-18T12:00:00+08:00"),
};
export const previewMockSession: MockSession = {
  sessionId: "synthetic-completed-interview", title: "合成模拟面试示例", targetRole: "后端工程师",
  billingClass: "daily_pass_free", refunded: false, createdAtMs: previewMockQuote.nowMs,
  resumeId: "synthetic-resume", resumeVersion: "synthetic-version", error: null,
  billableMs: 0, billedMinutes: 0, interacting: false, partial: true,
  durationLimitMinutes: 60,
  state: { phase: "completed", version: 1, capture_epoch: null, rounds: [
    { question_id: "synthetic-q1", question: "请介绍你实际负责的数据接口工作。", answer: "我负责使用Python开发数据接口。", submission_id: "synthetic-a1" },
  ] },
  report: { summary: "合成示例：可以更清楚地描述个人贡献和验证方法。", overall_score: 75,
    dimensions: { relevance: 80, clarity: 75, depth: 70, evidence: 75 },
    feedback: [{ question_id: "synthetic-q1", answer_quote: "我负责使用Python开发数据接口。", strength: "说明了实际负责的工作。", improvement: "补充实现过程。", suggestion: "结合真实经历说明接口设计与验证方法。" }],
    practice_priorities: ["用真实项目说明个人贡献。"],
  },
};
