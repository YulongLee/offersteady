import type { AnswerProvenance, AnswerTaskSnapshot, AudioSourceDegradedEvent, BillingOrder, BillingProduct, BillingSupportConfig, CancelAnswerCommand, CancelAnswerResult, CaptureState, CompanionDeviceStatus, ContextLibrarySource, DesktopReleaseManifest, KnowledgeCollection, KnowledgeDocumentVersion, OfficialCheckoutOrder, PointsLedgerEntry, PointsRedemptionRequest, PointsRedemptionResult, QuestionCandidateEvent, SafeAccountSummary, SessionContextSelection, SpeakerTranscriptSegment, TimePassEntitlement, UsageRates } from "@offersteady/protocol";
import type { ManualAnswerStreamUpdate } from "./live-answer-stream";

export type ResourceStatus = "missing" | "processing" | "ready" | "error" | "deleted";
export type SessionStatus = "preparing" | "ready" | "active" | "paused" | "ended" | "error";
export type QuestionStatus = "listening" | "transcribing" | "confirmed" | "generating" | "streaming" | "uncertain" | "failed" | "offline" | "cancelled";
export type ReviewStatus = "waiting" | "generating" | "complete" | "failed";

export interface PreparedResource {
  readonly id: string;
  readonly kind: "resume" | "jd" | "knowledge";
  readonly name: string;
  readonly status: ResourceStatus;
  readonly summary: string;
  readonly reusable: boolean;
}

export interface InterviewSummary {
  readonly id: string;
  readonly title: string;
  readonly role: string;
  readonly company?: string;
  readonly status: SessionStatus;
  readonly updatedAt: string;
  readonly readiness: number;
}

export interface AnswerAdvice {
  readonly outline: readonly string[];
  readonly detail: string;
  readonly sourceTypes: readonly ("简历" | "JD" | "知识库" | "截图")[];
  readonly inference: string;
  readonly uncertain: boolean;
  readonly provenance: AnswerProvenance;
}

export interface InterviewQuestion {
  readonly id: string;
  readonly askedAt: string;
  readonly text: string;
  readonly input: "desktop-audio" | "manual" | "screenshot";
  readonly status: QuestionStatus;
  readonly advice: AnswerAdvice;
}

export interface InterviewReview {
  readonly status: ReviewStatus;
  readonly duration: string;
  readonly summary: string;
  readonly screenshots: readonly { id: string; name: string }[];
}

export interface PreparationState {
  readonly resources: readonly PreparedResource[];
  readonly device: CompanionDeviceStatus | null;
}

export interface DesktopDeviceBinding {
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

export interface WebAppState {
  interviews: InterviewSummary[];
  preparation: PreparationState;
  questions: InterviewQuestion[];
  review: InterviewReview;
  captureState: CaptureState;
  librarySources: ContextLibrarySource[];
  contextSelections: Record<string, SessionContextSelection>;
  billing: BillingPresentationState;
  speaker: SpeakerPresentationState;
  activeAnswerTask: AnswerTaskSnapshot | null;
  account: SafeAccountSummary;
  knowledgeCollections: KnowledgeCollection[];
  knowledgeDocuments: KnowledgeDocumentVersion[];
  releaseManifest: DesktopReleaseManifest;
}

export interface BillingPresentationState {
  readonly catalog: readonly BillingProduct[];
  readonly rates: UsageRates;
  readonly balance: number;
  readonly ledger: readonly PointsLedgerEntry[];
  readonly activePass: TimePassEntitlement | null;
  readonly queuedPasses: readonly TimePassEntitlement[];
  readonly orders: readonly BillingOrder[];
  readonly officialOrders: readonly OfficialCheckoutOrder[];
  readonly support: BillingSupportConfig;
}

export interface SpeakerPresentationState {
  readonly mode: "dual-channel" | "manual-only";
  readonly transcripts: readonly SpeakerTranscriptSegment[];
  readonly pendingQuestion: QuestionCandidateEvent | null;
  readonly degradation: AudioSourceDegradedEvent | null;
  readonly runtimeNotice: {
    readonly stage: string;
    readonly message: string;
  } | null;
}

export interface ScreenshotTask {
  readonly name: string;
  readonly stage: "capturing" | "waiting-desktop" | "uploading" | "uploaded" | "recognizing" | "generating" | "completed" | "failed" | "cancelled";
  readonly errorMessage?: string;
}

export interface LiveActionState {
  readonly manualDraft: string;
  readonly screenshotTask: ScreenshotTask | null;
  readonly pendingQuestion: QuestionCandidateEvent | null;
}

export interface LiveWorkspaceViewState {
  readonly splitRatio: number;
  readonly viewingAnswerId: string | null;
  readonly newAnswerAvailable: boolean;
}

export interface SubmitManualAnswerCommand {
  readonly interviewId: string;
  readonly question: string;
  readonly idempotencyKey: string;
}

export interface SubmitScreenshotAnswerCommand {
  readonly interviewId: string;
  readonly instruction: string;
}

export interface SubmitManualAnswerResult {
  readonly question: InterviewQuestion;
  readonly task: AnswerTaskSnapshot;
}

export interface InterviewAppAdapter {
  loadState(signal?: AbortSignal, options?: { readonly auth?: boolean }): Promise<WebAppState>;
  createDraft(input: { title: string; role: string; company?: string }, signal?: AbortSignal): Promise<InterviewSummary>;
  confirmInterviewMaterials(selection: SessionContextSelection, signal?: AbortSignal): Promise<SessionContextSelection>;
  startInterviewSession(id: string, signal?: AbortSignal): Promise<InterviewSummary>;
  bindDesktopDevice(command: { interviewId: string; manualCode: string }, signal?: AbortSignal): Promise<DesktopDeviceBinding>;
  getDesktopDeviceBinding(interviewId: string, signal?: AbortSignal): Promise<DesktopDeviceBinding | null>;
  sendDesktopSessionHeartbeat(command: { interviewId: string; bindingId?: string | null; page: "preparation" | "live" }, signal?: AbortSignal): Promise<void>;
  loadRealtimeSession(interviewId: string, signal?: AbortSignal): Promise<Pick<WebAppState, "speaker"> & Partial<Pick<WebAppState, "captureState">>>;
  subscribeRealtimeSession(interviewId: string, onUpdate: (state: Pick<WebAppState, "speaker"> & Partial<Pick<WebAppState, "captureState">>) => void, signal?: AbortSignal): Promise<void>;
  deleteInterview(id: string, signal?: AbortSignal): Promise<void>;
  deleteScreenshot(id: string, signal?: AbortSignal): Promise<void>;
  submitManualAnswer(command: SubmitManualAnswerCommand, signal?: AbortSignal, onStreamUpdate?: (update: ManualAnswerStreamUpdate) => void): Promise<SubmitManualAnswerResult>;
  submitScreenshotAnswer(command: SubmitScreenshotAnswerCommand, signal?: AbortSignal, onStage?: (task: ScreenshotTask) => void): Promise<SubmitManualAnswerResult>;
  cancelAnswer(command: CancelAnswerCommand, current: AnswerTaskSnapshot, signal?: AbortSignal): Promise<CancelAnswerResult>;
  redeemPoints(request: PointsRedemptionRequest, signal?: AbortSignal): Promise<PointsRedemptionResult>;
  createCheckoutOrder(request: { productId: string; channel: "wechat" | "alipay"; idempotencyKey: string }, signal?: AbortSignal): Promise<OfficialCheckoutOrder>;
  getCheckoutOrder(orderId: string, signal?: AbortSignal): Promise<OfficialCheckoutOrder>;
}

export class AppError extends Error {
  constructor(readonly code: "aborted" | "validation" | "network" | "not-implemented" | "unknown", message: string) {
    super(message);
    this.name = "AppError";
  }
}

export const normalizeError = (error: unknown): AppError => {
  if (error instanceof AppError) return error;
  if (error instanceof DOMException && error.name === "AbortError") return new AppError("aborted", "请求已取消");
  if (typeof error === "object" && error !== null && "status" in error && (error as { status?: number }).status === 501) return new AppError("not-implemented", "该功能正在接入后端基础工程");
  if (error instanceof Error && error.message) return new AppError("unknown", error.message);
  return new AppError("unknown", "暂时无法完成操作，请稍后重试");
};
