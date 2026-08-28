import type { CaptureState, FoundationIndexResponse } from "@offersteady/protocol";

import type { AnswerProvenance, AnswerSourceReference, AnswerTaskSnapshot, CancelAnswerResult, OfficialCheckoutOrder, PointsRedemptionResult } from "@offersteady/protocol";
import { AppError } from "./domain";
import type { ActiveInterviewConflict, AnswerAdvice, BillingPresentationState, DesktopDeviceBinding, DesktopShortcutScreenshotUpdate, IdleInterviewStatus, InterviewAppAdapter, InterviewLanguage, InterviewQuestion, InterviewReview, InterviewSummary, InterviewWorkspaceSnapshot, PreparationAudioReadiness, ReferralActivationResult, ReferralStatus, ScreenshotTask, SubmitManualAnswerResult, WebAppState } from "./domain";
import { createJsonClient, withBaseUrl } from "./api-client";
import { authClient } from "./auth-client";
import { createSseParser, type LiveAnswerStreamEvent, type ManualAnswerStreamUpdate } from "./live-answer-stream";
import {
  recordSubtitleBackendStages,
  recordSubtitleRevisionStage,
  subtitleRevisionDiagnosticsEnabled,
  subtitleRevisionIdentity,
  updateRemoteSubtitleStageCounts,
} from "./realtime-subtitle-diagnostics";

interface BackendSessionResponse {
  readonly sessionId: string;
  readonly title: string;
  readonly interviewLanguage?: InterviewLanguage;
  readonly status: "preparing" | "live" | "ended";
  readonly updatedAtMs: number;
  readonly materialBinding: {
    readonly revision: number;
    readonly resumeDocumentId: string | null;
    readonly jobDescriptionDocumentId: string | null;
    readonly knowledgeDocumentIds: readonly string[];
    readonly confirmedAtMs: number | null;
  };
}

const MAX_PENDING_PERFORMANCE_ACKS = 16;
const TRANSCRIPT_ACK_INTERVAL_MS = 1_000;
export const FIRST_REALTIME_SNAPSHOT_TIMEOUT_MS = 2_000;

interface BackendActiveSessionConflictResponse {
  readonly currentSessionId: string;
  readonly activeSession: BackendSessionResponse | null;
}

interface BackendInterviewReviewResponse {
  readonly sessionId: string;
  readonly title: string;
  readonly status: "ended";
  readonly startedAtMs: number | null;
  readonly endedAtMs: number | null;
  readonly durationMs: number;
  readonly transcripts: readonly {
    readonly id: string;
    readonly role: "interviewer" | "candidate";
    readonly speakerLabel: "面试官" | "我";
    readonly text: string;
    readonly occurredAtMs: number;
    readonly ordering: number;
  }[];
}

interface BackendSupersedeActiveSessionResponse {
  readonly currentSessionId: string;
  readonly retiredSessionIds: readonly string[];
}

interface BackendLiveAnswerTaskResponse {
  readonly taskId: string;
  readonly sessionId: string;
  readonly ownerUserId: string;
  readonly question: string;
  readonly rawQuestion?: string | null;
  readonly normalizedQuestion?: string | null;
  readonly questionNormalizationStatus?: "pending" | "completed" | "fallback" | "not-requested";
  readonly answerText: string;
  readonly status: "queued" | "streaming" | "completed" | "failed" | "cancelled";
  readonly errorMessage?: string | null;
  readonly materialContextStatus?: string;
  readonly fixedSourceCount?: number;
  readonly retrievedSourceCount?: number;
  readonly materialProvenance?: {
    readonly selectionRevision?: number;
    readonly usedSources?: readonly BackendAnswerSourceReference[];
    readonly unavailableSources?: readonly BackendAnswerSourceReference[];
    readonly fixedSourceCount?: number;
    readonly retrievedSourceCount?: number;
    readonly noPersonalMaterialUsed?: boolean;
  };
  readonly unavailableMaterialSources?: readonly BackendAnswerSourceReference[];
  readonly updatedAtMs: number;
  readonly chunks?: readonly {
    readonly sequence: number;
    readonly text: string;
    readonly isFinal: boolean;
  }[];
}

interface BackendAnswerSourceReference {
  readonly sourceId: string;
  readonly sourceVersion: string;
  readonly displayName: string;
  readonly kind: "resume" | "jd" | "knowledge";
  readonly documentId?: string | null;
  readonly documentVersionId?: string | null;
  readonly contextRole?: "fixed" | "retrieved";
  readonly evidenceSummary?: string | null;
  readonly retrievalCount?: number;
  readonly truncated?: boolean;
  readonly unavailable?: boolean;
  readonly unavailableReason?: string | null;
}

interface BackendLiveAnswerResponse {
  readonly task: BackendLiveAnswerTaskResponse;
}

interface BackendRemoteScreenshotCaptureRequestResponse {
  readonly requestId: string;
  readonly sessionId: string;
  readonly ownerUserId: string;
  readonly deviceId: string;
  readonly manualCode: string;
  readonly instruction: string;
  readonly createdAtMs: number;
  readonly updatedAtMs: number;
  readonly status: "requested" | "processing" | "completed" | "failed" | "cancelled";
  readonly stage?: string | null;
  readonly telemetry?: Record<string, unknown> | null;
  readonly answerTaskId?: string | null;
  readonly errorMessage?: string | null;
  readonly capturedFilename?: string | null;
  readonly answerTask?: BackendScreenshotAnswerTaskResponse | null;
}

interface BackendCancelledScreenshotTaskResponse extends BackendScreenshotAnswerTaskResponse {}

interface BackendScreenshotAnswerTaskResponse {
  readonly taskId: string;
  readonly sessionId: string;
  readonly ownerUserId: string;
  readonly instruction: string;
  readonly answerText: string;
  readonly status: "queued" | "processing-images" | "vision-running" | "streaming" | "completed" | "failed" | "cancelled";
  readonly imageIds: readonly string[];
  readonly imageCount: number;
  readonly providerName?: string | null;
  readonly modelName?: string | null;
  readonly visionProviderName?: string | null;
  readonly visionModelName?: string | null;
  readonly promptTemplateId?: string | null;
  readonly promptVersion?: string | null;
  readonly retrievalExcerptCount: number;
  readonly retryCount: number;
  readonly errorCode?: string | null;
  readonly errorMessage?: string | null;
  readonly createdAtMs: number;
  readonly updatedAtMs: number;
  readonly completedAtMs?: number | null;
  readonly visionSummaryTitle?: string | null;
  readonly chunks: readonly {
    readonly sequence: number;
    readonly text: string;
    readonly isFinal: boolean;
  }[];
}

interface BackendScreenshotAnswerResponse {
  readonly task: BackendScreenshotAnswerTaskResponse;
}

interface BackendDesktopBindingResponse {
  readonly bindingId: string;
  readonly sessionId: string;
  readonly deviceId: string;
  readonly manualCode: string;
  readonly displayName: string;
  readonly capabilities: Record<string, unknown>;
  readonly status: "bound" | "stale";
  readonly boundAtMs: number;
  readonly lastSeenAtMs: number;
}

interface BackendRecentDesktopDeviceResponse {
  readonly deviceId: string;
  readonly displayName: string;
  readonly maskedManualCode: string;
  readonly capabilities: Record<string, unknown>;
  readonly online: boolean;
  readonly lastSeenAtMs: number;
  readonly accountBound?: boolean;
  readonly devicePresence?: "online" | "offline";
  readonly permissionStatus?: Record<string, unknown>;
}

interface BackendAccountDesktopDeviceResponse extends BackendRecentDesktopDeviceResponse {
  readonly linkedAtMs: number;
  readonly lastUsedAtMs: number;
  readonly activeInterview?: { readonly sessionId: string; readonly bindingId: string; readonly connectedAtMs: number } | null;
}

interface BackendRealtimeTranscriptListResponse {
  readonly sessionId: string;
  readonly transcripts: readonly {
    readonly segmentId: string;
    readonly sessionId?: string;
    readonly sourceId: string;
    readonly sourceKind: "microphone" | "system" | "mixed";
    readonly role: "candidate" | "interviewer";
    readonly revision: number;
    readonly text: string;
    readonly transcriptConfidence: number;
    readonly startedAtMs: number;
    readonly endedAtMs: number;
    readonly isFinal: boolean;
    readonly turnState?: "speaking" | "tail" | "committing";
    readonly terminalState?: "final" | "incomplete";
    readonly finalizationReason?: "silence" | "max-duration" | "capture-stop" | "source-recovery" | "backend-watchdog" | "provider-completed" | "provider-timeout";
    readonly overlap: boolean;
    readonly publishedAtMs?: number;
    readonly performance?: {
      readonly traceId?: string;
      readonly channel?: string;
      readonly captureToSendMs?: number;
      readonly sendToIngestMs?: number;
      readonly captureToIngestMs?: number;
      readonly queueWaitMs?: number;
      readonly asrTtftMs?: number;
      readonly finalTranscriptMs?: number;
      readonly backendPushMs?: number;
      readonly captureToPublishMs?: number;
      readonly frontendRenderMs?: number;
      readonly liveObservedAtMs?: number;
      readonly publisherConnectedAtMs?: number;
      readonly sourceReadyAtMs?: number;
      readonly sourceReadyMode?: "promoted" | "opened" | "stale-fallback";
      readonly desktopTerminalEnqueueAtMs?: number;
      readonly eventId?: string;
      readonly speechStartAtMs?: number;
      readonly desktopWsSendAtMs?: number;
      readonly backendWsReceiveAtMs?: number;
      readonly qwenAudioAppendAtMs?: number;
      readonly qwenFirstAudioAppendAtMs?: number;
      readonly qwenPartialReceivedAtMs?: number;
      readonly redisEventXaddAtMs?: number;
      readonly redisEventXaddStartAtMs?: number;
      readonly redisEventXaddCompleteAtMs?: number;
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
    };
  }[];
}

interface BackendRealtimeQuestionCandidateListResponse {
  readonly sessionId: string;
  readonly candidates: readonly {
    readonly candidateId: string;
    readonly sourceSegmentIds: readonly string[];
    readonly text: string;
    readonly state: "needs-confirmation" | "confirmed" | "dismissed";
    readonly reason: string;
    readonly confidence: number;
  }[];
}

interface BackendRealtimeEventListResponse {
  readonly sessionId: string;
  readonly events: readonly {
    readonly eventId: string;
    readonly kind: string;
    readonly payload: Record<string, unknown>;
    readonly createdAtMs: number;
  }[];
}

interface BackendRealtimeRuntimeResponse {
  readonly sessionId: string;
  readonly sessionStatus: string;
  readonly stage: string;
  readonly backendReachable: boolean;
  readonly deviceRegistered: boolean;
  readonly machineCodeBound: boolean;
  readonly sessionLive: boolean;
  readonly captureState?: string;
  readonly readinessState?: "preparing" | "ready" | "degraded" | "paused" | string;
  readonly sourceReadiness?: Readonly<Record<string, "preparing" | "ready" | "degraded" | string>>;
  readonly manualCode?: string | null;
  readonly deviceId?: string | null;
  readonly displayName?: string | null;
  readonly transcriptCount: number;
  readonly questionCandidateCount: number;
  readonly latestState?: string | null;
  readonly lastErrorCode?: string | null;
  readonly anomalyReasons?: readonly string[];
  readonly dominantBottleneck?: string | null;
  readonly evidence?: {
    readonly bindingReady?: boolean;
    readonly sessionLive?: boolean;
    readonly publisherCreated?: boolean;
    readonly publisherCount?: number;
    readonly localSignalObserved?: boolean;
    readonly localSignalSources?: readonly string[];
    readonly realFrameReceiptReceived?: boolean;
    readonly realFrameSources?: readonly string[];
    readonly diagnosticProbeFrameReceived?: boolean;
    readonly asrAccepted?: boolean;
    readonly asrAcceptedSources?: readonly string[];
    readonly transcriptEmitted?: boolean;
    readonly transcriptCount?: number;
    readonly webConsumerSeen?: boolean;
    readonly webConsumerLastSeenAtMs?: number | null;
  };
  readonly performance?: {
    readonly latestBySource?: Record<string, {
      readonly traceId?: string;
      readonly captureToSendMs?: number;
      readonly sendToIngestMs?: number;
      readonly captureToIngestMs?: number;
      readonly queueWaitMs?: number;
      readonly asrTtftMs?: number;
      readonly finalTranscriptMs?: number;
      readonly backendPushMs?: number;
      readonly captureToPublishMs?: number;
      readonly frontendRenderMs?: number;
      readonly eventId?: string;
      readonly speechStartAtMs?: number;
      readonly redisEventXreadAtMs?: number;
      readonly sseEventSendAtMs?: number;
      readonly browserEventReceiveAtMs?: number;
      readonly browserStateUpdateAtMs?: number;
      readonly browserRenderAtMs?: number;
    }>;
    readonly countersBySource?: Record<string, {
      readonly queueDepth: number;
      readonly droppedPartialUpdates: number;
      readonly connectionRecreations: number;
      readonly emptyResultsSuppressed: number;
      readonly phantomResultsSuppressed: number;
      readonly repetitiveResultsSuppressed: number;
      readonly duplicateResultsSuppressed: number;
      readonly fillerResultsSuppressed: number;
      readonly chunksProduced: number;
      readonly chunksUploaded: number;
      readonly serializedAudioBytes: number;
      readonly providerAppendCount?: number;
      readonly providerCommitCount?: number;
      readonly providerCompletedMissing?: number;
      readonly blankPartialSuppressed?: number;
      readonly vadToManualFallbacks?: number;
      readonly idleProviderSessionClosures?: number;
      readonly activeProviderSessions?: number;
    }>;
  };
  readonly sourceHealth: readonly {
    readonly sourceId: string;
    readonly sourceKind: "microphone" | "system" | "mixed" | string;
    readonly label: string;
    readonly state: string;
    readonly stage?: string | null;
    readonly level: number;
    readonly lastSignalAtMs?: number | null;
    readonly readinessState?: "unchecked" | "ready" | "stale" | string | null;
    readonly readinessExpiresAtMs?: number | null;
    readonly errorCode?: string | null;
    readonly frameCount?: number | null;
    readonly backendFrameCount?: number | null;
    readonly pendingFrameCount?: number | null;
    readonly oldestPendingFrameAgeMs?: number | null;
    readonly droppedFrameCount?: number | null;
    readonly reconnectCount?: number | null;
    readonly lastAckAtMs?: number | null;
    readonly lastReconnectReason?: string | null;
    readonly noiseFloor?: number | null;
    readonly captureProcessor?: string | null;
  }[];
}

interface BackendRealtimeSessionStreamEvent {
  readonly type: "snapshot" | "update";
  readonly cursor?: number;
  readonly transcripts?: BackendRealtimeTranscriptListResponse;
  readonly candidates?: BackendRealtimeQuestionCandidateListResponse;
  readonly events: BackendRealtimeEventListResponse;
  readonly runtime?: BackendRealtimeRuntimeResponse | null;
}

interface MaterializedRealtimeSessionStreamEvent extends BackendRealtimeSessionStreamEvent {
  readonly transcripts: BackendRealtimeTranscriptListResponse;
  readonly candidates: BackendRealtimeQuestionCandidateListResponse;
  readonly runtime: BackendRealtimeRuntimeResponse | null;
}

type BackendRealtimeTranscript = BackendRealtimeTranscriptListResponse["transcripts"][number];
type BackendRealtimeCandidate = BackendRealtimeQuestionCandidateListResponse["candidates"][number];

const materializeRealtimeDelta = (
  interviewId: string,
  current: MaterializedRealtimeSessionStreamEvent | null,
  incoming: BackendRealtimeSessionStreamEvent,
): MaterializedRealtimeSessionStreamEvent | null => {
  if (incoming.type === "snapshot") {
    if (!incoming.transcripts || !incoming.candidates || incoming.runtime === undefined) return null;
    return incoming as MaterializedRealtimeSessionStreamEvent;
  }
  // Compatibility with servers from the migration window that labelled a
  // complete payload as an update.
  if (!current && incoming.transcripts && incoming.candidates && incoming.runtime !== undefined) {
    return incoming as MaterializedRealtimeSessionStreamEvent;
  }
  if (!current) return null;
  const transcriptById = new Map(current.transcripts.transcripts.map(item => [item.segmentId, item]));
  const candidateById = new Map(current.candidates.candidates.map(item => [item.candidateId, item]));
  let runtime = incoming.runtime !== undefined ? incoming.runtime : current.runtime;
  for (const event of incoming.events.events) {
    if (event.kind === "transcript-committing") {
      const segmentId = typeof event.payload.segmentId === "string" ? event.payload.segmentId : "";
      const existing = segmentId ? transcriptById.get(segmentId) : undefined;
      if (existing && !existing.isFinal) transcriptById.set(segmentId, { ...existing, turnState: "committing" });
    }
    if (event.kind === "transcript-updated") {
      const payload = event.payload;
      const segmentId = typeof payload.segmentId === "string" ? payload.segmentId : "";
      const existing = segmentId ? transcriptById.get(segmentId) : undefined;
      const revision = typeof payload.revision === "number" ? payload.revision : 0;
      const isFinal = payload.isFinal === true;
      if (!segmentId || (existing && (revision < existing.revision || (revision === existing.revision && existing.isFinal) || (existing.isFinal && !isFinal)))) continue;
      const sourceKind = payload.sourceKind === "microphone" || payload.sourceKind === "system" || payload.sourceKind === "mixed"
        ? payload.sourceKind
        : existing?.sourceKind;
      const role = payload.role === "candidate" || payload.role === "interviewer" ? payload.role : existing?.role;
      if (!sourceKind || !role) continue;
      const finalizationReason = typeof payload.finalizationReason === "string" && [
        "silence", "max-duration", "capture-stop", "source-recovery", "backend-watchdog", "provider-completed", "provider-timeout",
      ].includes(payload.finalizationReason)
        ? payload.finalizationReason as NonNullable<BackendRealtimeTranscript["finalizationReason"]>
        : undefined;
      const next: BackendRealtimeTranscript = {
        segmentId,
        sourceId: typeof payload.sourceId === "string" ? payload.sourceId : existing?.sourceId ?? segmentId,
        sourceKind,
        role,
        revision,
        text: (() => {
          const incomingText = typeof payload.text === "string" ? payload.text : existing?.text ?? "";
          if (isFinal || !existing || existing.isFinal) return incomingText;
          const compact = (value: string) => value
            .replace(/\s+/g, "")
            .replace(/[，。！？、；：,.!?;:~～…·\-—_]+/g, "");
          return compact(incomingText).length < compact(existing.text).length ? existing.text : incomingText;
        })(),
        transcriptConfidence: typeof payload.transcriptConfidence === "number" ? payload.transcriptConfidence : existing?.transcriptConfidence ?? 0,
        startedAtMs: typeof payload.startedAtMs === "number" ? payload.startedAtMs : existing?.startedAtMs ?? event.createdAtMs,
        endedAtMs: typeof payload.endedAtMs === "number" ? payload.endedAtMs : existing?.endedAtMs ?? event.createdAtMs,
        isFinal,
        ...(isFinal ? {} : {
          turnState: existing?.turnState === "committing" ? "committing" as const : "speaking" as const,
        }),
        overlap: typeof payload.overlap === "boolean" ? payload.overlap : existing?.overlap ?? false,
        ...(payload.terminalState === "final" || payload.terminalState === "incomplete" ? { terminalState: payload.terminalState } : {}),
        ...(finalizationReason ? { finalizationReason } : {}),
        ...(typeof payload.publishedAtMs === "number" ? { publishedAtMs: payload.publishedAtMs } : {}),
        ...(typeof payload.performance === "object" && payload.performance !== null ? { performance: payload.performance as NonNullable<BackendRealtimeTranscript["performance"]> } : {}),
      };
      transcriptById.set(segmentId, next);
    }
    if ((event.kind === "question-candidate" || event.kind === "question-confirmed") && typeof event.payload.candidate === "object" && event.payload.candidate !== null) {
      const candidate = event.payload.candidate as BackendRealtimeCandidate;
      if (typeof candidate.candidateId === "string") candidateById.set(candidate.candidateId, candidate);
    }
    if (runtime && event.kind === "capture-control" && (event.payload.captureState === "paused" || event.payload.captureState === "capturing")) {
      runtime = { ...runtime, captureState: event.payload.captureState };
    }
    if (runtime && event.kind === "connection-state" && typeof event.payload.status === "string") {
      runtime = { ...runtime, latestState: event.payload.status };
    }
  }
  const events = [...current.events.events, ...incoming.events.events]
    .filter((item, index, items) => items.findIndex(candidate => candidate.eventId === item.eventId) === index)
    .sort((left, right) => left.createdAtMs - right.createdAtMs)
    .slice(-128);
  const transcripts = [...transcriptById.values()].sort((left, right) => left.startedAtMs - right.startedAtMs || left.segmentId.localeCompare(right.segmentId));
  const candidates = [...candidateById.values()];
  return {
    type: "update",
    cursor: Math.max(current.cursor ?? 0, incoming.cursor ?? 0),
    transcripts: { sessionId: current.transcripts.sessionId || interviewId, transcripts },
    candidates: { sessionId: current.candidates.sessionId || interviewId, candidates },
    events: { sessionId: current.events.sessionId || interviewId, events },
    runtime: runtime ? { ...runtime, transcriptCount: transcripts.length, questionCandidateCount: candidates.length } : null,
  };
};

interface BackendRealtimeSessionSnapshotResponse {
  readonly sessionId: string;
  readonly ownerUserId: string;
  readonly cursor: number;
  readonly resumable: boolean;
  readonly transcripts: BackendRealtimeTranscriptListResponse;
  readonly candidates: BackendRealtimeQuestionCandidateListResponse;
  readonly events: BackendRealtimeEventListResponse;
  readonly runtime: BackendRealtimeRuntimeResponse;
}

interface BackendCancelAnswerResponse {
  readonly outcome: CancelAnswerResult["outcome"];
  readonly task: BackendLiveAnswerTaskResponse;
  readonly billingReleased: boolean;
}

const authHeaders = () => {
  const session = authClient.readStoredSession();
  return session ? { Authorization: `Bearer ${session.accessToken}` } : {};
};

export const createAuthRefreshingFetch = (
  fetchImpl: typeof fetch,
  refreshSession: () => Promise<void> = () => authClient.refresh().then(() => undefined),
): typeof fetch => {
  let refreshInFlight: Promise<void> | null = null;
  return async (input, init) => {
    const response = await fetchImpl(input, init);
    if (response.status !== 401 || !authClient.readStoredSession()) return response;
    try {
      if (!refreshInFlight) {
        refreshInFlight = refreshSession().finally(() => {
          refreshInFlight = null;
        });
      }
      await refreshInFlight;
    } catch {
      return response;
    }
    const session = authClient.readStoredSession();
    if (!session) return response;
    const headers = new Headers(init?.headers);
    headers.set("Authorization", `Bearer ${session.accessToken}`);
    return fetchImpl(input, { ...init, headers });
  };
};

const requireUserId = () => {
  const session = authClient.readStoredSession();
  if (session) return session.account.id;
  throw new AppError("validation", "请先登录后再继续操作");
};

const toInterviewSummary = (session: BackendSessionResponse, fallback?: { title?: string; role?: string; company?: string }): InterviewSummary => ({
  id: session.sessionId,
  title: session.title || fallback?.title || "新的面试",
  interviewLanguage: session.interviewLanguage ?? "zh-CN",
  role: fallback?.role || session.title || "目标岗位",
  ...(fallback?.company?.trim() ? { company: fallback.company.trim() } : {}),
  status: session.status === "live" ? "active" : session.status,
  updatedAt: "刚刚",
  readiness: session.materialBinding.confirmedAtMs ? 100 : 0,
});

const deriveInterviewTitle = (input: { title: string; role: string; company?: string }) => {
  const explicitTitle = input.title.trim();
  const role = input.role.trim();
  const company = input.company?.trim() ?? "";

  if (explicitTitle && explicitTitle !== "新的面试") {
    return explicitTitle;
  }

  const derivedTitle = [company, role].filter(Boolean).join(" · ");
  return derivedTitle || explicitTitle || "新的面试";
};

const toDesktopDeviceBinding = (binding: BackendDesktopBindingResponse): DesktopDeviceBinding => ({
  bindingId: binding.bindingId,
  sessionId: binding.sessionId,
  deviceId: binding.deviceId,
  manualCode: binding.manualCode,
  displayName: binding.displayName,
  capabilities: binding.capabilities,
  status: binding.status,
  boundAtMs: binding.boundAtMs,
  lastSeenAtMs: binding.lastSeenAtMs,
});

export const toPreparationAudioReadiness = (
  runtime: BackendRealtimeRuntimeResponse,
  nowMs = Date.now(),
): PreparationAudioReadiness => {
  const sources = (["microphone", "system"] as const).map(sourceKind => {
    const health = runtime.sourceHealth.find(item => item.sourceKind === sourceKind);
    const backendState = runtime.sourceReadiness?.[sourceKind];
    const signalFresh = Boolean(
      health?.lastSignalAtMs
      && nowMs >= health.lastSignalAtMs
      && nowMs - health.lastSignalAtMs <= 120_000,
    );
    const degraded = backendState === "degraded" || ["unavailable", "permission-denied", "error"].includes(health?.state ?? "");
    const ready = backendState === "ready" && signalFresh;
    const label = sourceKind === "system" ? "电脑输出" : "麦克风";
    return {
      sourceKind,
      state: degraded ? "degraded" as const : ready ? "ready" as const : "checking" as const,
      ...(health?.lastSignalAtMs ? { lastSignalAtMs: health.lastSignalAtMs } : {}),
      message: degraded
        ? `${label}不可用，请在伴随程序中重新检查`
        : ready
          ? `${label}声音检查通过`
          : health?.state === "silent"
            ? `${label}已打开，等待检测到真实声音`
            : `${label}和识别服务正在准备`,
    };
  });
  return {
    state: sources.some(item => item.state === "degraded")
      ? "degraded"
      : sources.every(item => item.state === "ready")
        ? "ready"
        : "checking",
    sources,
    updatedAtMs: nowMs,
  };
};

const answerTextFromTask = (task: BackendLiveAnswerTaskResponse) => {
  const chunkText = task.chunks?.length ? [...task.chunks].sort((left, right) => left.sequence - right.sequence).map(chunk => chunk.text).join("") : "";
  return task.answerText || chunkText;
};

const taskStatus = (task: BackendLiveAnswerTaskResponse): AnswerTaskSnapshot["status"] =>
  task.status === "streaming" ? "generating" : task.status === "completed" ? "completed" : task.status;

const sourceFromBackend = (source: BackendAnswerSourceReference): AnswerSourceReference => ({
  sourceId: source.sourceId,
  sourceVersion: source.sourceVersion,
  displayName: source.displayName,
  kind: source.kind,
  ...(source.documentId ? { documentId: source.documentId } : {}),
  ...(source.documentVersionId ? { documentVersionId: source.documentVersionId } : {}),
  ...(source.contextRole ? { contextRole: source.contextRole } : {}),
  ...(source.evidenceSummary ? { evidenceSummary: source.evidenceSummary } : {}),
  ...(typeof source.retrievalCount === "number" ? { retrievalCount: source.retrievalCount } : {}),
  ...(typeof source.truncated === "boolean" ? { truncated: source.truncated } : {}),
  ...(typeof source.unavailable === "boolean" ? { unavailable: source.unavailable } : {}),
  ...(source.unavailableReason ? { unavailableReason: source.unavailableReason } : {}),
});

const provenanceFromTask = (task: BackendLiveAnswerTaskResponse): AnswerProvenance => {
  const material = task.materialProvenance;
  return {
    selectionRevision: material?.selectionRevision ?? 0,
    usedSources: (material?.usedSources ?? []).map(sourceFromBackend),
    unavailableSources: (material?.unavailableSources ?? task.unavailableMaterialSources ?? []).map(sourceFromBackend),
    fixedSourceCount: material?.fixedSourceCount ?? task.fixedSourceCount ?? 0,
    retrievedSourceCount: material?.retrievedSourceCount ?? task.retrievedSourceCount ?? 0,
    noPersonalMaterialUsed: material?.noPersonalMaterialUsed ?? !(material?.usedSources?.length),
  };
};

const captureStates = new Set<CaptureState>(["not-connected", "permission-required", "ready", "capturing", "paused", "reconnecting", "error"]);

const toCaptureState = (value: unknown): CaptureState | undefined => {
  if (typeof value !== "string") return undefined;
  return captureStates.has(value as CaptureState) ? value as CaptureState : undefined;
};

const toSpeakerRole = (role: "candidate" | "interviewer", sourceKind: "microphone" | "system" | "mixed") => {
  if (role === "candidate") {
    return {
      speakerId: "candidate",
      role: "candidate" as const,
      sourceKind: sourceKind === "microphone" ? "microphone" as const : "microphone" as const,
    };
  }
  return {
    speakerId: "interviewer",
    role: "interviewer" as const,
    sourceKind: sourceKind === "system" ? "system" as const : "system" as const,
  };
};

const runtimeNotice = (runtime: BackendRealtimeRuntimeResponse | null, degradedEvent?: BackendRealtimeEventListResponse["events"][number]) => {
  if (degradedEvent?.payload?.reason === "mixed-input") return null;
  if (!runtime) return { stage: "backend-unreachable", message: "当前 session 的实时链路状态暂不可用，请检查后端连接。" };
  if (!runtime.machineCodeBound) return { stage: runtime.stage, message: "当前 session 尚未绑定桌面伴随程序，请先输入机器码并保持网页在线。" };
  if (!runtime.sessionLive) return { stage: runtime.stage, message: "本场面试还未开始，开始面试后才会同步“面试官 / 我”的实时对话。" };
  if (runtime.readinessState === "degraded") {
    const unavailable = Object.entries(runtime.sourceReadiness ?? {})
      .filter(([, state]) => state === "degraded")
      .map(([source]) => source === "system" ? "电脑输出" : source === "microphone" ? "麦克风" : source)
      .join("、");
    return { stage: runtime.stage, message: `${unavailable || "实时音频"}尚未就绪，其他可用声道会继续工作；请在伴随程序中检查对应设备。` };
  }
  if (runtime.readinessState === "preparing") return { stage: runtime.stage, message: "实时语音链路正在准备，麦克风、电脑输出和识别服务全部就绪后即可立即开始。" };
  if (runtime.dominantBottleneck === "capture-no-frame") return { stage: runtime.stage, message: "桌面端已绑定，但真实麦克风/电脑输出还没有产生可发送音频帧；请检查伴随程序采集权限和已选输入设备。" };
  if (runtime.dominantBottleneck === "publisher-no-connect") {
    return runtime.evidence?.publisherCreated
      ? { stage: runtime.stage, message: "实时发布通道已建立，正在等待麦克风或电脑输出产生可识别音频帧。" }
      : { stage: runtime.stage, message: "当前 session 尚未建立实时发布通道，请确认已点击开始面试且桌面助手保持连接。" };
  }
  if (runtime.dominantBottleneck === "backend-no-receipt") return { stage: runtime.stage, message: "桌面端检测到本地声音，但后端还没有收到真实音频帧，问题在桌面发布或网络传输链路。" };
  if (runtime.dominantBottleneck === "asr-accepted-no-text") return { stage: runtime.stage, message: "ASR 已接收音频帧，但没有形成可展示文本；可能是静音、口头语被过滤或识别超时。" };
  if (runtime.dominantBottleneck === "web-no-consumer") return { stage: runtime.stage, message: "后端已有实时转写，但当前网页还没有消费到 live session，请刷新页面或检查实时订阅。" };
  if (runtime.dominantBottleneck === "desktop_no_audio_frames") return { stage: runtime.stage, message: "桌面端已绑定，但真实麦克风/电脑输出还没有产生可发送音频帧；请检查伴随程序采集权限和已选输入设备。" };
  if (runtime.dominantBottleneck?.includes("desktop_send_backlog")) return { stage: runtime.stage, message: "桌面端正在采集，但发送积压过高，实时字幕会明显变慢。" };
  if (runtime.dominantBottleneck?.includes("desktop_audio_gap")) return { stage: runtime.stage, message: "桌面端检测到音频发送缺口，正在自动恢复连接；请保持助手在线并检查当前网络。" };
  if (runtime.dominantBottleneck?.includes("backend_ingest_queue_delayed")) return { stage: runtime.stage, message: "后端已收到音频，但排队等待过长，实时对话正在追赶中。" };
  if (runtime.dominantBottleneck?.includes("provider_partial_timeout")) return { stage: runtime.stage, message: "音频已经送入 ASR，但首段 partial 返回过慢，当前瓶颈在实时识别链路。" };
  if (runtime.dominantBottleneck?.includes("provider_final_timeout")) return { stage: runtime.stage, message: "实时字幕已开始返回，但 final 收束过慢，当前瓶颈在 ASR 完成阶段。" };
  if (runtime.dominantBottleneck?.includes("publish_lag")) return { stage: runtime.stage, message: "识别结果已生成，但发布到网页对话区存在延迟。" };
  if (runtime.dominantBottleneck?.includes("repetitive_transcript_suppressed")) return { stage: runtime.stage, message: "已检测到异常重复转写，系统暂时忽略了这段结果；请检查麦克风回声或电脑输出采集是否混入杂音。" };
  if (runtime.dominantBottleneck?.includes("duplicate_transcript_suppressed")) return { stage: runtime.stage, message: "已检测到短时间内高度重复的转写，系统暂时忽略了这段结果；请检查是否存在回声、复读或采集串音。" };
  if (runtime.dominantBottleneck?.includes("filler_transcript_suppressed")) return { stage: runtime.stage, message: "已自动忽略口头语和极短碎片发言，实时对话区会优先保留真正有信息量的内容。" };
  if (runtime.lastErrorCode === "asr-failed") return { stage: runtime.stage, message: "后端已收到当前 session 音频，但实时转写失败，请检查 ASR 配置。" };
  if (runtime.lastErrorCode?.startsWith("realtime_asr_")) return { stage: runtime.stage, message: "ASR 实时转写通道异常，已收到音频但转写超时/失败，请检查麦克风采集质量、网络链路或重连桌面端。" };
  if (runtime.latestState === "failed") return { stage: runtime.stage, message: "当前 session 的实时发布链路失败，请检查桌面伴随程序连接状态。" };
  const hasFrames = Boolean(runtime.evidence?.realFrameReceiptReceived) || runtime.sourceHealth.some((item) => (item.frameCount ?? 0) > 0 || (item.backendFrameCount ?? 0) > 0);
  if (!hasFrames && runtime.evidence?.diagnosticProbeFrameReceived) return { stage: runtime.stage, message: "ASR 合成探针可达，但桌面真实采集仍为 0 帧；需要修复桌面采集链路。" };
  if (!hasFrames) return { stage: runtime.stage, message: "当前 session 尚未采集到有效音频帧，请检查麦克风、电脑输出和桌面伴随程序状态。" };
  if (runtime.stage === "publishing" || runtime.stage === "transcribing") return { stage: runtime.stage, message: "当前 session 正在接收音频并返回 partial 字幕，网页会优先显示最新片段。" };
  return { stage: runtime.stage, message: "当前 session 正在同步实时对话，请稍候。" };
};

const toAnswerTaskSnapshot = (task: BackendLiveAnswerTaskResponse, current: AnswerTaskSnapshot): AnswerTaskSnapshot => {
  const next: AnswerTaskSnapshot = {
    ...current,
    id: task.taskId,
    interviewId: task.sessionId,
    userId: task.ownerUserId,
    question: task.question,
    status: taskStatus(task),
    updatedAtMs: task.updatedAtMs,
    revision: current.revision + 1,
    provenance: provenanceFromTask(task),
    ...(task.materialContextStatus ? { materialContextStatus: task.materialContextStatus } : {}),
  };
  const completedText = answerTextFromTask(task) || current.completedText;
  if (completedText) return { ...next, completedText };
  return next;
};

const adviceFromLiveAnswerTask = (task: BackendLiveAnswerTaskResponse): AnswerAdvice => {
  const answerText = answerTextFromTask(task);
  const failed = task.status === "failed";
  return {
    outline: [],
    detail: answerText || task.errorMessage || (failed ? "回答生成失败，请稍后重试。" : "回答正在生成，完成后会在这里展示。"),
    sourceTypes: ["简历", "JD", "知识库"],
    inference: "",
    uncertain: failed,
    provenance: provenanceFromTask(task),
  };
};

const mapRealtimeState = (
  interviewId: string,
  transcripts: BackendRealtimeTranscriptListResponse,
  candidates: BackendRealtimeQuestionCandidateListResponse,
  events: BackendRealtimeEventListResponse,
  runtime: BackendRealtimeRuntimeResponse | null,
) => {
  const pending = candidates.candidates.find(candidate => candidate.state === "needs-confirmation");
  const newestEvents = [...events.events].sort((left, right) => right.createdAtMs - left.createdAtMs);
  const latestDeviceStatus = newestEvents.find(event => event.kind === "device-status");
  const latestDegraded = newestEvents.find(event => event.kind === "degraded");
  const latestShortcutAccepted = newestEvents.find(event => event.kind === "screenshot-shortcut-accepted" && typeof event.payload.requestId === "string");
  const latestScreenshotUpdate = newestEvents.find(event => event.kind === "screenshot-capture-updated" && typeof event.payload.requestId === "string");
  const latestAnswerUpdate = newestEvents.find(event => event.kind === "answer-task-updated" && typeof event.payload.task === "object" && event.payload.task !== null);
  const committingSegments = new Set(newestEvents
    .filter(event => event.kind === "transcript-committing" && typeof event.payload.segmentId === "string")
    .map(event => String(event.payload.segmentId)));
  const useScreenshotUpdate = Boolean(latestScreenshotUpdate && (
    !latestShortcutAccepted
    || latestScreenshotUpdate.createdAtMs >= latestShortcutAccepted.createdAtMs
    || latestScreenshotUpdate.payload.requestId === latestShortcutAccepted.payload.requestId
  ));
  const reportedCaptureState = toCaptureState(runtime?.captureState)
    ?? toCaptureState(latestDeviceStatus?.payload.captureState)
    ?? (runtime?.sessionLive && runtime.machineCodeBound ? "capturing" as const : undefined);
  const captureState = reportedCaptureState === "capturing" && runtime?.readinessState === "degraded"
    ? "error" as const
    : reportedCaptureState;
  const meaningfulTranscripts = transcripts.transcripts.filter(segment => segment.text.replace(/[，。！？、；：,.!?;:~～…·\s]+/g, "").trim());
  const degraded = latestDegraded?.payload?.reason === "mixed-input"
    ? {
        id: latestDegraded.eventId,
        sessionId: transcripts.sessionId || interviewId,
        reason: "mixed-input" as const,
        sourceKind: "mixed" as const,
        detectedAtMs: latestDegraded.createdAtMs,
        manualInputAvailable: true as const,
      }
    : null;
  return {
    speaker: {
      mode: degraded ? "manual-only" as const : "dual-channel" as const,
      transcripts: meaningfulTranscripts
        .filter(segment => !segment.sessionId || segment.sessionId === interviewId)
        .filter(segment => segment.sourceKind === "microphone" || segment.sourceKind === "system")
        .map(segment => ({
          ...toSpeakerRole(segment.role, segment.sourceKind),
          id: segment.segmentId,
          sessionId: transcripts.sessionId || interviewId,
          revision: segment.revision,
          sourceId: segment.sourceId,
          text: segment.text,
          transcriptConfidence: segment.transcriptConfidence,
          startedAtMs: segment.startedAtMs,
          endedAtMs: segment.endedAtMs,
          isFinal: segment.isFinal,
          ...(!segment.isFinal && (segment.turnState === "committing" || committingSegments.has(segment.segmentId))
            ? { turnState: "committing" as const }
            : !segment.isFinal ? { turnState: "speaking" as const } : {}),
          ...(segment.terminalState ? { terminalState: segment.terminalState } : {}),
          ...(segment.finalizationReason ? { finalizationReason: segment.finalizationReason } : {}),
          overlap: segment.overlap,
          ...(segment.publishedAtMs !== undefined ? { publishedAtMs: segment.publishedAtMs } : {}),
          ...(segment.performance ? { performance: segment.performance } : {}),
        })),
      pendingQuestion: pending ? {
        id: pending.candidateId,
        sessionId: candidates.sessionId || interviewId,
        revision: 1,
        sourceSegmentIds: pending.sourceSegmentIds,
        text: pending.text,
        state: pending.state === "needs-confirmation" ? "needs-confirmation" as const : "auto-confirmed" as const,
        reason: pending.reason === "low-transcript-confidence" ? "low-transcript-confidence" as const : "high-confidence-question" as const,
        confidence: pending.confidence,
      } : null,
      degradation: degraded,
      runtimeNotice: meaningfulTranscripts.length > 0 ? null : runtimeNotice(runtime, latestDegraded),
    },
    ...(captureState ? { captureState } : {}),
    ...(useScreenshotUpdate && latestScreenshotUpdate ? {
      shortcutScreenshotUpdate: screenshotEventToUpdate(latestScreenshotUpdate),
    } : latestShortcutAccepted ? {
      shortcutScreenshotUpdate: {
        requestId: String(latestShortcutAccepted.payload.requestId),
        status: "requested" as const,
        screenshotTask: { name: "共享屏幕截取", stage: "waiting-desktop" as const },
        notificationId: latestShortcutAccepted.eventId,
        acceptedAtMs: latestShortcutAccepted.createdAtMs,
      },
    } : {}),
    ...(latestAnswerUpdate ? {
      answerUpdate: toSubmitManualAnswerResult(
        latestAnswerUpdate.payload.task as unknown as BackendLiveAnswerTaskResponse,
        "manual",
      ),
    } : {}),
  };
};

const questionStatusFromTask = (task: BackendLiveAnswerTaskResponse): InterviewQuestion["status"] =>
  task.status === "completed" ? "confirmed" : task.status === "failed" ? "failed" : task.status === "cancelled" ? "cancelled" : task.status === "streaming" ? "streaming" : "generating";

const toSubmitManualAnswerResult = (
  task: BackendLiveAnswerTaskResponse,
  input: InterviewQuestion["input"] = "manual",
): SubmitManualAnswerResult => ({
  question: {
    id: task.taskId,
    askedAt: "刚刚",
    text: task.normalizedQuestion?.trim() || task.question,
    ...(task.rawQuestion ? { rawText: task.rawQuestion } : {}),
    ...(task.questionNormalizationStatus ? { questionNormalizationStatus: task.questionNormalizationStatus } : {}),
    input,
    status: questionStatusFromTask(task),
    advice: adviceFromLiveAnswerTask(task),
  },
  task: {
    id: task.taskId,
    interviewId: task.sessionId,
    userId: task.ownerUserId,
    billingUsageId: `live-answer:${task.taskId}`,
    questionId: task.taskId,
    revision: 1,
    status: taskStatus(task),
    question: task.normalizedQuestion?.trim() || task.question,
    ...(task.status === "completed" ? { completedText: answerTextFromTask(task) } : { partialText: answerTextFromTask(task) || "正在调用当前对话模型生成回答…" }),
    provenance: provenanceFromTask(task),
    ...(task.materialContextStatus ? { materialContextStatus: task.materialContextStatus } : {}),
    updatedAtMs: task.updatedAtMs,
  },
});

const screenshotAnswerText = (task: BackendScreenshotAnswerTaskResponse) =>
  task.answerText || [...task.chunks].sort((left, right) => left.sequence - right.sequence).map(chunk => chunk.text).join("");

const toSubmitScreenshotAnswerResult = (task: BackendScreenshotAnswerTaskResponse, fallbackQuestion: string): SubmitManualAnswerResult => {
  const answerText = screenshotAnswerText(task);
  const failed = task.status === "failed";
  const questionText = fallbackQuestion.trim() || task.visionSummaryTitle?.trim() || task.instruction.trim() || "请根据当前截图直接回答";
  return {
    question: {
      id: task.taskId,
      askedAt: "刚刚",
      text: questionText,
      input: "screenshot",
      status: task.status === "completed" ? "confirmed" : failed ? "failed" : "generating",
      advice: {
        outline: [],
        detail: answerText || task.errorMessage || (failed ? "截图回答失败，请稍后重试。" : "正在识别截图并生成回答…"),
        sourceTypes: ["截图"],
        inference: "",
        uncertain: failed,
        provenance: { selectionRevision: 0, usedSources: [] },
      },
    },
    task: {
      id: task.taskId,
      interviewId: task.sessionId,
      userId: task.ownerUserId,
      billingUsageId: `screenshot-answer:${task.taskId}`,
      questionId: task.taskId,
      revision: 1,
      status: task.status === "completed" ? "completed" : task.status === "failed" ? "failed" : "generating",
      question: questionText,
      ...(task.status === "completed" ? { completedText: answerText } : { partialText: answerText || "正在识别截图并生成回答…" }),
      updatedAtMs: task.updatedAtMs,
    },
  };
};

const screenshotStageToTask = (current: BackendRemoteScreenshotCaptureRequestResponse): ScreenshotTask => {
  const stage = current.stage || current.status;
  const mapped: ScreenshotTask["stage"] =
    stage === "requested" ? "waiting-desktop"
      : stage === "claimed" ? "uploading"
        : stage === "uploaded" ? "uploaded"
          : stage === "vision-running" ? "generating"
            : stage === "completed" ? "completed"
              : stage === "cancelled" ? "cancelled"
                : stage === "failed" || current.status === "failed" || stage === "capture-failed" || stage === "upload-failed" ? "failed"
                  : "recognizing";
  const message = current.errorMessage || (mapped === "failed" ? "截屏回答失败，请稍后重试。" : undefined);
  return { name: current.capturedFilename || "共享屏幕截取", stage: mapped, ...(message ? { errorMessage: message } : {}) };
};

const screenshotEventToTask = (payload: Record<string, unknown>): ScreenshotTask => {
  const status = String(payload.status ?? "processing");
  const stage = String(payload.stage ?? status);
  const mapped: ScreenshotTask["stage"] =
    stage === "requested" || stage === "waiting-desktop" ? "waiting-desktop"
      : stage === "claimed" ? "uploading"
        : stage === "uploaded" ? "uploaded"
          : stage === "vision-running" ? "generating"
            : stage === "completed" ? "completed"
              : stage === "cancelled" ? "cancelled"
                : status === "failed" || stage.includes("failed") ? "failed" : "recognizing";
  const errorMessage = typeof payload.errorMessage === "string" ? payload.errorMessage : undefined;
  return { name: "共享屏幕截取", stage: mapped, ...(errorMessage ? { errorMessage } : {}) };
};

const screenshotEventToUpdate = (event: BackendRealtimeEventListResponse["events"][number]): DesktopShortcutScreenshotUpdate => {
  const payload = event.payload;
  const status = String(payload.status ?? "processing") as DesktopShortcutScreenshotUpdate["status"];
  const answerTask = payload.answerTask && typeof payload.answerTask === "object"
    ? payload.answerTask as BackendScreenshotAnswerTaskResponse
    : null;
  return {
    requestId: String(payload.requestId),
    status,
    screenshotTask: screenshotEventToTask(payload),
    notificationId: event.eventId,
    ...(answerTask ? { result: toSubmitScreenshotAnswerResult(answerTask, answerTask.visionSummaryTitle?.trim() || answerTask.instruction) } : {}),
  };
};

export class BackendPreviewInterviewAdapter implements InterviewAppAdapter {
  private readonly client;
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;
  private foundation: FoundationIndexResponse | null = null;
  private readonly captureEventWaiters = new Map<string, Set<(payload: Record<string, unknown>) => void>>();
  private readonly acknowledgedPerformanceTraces = new Set<string>();
  private readonly acknowledgedPerformanceTraceOrder: string[] = [];
  private readonly pendingPerformanceAcks: Array<{ readonly key: string; readonly send: () => Promise<unknown> }> = [];
  private readonly lastTranscriptAckAtBySegment = new Map<string, number>();
  private performanceAckInFlight = false;

  private drainPerformanceAcks() {
    if (this.performanceAckInFlight) return;
    const next = this.pendingPerformanceAcks.shift();
    if (!next) return;
    this.performanceAckInFlight = true;
    void next.send()
      .catch(() => {
        this.acknowledgedPerformanceTraces.delete(next.key);
      })
      .finally(() => {
        this.performanceAckInFlight = false;
        this.drainPerformanceAcks();
      });
  }

  private enqueuePerformanceAck(key: string, send: () => Promise<unknown>) {
    while (this.pendingPerformanceAcks.length >= MAX_PENDING_PERFORMANCE_ACKS) {
      const dropped = this.pendingPerformanceAcks.shift();
      if (dropped) this.acknowledgedPerformanceTraces.delete(dropped.key);
    }
    this.pendingPerformanceAcks.push({ key, send });
    this.drainPerformanceAcks();
  }

  private recordRealtimeDeliveryMetric(
    interviewId: string,
    kind: "connect" | "first-snapshot" | "connected-duration" | "reconnect" | "fallback-snapshot",
    options: { readonly durationMs?: number; readonly attempt?: number; readonly reason?: "opened" | "eof" | "network" | "aborted" | "recovered" | "first-snapshot-timeout" | "first-snapshot-eof" | "unknown" } = {},
  ) {
    void this.client.request(`/api/v1/realtime-speech/sessions/${interviewId}/delivery-metrics`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: requireUserId(),
        kind,
        ...(options.durationMs === undefined ? {} : { durationMs: Math.max(0, Math.min(3_600_000, Math.round(options.durationMs))) }),
        ...(options.attempt === undefined ? {} : { attempt: options.attempt }),
        ...(options.reason ? { reason: options.reason } : {}),
      }),
    }).catch(() => undefined);
  }

  private acknowledgeRuntimePerformance(
    interviewId: string,
    traceId: string,
    stage: "transcript-delivery" | "transcript-render" | "screenshot-first-render" | "answer-first-render",
    startedAtMs: number,
    taskId?: string,
    delivery?: {
      readonly eventId?: string;
      readonly browserEventReceiveAtMs?: number;
      readonly browserStreamChunkReceivedAtMs?: number;
      readonly browserEventParsedAtMs?: number;
      readonly transcriptStoreUpdateStartAtMs?: number;
      readonly transcriptStoreUpdateCompleteAtMs?: number;
      readonly browserStateUpdateAtMs?: number;
      readonly reactRenderStartAtMs?: number;
      readonly reactCommitAtMs?: number;
      readonly browserPaintAtMs?: number;
      readonly browserRenderAtMs?: number;
      readonly renderedRevision?: number;
      readonly renderedTextLength?: number;
      readonly segmentId?: string;
      readonly isFinal?: boolean;
      readonly visibilityState?: DocumentVisibilityState;
    },
  ) {
    const observedAtMs = Date.now();
    if (stage === "transcript-delivery" && delivery?.eventId && !subtitleRevisionDiagnosticsEnabled()) return;
    if (stage === "transcript-render" && delivery?.segmentId && !subtitleRevisionDiagnosticsEnabled()) {
      const lastAcknowledgedAtMs = this.lastTranscriptAckAtBySegment.get(delivery.segmentId);
      if (!delivery.isFinal && lastAcknowledgedAtMs !== undefined && observedAtMs - lastAcknowledgedAtMs < TRANSCRIPT_ACK_INTERVAL_MS) return;
      this.lastTranscriptAckAtBySegment.set(delivery.segmentId, observedAtMs);
      if (this.lastTranscriptAckAtBySegment.size > 256) {
        const oldest = this.lastTranscriptAckAtBySegment.keys().next().value;
        if (oldest) this.lastTranscriptAckAtBySegment.delete(oldest);
      }
    }
    const key = `${stage}:${delivery?.eventId ?? traceId}`;
    if (!traceId || this.acknowledgedPerformanceTraces.has(key)) return;
    this.acknowledgedPerformanceTraces.add(key);
    this.acknowledgedPerformanceTraceOrder.push(key);
    while (this.acknowledgedPerformanceTraceOrder.length > 4_096) {
      const expired = this.acknowledgedPerformanceTraceOrder.shift();
      if (expired) this.acknowledgedPerformanceTraces.delete(expired);
    }
    const durationMs = Math.max(0, Math.min(120_000, observedAtMs - startedAtMs));
    const send = () => {
      const browserRenderAtMs = delivery?.browserRenderAtMs;
      this.enqueuePerformanceAck(key, () => this.client.request(`/api/v1/realtime-speech/sessions/${interviewId}/performance-ack`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          userId: requireUserId(), traceId, stage,
          durationMs,
          ...(taskId ? { taskId } : {}),
          ...(delivery?.eventId ? { eventId: delivery.eventId } : {}),
          ...(delivery?.browserEventReceiveAtMs === undefined ? {} : { browserEventReceiveAtMs: delivery.browserEventReceiveAtMs }),
          ...(delivery?.browserStreamChunkReceivedAtMs === undefined ? {} : { browserStreamChunkReceivedAtMs: delivery.browserStreamChunkReceivedAtMs }),
          ...(delivery?.browserEventParsedAtMs === undefined ? {} : { browserEventParsedAtMs: delivery.browserEventParsedAtMs }),
          ...(delivery?.transcriptStoreUpdateStartAtMs === undefined ? {} : { transcriptStoreUpdateStartAtMs: delivery.transcriptStoreUpdateStartAtMs }),
          ...(delivery?.transcriptStoreUpdateCompleteAtMs === undefined ? {} : { transcriptStoreUpdateCompleteAtMs: delivery.transcriptStoreUpdateCompleteAtMs }),
          ...(delivery?.browserStateUpdateAtMs === undefined ? {} : { browserStateUpdateAtMs: delivery.browserStateUpdateAtMs }),
          ...(delivery?.reactRenderStartAtMs === undefined ? {} : { reactRenderStartAtMs: delivery.reactRenderStartAtMs }),
          ...(delivery?.reactCommitAtMs === undefined ? {} : { reactCommitAtMs: delivery.reactCommitAtMs }),
          ...(delivery?.browserPaintAtMs === undefined ? {} : { browserPaintAtMs: delivery.browserPaintAtMs }),
          ...(browserRenderAtMs === undefined ? {} : { browserRenderAtMs }),
          ...(delivery?.renderedRevision === undefined ? {} : { renderedRevision: delivery.renderedRevision }),
          ...(delivery?.renderedTextLength === undefined ? {} : { renderedTextLength: delivery.renderedTextLength }),
          ...(delivery?.visibilityState ? { visibilityState: delivery.visibilityState } : {}),
        }),
      }));
    };
    if (stage === "transcript-delivery" || delivery?.browserRenderAtMs !== undefined) send();
    else if (typeof requestAnimationFrame === "function") requestAnimationFrame(send);
    else window.setTimeout(send, 0);
  }

  private publishCaptureEvents(events: BackendRealtimeEventListResponse) {
    for (const event of events.events) {
      if (event.kind !== "screenshot-capture-updated") continue;
      const requestId = typeof event.payload.requestId === "string" ? event.payload.requestId : "";
      if (!requestId) continue;
      for (const listener of this.captureEventWaiters.get(requestId) ?? []) listener(event.payload);
    }
  }

  private waitForCaptureEvent(requestId: string, timeoutMs: number, signal?: AbortSignal): Promise<Record<string, unknown> | null> {
    return new Promise((resolve, reject) => {
      const listeners = this.captureEventWaiters.get(requestId) ?? new Set();
      const cleanup = () => {
        window.clearTimeout(timer);
        signal?.removeEventListener("abort", onAbort);
        listeners.delete(onEvent);
        if (listeners.size === 0) this.captureEventWaiters.delete(requestId);
      };
      const onEvent = (payload: Record<string, unknown>) => {
        cleanup();
        resolve(payload);
      };
      const onAbort = () => {
        cleanup();
        reject(new DOMException("Aborted", "AbortError"));
      };
      const timer = window.setTimeout(() => {
        cleanup();
        resolve(null);
      }, timeoutMs);
      listeners.add(onEvent);
      this.captureEventWaiters.set(requestId, listeners);
      signal?.addEventListener("abort", onAbort, { once: true });
    });
  }

  constructor(baseUrl: string, fetchImpl?: typeof fetch) {
    this.baseUrl = baseUrl;
    const rawFetch = fetchImpl ?? ((input, init) => window.fetch(input, init));
    this.fetchImpl = createAuthRefreshingFetch(rawFetch);
    this.client = createJsonClient({ baseUrl, fetchImpl: this.fetchImpl });
    if (typeof window !== "undefined") {
      window.addEventListener("offersteady:realtime-transcript-rendered", ((event: CustomEvent) => {
        const detail = event.detail as {
          readonly sessionId?: string;
          readonly traceId?: string;
          readonly eventId?: string;
          readonly browserEventReceiveAtMs?: number;
          readonly browserStreamChunkReceivedAtMs?: number;
          readonly browserEventParsedAtMs?: number;
          readonly transcriptStoreUpdateStartAtMs?: number;
          readonly transcriptStoreUpdateCompleteAtMs?: number;
          readonly browserStateUpdateAtMs?: number;
          readonly reactRenderStartAtMs?: number;
          readonly reactCommitAtMs?: number;
          readonly browserPaintAtMs?: number;
          readonly browserRenderAtMs?: number;
          readonly renderedRevision?: number;
          readonly renderedTextLength?: number;
          readonly segmentId?: string;
          readonly isFinal?: boolean;
          readonly visibilityState?: DocumentVisibilityState;
        } | undefined;
        if (!detail?.sessionId || !detail.traceId || detail.browserRenderAtMs === undefined) return;
        this.acknowledgeRuntimePerformance(
          detail.sessionId,
          detail.traceId,
          "transcript-render",
          detail.browserStateUpdateAtMs ?? detail.browserRenderAtMs,
          undefined,
          detail,
        );
      }) as EventListener);
    }
  }

  async probe(signal?: AbortSignal): Promise<FoundationIndexResponse> {
    if (this.foundation) return this.foundation;
    this.foundation = await this.client.request<FoundationIndexResponse>("/api/v1/system/foundation", undefined, signal);
    return this.foundation;
  }

  async loadState(signal?: AbortSignal, options?: { readonly auth?: boolean }): Promise<WebAppState> {
    return this.client.request<WebAppState>("/api/v1/web/state", { headers: options?.auth === false ? {} : authHeaders() }, signal);
  }

  async getBillingState(signal?: AbortSignal): Promise<BillingPresentationState> {
    return this.client.request<BillingPresentationState>("/api/v1/billing/state", { headers: authHeaders() }, signal);
  }

  async getReferralStatus(signal?: AbortSignal): Promise<ReferralStatus> {
    return this.client.request<ReferralStatus>("/api/v1/billing/referrals/me", { headers: authHeaders() }, signal);
  }

  async resolveReferral(code: string, signal?: AbortSignal) {
    return this.client.request<{ valid: boolean; enabled: boolean; rewardPoints?: number; inviterRewardPoints?: number; inviteeRewardPoints?: number; activationWindowDays?: number }>(`/api/v1/billing/referrals/${encodeURIComponent(code)}`, undefined, signal);
  }

  async activateReferral(code: string, signal?: AbortSignal): Promise<ReferralActivationResult> {
    return this.client.request<ReferralActivationResult>("/api/v1/billing/referrals/activate", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ referralCode: code }),
    }, signal);
  }

  async createDraft(input: { title: string; role: string; company?: string }, signal?: AbortSignal) {
    const persistedTitle = deriveInterviewTitle(input);
    const created = await this.client.request<BackendSessionResponse>("/api/v1/sessions", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ userId: requireUserId(), title: persistedTitle }),
    }, signal);
    return toInterviewSummary(created, { ...input, title: persistedTitle });
  }

  async updateInterviewLanguage(id: string, interviewLanguage: InterviewLanguage, signal?: AbortSignal) {
    const updated = await this.client.request<BackendSessionResponse>(`/api/v1/sessions/${id}/language`, {
      method: "PATCH",
      headers: authHeaders(),
      body: JSON.stringify({ userId: requireUserId(), interviewLanguage }),
    }, signal);
    return toInterviewSummary(updated);
  }

  async confirmInterviewMaterials(selection: Parameters<InterviewAppAdapter["confirmInterviewMaterials"]>[0], signal?: AbortSignal) {
    const confirmed = await this.client.request<BackendSessionResponse>(`/api/v1/sessions/${selection.sessionId}/materials/confirm`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: requireUserId(),
        resumeDocumentId: selection.resumeSourceId,
        jobDescriptionDocumentId: selection.jobDescriptionSourceId,
        knowledgeDocumentIds: selection.knowledgeSourceIds,
      }),
    }, signal);
    return {
      sessionId: confirmed.sessionId,
      resumeSourceId: confirmed.materialBinding.resumeDocumentId,
      jobDescriptionSourceId: confirmed.materialBinding.jobDescriptionDocumentId,
      knowledgeSourceIds: confirmed.materialBinding.knowledgeDocumentIds,
      revision: confirmed.materialBinding.revision,
      confirmedAtMs: confirmed.materialBinding.confirmedAtMs,
    };
  }

  async getActiveInterviewConflict(id: string, signal?: AbortSignal): Promise<ActiveInterviewConflict> {
    const conflict = await this.client.request<BackendActiveSessionConflictResponse>(`/api/v1/sessions/${id}/active-conflict?userId=${encodeURIComponent(requireUserId())}`, {
      headers: authHeaders(),
    }, signal);
    return {
      currentInterviewId: conflict.currentSessionId,
      activeInterview: conflict.activeSession ? toInterviewSummary(conflict.activeSession) : null,
    };
  }

  async supersedeActiveInterview(command: Parameters<InterviewAppAdapter["supersedeActiveInterview"]>[0], signal?: AbortSignal) {
    const result = await this.client.request<BackendSupersedeActiveSessionResponse>(`/api/v1/sessions/${command.interviewId}/supersede-active`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: requireUserId(),
        expectedPreviousSessionId: command.expectedPreviousInterviewId,
      }),
    }, signal);
    return result.retiredSessionIds;
  }

  async startInterviewSession(id: string, signal?: AbortSignal) {
    const started = await this.client.request<BackendSessionResponse>(`/api/v1/sessions/${id}/start`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ userId: requireUserId() }),
    }, signal);
    return toInterviewSummary(started);
  }

  async getInterviewIdleStatus(id: string, signal?: AbortSignal): Promise<IdleInterviewStatus> {
    return this.client.request<IdleInterviewStatus>(`/api/v1/sessions/${id}/idle-status?userId=${encodeURIComponent(requireUserId())}`, {
      headers: authHeaders(),
    }, signal);
  }

  async continueInterviewSession(id: string, signal?: AbortSignal): Promise<IdleInterviewStatus> {
    await this.client.request(`/api/v1/sessions/${id}/continue`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ userId: requireUserId() }),
    }, signal);
    return this.getInterviewIdleStatus(id, signal);
  }

  async controlInterviewCapture(id: string, action: "pause" | "resume", signal?: AbortSignal): Promise<CaptureState> {
    const result = await this.client.request<{ captureState: string }>(`/api/v1/realtime-speech/sessions/${id}/capture-control`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ userId: requireUserId(), action }),
    }, signal);
    const captureState = toCaptureState(result.captureState);
    if (captureState !== "paused" && captureState !== "capturing") throw new AppError("validation", "后端返回了无效的收音状态");
    return captureState;
  }

  async endInterviewSession(id: string, signal?: AbortSignal): Promise<void> {
    await this.client.request(`/api/v1/sessions/${id}/end`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ userId: requireUserId() }),
    }, signal);
  }

  async bindDesktopDevice(command: Parameters<InterviewAppAdapter["bindDesktopDevice"]>[0], signal?: AbortSignal) {
    const binding = await this.client.request<BackendDesktopBindingResponse>(`/api/v1/realtime-speech/sessions/${command.interviewId}/desktop-binding`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: requireUserId(),
        manualCode: command.manualCode?.trim() || null,
        reuseLastDevice: command.reuseLastDevice === true,
      }),
    }, signal);
    return toDesktopDeviceBinding(binding);
  }

  async getLastDesktopDevice(signal?: AbortSignal) {
    const device = await this.client.request<BackendRecentDesktopDeviceResponse | null>(`/api/v1/realtime-speech/desktop-devices/last-used?userId=${encodeURIComponent(requireUserId())}`, {
      headers: authHeaders(),
    }, signal);
    return device;
  }

  async listDesktopDevices(signal?: AbortSignal) {
    return this.client.request<BackendAccountDesktopDeviceResponse[]>("/api/v1/realtime-speech/desktop-devices", {
      headers: authHeaders(),
    }, signal);
  }

  async getDesktopDeviceBinding(interviewId: string, signal?: AbortSignal) {
    try {
      const binding = await this.client.request<BackendDesktopBindingResponse>(`/api/v1/realtime-speech/sessions/${interviewId}/desktop-binding?userId=${encodeURIComponent(requireUserId())}`, {
        headers: authHeaders(),
      }, signal);
      return binding.status === "bound" ? toDesktopDeviceBinding(binding) : null;
    } catch (error) {
      if (error instanceof Error && (error.message.includes("404") || error.message.includes("尚未绑定"))) return null;
      return null;
    }
  }

  async getPreparationAudioReadiness(interviewId: string, signal?: AbortSignal) {
    const runtime = await this.client.request<BackendRealtimeRuntimeResponse>(
      `/api/v1/realtime-speech/sessions/${interviewId}/runtime?userId=${encodeURIComponent(requireUserId())}`,
      { headers: authHeaders() },
      signal,
    );
    return toPreparationAudioReadiness(runtime);
  }

  async sendDesktopSessionHeartbeat(command: Parameters<InterviewAppAdapter["sendDesktopSessionHeartbeat"]>[0], signal?: AbortSignal) {
    return this.client.request<{ pageInstanceId: string | null; leaseGeneration: number; leaseExpiresAtMs: number }>(`/api/v1/realtime-speech/sessions/${command.interviewId}/web-heartbeat`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: requireUserId(),
        bindingId: command.bindingId ?? null,
        page: command.page,
        pageInstanceId: command.pageInstanceId ?? null,
      }),
    }, signal);
  }

  async loadRealtimeSession(interviewId: string, signal?: AbortSignal, lease?: { readonly pageInstanceId: string; readonly leaseGeneration: number }) {
    const startedAt = Date.now();
    const leaseQuery = lease ? `&pageInstanceId=${encodeURIComponent(lease.pageInstanceId)}&leaseGeneration=${lease.leaseGeneration}` : "";
    const snapshot = await this.client.request<BackendRealtimeSessionSnapshotResponse>(
      `/api/v1/realtime-speech/sessions/${interviewId}/snapshot?userId=${encodeURIComponent(requireUserId())}${leaseQuery}`,
      { headers: authHeaders() },
      signal,
    );
    if (typeof snapshot.cursor === "number") window.sessionStorage?.setItem(`offersteady:realtime-cursor:${interviewId}`, String(snapshot.cursor));
    this.publishCaptureEvents(snapshot.events);
    this.recordRealtimeDeliveryMetric(interviewId, "fallback-snapshot", { durationMs: Date.now() - startedAt, reason: "recovered" });
    return mapRealtimeState(interviewId, snapshot.transcripts, snapshot.candidates, snapshot.events, snapshot.runtime);
  }

  async loadInterviewWorkspace(interviewId: string, signal?: AbortSignal): Promise<InterviewWorkspaceSnapshot> {
    const [chatTasks, screenshotTasks] = await Promise.all([
      this.client.request<readonly BackendLiveAnswerTaskResponse[]>(`/api/v1/live-answer/sessions/${interviewId}/history?userId=${encodeURIComponent(requireUserId())}`, {
        headers: authHeaders(),
      }, signal),
      this.client.request<readonly BackendScreenshotAnswerTaskResponse[]>(`/api/v1/screenshot-answer/sessions/${interviewId}/history?userId=${encodeURIComponent(requireUserId())}`, {
        headers: authHeaders(),
      }, signal),
    ]);
    const results = [
      ...chatTasks.map(task => ({ updatedAtMs: task.updatedAtMs, result: toSubmitManualAnswerResult(task) })),
      ...screenshotTasks.map(task => ({ updatedAtMs: task.updatedAtMs, result: toSubmitScreenshotAnswerResult(task, task.visionSummaryTitle?.trim() || task.instruction) })),
    ].sort((left, right) => right.updatedAtMs - left.updatedAtMs);
    const active = results.find(item => item.result.task.status === "queued" || item.result.task.status === "generating");
    return {
      questions: results.map(item => item.result.question),
      activeAnswerTask: active?.result.task ?? results[0]?.result.task ?? null,
    };
  }

  async loadInterviewReview(interviewId: string, signal?: AbortSignal): Promise<InterviewReview> {
    const review = await this.client.request<BackendInterviewReviewResponse>(`/api/v1/sessions/${interviewId}/review?userId=${encodeURIComponent(requireUserId())}`, {
      headers: authHeaders(),
    }, signal);
    const durationMinutes = Math.max(0, Math.round(review.durationMs / 60_000));
    return {
      status: "complete",
      duration: `${durationMinutes} 分钟`,
      summary: review.transcripts.length ? "已从本场持久记录整理面试官与我的语音转写。" : "本场没有可用的持久语音转写。",
      screenshots: [],
      sessionId: review.sessionId,
      title: review.title,
      startedAtMs: review.startedAtMs,
      endedAtMs: review.endedAtMs,
      transcripts: review.transcripts,
    };
  }

  async loadDesktopShortcutScreenshotUpdates(interviewId: string, signal?: AbortSignal) {
    const requests = await this.client.request<readonly BackendRemoteScreenshotCaptureRequestResponse[]>(`/api/v1/screenshot-answer/sessions/${interviewId}/remote-capture-requests?userId=${encodeURIComponent(requireUserId())}`, {
      headers: authHeaders(),
    }, signal);
    return requests
      .filter(request => request.instruction.includes("[来源:助手快捷键]"))
      .map(request => ({
        requestId: request.requestId,
        status: request.status,
        screenshotTask: screenshotStageToTask(request),
        ...(request.status === "completed" && request.answerTask
          ? {
              result: toSubmitScreenshotAnswerResult(
                request.answerTask,
                request.answerTask.visionSummaryTitle?.trim() || "请根据当前截图直接回答",
              ),
            }
          : {}),
      }));
  }

  async cancelDesktopShortcutScreenshot(requestId: string, signal?: AbortSignal) {
    await this.client.request<BackendRemoteScreenshotCaptureRequestResponse>(`/api/v1/screenshot-answer/capture-requests/${encodeURIComponent(requestId)}/cancel`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ userId: requireUserId() }),
    }, signal);
  }

  async subscribeRealtimeSession(interviewId: string, onUpdate: Parameters<InterviewAppAdapter["subscribeRealtimeSession"]>[1], signal?: AbortSignal, lease?: { readonly pageInstanceId: string; readonly leaseGeneration: number }) {
    const connectStartedAt = Date.now();
    let firstSnapshotRecorded = false;
    const cursorKey = `offersteady:realtime-cursor:${interviewId}`;
    const storedCursor = typeof window.sessionStorage?.getItem === "function" ? Number(window.sessionStorage.getItem(cursorKey) ?? "0") : 0;
    const cursor = Number.isFinite(storedCursor) && storedCursor > 0 ? storedCursor : 0;
    const requestInit: RequestInit = {
      method: "GET",
      headers: {
        Accept: "text/event-stream",
        ...authHeaders(),
      },
    };
    if (signal) requestInit.signal = signal;
    const leaseQuery = lease ? `&pageInstanceId=${encodeURIComponent(lease.pageInstanceId)}&leaseGeneration=${lease.leaseGeneration}` : "";
    const response = await this.fetchImpl(withBaseUrl(this.baseUrl, `/api/v1/realtime-speech/sessions/${interviewId}/stream?userId=${encodeURIComponent(requireUserId())}&cursor=${cursor}${leaseQuery}`), requestInit);
    if (!response.ok) {
      const error = new AppError("validation", `实时对话订阅失败（${response.status}）`) as AppError & {
        status: number;
      };
      error.status = response.status;
      throw error;
    }
    if (!response.body) throw new AppError("network", "当前浏览器不支持实时对话订阅读取");
    const connectedAt = Date.now();
    this.recordRealtimeDeliveryMetric(interviewId, "connect", { durationMs: connectedAt - connectStartedAt, reason: "opened" });
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let streamSnapshot: MaterializedRealtimeSessionStreamEvent | null = null;
    let pendingSnapshot: MaterializedRealtimeSessionStreamEvent | null = null;
    let pendingDeliveryEvents: BackendRealtimeEventListResponse["events"] = [];
    let terminalStatus: number | null = null;
    let flushHandle: number | null = null;
    let latestChunkReceivedAtMs = 0;
    let firstSnapshotTimer: number | null = null;
    const clearFirstSnapshotDeadline = () => {
      if (firstSnapshotTimer === null) return;
      window.clearTimeout(firstSnapshotTimer);
      firstSnapshotTimer = null;
    };
    const firstSnapshotFailure = (reason: "first-snapshot-timeout" | "first-snapshot-eof") => {
      const error = new AppError("network", reason === "first-snapshot-timeout"
        ? "实时字幕首个快照等待超时"
        : "实时字幕连接在首个快照前结束") as AppError & {
          realtimeFailure: "first-snapshot-timeout" | "first-snapshot-eof";
        };
      error.realtimeFailure = reason;
      this.recordRealtimeDeliveryMetric(interviewId, "reconnect", {
        durationMs: Date.now() - connectedAt,
        reason,
      });
      return error;
    };
    const firstSnapshotDeadline = new Promise<never>((_resolve, reject) => {
      firstSnapshotTimer = window.setTimeout(
        () => reject(firstSnapshotFailure("first-snapshot-timeout")),
        FIRST_REALTIME_SNAPSHOT_TIMEOUT_MS,
      );
    });
    const coalescePendingDeliveryEvents = (events: BackendRealtimeEventListResponse["events"]) => {
      const latestTranscriptIndexBySegment = new Map<string, number>();
      const latestTranscriptRankBySegment = new Map<string, readonly [boolean, number, number]>();
      events.forEach((item, index) => {
        if (item.kind !== "transcript-updated") return;
        const segmentId = typeof item.payload.segmentId === "string" ? item.payload.segmentId : "";
        if (!segmentId) return;
        const rank = [item.payload.isFinal === true, typeof item.payload.revision === "number" ? item.payload.revision : 0, index] as const;
        const current = latestTranscriptRankBySegment.get(segmentId);
        if (!current || Number(rank[0]) > Number(current[0])
          || (rank[0] === current[0] && (rank[1] > current[1] || (rank[1] === current[1] && rank[2] > current[2])))) {
          latestTranscriptRankBySegment.set(segmentId, rank);
          latestTranscriptIndexBySegment.set(segmentId, index);
        }
      });
      return events.filter((item, index) => {
        if (item.kind !== "transcript-updated") return true;
        const segmentId = typeof item.payload.segmentId === "string" ? item.payload.segmentId : "";
        return !segmentId || latestTranscriptIndexBySegment.get(segmentId) === index;
      });
    };
    const markStateUpdate = (
      payload: MaterializedRealtimeSessionStreamEvent,
      stateUpdateStartedAtMs: number,
      stateUpdatedAtMs: number,
    ) => ({
      ...payload,
      transcripts: {
        ...payload.transcripts,
        transcripts: payload.transcripts.transcripts.map(transcript => transcript.performance
          ? { ...transcript, performance: {
              ...transcript.performance,
              transcriptStoreUpdateStartAtMs: transcript.performance.transcriptStoreUpdateStartAtMs ?? stateUpdateStartedAtMs,
              transcriptStoreUpdateCompleteAtMs: transcript.performance.transcriptStoreUpdateCompleteAtMs ?? stateUpdatedAtMs,
              browserStateUpdateAtMs: stateUpdatedAtMs,
            } }
          : transcript),
      },
    });
    const acknowledgeTranscriptDelivery = (
      sessionId: string,
      events: BackendRealtimeEventListResponse["events"],
      stateUpdateStartedAtMs: number,
      stateUpdatedAtMs: number,
    ) => {
      for (const item of events) {
        if (item.kind !== "transcript-updated") continue;
        const rawPerformance = item.payload.performance;
        if (!rawPerformance || typeof rawPerformance !== "object") continue;
        const performance = rawPerformance as Record<string, unknown>;
        const traceId = typeof performance.traceId === "string" ? performance.traceId : "";
        const eventId = typeof performance.eventId === "string" ? performance.eventId : item.eventId;
        const browserEventReceiveAtMs = typeof performance.browserEventReceiveAtMs === "number"
          ? performance.browserEventReceiveAtMs
          : undefined;
        const sseEventSendAtMs = typeof performance.sseEventSendAtMs === "number"
          ? performance.sseEventSendAtMs
          : Date.now();
        const visibilityState: DocumentVisibilityState = performance.visibilityState === "hidden" ? "hidden" : "visible";
        this.acknowledgeRuntimePerformance(
          sessionId,
          traceId,
          "transcript-delivery",
          sseEventSendAtMs,
          undefined,
          {
            eventId,
            ...(browserEventReceiveAtMs === undefined ? {} : { browserEventReceiveAtMs }),
            ...(typeof performance.browserStreamChunkReceivedAtMs === "number" ? { browserStreamChunkReceivedAtMs: performance.browserStreamChunkReceivedAtMs } : {}),
            ...(typeof performance.browserEventParsedAtMs === "number" ? { browserEventParsedAtMs: performance.browserEventParsedAtMs } : {}),
            transcriptStoreUpdateStartAtMs: stateUpdateStartedAtMs,
            transcriptStoreUpdateCompleteAtMs: stateUpdatedAtMs,
            browserStateUpdateAtMs: stateUpdatedAtMs,
            visibilityState,
          },
        );
      }
    };
    const scheduleFlush = () => {
      if (flushHandle !== null) return;
      const flush = () => {
        flushHandle = null;
        const pendingPayload = pendingSnapshot;
        pendingSnapshot = null;
        if (!pendingPayload || (pendingPayload.type !== "snapshot" && pendingPayload.type !== "update")) return;
        const stateUpdateStartedAtMs = Date.now();
        for (const item of pendingDeliveryEvents) {
          if (item.kind !== "transcript-updated") continue;
          const identity = subtitleRevisionIdentity(pendingPayload.events.sessionId, item.eventId, item.payload);
          if (identity) recordSubtitleRevisionStage(identity, "store-start", stateUpdateStartedAtMs, { visibilityState: document.visibilityState });
        }
        const mappedState = mapRealtimeState(interviewId, pendingPayload.transcripts, pendingPayload.candidates, pendingPayload.events, pendingPayload.runtime);
        onUpdate(mappedState, { type: pendingPayload.type, cursor: pendingPayload.cursor ?? 0 });
        const stateUpdatedAtMs = Date.now();
        const payload = markStateUpdate(pendingPayload, stateUpdateStartedAtMs, stateUpdatedAtMs);
        if (typeof payload.cursor === "number") window.sessionStorage?.setItem(cursorKey, String(payload.cursor));
        const deliveryEvents = pendingDeliveryEvents;
        pendingDeliveryEvents = [];
        for (const item of deliveryEvents) {
          if (item.kind !== "transcript-updated") continue;
          const identity = subtitleRevisionIdentity(payload.events.sessionId, item.eventId, item.payload);
          if (!identity) continue;
          recordSubtitleRevisionStage(identity, "store-complete", stateUpdatedAtMs, { visibilityState: document.visibilityState });
        }
        acknowledgeTranscriptDelivery(payload.events.sessionId, deliveryEvents, stateUpdateStartedAtMs, stateUpdatedAtMs);
        this.publishCaptureEvents({ sessionId: payload.events.sessionId, events: deliveryEvents });
      };
      // State delivery must not wait for the next paint. A zero-delay task lets
      // the parser coalesce a burst while keeping transcript state ahead of UI
      // rendering and unrelated main-thread animation work.
      flushHandle = window.setTimeout(flush, 0);
    };
    const parser = createSseParser((event) => {
      const realtimeEvent = event as unknown as { type?: string };
      if (realtimeEvent.type === "revoked") {
        terminalStatus = 410;
        pendingSnapshot = null;
        return;
      }
      if (realtimeEvent.type !== "snapshot" && realtimeEvent.type !== "update") return;
      const parsedAtMs = Date.now();
      const receivedAtMs = latestChunkReceivedAtMs || parsedAtMs;
      const rawPayload = realtimeEvent as BackendRealtimeSessionStreamEvent;
      const payload = {
        ...rawPayload,
        events: {
          ...rawPayload.events,
          events: rawPayload.events.events.map(item => {
            if (item.kind !== "transcript-updated") return item;
            const performance = item.payload.performance;
            if (!performance || typeof performance !== "object") return item;
            return {
              ...item,
              payload: {
                ...item.payload,
                performance: {
                  ...performance,
                  browserStreamChunkReceivedAtMs: receivedAtMs,
                  browserEventParsedAtMs: parsedAtMs,
                  browserEventReceiveAtMs: receivedAtMs,
                  eventId: item.eventId,
                  visibilityState: document.visibilityState,
                },
              },
            };
          }),
        },
      } as BackendRealtimeSessionStreamEvent;
      if (payload.type === "snapshot" && !firstSnapshotRecorded) {
        firstSnapshotRecorded = true;
        clearFirstSnapshotDeadline();
        this.recordRealtimeDeliveryMetric(interviewId, "first-snapshot", { durationMs: Date.now() - connectStartedAt, reason: "opened" });
      }
      for (const item of payload.events.events) {
        if (item.kind !== "transcript-updated") continue;
        const identity = subtitleRevisionIdentity(payload.events.sessionId, item.eventId, item.payload);
        if (!identity) continue;
        const performance = item.payload.performance as Record<string, unknown>;
        recordSubtitleBackendStages(identity, performance);
        recordSubtitleRevisionStage(identity, "browser-chunk", receivedAtMs, { visibilityState: document.visibilityState });
        recordSubtitleRevisionStage(identity, "browser-parse", parsedAtMs, { visibilityState: document.visibilityState });
      }
      streamSnapshot = materializeRealtimeDelta(interviewId, streamSnapshot, payload);
      pendingSnapshot = streamSnapshot;
      pendingDeliveryEvents = coalescePendingDeliveryEvents(
        [...pendingDeliveryEvents, ...payload.events.events].filter(
          (item, index, items) => items.findIndex(candidate => candidate.eventId === item.eventId) === index,
        ),
      );
      scheduleFlush();
    });
    const diagnosticsPoll = subtitleRevisionDiagnosticsEnabled()
      ? window.setInterval(() => {
          void this.client.request<{ revisionDiagnostics?: { stageCounts?: Record<string, number> } }>(
            `/api/v1/realtime-speech/sessions/${interviewId}/performance-summary?userId=${encodeURIComponent(requireUserId())}`,
            { headers: authHeaders() },
          ).then(summary => updateRemoteSubtitleStageCounts(summary.revisionDiagnostics?.stageCounts)).catch(() => undefined);
        }, 2_000)
      : null;
    try {
      while (true) {
        const { done, value } = await Promise.race([reader.read(), firstSnapshotDeadline]);
        if (done) break;
        latestChunkReceivedAtMs = Date.now();
        parser.push(decoder.decode(value, { stream: true }));
      }
    } finally {
      clearFirstSnapshotDeadline();
      if (diagnosticsPoll !== null) window.clearInterval(diagnosticsPoll);
      if (!firstSnapshotRecorded) {
        void reader.cancel().catch(() => undefined);
        if (flushHandle !== null) {
          window.clearTimeout(flushHandle);
          flushHandle = null;
        }
      }
    }
    parser.push(decoder.decode());
    parser.flush();
    if (!firstSnapshotRecorded && terminalStatus === null && !signal?.aborted) throw firstSnapshotFailure("first-snapshot-eof");
    const pendingFinalSnapshot = pendingSnapshot as MaterializedRealtimeSessionStreamEvent | null;
    if (pendingFinalSnapshot) {
      const stateUpdateStartedAtMs = Date.now();
      for (const item of pendingDeliveryEvents) {
        if (item.kind !== "transcript-updated") continue;
        const identity = subtitleRevisionIdentity(pendingFinalSnapshot.events.sessionId, item.eventId, item.payload);
        if (identity) recordSubtitleRevisionStage(identity, "store-start", stateUpdateStartedAtMs, { visibilityState: document.visibilityState });
      }
      onUpdate(
        mapRealtimeState(interviewId, pendingFinalSnapshot.transcripts, pendingFinalSnapshot.candidates, pendingFinalSnapshot.events, pendingFinalSnapshot.runtime),
        { type: pendingFinalSnapshot.type, cursor: pendingFinalSnapshot.cursor ?? 0 },
      );
      const stateUpdatedAtMs = Date.now();
      const finalSnapshot = markStateUpdate(pendingFinalSnapshot, stateUpdateStartedAtMs, stateUpdatedAtMs);
      if (typeof finalSnapshot.cursor === "number") window.sessionStorage?.setItem(cursorKey, String(finalSnapshot.cursor));
      this.publishCaptureEvents({ sessionId: finalSnapshot.events.sessionId, events: pendingDeliveryEvents });
      for (const item of pendingDeliveryEvents) {
        if (item.kind !== "transcript-updated") continue;
        const identity = subtitleRevisionIdentity(finalSnapshot.events.sessionId, item.eventId, item.payload);
        if (identity) recordSubtitleRevisionStage(identity, "store-complete", stateUpdatedAtMs, { visibilityState: document.visibilityState });
      }
      acknowledgeTranscriptDelivery(finalSnapshot.events.sessionId, pendingDeliveryEvents, stateUpdateStartedAtMs, stateUpdatedAtMs);
      pendingDeliveryEvents = [];
      pendingSnapshot = null;
    }
    if (flushHandle !== null) {
      window.clearTimeout(flushHandle);
      flushHandle = null;
    }
    if (terminalStatus !== null) {
      window.sessionStorage?.removeItem(cursorKey);
      const error = new AppError("validation", "当前面试已被新的面试接管") as AppError & { status: number };
      error.status = terminalStatus;
      throw error;
    }
    this.recordRealtimeDeliveryMetric(interviewId, "connected-duration", {
      durationMs: Date.now() - connectedAt,
      reason: signal?.aborted ? "aborted" : "eof",
    });
  }

  async deleteInterview(id: string, signal?: AbortSignal) {
    await this.client.request(`/api/v1/sessions/${id}?userId=${encodeURIComponent(requireUserId())}`, {
      method: "DELETE",
      headers: authHeaders(),
    }, signal);
  }

  async deleteScreenshot(id: string, signal?: AbortSignal) {
    await this.client.request(`/api/v1/screenshot-answer/tasks/${id}?userId=${encodeURIComponent(requireUserId())}`, {
      method: "DELETE",
      headers: authHeaders(),
    }, signal);
  }

  async submitManualAnswer(command: Parameters<InterviewAppAdapter["submitManualAnswer"]>[0], signal?: AbortSignal, onStreamUpdate?: (update: ManualAnswerStreamUpdate) => void) {
    if (onStreamUpdate) return this.submitManualAnswerStream(command, signal, onStreamUpdate);
    const result = await this.client.request<BackendLiveAnswerResponse>("/api/v1/live-answer/questions", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: requireUserId(),
        sessionId: command.interviewId,
        question: command.question,
        stream: true,
        idempotencyKey: command.idempotencyKey,
        ...(command.questionId ? { questionId: command.questionId } : {}),
        ...(command.questionRevision ? { questionRevision: command.questionRevision } : {}),
        ...(command.clickedAtMs ? { clickedAtMs: command.clickedAtMs } : {}),
        ...(command.prefetchRevision ? { prefetchRevision: command.prefetchRevision } : {}),
      }),
    }, signal);
    return toSubmitManualAnswerResult(result.task);
  }

  private async submitManualAnswerStream(command: Parameters<InterviewAppAdapter["submitManualAnswer"]>[0], signal: AbortSignal | undefined, onStreamUpdate: (update: ManualAnswerStreamUpdate) => void): Promise<SubmitManualAnswerResult> {
    let latest: SubmitManualAnswerResult | null = null;
    let failureMessage = "回答生成失败，请稍后重试。";
    const emit = (event: LiveAnswerStreamEvent) => {
      if (!event.task) return;
      const result = toSubmitManualAnswerResult(event.task as BackendLiveAnswerTaskResponse);
      latest = result;
      if (event.type === "failed" && (event.errorMessage || event.partialText)) {
        failureMessage = event.errorMessage ?? failureMessage;
      }
      onStreamUpdate({ result, event });
    };
    const requestInit: RequestInit = {
      method: "POST",
      headers: {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
        ...authHeaders(),
      },
      body: JSON.stringify({
        userId: requireUserId(),
        sessionId: command.interviewId,
        question: command.question,
        stream: true,
        idempotencyKey: command.idempotencyKey,
        ...(command.questionId ? { questionId: command.questionId } : {}),
        ...(command.questionRevision ? { questionRevision: command.questionRevision } : {}),
        ...(command.clickedAtMs ? { clickedAtMs: command.clickedAtMs } : {}),
        ...(command.prefetchRevision ? { prefetchRevision: command.prefetchRevision } : {}),
      }),
    };
    if (signal) requestInit.signal = signal;
    const response = await this.fetchImpl(withBaseUrl(this.baseUrl, "/api/v1/live-answer/questions/stream"), requestInit);
    if (!response.ok) throw new AppError("validation", `实时回答启动失败（${response.status}）`);
    if (!response.body) throw new AppError("network", "当前浏览器不支持流式回答读取");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const parser = createSseParser(emit);
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      parser.push(decoder.decode(value, { stream: true }));
    }
    parser.push(decoder.decode());
    parser.flush();
    if (!latest) throw new AppError("validation", failureMessage);
    return latest;
  }

  async submitScreenshotAnswer(command: Parameters<InterviewAppAdapter["submitScreenshotAnswer"]>[0], signal?: AbortSignal, onStage?: (task: ScreenshotTask) => void, onAnswerUpdate?: (result: SubmitManualAnswerResult) => void) {
    let captureRequest: BackendRemoteScreenshotCaptureRequestResponse;
    try {
      captureRequest = await this.client.request<BackendRemoteScreenshotCaptureRequestResponse>(`/api/v1/screenshot-answer/sessions/${command.interviewId}/remote-capture-requests`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          userId: requireUserId(),
          instruction: command.instruction,
        }),
      }, signal);
      onStage?.(screenshotStageToTask(captureRequest));
    } catch (error) {
      if (error instanceof TypeError && error.message.includes("Failed to fetch")) {
        throw new AppError("network", "后端截图接口暂时不可达，请确认后端服务已启动且网页正在使用正确的 API 地址。");
      }
      throw error;
    }
    const cancelRemoteCapture = async () => {
      await this.client.request<BackendRemoteScreenshotCaptureRequestResponse>(`/api/v1/screenshot-answer/capture-requests/${captureRequest.requestId}/cancel`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ userId: requireUserId() }),
      }).catch(() => undefined);
    };
    try {
      const deadlineAt = Date.now() + 120000;
      let recoveryDelayMs = 1000;
      while (Date.now() < deadlineAt) {
        if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
        const pushed = await this.waitForCaptureEvent(captureRequest.requestId, recoveryDelayMs, signal);
        if (pushed) {
          onStage?.(screenshotEventToTask(pushed));
          const pushedStatus = String(pushed.status ?? "processing");
          const pushedTask = pushed.answerTask && typeof pushed.answerTask === "object"
            ? pushed.answerTask as BackendScreenshotAnswerTaskResponse
            : null;
          if (pushedTask) {
            onAnswerUpdate?.(toSubmitScreenshotAnswerResult(pushedTask, command.instruction));
            if (screenshotAnswerText(pushedTask)) {
              this.acknowledgeRuntimePerformance(
                command.interviewId,
                captureRequest.requestId,
                "screenshot-first-render",
                captureRequest.createdAtMs,
                pushedTask.taskId,
              );
            }
          }
          if (pushedStatus === "completed" && pushedTask) return toSubmitScreenshotAnswerResult(pushedTask, command.instruction);
          if (pushedStatus === "cancelled") throw new DOMException("Aborted", "AbortError");
          if (pushedStatus === "failed") throw new AppError("validation", `${pushed.stage ? `截图阶段 ${String(pushed.stage)} 失败：` : ""}${String(pushed.errorMessage || "伴随程序截屏回答失败，请检查本地助手状态后重试。")}`);
          recoveryDelayMs = 1000;
          continue;
        }
        const current = await this.client.request<BackendRemoteScreenshotCaptureRequestResponse>(`/api/v1/screenshot-answer/capture-requests/${captureRequest.requestId}?userId=${encodeURIComponent(requireUserId())}`, {
          method: "GET",
          headers: authHeaders(),
        }, signal);
        onStage?.(screenshotStageToTask(current));
        if (current.answerTask) {
          onAnswerUpdate?.(toSubmitScreenshotAnswerResult(current.answerTask, command.instruction));
          if (screenshotAnswerText(current.answerTask)) {
            this.acknowledgeRuntimePerformance(
              command.interviewId,
              captureRequest.requestId,
              "screenshot-first-render",
              captureRequest.createdAtMs,
              current.answerTask.taskId,
            );
          }
        }
        if (current.status === "completed" && current.answerTask) return toSubmitScreenshotAnswerResult(current.answerTask, command.instruction);
        if (current.status === "cancelled") throw new DOMException("Aborted", "AbortError");
        if (current.status === "failed") throw new AppError("validation", `${current.stage ? `截图阶段 ${current.stage} 失败：` : ""}${current.errorMessage || "伴随程序截屏回答失败，请检查本地助手状态后重试。"}`);
        recoveryDelayMs = Math.min(recoveryDelayMs * 2, 8000);
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        await cancelRemoteCapture();
      }
      throw error;
    }
    await cancelRemoteCapture();
    throw new AppError("network", "等待本地助手截屏超时，请确认伴随程序已连接且正在运行。");
  }

  async cancelAnswer(command: Parameters<InterviewAppAdapter["cancelAnswer"]>[0], current: Parameters<InterviewAppAdapter["cancelAnswer"]>[1], signal?: AbortSignal) {
    if (current.billingUsageId.startsWith("screenshot-answer:")) {
      const result = await this.client.request<BackendCancelledScreenshotTaskResponse>(`/api/v1/screenshot-answer/tasks/${command.answerTaskId}?userId=${encodeURIComponent(requireUserId())}`, {
        method: "DELETE",
        headers: authHeaders(),
      }, signal);
      return {
        outcome: result.status === "cancelled" ? "cancelled" : "not-cancellable",
        task: {
          ...current,
          id: result.taskId,
          interviewId: result.sessionId,
          userId: result.ownerUserId,
          question: result.visionSummaryTitle?.trim() || current.question,
          status: result.status === "cancelled" ? "cancelled" : current.status,
          updatedAtMs: result.updatedAtMs,
          revision: current.revision + 1,
        },
        billingReleased: result.status === "cancelled",
      } satisfies CancelAnswerResult;
    }
    const result = await this.client.request<BackendCancelAnswerResponse>(`/api/v1/live-answer/tasks/${command.answerTaskId}/cancel`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: requireUserId(),
        expectedRevision: command.expectedRevision,
        idempotencyKey: command.idempotencyKey,
      }),
    }, signal);
    return {
      outcome: result.outcome,
      task: toAnswerTaskSnapshot(result.task, current),
      billingReleased: result.billingReleased,
    } satisfies CancelAnswerResult;
  }

  async redeemPoints(request: Parameters<InterviewAppAdapter["redeemPoints"]>[0], signal?: AbortSignal): Promise<PointsRedemptionResult> {
    return this.client.request<PointsRedemptionResult>("/api/v1/billing/redemptions", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ userId: requireUserId(), code: request.code, idempotencyKey: request.idempotencyKey }),
    }, signal);
  }

  async createCheckoutOrder(request: Parameters<InterviewAppAdapter["createCheckoutOrder"]>[0], signal?: AbortSignal): Promise<OfficialCheckoutOrder> {
    return this.client.request<OfficialCheckoutOrder>("/api/v1/billing/checkout-orders", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ userId: requireUserId(), productId: request.productId, channel: request.channel, idempotencyKey: request.idempotencyKey }),
    }, signal);
  }

  async getCheckoutOrder(orderId: string, signal?: AbortSignal): Promise<OfficialCheckoutOrder> {
    return this.client.request<OfficialCheckoutOrder>(`/api/v1/billing/checkout-orders/${encodeURIComponent(orderId)}`, {
      headers: authHeaders(),
    }, signal);
  }
}
