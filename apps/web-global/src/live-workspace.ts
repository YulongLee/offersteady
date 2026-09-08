import { canApplyTranscriptRevision, type AnswerTaskSnapshot } from "@offersteady/protocol";
import type { InterviewQuestion, InterviewWorkspaceSnapshot, LiveWorkspaceViewState, SpeakerPresentationState, WebAppState } from "./domain";
import { flattenTranscriptLifecycle } from "./conversation-turns";

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

const terminalAnswerStatuses = new Set<AnswerTaskSnapshot["status"]>(["completed", "failed", "cancelled"]);

const longerText = (left?: string, right?: string) => {
  if (!left) return right;
  if (!right) return left;
  return right.length > left.length ? right : left;
};

export const mergeAnswerTask = (current: AnswerTaskSnapshot | null, incoming: AnswerTaskSnapshot | null): AnswerTaskSnapshot | null => {
  if (!current) return incoming;
  if (!incoming) return current;
  if (current.id !== incoming.id) return incoming.updatedAtMs >= current.updatedAtMs ? incoming : current;

  const currentTerminal = terminalAnswerStatuses.has(current.status);
  const incomingTerminal = terminalAnswerStatuses.has(incoming.status);
  const preferIncoming = incoming.revision > current.revision
    || (incoming.revision === current.revision && incomingTerminal && !currentTerminal)
    || (incoming.revision === current.revision && incomingTerminal === currentTerminal && incoming.updatedAtMs >= current.updatedAtMs);
  const chosen = preferIncoming ? incoming : current;
  const partialText = longerText(current.partialText, incoming.partialText);
  const completedText = longerText(current.completedText, incoming.completedText);
  return {
    ...chosen,
    ...(partialText ? { partialText } : {}),
    ...(completedText ? { completedText } : {}),
    updatedAtMs: Math.max(current.updatedAtMs, incoming.updatedAtMs),
  };
};

const mergeQuestion = (current: InterviewQuestion, incoming: InterviewQuestion, preferCurrent: boolean, preserveLongestDetail = false): InterviewQuestion => {
  const chosen = preferCurrent ? current : incoming;
  const other = preferCurrent ? incoming : current;
  return {
    ...other,
    ...chosen,
    advice: {
      ...other.advice,
      ...chosen.advice,
      detail: preferCurrent || preserveLongestDetail ? longerText(current.advice.detail, incoming.advice.detail) ?? chosen.advice.detail : chosen.advice.detail,
    },
  };
};

export const reconcileAnswerWorkspace = (
  current: InterviewWorkspaceSnapshot,
  incoming: InterviewWorkspaceSnapshot,
  options: { readonly preferIncomingTask?: boolean } = {},
) => {
  const activeAnswerTask = options.preferIncomingTask && incoming.activeAnswerTask && current.activeAnswerTask?.id !== incoming.activeAnswerTask.id
    ? incoming.activeAnswerTask
    : mergeAnswerTask(current.activeAnswerTask, incoming.activeAnswerTask);
  const currentById = new Map(current.questions.map(question => [question.id, question]));
  const incomingIds = new Set(incoming.questions.map(question => question.id));
  const currentTask = current.activeAnswerTask;
  const incomingTask = incoming.activeAnswerTask;
  const sameTask = Boolean(currentTask && incomingTask && currentTask.id === incomingTask.id);
  const currentTaskTerminal = Boolean(currentTask && terminalAnswerStatuses.has(currentTask.status));
  const incomingTaskTerminal = Boolean(incomingTask && terminalAnswerStatuses.has(incomingTask.status));
  const preferCurrentTask = Boolean(currentTask && activeAnswerTask?.id === currentTask.id && (
    !incomingTask
    || incomingTask.id !== currentTask.id
    || currentTask.revision > incomingTask.revision
    || (currentTaskTerminal && !incomingTaskTerminal)
    || (currentTask.revision === incomingTask.revision && currentTaskTerminal === incomingTaskTerminal && currentTask.updatedAtMs > incomingTask.updatedAtMs)
  ));
  const preferCurrentQuestionId = preferCurrentTask ? currentTask?.questionId ?? null : null;
  const preserveLongestQuestionId = sameTask && !(incomingTaskTerminal && !currentTaskTerminal)
    ? currentTask?.questionId ?? null
    : null;
  const mergedIncoming = incoming.questions.map(question => {
    const existing = currentById.get(question.id);
    return existing ? mergeQuestion(existing, question, question.id === preferCurrentQuestionId, question.id === preserveLongestQuestionId) : question;
  });
  const localOnly = current.questions.filter(question => !incomingIds.has(question.id));
  const questions = [...mergedIncoming, ...localOnly];
  if (activeAnswerTask) {
    const activeIndex = questions.findIndex(question => question.id === activeAnswerTask.questionId);
    if (activeIndex > 0) questions.unshift(...questions.splice(activeIndex, 1));
  }
  return { questions, activeAnswerTask };
};

const hasVisibleTranscriptText = (text: string) => text.replace(/\s+/g, "").length > 0;

export const isolateRealtimeSpeakerSession = (
  speaker: SpeakerPresentationState,
  sessionId: string,
): SpeakerPresentationState => {
  const hasForeignSessionState = speaker.transcripts.some(segment => segment.sessionId !== sessionId)
    || Boolean(speaker.pendingQuestion && speaker.pendingQuestion.sessionId !== sessionId)
    || Boolean(speaker.autoAnswerQuestion && speaker.autoAnswerQuestion.sessionId !== sessionId)
    || Boolean(speaker.degradation && speaker.degradation.sessionId !== sessionId);
  return {
    ...speaker,
    transcripts: speaker.transcripts.filter(segment => segment.sessionId === sessionId),
    pendingQuestion: speaker.pendingQuestion?.sessionId === sessionId ? speaker.pendingQuestion : null,
    autoAnswerQuestion: speaker.autoAnswerQuestion?.sessionId === sessionId ? speaker.autoAnswerQuestion : null,
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
    autoAnswerQuestion: null,
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
    if (canApplyTranscriptRevision(existing, segment)) {
      latestById.set(segment.id, segment);
    }
  }
  return {
    ...scopedIncoming,
    transcripts: flattenTranscriptLifecycle([...latestById.values()]),
  };
};
