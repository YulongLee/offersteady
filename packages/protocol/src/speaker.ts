export type InterviewRole = "candidate" | "interviewer";
export type LegacyInterviewRole = InterviewRole | "unknown";
export type SpeakerSourceKind = "microphone" | "system";
export type LegacySpeakerSourceKind = SpeakerSourceKind | "mixed";
export type QuestionCandidateState = "auto-confirmed" | "needs-confirmation" | "rejected";
export type QuestionTriggerReason = "high-confidence-question" | "source-degraded" | "low-transcript-confidence" | "overlap" | "incomplete" | "non-question" | "candidate-speech" | "duplicate";
export type AudioSourceDegradationReason = "mixed-input" | "source-missing" | "source-disconnected" | "incompatible-client";

export interface SpeakerTranscriptSegment {
  readonly id: string;
  readonly sessionId: string;
  readonly revision: number;
  readonly sourceId: string;
  readonly sourceKind: SpeakerSourceKind;
  readonly speakerId: string;
  readonly role: InterviewRole;
  readonly text: string;
  readonly transcriptConfidence: number;
  readonly startedAtMs: number;
  readonly endedAtMs: number;
  readonly isFinal: boolean;
  readonly overlap: boolean;
  readonly publishedAtMs?: number;
  readonly performance?: {
    readonly captureToIngestMs?: number;
    readonly queueWaitMs?: number;
    readonly asrTtftMs?: number;
    readonly finalTranscriptMs?: number;
    readonly backendPushMs?: number;
    readonly frontendRenderMs?: number;
  };
}

export interface LegacySpeakerTranscriptSegment extends Omit<SpeakerTranscriptSegment, "sourceKind" | "role"> {
  readonly sourceKind: LegacySpeakerSourceKind;
  readonly role: LegacyInterviewRole;
  readonly speakerConfidence?: number;
  readonly roleConfidence?: number;
}

export interface AudioSourceDegradedEvent {
  readonly id: string;
  readonly sessionId: string;
  readonly reason: AudioSourceDegradationReason;
  readonly sourceKind?: LegacySpeakerSourceKind;
  readonly detectedAtMs: number;
  readonly manualInputAvailable: true;
}

export type LegacyTranscriptRoutingResult =
  | { readonly kind: "routable"; readonly segment: SpeakerTranscriptSegment }
  | { readonly kind: "degraded"; readonly event: AudioSourceDegradedEvent };

export const routeLegacyTranscript = (
  segment: LegacySpeakerTranscriptSegment,
  detectedAtMs = Date.now(),
): LegacyTranscriptRoutingResult => {
  if (segment.sourceKind !== "microphone" && segment.sourceKind !== "system") {
    return { kind: "degraded", event: { id: `degraded:${segment.id}`, sessionId: segment.sessionId, reason: "mixed-input", sourceKind: segment.sourceKind, detectedAtMs, manualInputAvailable: true } };
  }
  if (segment.role === "unknown") {
    return { kind: "degraded", event: { id: `degraded:${segment.id}`, sessionId: segment.sessionId, reason: "incompatible-client", sourceKind: segment.sourceKind, detectedAtMs, manualInputAvailable: true } };
  }
  const { speakerConfidence: _speakerConfidence, roleConfidence: _roleConfidence, ...base } = segment;
  return { kind: "routable", segment: { ...base, sourceKind: segment.sourceKind, role: segment.sourceKind === "microphone" ? "candidate" : "interviewer" } };
};

export interface QuestionCandidateEvent {
  readonly id: string;
  readonly sessionId: string;
  readonly revision: number;
  readonly sourceSegmentIds: readonly string[];
  readonly text: string;
  readonly state: QuestionCandidateState;
  readonly reason: QuestionTriggerReason;
  readonly confidence: number;
}

export interface QuestionConfirmedEvent {
  readonly id: string;
  readonly sessionId: string;
  readonly questionCandidateId: string;
  readonly questionRevision: number;
  readonly text: string;
  readonly confirmedBy: "automatic" | "user";
  readonly answerTaskId: string;
  readonly billingUsageId: string;
  readonly confirmedAtMs: number;
}

export interface SpeakerAwareCapabilities {
  readonly roleAwareTranscripts: boolean;
  readonly audioRouting: "dual-channel" | "manual-only";
  readonly supportedLanguages: readonly string[];
}
