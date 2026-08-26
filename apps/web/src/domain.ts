import type { AnswerProvenance, AnswerTaskSnapshot, AudioSourceDegradedEvent, BillingOrder, BillingProduct, BillingSupportConfig, CancelAnswerCommand, CancelAnswerResult, CaptureState, CompanionDeviceStatus, ContextLibrarySource, DesktopReleaseManifest, KnowledgeCollection, KnowledgeDocumentVersion, OfficialCheckoutOrder, PointsLedgerEntry, PointsRedemptionRequest, PointsRedemptionResult, QuestionCandidateEvent, SafeAccountSummary, SessionContextSelection, SpeakerTranscriptSegment, TimePassEntitlement, UsageRates } from "@offersteady/protocol";
import type { ManualAnswerStreamUpdate } from "./live-answer-stream";

export type ResourceStatus = "missing" | "processing" | "ready" | "error" | "deleted";
export type SessionStatus = "preparing" | "ready" | "active" | "paused" | "ended" | "error";
export type InterviewLanguage = "zh-CN" | "en-US";
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
  readonly interviewLanguage?: InterviewLanguage;
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
  readonly rawText?: string;
  readonly questionNormalizationStatus?: "pending" | "completed" | "fallback" | "not-requested";
  readonly input: "desktop-audio" | "manual" | "screenshot";
  readonly status: QuestionStatus;
  readonly advice: AnswerAdvice;
}

export interface InterviewReview {
  readonly status: ReviewStatus;
  readonly duration: string;
  readonly summary: string;
  readonly screenshots: readonly { id: string; name: string }[];
  readonly sessionId?: string;
  readonly title?: string;
  readonly startedAtMs?: number | null;
  readonly endedAtMs?: number | null;
  readonly transcripts: readonly InterviewReviewTranscript[];
}

export interface InterviewReviewTranscript {
  readonly id: string;
  readonly role: "interviewer" | "candidate";
  readonly speakerLabel: "面试官" | "我";
  readonly text: string;
  readonly occurredAtMs: number;
  readonly ordering: number;
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

export interface RecentDesktopDevice {
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

export interface AccountDesktopDevice extends RecentDesktopDevice {
  readonly linkedAtMs: number;
  readonly lastUsedAtMs: number;
  readonly activeInterview?: {
    readonly sessionId: string;
    readonly bindingId: string;
    readonly connectedAtMs: number;
  } | null;
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

export interface InterviewWorkspaceSnapshot {
  readonly questions: readonly InterviewQuestion[];
  readonly activeAnswerTask: AnswerTaskSnapshot | null;
}

export interface BillingPresentationState {
  readonly availablePaymentChannels: readonly ("wechat" | "alipay")[];
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

export interface ReferralStatus {
  readonly enabled: boolean;
  readonly rewardPoints: number;
  readonly inviterRewardPoints?: number;
  readonly inviteeRewardPoints?: number;
  readonly activationWindowDays?: number;
  readonly eligibleToActivate?: boolean;
  readonly activationDeadlineMs?: number | null;
  readonly activationEligibilityReason?: "already-activated" | "registration-time-unavailable" | "activation-window-expired" | "activity-disabled" | null;
  readonly activatedReward?: {
    readonly inviterRewardPoints: number;
    readonly inviteeRewardPoints: number;
    readonly activatedAtMs: number;
  } | null;
  readonly configVersion: number;
  readonly referralCode: string;
  readonly shareUrl: string;
  readonly inviteCount: number;
  readonly totalRewardPoints: number;
  readonly hasActivatedReferral: boolean;
}

export interface ReferralActivationResult {
  readonly outcome: "activated" | "already-activated" | "invalid-code" | "self-referral" | "disabled" | "activation-window-expired" | "registration-time-unavailable";
  readonly replayed?: boolean;
  readonly rewardPoints?: number;
  readonly inviterRewardPoints?: number;
  readonly inviteeRewardPoints?: number;
  readonly activationDeadlineMs?: number;
  readonly activatedAtMs?: number;
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
  readonly quickAnswerStatus?: "idle" | "processing" | "success" | "failed" | "cancelled";
  readonly quickAnswerMessage?: string;
  readonly screenshotAnswerStatus?: "idle" | "processing" | "success" | "failed" | "cancelled";
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
  readonly questionId?: string;
  readonly questionRevision?: number;
  readonly clickedAtMs?: number;
  readonly prefetchRevision?: number;
}

export interface SubmitScreenshotAnswerCommand {
  readonly interviewId: string;
  readonly instruction: string;
}

export interface ActiveInterviewConflict {
  readonly currentInterviewId: string;
  readonly activeInterview: InterviewSummary | null;
}

export interface IdleInterviewStatus {
  readonly sessionId: string;
  readonly state: "active" | "warning" | "ended";
  readonly lastActivityAtMs: number;
  readonly warningAtMs: number;
  readonly expiresAtMs: number;
  readonly remainingMs: number;
  readonly autoEnded?: boolean;
}

export interface SubmitManualAnswerResult {
  readonly question: InterviewQuestion;
  readonly task: AnswerTaskSnapshot;
}

export interface DesktopShortcutScreenshotUpdate {
  readonly requestId: string;
  readonly status: "requested" | "processing" | "completed" | "failed" | "cancelled";
  readonly screenshotTask: ScreenshotTask;
  readonly result?: SubmitManualAnswerResult;
  readonly notificationId?: string;
  readonly acceptedAtMs?: number;
}

export type RealtimeSessionUpdate = Pick<WebAppState, "speaker"> & Partial<Pick<WebAppState, "captureState">> & {
  readonly shortcutScreenshotUpdate?: DesktopShortcutScreenshotUpdate;
  readonly answerUpdate?: SubmitManualAnswerResult;
};

export interface InterviewAppAdapter {
  loadState(signal?: AbortSignal, options?: { readonly auth?: boolean }): Promise<WebAppState>;
  getBillingState(signal?: AbortSignal): Promise<BillingPresentationState>;
  getReferralStatus(signal?: AbortSignal): Promise<ReferralStatus>;
  resolveReferral(code: string, signal?: AbortSignal): Promise<{ valid: boolean; enabled: boolean; rewardPoints?: number; inviterRewardPoints?: number; inviteeRewardPoints?: number; activationWindowDays?: number }>;
  activateReferral(code: string, signal?: AbortSignal): Promise<ReferralActivationResult>;
  createDraft(input: { title: string; role: string; company?: string }, signal?: AbortSignal): Promise<InterviewSummary>;
  updateInterviewLanguage(id: string, interviewLanguage: InterviewLanguage, signal?: AbortSignal): Promise<InterviewSummary>;
  confirmInterviewMaterials(selection: SessionContextSelection, signal?: AbortSignal): Promise<SessionContextSelection>;
  getActiveInterviewConflict(id: string, signal?: AbortSignal): Promise<ActiveInterviewConflict>;
  supersedeActiveInterview(command: { interviewId: string; expectedPreviousInterviewId: string }, signal?: AbortSignal): Promise<readonly string[]>;
  startInterviewSession(id: string, signal?: AbortSignal): Promise<InterviewSummary>;
  getInterviewIdleStatus(id: string, signal?: AbortSignal): Promise<IdleInterviewStatus>;
  continueInterviewSession(id: string, signal?: AbortSignal): Promise<IdleInterviewStatus>;
  controlInterviewCapture(id: string, action: "pause" | "resume", signal?: AbortSignal): Promise<CaptureState>;
  endInterviewSession(id: string, signal?: AbortSignal): Promise<void>;
  bindDesktopDevice(command: { interviewId: string; manualCode?: string; reuseLastDevice?: boolean }, signal?: AbortSignal): Promise<DesktopDeviceBinding>;
  getLastDesktopDevice?(signal?: AbortSignal): Promise<RecentDesktopDevice | null>;
  listDesktopDevices?(signal?: AbortSignal): Promise<readonly AccountDesktopDevice[]>;
  getDesktopDeviceBinding(interviewId: string, signal?: AbortSignal): Promise<DesktopDeviceBinding | null>;
  sendDesktopSessionHeartbeat(command: { interviewId: string; bindingId?: string | null; page: "preparation" | "live"; pageInstanceId?: string }, signal?: AbortSignal): Promise<{ pageInstanceId: string | null; leaseGeneration: number; leaseExpiresAtMs: number }>;
  loadRealtimeSession(interviewId: string, signal?: AbortSignal, lease?: { readonly pageInstanceId: string; readonly leaseGeneration: number }): Promise<RealtimeSessionUpdate>;
  loadInterviewWorkspace(interviewId: string, signal?: AbortSignal): Promise<InterviewWorkspaceSnapshot>;
  loadInterviewReview(interviewId: string, signal?: AbortSignal): Promise<InterviewReview>;
  loadDesktopShortcutScreenshotUpdates(interviewId: string, signal?: AbortSignal): Promise<readonly DesktopShortcutScreenshotUpdate[]>;
  cancelDesktopShortcutScreenshot(requestId: string, signal?: AbortSignal): Promise<void>;
  subscribeRealtimeSession(interviewId: string, onUpdate: (state: RealtimeSessionUpdate, delivery?: { readonly type: "snapshot" | "update"; readonly cursor: number }) => void, signal?: AbortSignal, lease?: { readonly pageInstanceId: string; readonly leaseGeneration: number }): Promise<void>;
  deleteInterview(id: string, signal?: AbortSignal): Promise<void>;
  deleteScreenshot(id: string, signal?: AbortSignal): Promise<void>;
  submitManualAnswer(command: SubmitManualAnswerCommand, signal?: AbortSignal, onStreamUpdate?: (update: ManualAnswerStreamUpdate) => void): Promise<SubmitManualAnswerResult>;
  submitScreenshotAnswer(command: SubmitScreenshotAnswerCommand, signal?: AbortSignal, onStage?: (task: ScreenshotTask) => void, onAnswerUpdate?: (result: SubmitManualAnswerResult) => void): Promise<SubmitManualAnswerResult>;
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
