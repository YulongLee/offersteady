import { describe, expect, it } from "vitest";
import { canTransitionAnswerTask, routeLegacyTranscript, supportsAnswerCancellation, supportsDualChannelRoleRouting, supportsSpeakerAwareTranscripts, type QuestionConfirmedEvent, type SpeakerTranscriptSegment } from "../src/index.js";

describe("speaker-aware protocol events", () => {
  it("round-trips a revisioned transcript segment", () => {
    const segment: SpeakerTranscriptSegment = {
      id: "seg-1", sessionId: "session-1", revision: 2, sourceId: "system", sourceKind: "system",
      speakerId: "speaker-1", role: "interviewer",
      text: "讲讲你做过的性能优化", transcriptConfidence: .94, startedAtMs: 1000, endedAtMs: 2600,
      isFinal: true, overlap: false,
    };
    expect(JSON.parse(JSON.stringify(segment))).toEqual(segment);
  });

  it("binds one confirmed question to stable answer and billing IDs", () => {
    const event: QuestionConfirmedEvent = {
      id: "confirmed-1", sessionId: "session-1", questionCandidateId: "candidate-1", questionRevision: 1,
      text: "为什么选择 React？", confirmedBy: "automatic", answerTaskId: "answer:candidate-1",
      billingUsageId: "usage:candidate-1", confirmedAtMs: 3000,
    };
    expect(event.answerTaskId).toBe("answer:candidate-1");
    expect(event.billingUsageId).toBe("usage:candidate-1");
  });

  it("keeps protocol compatibility explicit", () => {
    expect(supportsSpeakerAwareTranscripts("1.0.0")).toBe(true);
    expect(supportsDualChannelRoleRouting("1.0.0")).toBe(true);
    expect(supportsAnswerCancellation("1.0.0")).toBe(true);
    expect(supportsSpeakerAwareTranscripts("0.9.0")).toBe(false);
  });

  it("isolates legacy unknown and mixed-source segments", () => {
    const base = {
      id: "legacy", sessionId: "session-1", revision: 1, sourceId: "legacy", speakerId: "legacy-speaker",
      text: "untrusted synthetic text", transcriptConfidence: .5, startedAtMs: 1, endedAtMs: 2, isFinal: true, overlap: false,
    } as const;
    expect(routeLegacyTranscript({ ...base, sourceKind: "mixed", role: "unknown" }, 10)).toMatchObject({ kind: "degraded", event: { reason: "mixed-input" } });
    expect(routeLegacyTranscript({ ...base, sourceKind: "system", role: "unknown" }, 10)).toMatchObject({ kind: "degraded", event: { reason: "incompatible-client" } });
    expect(routeLegacyTranscript({ ...base, sourceKind: "microphone", role: "interviewer" }, 10)).toMatchObject({ kind: "routable", segment: { role: "candidate" } });
  });

  it("keeps answer task transitions monotonic", () => {
    expect(canTransitionAnswerTask("queued", "generating")).toBe(true);
    expect(canTransitionAnswerTask("generating", "cancelled")).toBe(true);
    expect(canTransitionAnswerTask("cancelled", "completed")).toBe(false);
    expect(canTransitionAnswerTask("completed", "cancelled")).toBe(false);
  });
});
