export type SubtitleRevisionStage =
  | "qwen"
  | "event"
  | "redis-xadd"
  | "redis-xread"
  | "sse-yield"
  | "browser-chunk"
  | "browser-parse"
  | "store-start"
  | "store-complete"
  | "react-render"
  | "react-commit"
  | "paint";

export interface SubtitleRevisionIdentity {
  readonly sessionId: string;
  readonly channel: string;
  readonly utteranceId: string;
  readonly segmentId: string;
  readonly revision: number;
  readonly eventId: string;
  readonly traceId: string;
  readonly textLength: number;
}

interface RevisionRecord extends SubtitleRevisionIdentity {
  readonly stages: Partial<Record<SubtitleRevisionStage, number>>;
  readonly visibilityState: DocumentVisibilityState;
  readonly renderedTextLength?: number;
}

export interface SubtitleDiagnosticsSnapshot {
  readonly enabled: boolean;
  readonly currentRevision: number;
  readonly currentEventId: string | null;
  readonly stageCounts: Readonly<Record<SubtitleRevisionStage, number>>;
  readonly remoteStageCounts: Readonly<Record<string, number>>;
  readonly latestStageAtMs: Readonly<Partial<Record<SubtitleRevisionStage, number>>>;
  readonly visibilityState: DocumentVisibilityState;
  readonly records: number;
}

const MAX_RECORDS = 4_096;
const stages: readonly SubtitleRevisionStage[] = [
  "qwen", "event", "redis-xadd", "redis-xread", "sse-yield", "browser-chunk",
  "browser-parse", "store-start", "store-complete", "react-render", "react-commit", "paint",
];
const records = new Map<string, RevisionRecord>();
const order: string[] = [];
const listeners = new Set<() => void>();
const stageCounts = Object.fromEntries(stages.map(stage => [stage, 0])) as Record<SubtitleRevisionStage, number>;
const latestStageAtMs: Partial<Record<SubtitleRevisionStage, number>> = {};
let remoteStageCounts: Record<string, number> = {};
let currentRevision = 0;
let currentEventId: string | null = null;
let cachedSnapshot: SubtitleDiagnosticsSnapshot;

export const subtitleRevisionDiagnosticsEnabled = () => {
  if (typeof window === "undefined") return false;
  return new URLSearchParams(window.location.search).get("subtitleDiagnostics") === "1";
};

const refreshSnapshot = () => {
  cachedSnapshot = {
    enabled: subtitleRevisionDiagnosticsEnabled(),
    currentRevision,
    currentEventId,
    stageCounts: { ...stageCounts },
    remoteStageCounts: { ...remoteStageCounts },
    latestStageAtMs: { ...latestStageAtMs },
    visibilityState: typeof document === "undefined" ? "hidden" : document.visibilityState,
    records: records.size,
  };
  for (const listener of listeners) listener();
};

refreshSnapshot();

export const recordSubtitleRevisionStage = (
  identity: SubtitleRevisionIdentity,
  stage: SubtitleRevisionStage,
  atMs = Date.now(),
  options: { readonly visibilityState?: DocumentVisibilityState; readonly renderedTextLength?: number } = {},
) => {
  if (!subtitleRevisionDiagnosticsEnabled() || !identity.eventId || !identity.traceId) return;
  const existing = records.get(identity.eventId);
  const nextStages = { ...(existing?.stages ?? {}) };
  const firstForStage = nextStages[stage] === undefined;
  nextStages[stage] = atMs;
  const record: RevisionRecord = {
    ...identity,
    stages: nextStages,
    visibilityState: options.visibilityState ?? (typeof document === "undefined" ? "hidden" : document.visibilityState),
    ...(options.renderedTextLength === undefined ? {} : { renderedTextLength: options.renderedTextLength }),
  };
  if (!existing) {
    records.set(identity.eventId, record);
    order.push(identity.eventId);
    while (order.length > MAX_RECORDS) {
      const expired = order.shift();
      if (expired) records.delete(expired);
    }
  } else {
    records.set(identity.eventId, record);
  }
  if (firstForStage) stageCounts[stage] += 1;
  latestStageAtMs[stage] = atMs;
  if (identity.revision >= currentRevision) {
    currentRevision = identity.revision;
    currentEventId = identity.eventId;
  }
  refreshSnapshot();
};

export const recordSubtitleBackendStages = (
  identity: SubtitleRevisionIdentity,
  performance: Readonly<Record<string, unknown>>,
) => {
  const mapping: readonly [SubtitleRevisionStage, string][] = [
    ["qwen", "qwenPartialReceivedAtMs"],
    ["event", "transcriptEventCreatedAtMs"],
    ["redis-xadd", "redisEventXaddCompleteAtMs"],
    ["redis-xread", "redisEventXreadAtMs"],
    ["sse-yield", "sseGeneratorYieldAtMs"],
  ];
  for (const [stage, field] of mapping) {
    const timestamp = performance[field];
    if (typeof timestamp === "number") recordSubtitleRevisionStage(identity, stage, timestamp);
  }
};

export const updateRemoteSubtitleStageCounts = (counts: unknown) => {
  if (!subtitleRevisionDiagnosticsEnabled() || !counts || typeof counts !== "object") return;
  remoteStageCounts = Object.fromEntries(
    Object.entries(counts).filter((entry): entry is [string, number] => typeof entry[1] === "number"),
  );
  refreshSnapshot();
};

export const subscribeSubtitleDiagnostics = (listener: () => void) => {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
};

export const getSubtitleDiagnosticsSnapshot = () => cachedSnapshot;

export const subtitleRevisionIdentity = (
  sessionId: string,
  eventId: string,
  payload: Readonly<Record<string, unknown>>,
): SubtitleRevisionIdentity | null => {
  const performance = payload.performance;
  if (!performance || typeof performance !== "object") return null;
  const timing = performance as Record<string, unknown>;
  const traceId = typeof timing.traceId === "string" ? timing.traceId : "";
  const channel = typeof payload.sourceKind === "string"
    ? payload.sourceKind
    : typeof timing.channel === "string" ? timing.channel : "unknown";
  const segmentId = typeof payload.segmentId === "string"
    ? payload.segmentId
    : typeof timing.segmentId === "string" ? timing.segmentId : "";
  const utteranceId = typeof timing.utteranceId === "string" ? timing.utteranceId : segmentId;
  const revision = typeof payload.revision === "number"
    ? payload.revision
    : typeof timing.revision === "number" ? timing.revision : 0;
  const textLength = typeof payload.text === "string"
    ? payload.text.length
    : typeof timing.textLength === "number" ? timing.textLength : 0;
  if (!traceId || !segmentId || !utteranceId || !eventId || revision <= 0) return null;
  return { sessionId, channel, utteranceId, segmentId, revision, eventId, traceId, textLength };
};

declare global {
  interface Window {
    __offersteadySubtitleRevisionDiagnostics?: {
      readonly snapshot: () => SubtitleDiagnosticsSnapshot;
    };
  }
}

if (typeof window !== "undefined" && subtitleRevisionDiagnosticsEnabled()) {
  window.__offersteadySubtitleRevisionDiagnostics = { snapshot: getSubtitleDiagnosticsSnapshot };
}
