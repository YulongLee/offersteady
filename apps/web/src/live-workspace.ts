import type { InterviewQuestion, LiveWorkspaceViewState, SpeakerPresentationState, WebAppState } from "./domain";

export interface AnswerPage {
  readonly answer: InterviewQuestion;
  readonly index: number;
  readonly total: number;
  readonly previousId: string | null;
  readonly nextId: string | null;
  readonly isLatest: boolean;
}

export const DEFAULT_SPLIT_RATIO = 42;
export const ABSOLUTE_MIN_SPLIT_RATIO = 25;
export const ABSOLUTE_MAX_SPLIT_RATIO = 75;
export const SPLIT_LAYOUT_VERSION = 1;

export interface SplitRatioBounds { readonly min: number; readonly max: number }

export const splitRatioBounds = (containerWidth: number, conversationMin = 320, answerMin = 420, dividerWidth = 12): SplitRatioBounds => {
  const usable = Math.max(1, containerWidth - dividerWidth);
  const min = Math.max(ABSOLUTE_MIN_SPLIT_RATIO, conversationMin / usable * 100);
  const max = Math.min(ABSOLUTE_MAX_SPLIT_RATIO, 100 - answerMin / usable * 100);
  return min <= max ? { min, max } : { min: DEFAULT_SPLIT_RATIO, max: DEFAULT_SPLIT_RATIO };
};

export const clampSplitRatio = (ratio: number, bounds: SplitRatioBounds = { min: ABSOLUTE_MIN_SPLIT_RATIO, max: ABSOLUTE_MAX_SPLIT_RATIO }) => Math.min(bounds.max, Math.max(bounds.min, ratio));

export const splitRatioStorageKey = (sessionId: string) => `offersteady.live.${sessionId}.split.v${SPLIT_LAYOUT_VERSION}`;

export const parseStoredSplitRatio = (raw: string | null): number => {
  if (!raw) return DEFAULT_SPLIT_RATIO;
  try {
    const value = JSON.parse(raw) as { version?: unknown; ratio?: unknown };
    if (value.version !== SPLIT_LAYOUT_VERSION || typeof value.ratio !== "number" || !Number.isFinite(value.ratio) || value.ratio < ABSOLUTE_MIN_SPLIT_RATIO || value.ratio > ABSOLUTE_MAX_SPLIT_RATIO) return DEFAULT_SPLIT_RATIO;
    return value.ratio;
  } catch { return DEFAULT_SPLIT_RATIO; }
};

export const serializeSplitRatio = (ratio: number) => JSON.stringify({ version: SPLIT_LAYOUT_VERSION, ratio: clampSplitRatio(ratio) });

export const initialLiveWorkspaceView = (splitRatio = DEFAULT_SPLIT_RATIO): LiveWorkspaceViewState => ({ splitRatio: clampSplitRatio(splitRatio), viewingAnswerId: null, newAnswerAvailable: false });

export const answerPage = (answers: readonly InterviewQuestion[], viewingAnswerId: string | null): AnswerPage | null => {
  if (!answers.length) return null;
  const requestedIndex = viewingAnswerId ? answers.findIndex(answer => answer.id === viewingAnswerId) : 0;
  const index = requestedIndex >= 0 ? requestedIndex : 0;
  return {
    answer: answers[index]!, index, total: answers.length,
    previousId: index < answers.length - 1 ? answers[index + 1]!.id : null,
    nextId: index > 0 ? answers[index - 1]!.id : null,
    isLatest: index === 0,
  };
};

export const noteNewAnswer = (view: LiveWorkspaceViewState, previousLatestId: string | undefined, nextLatestId: string | undefined): LiveWorkspaceViewState => previousLatestId && nextLatestId && previousLatestId !== nextLatestId && view.viewingAnswerId
  ? { ...view, newAnswerAvailable: true }
  : view;

const hasVisibleTranscriptText = (text: string) => text.replace(/\s+/g, "").length > 0;

export const isolateRealtimeSpeakerSession = (
  speaker: SpeakerPresentationState,
  sessionId: string,
): SpeakerPresentationState => {
  const hasForeignSessionState = speaker.transcripts.some(segment => segment.sessionId !== sessionId)
    || Boolean(speaker.pendingQuestion && speaker.pendingQuestion.sessionId !== sessionId)
    || Boolean(speaker.degradation && speaker.degradation.sessionId !== sessionId);
  return {
    ...speaker,
    transcripts: speaker.transcripts.filter(segment => segment.sessionId === sessionId),
    pendingQuestion: speaker.pendingQuestion?.sessionId === sessionId ? speaker.pendingQuestion : null,
    degradation: speaker.degradation?.sessionId === sessionId ? speaker.degradation : null,
    runtimeNotice: hasForeignSessionState ? null : speaker.runtimeNotice,
  };
};

export const resetTransientInterviewState = (state: WebAppState): WebAppState => ({
  ...state,
  questions: [],
  captureState: "ready",
  speaker: {
    mode: "dual-channel",
    transcripts: [],
    pendingQuestion: null,
    degradation: null,
    runtimeNotice: null,
  },
  activeAnswerTask: null,
});

export const reconcileRealtimeSpeaker = (
  current: SpeakerPresentationState,
  incoming: SpeakerPresentationState,
  sessionId?: string,
): SpeakerPresentationState => {
  const scopedCurrent = sessionId ? isolateRealtimeSpeakerSession(current, sessionId) : current;
  const scopedIncoming = sessionId ? isolateRealtimeSpeakerSession(incoming, sessionId) : incoming;
  const latestById = new Map(scopedCurrent.transcripts.filter(segment => hasVisibleTranscriptText(segment.text)).map(segment => [segment.id, segment]));
  for (const segment of scopedIncoming.transcripts) {
    if (!hasVisibleTranscriptText(segment.text)) continue;
    const existing = latestById.get(segment.id);
    if (
      !existing
      || segment.revision > existing.revision
      || (segment.revision === existing.revision && segment.isFinal && !existing.isFinal)
    ) {
      latestById.set(segment.id, segment);
    }
  }
  return {
    ...scopedIncoming,
    transcripts: [...latestById.values()].sort((left, right) => (
      left.startedAtMs - right.startedAtMs || left.revision - right.revision
    )),
  };
};
