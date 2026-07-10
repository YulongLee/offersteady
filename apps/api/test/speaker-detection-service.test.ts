import { describe, expect, it } from "vitest";
import type { SpeakerTranscriptSegment } from "@offersteady/protocol";
import { RuleQuestionIntentAdapter, SourceRoleRouter, SpeakerAwareQuestionDetector, TranscriptEchoDetector } from "../src/speaker-detection-service.js";

const segment = (overrides: Partial<SpeakerTranscriptSegment> = {}): SpeakerTranscriptSegment => ({
  id: "seg-1", sessionId: "s1", revision: 1, sourceId: "system", sourceKind: "system", speakerId: "remote-1",
  role: "interviewer", text: "讲讲你做过的性能优化", transcriptConfidence: .95,
  startedAtMs: 1000, endedAtMs: 2200, isFinal: true, overlap: false, ...overrides,
});

describe("speaker-aware question detection", () => {
  it("maps clean channels and degrades conflicts without a third role", () => {
    const router = new SourceRoleRouter();
    expect(router.route("s1", "microphone")).toEqual({ kind: "routed", role: "candidate" });
    expect(router.route("s1", "system")).toEqual({ kind: "routed", role: "interviewer" });
    expect(router.route("s1", "system", true, 10)).toMatchObject({ kind: "degraded", event: { reason: "source-missing" } });
    expect(router.route("s1", "mixed", false, 11)).toMatchObject({ kind: "degraded", event: { reason: "mixed-input" } });
    expect(router.degrade("s1", "source-disconnected", "system", 12)).toMatchObject({ kind: "degraded", event: { reason: "source-disconnected" } });
    expect(router.route("s1", "system", false, 13)).toEqual({ kind: "routed", role: "interviewer" });
  });

  it("suppresses candidate echo across channels", () => {
    const detector = new TranscriptEchoDetector();
    expect(detector.isDuplicate(segment({ sourceKind: "microphone", text: "我负责了性能治理" }), segment({ id: "echo", text: "我负责了性能治理", startedAtMs: 1200 }))).toBe(true);
  });

  it.each(["为什么选择 React？", "讲讲你做过的性能优化", "How would you design this system?"])("recognizes question intent: %s", text => {
    expect(new RuleQuestionIntentAdapter().classify(text)).toBe("question");
  });

  it.each(["好的", "明白", "ok"])("rejects acknowledgement: %s", text => expect(new RuleQuestionIntentAdapter().classify(text)).toBe("non-question"));

  it("auto-confirms only a final high-confidence interviewer question", () => {
    const detector = new SpeakerAwareQuestionDetector(); const candidate = detector.upsert(segment());
    expect(candidate.state).toBe("auto-confirmed");
    const first = detector.confirm(candidate.id, "automatic", 10); const replay = detector.confirm(candidate.id, "automatic", 20);
    expect(replay).toEqual(first); expect(first.billingUsageId).toBe(`usage:${candidate.id}`);
  });

  it.each([
    ["microphone", "candidate", false, true, "rejected"],
    ["system", "interviewer", true, true, "needs-confirmation"],
    ["system", "interviewer", false, false, "needs-confirmation"],
  ] as const)("gates source=%s role=%s overlap=%s final=%s", (sourceKind, role, overlap, isFinal, expected) => {
    expect(new SpeakerAwareQuestionDetector().upsert(segment({ sourceKind, role, overlap, isFinal })).state).toBe(expected);
  });

  it("combines multi-part context and revisions without duplicate IDs", () => {
    const detector = new SpeakerAwareQuestionDetector();
    const first = segment({ id: "a", text: "我们团队很关注性能。", startedAtMs: 1, endedAtMs: 2 });
    const second = segment({ id: "b", text: "讲讲你做过的性能优化", startedAtMs: 3, endedAtMs: 4 });
    const candidate = detector.combine([first, second]);
    expect(candidate.text).toContain("我们团队很关注性能"); expect(candidate.state).toBe("auto-confirmed");
    expect(detector.combine([{ ...first, revision: 2 }, second]).id).toBe(candidate.id);
  });

  it("keeps multiple remote speakers under one interviewer role and clears session evidence", () => {
    const router = new SourceRoleRouter();
    expect(router.route("s1", "system")).toEqual({ kind: "routed", role: "interviewer" });
    expect(router.route("s1", "system")).toEqual({ kind: "routed", role: "interviewer" });
    const detector = new SpeakerAwareQuestionDetector();
    const candidate = detector.upsert(segment());
    detector.clearSession("s1");
    expect(() => detector.confirm(candidate.id, "automatic")).toThrow("question candidate not found");
  });
});
