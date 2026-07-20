import type { CaptureState, FoundationIndexResponse } from "@offersteady/protocol";

import type { AnswerProvenance, AnswerSourceReference, AnswerTaskSnapshot, CancelAnswerResult, OfficialCheckoutOrder, PointsRedemptionResult } from "@offersteady/protocol";
import { AppError } from "./domain";
import type { AnswerAdvice, DesktopDeviceBinding, InterviewAppAdapter, InterviewQuestion, InterviewSummary, ScreenshotTask, SubmitManualAnswerResult, WebAppState } from "./domain";
import { createJsonClient, withBaseUrl } from "./api-client";
import { authClient } from "./auth-client";
import { createSseParser, type LiveAnswerStreamEvent, type ManualAnswerStreamUpdate } from "./live-answer-stream";

interface BackendSessionResponse {
  readonly sessionId: string;
  readonly title: string;
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

interface BackendLiveAnswerTaskResponse {
  readonly taskId: string;
  readonly sessionId: string;
  readonly ownerUserId: string;
  readonly question: string;
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
    readonly overlap: boolean;
    readonly publishedAtMs?: number;
    readonly performance?: {
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
    }>;
  };
  readonly sourceHealth: readonly {
    readonly sourceId: string;
    readonly sourceKind: "microphone" | "system" | "mixed" | string;
    readonly label: string;
    readonly state: string;
    readonly stage?: string | null;
    readonly level: number;
    readonly errorCode?: string | null;
    readonly frameCount?: number | null;
    readonly backendFrameCount?: number | null;
  }[];
}

interface BackendRealtimeSessionStreamEvent {
  readonly type: "snapshot";
  readonly cursor?: number;
  readonly transcripts: BackendRealtimeTranscriptListResponse;
  readonly candidates: BackendRealtimeQuestionCandidateListResponse;
  readonly events: BackendRealtimeEventListResponse;
  readonly runtime: BackendRealtimeRuntimeResponse | null;
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
  const latestDeviceStatus = [...events.events].reverse().find(event => event.kind === "device-status");
  const latestDegraded = [...events.events].reverse().find(event => event.kind === "degraded");
  const captureState = toCaptureState(latestDeviceStatus?.payload.captureState)
    ?? (runtime?.sessionLive && runtime.machineCodeBound ? "capturing" as const : undefined);
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
  } satisfies Pick<WebAppState, "speaker"> & Partial<Pick<WebAppState, "captureState">>;
};

const questionStatusFromTask = (task: BackendLiveAnswerTaskResponse): InterviewQuestion["status"] =>
  task.status === "completed" ? "confirmed" : task.status === "failed" ? "failed" : task.status === "cancelled" ? "cancelled" : task.status === "streaming" ? "streaming" : "generating";

const toSubmitManualAnswerResult = (task: BackendLiveAnswerTaskResponse): SubmitManualAnswerResult => ({
  question: {
    id: task.taskId,
    askedAt: "刚刚",
    text: task.question,
    input: "manual",
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
    question: task.question,
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

export class BackendPreviewInterviewAdapter implements InterviewAppAdapter {
  private readonly client;
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;
  private foundation: FoundationIndexResponse | null = null;

  constructor(baseUrl: string, fetchImpl?: typeof fetch) {
    this.baseUrl = baseUrl;
    const rawFetch = fetchImpl ?? ((input, init) => window.fetch(input, init));
    this.fetchImpl = createAuthRefreshingFetch(rawFetch);
    this.client = createJsonClient({ baseUrl, fetchImpl: this.fetchImpl });
  }

  async probe(signal?: AbortSignal): Promise<FoundationIndexResponse> {
    if (this.foundation) return this.foundation;
    this.foundation = await this.client.request<FoundationIndexResponse>("/api/v1/system/foundation", undefined, signal);
    return this.foundation;
  }

  async loadState(signal?: AbortSignal, options?: { readonly auth?: boolean }): Promise<WebAppState> {
    return this.client.request<WebAppState>("/api/v1/web/state", { headers: options?.auth === false ? {} : authHeaders() }, signal);
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

  async startInterviewSession(id: string, signal?: AbortSignal) {
    const started = await this.client.request<BackendSessionResponse>(`/api/v1/sessions/${id}/start`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ userId: requireUserId() }),
    }, signal);
    return toInterviewSummary(started);
  }

  async bindDesktopDevice(command: Parameters<InterviewAppAdapter["bindDesktopDevice"]>[0], signal?: AbortSignal) {
    const binding = await this.client.request<BackendDesktopBindingResponse>(`/api/v1/realtime-speech/sessions/${command.interviewId}/desktop-binding`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ userId: requireUserId(), manualCode: command.manualCode.trim() }),
    }, signal);
    return toDesktopDeviceBinding(binding);
  }

  async getDesktopDeviceBinding(interviewId: string, signal?: AbortSignal) {
    try {
      const binding = await this.client.request<BackendDesktopBindingResponse>(`/api/v1/realtime-speech/sessions/${interviewId}/desktop-binding?userId=${encodeURIComponent(requireUserId())}`, {
        headers: authHeaders(),
      }, signal);
      return toDesktopDeviceBinding(binding);
    } catch (error) {
      if (error instanceof Error && (error.message.includes("404") || error.message.includes("尚未绑定"))) return null;
      return null;
    }
  }

  async sendDesktopSessionHeartbeat(command: Parameters<InterviewAppAdapter["sendDesktopSessionHeartbeat"]>[0], signal?: AbortSignal) {
    await this.client.request<Record<string, unknown>>(`/api/v1/realtime-speech/sessions/${command.interviewId}/web-heartbeat`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        userId: requireUserId(),
        bindingId: command.bindingId ?? null,
        page: command.page,
      }),
    }, signal);
  }

  async loadRealtimeSession(interviewId: string, signal?: AbortSignal) {
    const [transcripts, candidates, events, runtime] = await Promise.all([
      this.client.request<BackendRealtimeTranscriptListResponse>(`/api/v1/realtime-speech/sessions/${interviewId}/transcripts?userId=${encodeURIComponent(requireUserId())}`, { headers: authHeaders() }, signal),
      this.client.request<BackendRealtimeQuestionCandidateListResponse>(`/api/v1/realtime-speech/sessions/${interviewId}/question-candidates?userId=${encodeURIComponent(requireUserId())}`, { headers: authHeaders() }, signal),
      this.client.request<BackendRealtimeEventListResponse>(`/api/v1/realtime-speech/sessions/${interviewId}/events?userId=${encodeURIComponent(requireUserId())}`, { headers: authHeaders() }, signal).catch(() => ({ sessionId: interviewId, events: [] })),
      this.client.request<BackendRealtimeRuntimeResponse>(`/api/v1/realtime-speech/sessions/${interviewId}/runtime?userId=${encodeURIComponent(requireUserId())}`, { headers: authHeaders() }, signal).catch(() => null),
    ]);
    return mapRealtimeState(interviewId, transcripts, candidates, events, runtime);
  }

  async subscribeRealtimeSession(interviewId: string, onUpdate: (state: Pick<WebAppState, "speaker"> & Partial<Pick<WebAppState, "captureState">>) => void, signal?: AbortSignal) {
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
    const response = await this.fetchImpl(withBaseUrl(this.baseUrl, `/api/v1/realtime-speech/sessions/${interviewId}/stream?userId=${encodeURIComponent(requireUserId())}&cursor=${cursor}`), requestInit);
    if (!response.ok) throw new AppError("validation", `实时对话订阅失败（${response.status}）`);
    if (!response.body) throw new AppError("network", "当前浏览器不支持实时对话订阅读取");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let pendingSnapshot: BackendRealtimeSessionStreamEvent | null = null;
    let flushHandle: number | null = null;
    const scheduleFlush = () => {
      if (flushHandle !== null) return;
      const flush = () => {
        flushHandle = null;
        const payload = pendingSnapshot;
        pendingSnapshot = null;
        if (!payload || payload.type !== "snapshot") return;
        if (typeof payload.cursor === "number") window.sessionStorage?.setItem(cursorKey, String(payload.cursor));
        onUpdate(mapRealtimeState(interviewId, payload.transcripts, payload.candidates, payload.events, payload.runtime));
      };
      flushHandle = typeof requestAnimationFrame === "function"
        ? requestAnimationFrame(flush)
        : window.setTimeout(flush, 16);
    };
    const parser = createSseParser((event) => {
      const payload = event as unknown as BackendRealtimeSessionStreamEvent;
      if (payload.type !== "snapshot") return;
      pendingSnapshot = payload;
      scheduleFlush();
    });
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      parser.push(decoder.decode(value, { stream: true }));
    }
    parser.push(decoder.decode());
    parser.flush();
    const finalSnapshot = pendingSnapshot as BackendRealtimeSessionStreamEvent | null;
    if (finalSnapshot) {
      onUpdate(mapRealtimeState(interviewId, finalSnapshot.transcripts, finalSnapshot.candidates, finalSnapshot.events, finalSnapshot.runtime));
      pendingSnapshot = null;
    }
    if (flushHandle !== null) {
      if (typeof cancelAnimationFrame === "function") cancelAnimationFrame(flushHandle);
      else window.clearTimeout(flushHandle);
      flushHandle = null;
    }
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

  async submitScreenshotAnswer(command: Parameters<InterviewAppAdapter["submitScreenshotAnswer"]>[0], signal?: AbortSignal, onStage?: (task: ScreenshotTask) => void) {
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
      while (Date.now() < deadlineAt) {
        if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
        const current = await this.client.request<BackendRemoteScreenshotCaptureRequestResponse>(`/api/v1/screenshot-answer/capture-requests/${captureRequest.requestId}?userId=${encodeURIComponent(requireUserId())}`, {
          method: "GET",
          headers: authHeaders(),
        }, signal);
        onStage?.(screenshotStageToTask(current));
        if (current.status === "completed" && current.answerTask) return toSubmitScreenshotAnswerResult(current.answerTask, command.instruction);
        if (current.status === "cancelled") throw new DOMException("Aborted", "AbortError");
        if (current.status === "failed") throw new AppError("validation", `${current.stage ? `截图阶段 ${current.stage} 失败：` : ""}${current.errorMessage || "伴随程序截屏回答失败，请检查本地助手状态后重试。"}`);
        await new Promise<void>((resolve, reject) => {
          const timer = window.setTimeout(resolve, 200);
          signal?.addEventListener("abort", () => {
            window.clearTimeout(timer);
            reject(new DOMException("Aborted", "AbortError"));
          }, { once: true });
        });
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
