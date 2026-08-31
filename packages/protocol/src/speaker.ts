export type InterviewRole = "candidate" | "interviewer";
export type LegacyInterviewRole = InterviewRole | "unknown";
export type SpeakerSourceKind = "microphone" | "system";
export type LegacySpeakerSourceKind = SpeakerSourceKind | "mixed";
export type QuestionCandidateState = "auto-confirmed" | "needs-confirmation" | "rejected";
export type QuestionTriggerReason = "high-confidence-question" | "source-degraded" | "low-transcript-confidence" | "overlap" | "incomplete" | "non-question" | "candidate-speech" | "duplicate";
export type AudioSourceDegradationReason = "mixed-input" | "source-missing" | "source-disconnected" | "incompatible-client";
export type TranscriptTerminalState = "final" | "incomplete";
export type ExplicitAnswerInvocationSource = "quick-answer" | "screenshot-answer" | "manual-input";

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
  readonly turnState?: "speaking" | "tail" | "committing";
  /** `isFinal` remains for compatibility; terminalState distinguishes recovered incomplete turns. */
  readonly terminalState?: TranscriptTerminalState;
  readonly finalizationReason?: import("./realtime.js").RealtimeFinalizationReason;
  readonly sourceGeneration?: number;
  readonly overlap: boolean;
  readonly publishedAtMs?: number;
  readonly performance?: {
    readonly traceId?: string;
    readonly channel?: string;
    readonly eventId?: string;
    readonly speechStartAtMs?: number;
    readonly desktopLastMeaningfulSpeechAtMs?: number;
    readonly desktopWsSendAtMs?: number;
    readonly backendWsReceiveAtMs?: number;
    readonly qwenAudioAppendAtMs?: number;
    readonly qwenFirstAudioAppendAtMs?: number;
    readonly qwenPartialReceivedAtMs?: number;
    readonly transcriptEventCreatedAtMs?: number;
    readonly redisEventXaddStartAtMs?: number;
    readonly redisEventXaddCompleteAtMs?: number;
    readonly redisEventXaddAtMs?: number;
    readonly redisEventXreadAtMs?: number;
    readonly redisReadMode?: string;
    readonly sseGeneratorYieldAtMs?: number;
    readonly sseEventSendAtMs?: number;
    readonly browserStreamChunkReceivedAtMs?: number;
    readonly browserEventParsedAtMs?: number;
    readonly browserEventReceiveAtMs?: number;
    readonly transcriptStoreUpdateStartAtMs?: number;
    readonly transcriptStoreUpdateCompleteAtMs?: number;
    readonly browserStateUpdateAtMs?: number;
    readonly reactRenderStartAtMs?: number;
    readonly reactCommitAtMs?: number;
    readonly browserPaintAtMs?: number;
    readonly browserRenderAtMs?: number;
    readonly utteranceId?: string;
    readonly segmentId?: string;
    readonly textLength?: number;
    readonly captureToIngestMs?: number;
    readonly queueWaitMs?: number;
    readonly terminalQueueWaitMs?: number;
    readonly asrTtftMs?: number;
    readonly finalTranscriptMs?: number;
    readonly commitToLastPartialMs?: number;
    readonly commitToFinalMs?: number;
    readonly finalAddedCharacterCount?: number;
    readonly backendPushMs?: number;
    readonly frontendRenderMs?: number;
  };
}

export const transcriptTerminalState = (
  segment: Pick<SpeakerTranscriptSegment, "isFinal" | "terminalState">,
): TranscriptTerminalState | null => segment.terminalState ?? (segment.isFinal ? "final" : null);

const terminalRank = (state: TranscriptTerminalState | null): number => {
  if (state === "final") return 2;
  if (state === "incomplete") return 1;
  return 0;
};

/**
 * Segment revisions are monotonic and terminal precedence is irreversible.
 * A provider final may improve an incomplete recovery at the same/newer revision,
 * while no partial can make a terminal segment active again.
 */
export const canApplyTranscriptRevision = (
  current: Pick<SpeakerTranscriptSegment, "id" | "revision" | "isFinal" | "terminalState"> | undefined,
  incoming: Pick<SpeakerTranscriptSegment, "id" | "revision" | "isFinal" | "terminalState">,
): boolean => {
  if (!current || current.id !== incoming.id) return true;
  const currentTerminal = transcriptTerminalState(current);
  const incomingTerminal = transcriptTerminalState(incoming);
  if (terminalRank(incomingTerminal) < terminalRank(currentTerminal)) return false;
  if (incoming.revision < current.revision) return false;
  if (incoming.revision > current.revision) return true;
  return terminalRank(incomingTerminal) > terminalRank(currentTerminal);
};

export const TRANSCRIPT_MUTABLE_TAIL_CODEPOINTS = 16;
export const TRANSCRIPT_MIN_STABLE_PREFIX_CODEPOINTS = 2;

/**
 * Provider partials are complete hypotheses rather than append-only deltas.
 * Keep normal growth immediate, allow corrections only inside a bounded tail,
 * and never let a newer revision erase the stable visible prefix.
 */
export const stabilizeVisibleTranscriptText = (
  existingText: string | undefined,
  incomingText: string,
  _isFinal: boolean,
): string => {
  const current = existingText?.trim() ?? "";
  const incoming = incomingText.trim();
  if (!current) return incoming;
  const currentUnits = Array.from(current);
  const incomingUnits = Array.from(incoming);
  const startsWith = (whole: readonly string[], prefix: readonly string[]) => (
    prefix.length <= whole.length && prefix.every((unit, index) => whole[index] === unit)
  );
  if (startsWith(incomingUnits, currentUnits)) return incoming;
  if (!incoming || startsWith(currentUnits, incomingUnits) || incomingUnits.length < currentUnits.length) return current;
  let commonPrefixLength = 0;
  while (
    commonPrefixLength < currentUnits.length
    && commonPrefixLength < incomingUnits.length
    && currentUnits[commonPrefixLength] === incomingUnits[commonPrefixLength]
  ) commonPrefixLength += 1;
  let stablePrefixLength = Math.max(0, currentUnits.length - TRANSCRIPT_MUTABLE_TAIL_CODEPOINTS);
  if (currentUnits.length >= TRANSCRIPT_MIN_STABLE_PREFIX_CODEPOINTS * 2) {
    stablePrefixLength = Math.max(stablePrefixLength, TRANSCRIPT_MIN_STABLE_PREFIX_CODEPOINTS);
  }
  return commonPrefixLength >= stablePrefixLength ? incoming : current;
};

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
