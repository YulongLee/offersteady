import type { AudioSourceDegradationReason, AudioSourceDegradedEvent, InterviewRole, LegacySpeakerSourceKind, QuestionCandidateEvent, QuestionConfirmedEvent, QuestionTriggerReason, SpeakerTranscriptSegment } from "@offersteady/protocol";

export interface VoiceActivityAdapter { hasSpeech(samples: Float32Array): boolean; }
export interface EchoDetectionAdapter { isDuplicate(primary: SpeakerTranscriptSegment, candidate: SpeakerTranscriptSegment): boolean; }
export interface StreamingDiarizationAdapter { readonly capability: "dual-channel" | "unavailable"; diarize(segment: SpeakerTranscriptSegment): Promise<SpeakerTranscriptSegment>; }
export interface QuestionIntentAdapter { classify(text: string): "question" | "non-question" | "uncertain"; }

const normalize = (text: string) => text.toLowerCase().replace(/[\s，。！？,.!?]/g, "");
const overlapMs = (a: SpeakerTranscriptSegment, b: SpeakerTranscriptSegment) => Math.max(0, Math.min(a.endedAtMs, b.endedAtMs) - Math.max(a.startedAtMs, b.startedAtMs));

export class TranscriptEchoDetector implements EchoDetectionAdapter {
  isDuplicate(primary: SpeakerTranscriptSegment, candidate: SpeakerTranscriptSegment) {
    const close = overlapMs(primary, candidate) > 0 || Math.abs(primary.startedAtMs - candidate.startedAtMs) <= 1200;
    const left = normalize(primary.text); const right = normalize(candidate.text);
    return close && left.length > 2 && (left === right || left.includes(right) || right.includes(left));
  }
}

export class RuleQuestionIntentAdapter implements QuestionIntentAdapter {
  classify(text: string) {
    const normalized = text.trim().toLowerCase();
    if (!normalized) return "non-question" as const;
    if (/^(好的|好|嗯|明白|可以|ok|okay|thanks|thank you)[。.!！]?$/.test(normalized)) return "non-question" as const;
    if (/[?？]$/.test(normalized) || /(为什么|怎么|如何|哪一个|什么|讲讲|介绍一下|说说|具体|why|how|what|tell me|describe)/i.test(normalized)) return "question" as const;
    return normalized.length >= 8 ? "uncertain" as const : "non-question" as const;
  }
}

export interface TriggerThresholds { readonly transcript: number; readonly question: number; }
export const defaultTriggerThresholds: TriggerThresholds = { transcript: .8, question: .8 };

export type SourceRoleRoutingResult =
  | { readonly kind: "routed"; readonly role: InterviewRole }
  | { readonly kind: "degraded"; readonly event: AudioSourceDegradedEvent };

export class SourceRoleRouter {
  degrade(sessionId: string, reason: AudioSourceDegradationReason, sourceKind?: LegacySpeakerSourceKind, nowMs = Date.now()): SourceRoleRoutingResult {
    return { kind: "degraded", event: { id: `source-degraded:${sessionId}:${nowMs}`, sessionId, reason, ...(sourceKind ? { sourceKind } : {}), detectedAtMs: nowMs, manualInputAvailable: true } };
  }
  route(sessionId: string, sourceKind: LegacySpeakerSourceKind, conflictingChannelEvidence = false, nowMs = Date.now()): SourceRoleRoutingResult {
    if (conflictingChannelEvidence || sourceKind === "mixed") {
      return this.degrade(sessionId, sourceKind === "mixed" ? "mixed-input" : "source-missing", sourceKind, nowMs);
    }
    return { kind: "routed", role: sourceKind === "microphone" ? "candidate" : "interviewer" };
  }
}

export class SpeakerAwareQuestionDetector {
  private segments = new Map<string, SpeakerTranscriptSegment>();
  private candidates = new Map<string, QuestionCandidateEvent>();
  private confirmed = new Map<string, QuestionConfirmedEvent>();
  constructor(private readonly intent: QuestionIntentAdapter = new RuleQuestionIntentAdapter(), private readonly thresholds: TriggerThresholds = defaultTriggerThresholds) {}

  upsert(segment: SpeakerTranscriptSegment): QuestionCandidateEvent {
    const previous = this.segments.get(segment.id);
    if (previous && previous.revision > segment.revision) return this.candidateFor(previous);
    this.segments.set(segment.id, segment);
    const candidate = this.evaluate([segment]);
    this.candidates.set(candidate.id, candidate);
    return candidate;
  }

  combine(segments: readonly SpeakerTranscriptSegment[]): QuestionCandidateEvent {
    segments.forEach(segment => this.segments.set(segment.id, segment));
    const candidate = this.evaluate(segments);
    this.candidates.set(candidate.id, candidate);
    return candidate;
  }

  confirm(candidateId: string, confirmedBy: "automatic" | "user", nowMs = Date.now()) {
    const existing = this.confirmed.get(candidateId); if (existing) return existing;
    const candidate = this.candidates.get(candidateId); if (!candidate) throw new Error("question candidate not found");
    const event: QuestionConfirmedEvent = { id: `confirmed:${candidateId}`, sessionId: candidate.sessionId, questionCandidateId: candidate.id, questionRevision: candidate.revision, text: candidate.text, confirmedBy, answerTaskId: `answer:${candidateId}`, billingUsageId: `usage:${candidateId}`, confirmedAtMs: nowMs };
    this.confirmed.set(candidateId, event); return event;
  }

  clearSession(sessionId: string) {
    for (const [id, segment] of this.segments) if (segment.sessionId === sessionId) this.segments.delete(id);
    for (const [id, candidate] of this.candidates) if (candidate.sessionId === sessionId) this.candidates.delete(id);
    for (const [id, confirmed] of this.confirmed) if (confirmed.sessionId === sessionId) this.confirmed.delete(id);
  }

  private candidateFor(segment: SpeakerTranscriptSegment) { return this.candidates.get(this.stableId(segment.sessionId, [segment.id])) ?? this.evaluate([segment]); }
  private stableId(sessionId: string, ids: readonly string[]) { return `question:${sessionId}:${[...ids].sort().join("+")}`; }
  private evaluate(segments: readonly SpeakerTranscriptSegment[]): QuestionCandidateEvent {
    const ordered = [...segments].sort((a, b) => a.startedAtMs - b.startedAtMs);
    const last = ordered.at(-1)!; const text = ordered.map(segment => segment.text.trim()).filter(Boolean).join(" ");
    const id = this.stableId(last.sessionId, ordered.map(segment => segment.id));
    let state: QuestionCandidateEvent["state"] = "rejected"; let reason: QuestionTriggerReason = "non-question"; let confidence = 0;
    const intent = this.intent.classify(text);
    if (ordered.some(segment => segment.sourceKind === "microphone" || segment.role === "candidate")) reason = "candidate-speech";
    else if (ordered.some(segment => segment.overlap)) { state = "needs-confirmation"; reason = "overlap"; confidence = .45; }
    else if (!ordered.every(segment => segment.isFinal)) { state = "needs-confirmation"; reason = "incomplete"; confidence = .5; }
    else if (ordered.some(segment => segment.sourceKind !== "system" || segment.role !== "interviewer")) { state = "rejected"; reason = "source-degraded"; confidence = 0; }
    else if (ordered.some(segment => segment.transcriptConfidence < this.thresholds.transcript)) { state = "needs-confirmation"; reason = "low-transcript-confidence"; confidence = .55; }
    else if (intent === "question") { state = "auto-confirmed"; reason = "high-confidence-question"; confidence = .92; }
    else if (intent === "uncertain") { state = "needs-confirmation"; reason = "incomplete"; confidence = .6; }
    return { id, sessionId: last.sessionId, revision: Math.max(...ordered.map(segment => segment.revision)), sourceSegmentIds: ordered.map(segment => segment.id), text, state, reason, confidence };
  }
}
