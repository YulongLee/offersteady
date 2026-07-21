import type { AnswerTaskSnapshot, BillingProduct, CancelAnswerCommand, CancelAnswerResult, CompanionDeviceStatus, ContextLibrarySource, DesktopReleaseEntry, KnowledgeCollection, KnowledgeDocumentVersion, OfficialCheckoutOrder, PointsRedemptionRequest, PointsRedemptionResult, RedemptionSuccessData, SpeakerTranscriptSegment } from "@offersteady/protocol";
import type { InterviewAppAdapter, InterviewSummary, WebAppState } from "./domain";

const device: CompanionDeviceStatus = {
  deviceId: "synthetic-mac-device",
  displayName: "这台 Mac",
  captureState: "ready",
  connected: true,
  activeSourceIds: [],
  capabilities: {
    platform: "macos",
    platformVersion: "macOS 14.2+ universal",
    appVersion: "0.1.0",
    protocolVersion: "1.0.0",
    microphone: "granted",
    systemAudio: "granted",
    availableSources: [],
  },
  lastSeenAtMs: Date.now(),
};

export const syntheticLibrarySources: ContextLibrarySource[] = [
  { id: "resume-frontend", ownerUserId: "admin", kind: "resume", displayName: "高级前端工程师简历（合成）", version: "v3", status: "ready", updatedAtMs: 1_719_648_000_000, summary: "5 年前端经验，包含跨端工作台与性能治理。" },
  { id: "resume-product", ownerUserId: "admin", kind: "resume", displayName: "产品工程师简历（合成）", version: "v1", status: "ready", updatedAtMs: 1_716_969_600_000, summary: "产品工程与端到端交付经历。" },
  { id: "jd-frontend", ownerUserId: "admin", kind: "jd", displayName: "示例科技高级前端 JD", version: "v2", status: "ready", updatedAtMs: 1_719_734_400_000, summary: "React、TypeScript、工程化和复杂产品交付。" },
  { id: "jd-product", ownerUserId: "admin", kind: "jd", displayName: "合成产品工程师 JD", version: "v1", status: "ready", updatedAtMs: 1_718_900_000_000, summary: "端到端交付、用户研究和跨团队协作。" },
  { id: "jd-old", ownerUserId: "admin", kind: "jd", displayName: "旧版前端 JD", version: "v1", status: "failed", updatedAtMs: 1_700_000_000_000, summary: "解析失败，不能用于新回答。" },
  { id: "kb-performance", ownerUserId: "admin", kind: "knowledge", displayName: "前端性能治理", version: "v4", status: "ready", updatedAtMs: 1_719_648_000_000, summary: "性能指标、诊断路径和优化复盘。" },
  { id: "kb-microfrontend", ownerUserId: "admin", kind: "knowledge", displayName: "微前端项目复盘", version: "v2", status: "ready", updatedAtMs: 1_718_000_000_000, summary: "架构边界、隔离与迁移经验。" },
  { id: "kb-system-design", ownerUserId: "admin", kind: "knowledge", displayName: "系统设计清单", version: "v5", status: "ready", updatedAtMs: 1_719_000_000_000, summary: "容量、可靠性、数据与取舍检查项。" },
  { id: "kb-product", ownerUserId: "admin", kind: "knowledge", displayName: "产品方法论笔记", version: "v1", status: "disabled", updatedAtMs: 1_710_000_000_000, summary: "已停用，不参与当前面试。" },
];

const billingProducts: BillingProduct[] = [
  { id: "pass-3", catalogVersion: 3, kind: "time_pass", displayName: "3 天会员", priceCents: 6990, durationDays: 3, knowledgeIndexAllowance: 0, published: true },
  { id: "pass-7", catalogVersion: 3, kind: "time_pass", displayName: "7 天会员", priceCents: 12990, durationDays: 7, knowledgeIndexAllowance: 0, published: true },
  { id: "pass-15", catalogVersion: 3, kind: "time_pass", displayName: "15 天会员", priceCents: 21990, durationDays: 15, knowledgeIndexAllowance: 2, published: true },
  { id: "pass-30", catalogVersion: 3, kind: "time_pass", displayName: "30 天会员", priceCents: 32990, durationDays: 30, knowledgeIndexAllowance: 2, published: true },
  { id: "points-300", catalogVersion: 3, kind: "points_pack", displayName: "300 点", priceCents: 3990, points: 300, published: true },
  { id: "points-800", catalogVersion: 3, kind: "points_pack", displayName: "800 点", priceCents: 8990, points: 800, published: true },
  { id: "points-2000", catalogVersion: 3, kind: "points_pack", displayName: "2000 点", priceCents: 19990, points: 2000, published: true },
];

const knowledgeCollections: KnowledgeCollection[] = [
  { id: "collection-frontend", ownerUserId: "admin", name: "前端面试资料", createdAtMs: 1_719_000_000_000, updatedAtMs: 1_719_734_400_000 },
  { id: "collection-system", ownerUserId: "admin", name: "系统设计", createdAtMs: 1_718_000_000_000, updatedAtMs: 1_719_000_000_000 },
];
const knowledgeDocuments: KnowledgeDocumentVersion[] = [
  { id: "kb-performance", collectionId: "collection-frontend", ownerUserId: "admin", displayName: "前端性能治理", fileKind: "pdf", sizeBytes: 1_400_000, pageCount: 18, contentFingerprint: "fixture-performance", version: 4, status: "ready", createdAtMs: 1_719_648_000_000, safeSummary: "性能指标、诊断路径和优化复盘。" },
  { id: "kb-microfrontend", collectionId: "collection-frontend", ownerUserId: "admin", displayName: "微前端项目复盘", fileKind: "md", sizeBytes: 48_000, contentFingerprint: "fixture-microfrontend", version: 2, status: "ready", createdAtMs: 1_718_000_000_000, safeSummary: "架构边界、隔离与迁移经验。" },
  { id: "kb-product", collectionId: "collection-frontend", ownerUserId: "admin", displayName: "产品方法论笔记", fileKind: "md", sizeBytes: 21_000, contentFingerprint: "fixture-product", version: 1, status: "disabled", createdAtMs: 1_710_000_000_000, safeSummary: "已停用，不参与当前面试。" },
  { id: "kb-system-design", collectionId: "collection-system", ownerUserId: "admin", displayName: "系统设计清单", fileKind: "md", sizeBytes: 32_000, contentFingerprint: "fixture-system", version: 5, status: "ready", createdAtMs: 1_719_000_000_000, safeSummary: "容量、可靠性、数据与取舍检查项。" },
];
const releaseEntries: DesktopReleaseEntry[] = [
  { id: "mac-arm64-010", platform: "macos", architecture: "arm64", displayName: "macOS Apple Silicon", version: "0.1.0", minimumOs: "macOS 14.2+", fileSizeBytes: 82_000_000, sha256: "a".repeat(64), signingStatus: "verified", notarized: true, publishedAtMs: 1_719_734_400_000, protocolVersion: "1.0.0", downloadUrl: "/downloads/offersteady-macos-arm64.dmg", capabilities: { microphone: true, systemAudio: true, manualInputFallback: true, screenshotFallback: true } },
  { id: "mac-x64-010", platform: "macos", architecture: "x64", displayName: "macOS Intel", version: "0.1.0", minimumOs: "macOS 14.2+", fileSizeBytes: 86_000_000, sha256: "b".repeat(64), signingStatus: "verified", notarized: true, publishedAtMs: 1_719_734_400_000, protocolVersion: "1.0.0", downloadUrl: "/downloads/offersteady-macos-x64.dmg", capabilities: { microphone: true, systemAudio: true, manualInputFallback: true, screenshotFallback: true } },
  { id: "win-x64-preview", platform: "windows", architecture: "x64", displayName: "Windows 10/11", version: "0.1.0-preview", minimumOs: "Windows 10 22H2+", fileSizeBytes: 91_000_000, sha256: "c".repeat(64), signingStatus: "pending", notarized: false, publishedAtMs: 1_719_734_400_000, protocolVersion: "1.0.0", capabilities: { microphone: true, systemAudio: false, manualInputFallback: true, screenshotFallback: true } },
];

const transcripts: SpeakerTranscriptSegment[] = [
  { id: "transcript-q", sessionId: "demo", revision: 1, sourceId: "system-loopback", sourceKind: "system", speakerId: "interviewer-1", role: "interviewer", text: "请介绍一个你负责过的、最有挑战的前端项目。", transcriptConfidence: .95, startedAtMs: 1_000, endedAtMs: 4_000, isFinal: true, overlap: false },
  { id: "transcript-me", sessionId: "demo", revision: 1, sourceId: "mic-default", sourceKind: "microphone", speakerId: "candidate", role: "candidate", text: "我会先从项目背景开始讲。", transcriptConfidence: .94, startedAtMs: 4_600, endedAtMs: 6_100, isFinal: true, overlap: false },
  { id: "transcript-pending", sessionId: "demo", revision: 1, sourceId: "system-loopback", sourceKind: "system", speakerId: "interviewer-2", role: "interviewer", text: "还有一个细节，具体怎么监控", transcriptConfidence: .76, startedAtMs: 6_800, endedAtMs: 8_200, isFinal: false, overlap: false },
];

export const syntheticState: WebAppState = {
  interviews: [
    { id: "demo", title: "高级前端工程师面试", role: "高级前端工程师", company: "示例科技", status: "ready", updatedAt: "今天 18:10", readiness: 80 },
    { id: "review", title: "产品工程师模拟面试", role: "产品工程师", status: "ended", updatedAt: "昨天 21:30", readiness: 100 },
  ],
  preparation: {
    resources: [
      { id: "resume", kind: "resume", name: "候选人简历（合成）.pdf", status: "ready", summary: "5 年前端经验；负责过跨端工作台与性能治理。", reusable: true },
      { id: "jd", kind: "jd", name: "高级前端工程师 JD", status: "ready", summary: "关注 React、TypeScript、工程化和复杂产品交付。", reusable: false },
      { id: "kb", kind: "knowledge", name: "前端系统设计知识库", status: "ready", summary: "8 篇脱敏材料，覆盖性能、监控和架构取舍。", reusable: true },
    ],
    device,
  },
  questions: [
    {
      id: "q-current",
      askedAt: "18:24",
      text: "请介绍一个你负责过的、最有挑战的前端项目。",
      input: "desktop-audio",
      status: "confirmed",
      advice: {
        outline: ["先用一句话交代项目背景与目标", "聚焦你负责的技术决策与权衡", "用可核对的结果收尾，不补造数据"],
        detail: "可以按照 STAR 结构回答：先说明业务场景，再挑一个你真实做过的架构决策，解释为什么没有采用备选方案，最后引用简历中已存在的结果。如果结果没有量化数据，就诚实描述可观察到的改善。",
        sourceTypes: ["简历", "JD", "知识库"],
        inference: "JD 强调复杂产品交付，因此建议突出决策过程和协作边界。",
        uncertain: false,
        provenance: { selectionRevision: 1, usedSources: [
          { sourceId: "resume-frontend", sourceVersion: "v3", displayName: "高级前端工程师简历（合成）", kind: "resume" },
          { sourceId: "jd-frontend", sourceVersion: "v2", displayName: "示例科技高级前端 JD", kind: "jd" },
          { sourceId: "kb-performance", sourceVersion: "v4", displayName: "前端性能治理", kind: "knowledge" },
        ] },
      },
    },
    {
      id: "q-old",
      askedAt: "18:20",
      text: "请做一个简短的自我介绍。",
      input: "manual",
      status: "confirmed",
      advice: {
        outline: ["当前角色与年限", "与岗位最相关的两项经历", "为什么关注这个机会"],
        detail: "控制在 60–90 秒，优先使用简历中可核对的信息。",
        sourceTypes: ["简历", "JD"],
        inference: "岗位重视端到端交付，可将其作为经历筛选标准。",
        uncertain: false,
        provenance: { selectionRevision: 1, usedSources: [
          { sourceId: "resume-frontend", sourceVersion: "v3", displayName: "高级前端工程师简历（合成）", kind: "resume" },
          { sourceId: "jd-frontend", sourceVersion: "v2", displayName: "示例科技高级前端 JD", kind: "jd" },
        ] },
      },
    },
  ],
  review: {
    status: "complete",
    duration: "42 分钟",
    summary: "回答建议主要围绕项目决策、工程化和协作展开。复盘仅整理本场记录，不对候选人能力打分。",
    screenshots: [{ id: "shot-1", name: "系统设计题（合成）.png" }],
  },
  captureState: "ready",
  librarySources: syntheticLibrarySources,
  contextSelections: {
    demo: { sessionId: "demo", resumeSourceId: "resume-frontend", jobDescriptionSourceId: "jd-frontend", knowledgeSourceIds: ["kb-performance", "kb-system-design"], revision: 1, confirmedAtMs: 1_719_734_400_000 },
    review: { sessionId: "review", resumeSourceId: "resume-product", jobDescriptionSourceId: "jd-frontend", knowledgeSourceIds: ["kb-microfrontend"], revision: 2, confirmedAtMs: 1_719_000_000_000 },
  },
  billing: {
    catalog: billingProducts,
    rates: { catalogVersion: 4, answerPoints: 5, screenshotAnswerPoints: 15, knowledgeIndexMinimumPoints: 20, knowledgeIndexPointsPer1000Tokens: 4, tokenizerVersion: "synthetic-v1" },
    balance: 200,
    ledger: [{ id: "ledger-welcome", userId: "admin", kind: "welcome_grant", points: 200, createdAtMs: 1_719_734_400_000, referenceId: "welcome:admin", description: "新用户赠送积分" }],
    activePass: null,
    queuedPasses: [],
    orders: [],
    officialOrders: [],
    support: { wechatId: "OneShowAILab", email: "contact@oneshowailab.com", qrAssetPath: "", serviceHours: "工作日 10:00–18:00", refundSummary: "退款按订单状态和未使用权益人工审核" },
  },
  speaker: {
    mode: "dual-channel",
    transcripts,
    pendingQuestion: { id: "question:demo:transcript-pending", sessionId: "demo", revision: 1, sourceSegmentIds: ["transcript-pending"], text: "还有一个细节，具体怎么监控", state: "needs-confirmation", reason: "low-transcript-confidence", confidence: .55 },
    degradation: null,
    runtimeNotice: null,
  },
  activeAnswerTask: null,
  account: { id: "admin", displayName: "admin", createdAtMs: 1_719_000_000_000, bindings: [{ id: "prototype-binding", provider: "prototype", displayName: "本地 admin 身份", status: "active", boundAtMs: 1_719_000_000_000, canUnbind: false }] },
  knowledgeCollections,
  knowledgeDocuments,
  releaseManifest: { version: 1, generatedAtMs: 1_719_734_400_000, entries: releaseEntries },
};

const delay = async (signal?: AbortSignal) => {
  if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
  await Promise.resolve();
};

export class FixtureInterviewAdapter implements InterviewAppAdapter {
  private readonly cancelResults = new Map<string, CancelAnswerResult>();
  private redemption: RedemptionSuccessData | null = null;
  private readonly redemptionRequests = new Map<string, PointsRedemptionResult>();
  async loadState(signal?: AbortSignal) {
    await delay(signal);
    const state = structuredClone(syntheticState);
    if (this.redemption) state.billing = { ...state.billing, balance: this.redemption.newBalance, ledger: [this.redemption.ledgerEntry, ...state.billing.ledger] };
    return state;
  }

  async createDraft(input: { title: string; role: string; company?: string }, signal?: AbortSignal) {
    await delay(signal);
    const draft: InterviewSummary = {
      id: "draft",
      title: input.title.trim(),
      role: input.role.trim(),
      ...(input.company?.trim() ? { company: input.company.trim() } : {}),
      status: "preparing",
      updatedAt: "刚刚",
      readiness: 0,
    };
    return draft;
  }

  async confirmInterviewMaterials(selection: Parameters<InterviewAppAdapter["confirmInterviewMaterials"]>[0], signal?: AbortSignal) {
    await delay(signal);
    return structuredClone(selection);
  }

  async startInterviewSession(id: string, signal?: AbortSignal): Promise<InterviewSummary> {
    await delay(signal);
    const interview = syntheticState.interviews.find(item => item.id === id) ?? syntheticState.interviews[0]!;
    return { ...interview, id, status: "active", updatedAt: "刚刚" };
  }

  async bindDesktopDevice(command: Parameters<InterviewAppAdapter["bindDesktopDevice"]>[0], signal?: AbortSignal) {
    await delay(signal);
    return {
      bindingId: `fixture-binding-${command.manualCode}`,
      sessionId: command.interviewId,
      deviceId: `fixture-device-${command.manualCode}`,
      manualCode: command.manualCode,
      displayName: "面试稳伴随程序 · Mac",
      capabilities: { microphone: true, systemAudio: true, screenCapture: true },
      status: "bound",
      boundAtMs: Date.now(),
      lastSeenAtMs: Date.now(),
    } as const;
  }

  async getDesktopDeviceBinding(_interviewId: string, signal?: AbortSignal) {
    await delay(signal);
    return null;
  }

  async sendDesktopSessionHeartbeat(_command: Parameters<InterviewAppAdapter["sendDesktopSessionHeartbeat"]>[0], signal?: AbortSignal) {
    await delay(signal);
  }

  async loadRealtimeSession(_interviewId: string, signal?: AbortSignal) {
    await delay(signal);
    return { speaker: structuredClone(syntheticState.speaker) };
  }

  async subscribeRealtimeSession(_interviewId: string, onUpdate: (state: Pick<WebAppState, "speaker"> & Partial<Pick<WebAppState, "captureState">>) => void, signal?: AbortSignal) {
    await delay(signal);
    onUpdate({ speaker: structuredClone(syntheticState.speaker) });
  }

  async deleteInterview(_id: string, signal?: AbortSignal) {
    await delay(signal);
  }

  async deleteScreenshot(_id: string, signal?: AbortSignal) {
    await delay(signal);
  }

  async submitManualAnswer(command: Parameters<InterviewAppAdapter["submitManualAnswer"]>[0], signal?: AbortSignal) {
    await delay(signal);
    const taskId = `fixture-answer-${command.idempotencyKey.replace(/[^a-zA-Z0-9-]/g, "-")}`;
    const answerText = `这是来自后端模型链路的测试回答：${command.question}`;
    return {
      question: {
        id: taskId,
        askedAt: "刚刚",
        text: command.question,
        input: "manual",
        status: "confirmed",
        advice: {
          outline: ["先直接回应问题", "结合你的真实经历展开", "用可核对的结果收尾"],
          detail: answerText,
          sourceTypes: ["简历", "JD", "知识库"],
          inference: "该建议来自测试适配器，用于模拟后端 Chat Service 返回。",
          uncertain: false,
          provenance: { selectionRevision: 0, usedSources: [] },
        },
      },
      task: {
        id: taskId,
        interviewId: command.interviewId,
        userId: syntheticState.account.id,
        billingUsageId: `live-answer:${taskId}`,
        questionId: taskId,
        revision: 1,
        status: "completed",
        question: command.question,
        completedText: answerText,
        updatedAtMs: Date.now(),
      },
    } as const;
  }

  async submitScreenshotAnswer(command: Parameters<InterviewAppAdapter["submitScreenshotAnswer"]>[0], signal?: AbortSignal) {
    await delay(signal);
    const taskId = `fixture-screenshot-${Date.now()}`;
    const answerText = `这是来自多模截图链路的测试回答：${command.instruction}`;
    return {
      question: {
        id: taskId,
        askedAt: "刚刚",
        text: command.instruction,
        input: "screenshot",
        status: "confirmed",
        advice: {
          outline: ["先识别截图题目", "再输出可直接使用的回答", "补充关键边界和注意点"],
          detail: answerText,
          sourceTypes: ["简历", "JD", "知识库"],
          inference: "该建议来自测试适配器，用于模拟后端 Screenshot Answer Service 返回。",
          uncertain: false,
          provenance: { selectionRevision: 0, usedSources: [] },
        },
      },
      task: {
        id: taskId,
        interviewId: command.interviewId,
        userId: syntheticState.account.id,
        billingUsageId: `screenshot-answer:${taskId}`,
        questionId: taskId,
        revision: 1,
        status: "completed",
        question: command.instruction,
        completedText: answerText,
        updatedAtMs: Date.now(),
      },
    } as const;
  }

  async cancelAnswer(command: CancelAnswerCommand, current: AnswerTaskSnapshot, signal?: AbortSignal) {
    await delay(signal);
    const replay = this.cancelResults.get(command.idempotencyKey);
    if (replay) return structuredClone(replay);
    const outcome = current.revision !== command.expectedRevision ? "stale-revision" : current.status === "cancelled" ? "already-cancelled" : current.status === "queued" || current.status === "generating" ? "cancelled" : "not-cancellable";
    const task: AnswerTaskSnapshot = outcome === "cancelled" ? (() => { const { partialText: _partialText, ...base } = current; return { ...base, status: "cancelled", revision: current.revision + 1, updatedAtMs: Date.now() }; })() : current;
    const result: CancelAnswerResult = { outcome, task, billingReleased: outcome === "cancelled" || outcome === "already-cancelled" };
    this.cancelResults.set(command.idempotencyKey, result);
    return structuredClone(result);
  }

  async redeemPoints(request: PointsRedemptionRequest, signal?: AbortSignal) {
    await delay(signal);
    const replay = this.redemptionRequests.get(request.idempotencyKey); if (replay) return structuredClone(replay);
    const code = request.code.trim().toUpperCase();
    if (code === "SYNTHETIC-LIMIT") return { outcome: "rate-limited", retryAfterMs: 30_000 } as const;
    if (code === "SYNTHETIC-OUTAGE") return { outcome: "temporarily-unavailable" } as const;
    if (code !== "SYNTHETIC-DEMO") return { outcome: "code-unavailable" } as const;
    if (this.redemption) { const result = { outcome: "already-redeemed-by-you", data: this.redemption } as const; this.redemptionRequests.set(request.idempotencyKey, result); return structuredClone(result); }
    const redeemedAtMs = Date.now(); const points = 120; const newBalance = syntheticState.billing.balance + points; const redemptionId = `synthetic-redemption-${redeemedAtMs}`;
    this.redemption = { redemptionId, points, newBalance, publicHint: "••••-DEMO", redeemedAtMs, ledgerEntry: { id: `synthetic-ledger-${redeemedAtMs}`, userId: syntheticState.account.id, kind: "redemption_credit", points, createdAtMs: redeemedAtMs, referenceId: redemptionId, description: "合成演示兑换积分" } };
    const result = { outcome: "redeemed", data: this.redemption } as const; this.redemptionRequests.set(request.idempotencyKey, result); return structuredClone(result);
  }

  async createCheckoutOrder(request: Parameters<InterviewAppAdapter["createCheckoutOrder"]>[0], signal?: AbortSignal): Promise<OfficialCheckoutOrder> {
    await delay(signal);
    const product = syntheticState.billing.catalog.find(item => item.id === request.productId) ?? syntheticState.billing.catalog[0]!;
    const now = Date.now();
    return {
      id: `fixture-checkout-${request.idempotencyKey}`,
      userId: syntheticState.account.id,
      product,
      amountCents: product.priceCents,
      currency: "CNY",
      channel: request.channel,
      status: "payment_pending",
      action: { kind: "redirect", url: `https://pay.mzfpay.com/xpay/epay/submit.php?out_trade_no=fixture-checkout-${request.idempotencyKey}`, expiresAtMs: now + 900_000 },
      createdAtMs: now,
      updatedAtMs: now,
    };
  }

  async getCheckoutOrder(orderId: string, signal?: AbortSignal): Promise<OfficialCheckoutOrder> {
    await delay(signal);
    const product = syntheticState.billing.catalog[0]!;
    const now = Date.now();
    return {
      id: orderId,
      userId: syntheticState.account.id,
      product,
      amountCents: product.priceCents,
      currency: "CNY",
      channel: "wechat",
      status: "payment_pending",
      action: { kind: "redirect", url: `https://pay.mzfpay.com/xpay/epay/submit.php?out_trade_no=${orderId}`, expiresAtMs: now + 900_000 },
      createdAtMs: now,
      updatedAtMs: now,
    };
  }
}

export const fixtureAdapter = new FixtureInterviewAdapter();
