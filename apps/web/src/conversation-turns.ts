import type { SpeakerTranscriptSegment } from "@offersteady/protocol";

export const CONVERSATION_TURN_JOIN_GAP_MS = 700;
export const CONVERSATION_TURN_MAX_DURATION_MS = 45_000;
const CONVERSATION_TURN_MAX_SEGMENTS = 8;

export interface ConversationTurn extends SpeakerTranscriptSegment {
  readonly sourceSegmentIds: readonly string[];
}

const compactTranscriptText = (text: string) => text
  .replace(/\s+/g, "")
  .replace(/[，。！？、；：,.!?;:~～…·]/g, "")
  .trim();

const joinTranscriptText = (previous: string, current: string) => {
  const left = previous.trim();
  const right = current.trim();
  if (!left) return right;
  if (!right) return left;
  const compactLeft = compactTranscriptText(left);
  const compactRight = compactTranscriptText(right);
  if (compactLeft === compactRight) return right.length >= left.length ? right : left;
  if (compactLeft.includes(compactRight)) return left;
  if (compactRight.includes(compactLeft)) return right;
  return `${left} ${right}`;
};

export const reconcileTranscriptRevisions = (segments: readonly SpeakerTranscriptSegment[]) => {
  const latestById = new Map<string, SpeakerTranscriptSegment>();
  for (const segment of segments) {
    if (!compactTranscriptText(segment.text)) continue;
    const current = latestById.get(segment.id);
    if (!current || segment.revision > current.revision || (segment.revision === current.revision && segment.isFinal && !current.isFinal)) {
      latestById.set(segment.id, segment);
    }
  }
  return [...latestById.values()].sort((left, right) => left.startedAtMs - right.startedAtMs || left.revision - right.revision);
};

export const projectConversationTurns = (segments: readonly SpeakerTranscriptSegment[]): readonly ConversationTurn[] => {
  const turns: ConversationTurn[] = [];
  for (const segment of reconcileTranscriptRevisions(segments)) {
    const previous = turns.at(-1);
    const gapMs = previous ? segment.startedAtMs - previous.endedAtMs : Number.POSITIVE_INFINITY;
    const sourceSegmentIds = previous?.sourceSegmentIds ?? [];
    const canJoin = Boolean(previous)
      && previous!.sessionId === segment.sessionId
      && previous!.role === segment.role
      && previous!.sourceKind === segment.sourceKind
      && !previous!.overlap
      && !segment.overlap
      && gapMs >= -250
      && gapMs <= CONVERSATION_TURN_JOIN_GAP_MS
      && segment.endedAtMs - previous!.startedAtMs <= CONVERSATION_TURN_MAX_DURATION_MS
      && sourceSegmentIds.length < CONVERSATION_TURN_MAX_SEGMENTS;
    if (!canJoin || !previous) {
      turns.push({ ...segment, sourceSegmentIds: [segment.id] });
      continue;
    }
    turns[turns.length - 1] = {
      ...previous,
      revision: previous.revision + segment.revision,
      text: joinTranscriptText(previous.text, segment.text),
      transcriptConfidence: Math.min(previous.transcriptConfidence, segment.transcriptConfidence),
      endedAtMs: Math.max(previous.endedAtMs, segment.endedAtMs),
      isFinal: segment.isFinal,
      ...(segment.publishedAtMs !== undefined ? { publishedAtMs: segment.publishedAtMs } : {}),
      sourceSegmentIds: [...sourceSegmentIds, segment.id],
    };
  }
  return turns;
};

const normalizeQuickAnswerText = (text: string) => text.replace(/\s+/g, " ").trim();

export const latestInterviewerTurnText = (
  segments: readonly SpeakerTranscriptSegment[],
  detectedQuestion = "",
) => {
  const turns = projectConversationTurns(segments);
  const latestInterviewer = [...turns]
    .reverse()
    .find(turn => (turn.sourceKind === "system" || turn.role === "interviewer") && turn.text.trim());
  const normalizedDetected = normalizeQuickAnswerText(detectedQuestion);
  if (!latestInterviewer) return normalizedDetected;
  const latestCandidateBoundary = [...turns]
    .reverse()
    .find(turn => turn.role === "candidate" && turn.isFinal && turn.endedAtMs <= latestInterviewer.startedAtMs)?.endedAtMs ?? -Infinity;
  const eligibleInterviewerTurns = turns.filter(turn =>
    (turn.sourceKind === "system" || turn.role === "interviewer")
    && turn.endedAtMs > latestCandidateBoundary
    && turn.endedAtMs <= latestInterviewer.endedAtMs
  );
  const latestFinal = [...eligibleInterviewerTurns].reverse().find(turn => turn.isFinal);
  const newestPartial = !latestInterviewer.isFinal && (!latestFinal || latestInterviewer.endedAtMs > latestFinal.endedAtMs)
    ? latestInterviewer
    : null;
  const interviewerTurns = eligibleInterviewerTurns.filter(turn => turn.isFinal).slice(-4);
  if (newestPartial && !interviewerTurns.some(turn => turn.id === newestPartial.id)) interviewerTurns.push(newestPartial);
  const texts = interviewerTurns.map(turn => normalizeQuickAnswerText(turn.text)).filter(Boolean);
  if (normalizedDetected && !texts.some(text => text.includes(normalizedDetected) || normalizedDetected.includes(text))) texts.push(normalizedDetected);
  return texts.join(" ").trim();
};
