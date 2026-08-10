import { describe, expect, it } from "vitest";
import type { SpeakerTranscriptSegment } from "@offersteady/protocol";
import { latestInterviewerTurnText, projectConversationTurns, reconcileTranscriptRevisions } from "./conversation-turns";

const segment = (overrides: Partial<SpeakerTranscriptSegment> = {}): SpeakerTranscriptSegment => ({
  id: "segment-1",
  sessionId: "synthetic-session",
  revision: 1,
  sourceId: "synthetic-mic",
  sourceKind: "microphone",
  speakerId: "candidate",
  role: "candidate",
  text: "我叫李玉龙",
  transcriptConfidence: 0.96,
  startedAtMs: 1_000,
  endedAtMs: 2_000,
  isFinal: false,
  overlap: false,
  ...overrides,
});

describe("continuous conversation turns", () => {
  it("keeps only the newest revision of one streaming segment", () => {
    const first = segment();
    const latest = segment({ revision: 3, text: "我叫李玉龙，今年二十一岁", endedAtMs: 3_000 });
    expect(reconcileTranscriptRevisions([first, latest])).toEqual([latest]);
  });

  it("joins residual adjacent same-role fragments and retains source ids", () => {
    const turns = projectConversationTurns([
      segment({ id: "candidate-1", text: "我叫李玉龙。", isFinal: true }),
      segment({ id: "candidate-2", text: "今年二十一岁。", startedAtMs: 2_500, endedAtMs: 3_500, isFinal: true }),
    ]);
    expect(turns).toHaveLength(1);
    expect(turns[0]?.text).toBe("我叫李玉龙。 今年二十一岁。");
    expect(turns[0]?.sourceSegmentIds).toEqual(["candidate-1", "candidate-2"]);
  });

  it("does not join role changes, overlaps, or long gaps", () => {
    const turns = projectConversationTurns([
      segment({ id: "candidate-1", isFinal: true }),
      segment({ id: "interviewer-1", sourceKind: "system", role: "interviewer", speakerId: "interviewer", text: "请继续。", startedAtMs: 2_100, endedAtMs: 2_800, isFinal: true }),
      segment({ id: "interviewer-overlap", sourceKind: "system", role: "interviewer", speakerId: "interviewer", text: "声音重叠", startedAtMs: 2_900, endedAtMs: 3_100, isFinal: true, overlap: true }),
      segment({ id: "interviewer-late", sourceKind: "system", role: "interviewer", speakerId: "interviewer", text: "新的问题", startedAtMs: 5_000, endedAtMs: 5_800, isFinal: true }),
    ]);
    expect(turns.map(turn => turn.sourceSegmentIds)).toEqual([["candidate-1"], ["interviewer-1"], ["interviewer-overlap"], ["interviewer-late"]]);
  });

  it("builds quick-answer text from the latest bounded interviewer turn after candidate speech", () => {
    const text = latestInterviewerTurnText([
      segment({ id: "old-system", sourceKind: "system", role: "interviewer", speakerId: "interviewer", text: "旧问题", startedAtMs: 100, endedAtMs: 500, isFinal: true }),
      segment({ id: "candidate", text: "我的回答", startedAtMs: 600, endedAtMs: 1_000, isFinal: true }),
      segment({ id: "system-1", sourceKind: "system", role: "interviewer", speakerId: "interviewer", text: "请继续讲一下", startedAtMs: 1_500, endedAtMs: 2_000, isFinal: true }),
      segment({ id: "system-2", sourceKind: "system", role: "interviewer", speakerId: "interviewer", text: "你是怎么做监控闭环的？", startedAtMs: 2_100, endedAtMs: 3_000, isFinal: true }),
    ]);
    expect(text).toBe("请继续讲一下 你是怎么做监控闭环的？");
  });
});
