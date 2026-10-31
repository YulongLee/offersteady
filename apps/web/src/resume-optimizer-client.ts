import { authClient } from "./auth-client";
import { withBaseUrl } from "./api-client";
import { readRuntimeConfig } from "./runtime-config";
import { beginStateMutation } from "./state-read-scope";

export interface ResumeOptimizerCapabilities {
  readonly enabled: boolean; readonly eligible: boolean; readonly dailyLimit: number; readonly dailyRemaining: number;
  readonly quotaDay: string; readonly timezone: "Asia/Shanghai"; readonly resetAtMs: number; readonly memberRequired: boolean;
  readonly activeTimeMember: boolean; readonly nowMs: number; readonly billingClass: "daily_pass_free" | "points"; readonly entryPoints: 0 | 100; readonly availablePoints: number; readonly canStart: boolean;
  readonly exhausted: boolean; readonly activeJobId: string | null;
  readonly limits: { readonly resumeCharacters: number; readonly jdCharacters: number; readonly targetRoleCharacters: number; readonly draftCharacters: number };
  readonly exports: readonly ("docx" | "pdf")[];
}
export interface ResumeEvidence { readonly source: "resume" | "jd"; readonly quote: string }
export interface ResumeEditSummary {
  readonly proposedCount: number; readonly appliedCount: number; readonly retainedCount: number;
  readonly retainedReasonCounts: { readonly factCheck: number; readonly sourceQuote: number; readonly overlap: number; readonly unchanged: number };
}
export interface ResumeReview {
  readonly overallScore: number; readonly roleMatchingAssessed: boolean;
  readonly dimensions: readonly { readonly key: string; readonly score: number; readonly reason: string; readonly evidence: readonly ResumeEvidence[] }[];
  readonly suggestions: readonly { readonly priority: "high" | "medium" | "low"; readonly title: string; readonly explanation: string; readonly recommendation: string; readonly evidence: readonly ResumeEvidence[] }[];
  readonly missingFacts: readonly string[]; readonly disclaimer: string;
  readonly editSummary?: ResumeEditSummary;
}
export interface ResumeOptimizationSummary {
  readonly jobId: string; readonly status: "queued" | "running" | "completed" | "failed" | "cancelled"; readonly revision: number;
  readonly sourceDocumentId: string; readonly sourceVersionId: string; readonly sourceDisplayName: string; readonly targetRole: string;
  readonly billingClass: "daily_pass_free" | "points"; readonly pointsCharged: 0 | 100; readonly billingStatus: "reserved" | "settled" | "released";
  readonly hasJd: boolean; readonly quotaDay: string; readonly allowanceStatus: "reserved" | "settled" | "released";
  readonly createdAtMs: number; readonly updatedAtMs: number; readonly completedAtMs: number | null;
  readonly errorCode: string | null; readonly errorMessage: string | null; readonly savedDocumentId: string | null; readonly savedVersionId: string | null;
}
export interface ResumeOptimization extends ResumeOptimizationSummary {
  readonly sourceText: string; readonly jdText: string; readonly jdDocumentId: string | null; readonly jdVersionId: string | null;
  readonly review: ResumeReview | null; readonly initialDraftMarkdown: string | null; readonly draftMarkdown: string | null;
  readonly promptVersion: string; readonly scoreVersion: string;
}
export interface CreateResumeOptimization {
  readonly idempotencyKey: string; readonly sourceDocumentId: string; readonly sourceVersionId: string; readonly targetRole: string;
  readonly jdDocumentId: string | null; readonly jdVersionId: string | null; readonly jdText: string;
  readonly quotedQuotaDay: string; readonly quotedBillingClass: "daily_pass_free" | "points"; readonly quotedPoints: 0 | 100; readonly confirmPointsCharge: boolean; readonly confirmProcessing: true;
}
export const resumeOptimizerMessages: Readonly<Record<string, string>> = {
  resume_optimizer_insufficient_balance: "可用积分不足 100，请充值或开通时间会员后刷新报价。",
  resume_optimizer_points_confirmation_required: "请明确确认本次 100 积分费用后再开始。",
  resume_optimizer_disabled: "简历优化暂时不可用，请稍后重试。",
  resume_optimizer_membership_required: "请刷新本次优化报价后重试。",
  resume_optimizer_daily_limit: "今日免费次数已用完，请刷新报价后确认是否使用积分。",
  resume_optimizer_busy: "简历优化正在忙碌，请稍后重试。",
  resume_optimizer_not_found: "这次优化已不可用，源资料可能已删除。",
  resume_optimizer_source_unavailable: "所选资料已变化或尚未解析完成，请刷新资料并选择当前版本。",
  resume_optimizer_source_markup_unsupported: "简历或岗位描述含不支持的格式，请上传不含 HTML 标记的纯文本或 Markdown 版本后重试。本次未扣费或占用免费次数。",
  resume_optimizer_idempotency_conflict: "提交内容已变化，请核对输入后重新提交。",
  resume_optimizer_revision_conflict: "其他页面已保存更新版本。已保留你的本地编辑，请重新载入已保存稿后继续。",
  resume_optimizer_not_completed: "请等待优化完成后再编辑或下载。",
  resume_optimizer_invalid_draft: "请填写字数范围内的纯文本或 Markdown，不支持 HTML 和脚本。",
  resume_optimizer_provider_unconfigured: "简历优化暂时不可用，请稍后重试。",
  resume_optimizer_export_unavailable: "暂时无法生成此格式。可尝试 Word，或移除不支持的字符后重试。已保存稿不受影响。",
  resume_optimizer_quote_changed: "本次报价已变化，请核对最新免费次数和积分费用后重新确认。",
};
const retryOriginal = "原简历无需重新上传，请稍后重试。";
const refundedSuffix = "本次积分或免费次数已退还。";
const genericJobFailure = "未生成可用优化稿，原简历保留。";
// These are reviewed local constants, not text received from the provider.
const safeJobFailureMessages: Readonly<Record<string, readonly string[]>> = {
  invalid_output: [
    "AI 返回的结果超过处理上限，未能生成优化稿。" + retryOriginal,
    "AI 返回的结果格式不完整，未能生成优化稿。" + retryOriginal,
    "AI 返回的结果被截断，未能生成完整优化稿。" + retryOriginal,
    "AI 未正常完成生成，本次没有可用优化稿。" + retryOriginal,
    "AI 返回的结果存在重复字段，未能可靠读取。" + retryOriginal,
    "AI 返回的评分维度不完整，未能生成可靠评估。" + retryOriginal,
    "AI 返回的依据与原简历或岗位描述不一致，已停止生成。" + retryOriginal,
    "AI 未按要求提供中文说明，未能生成可用结果。" + retryOriginal,
    "AI 返回的待补充说明不符合要求，未能生成可用结果。" + retryOriginal,
    "AI 返回的改写位置无法与原简历唯一对应，已停止生成。" + retryOriginal,
    "AI 改写未通过原文事实检查，已停止生成。" + retryOriginal,
    "AI 返回的修改位置相互重叠，未能安全合并优化稿。" + retryOriginal,
    "AI 优化稿未通过完整性检查，未能安全交付。" + retryOriginal,
    "本次未生成可安全应用的有效修改，原简历已保留。",
  ],
  provider_timeout: ["AI 服务响应超时，请稍后重试，原简历无需重新上传。", "简历优化处理超时，请稍后重试，原简历无需重新上传。"],
  provider_unavailable: ["AI 服务暂时不可用，请稍后重试，原简历无需重新上传。"],
  provider_unconfigured: ["简历优化的 AI 服务尚未就绪，请联系支持人员检查服务配置。"],
  interrupted: ["简历优化处理已中断，请稍后重新发起，原简历无需重新上传。", "简历优化处理遇到内部错误，请稍后重试；若仍失败请联系支持人员。", "简历优化状态暂时无法处理，请稍后重试；若仍失败请联系支持人员。"],
};
export function resumeOptimizationFailureMessage(job: Pick<ResumeOptimizationSummary, "status" | "errorCode" | "errorMessage" | "allowanceStatus">): string {
  if (typeof job.errorCode !== "string") return genericJobFailure;
  const code = job.errorCode ?? "";
  const fallback = Object.prototype.hasOwnProperty.call(resumeOptimizerMessages, code) ? resumeOptimizerMessages[code]! : genericJobFailure;
  if (job.status !== "failed" || !["reserved", "settled", "released"].includes(job.allowanceStatus)
    || !Object.prototype.hasOwnProperty.call(safeJobFailureMessages, code)) return fallback;
  return safeJobFailureMessages[code]!.find(message => job.errorMessage === message
    || (job.allowanceStatus === "released" && job.errorMessage === message + refundedSuffix)) ?? fallback;
}

const exactObject = (value: unknown, keys: readonly string[]): value is Record<string, unknown> => value !== null && typeof value === "object"
  && !Array.isArray(value) && Object.keys(value).length === keys.length && keys.every(key => Object.prototype.hasOwnProperty.call(value, key));
const editCount = (value: unknown): value is number => typeof value === "number" && Number.isInteger(value) && value >= 0 && value <= 24;
export function resumeInitialDraftSummary(job: Pick<ResumeOptimization, "status" | "review">): string | null {
  if (job.status !== "completed") return null;
  const summary: unknown = job.review?.editSummary;
  if (!exactObject(summary, ["proposedCount", "appliedCount", "retainedCount", "retainedReasonCounts"])) return null;
  const { proposedCount, appliedCount, retainedCount, retainedReasonCounts } = summary;
  if (!editCount(proposedCount) || !editCount(appliedCount) || !editCount(retainedCount) || appliedCount < 1 || proposedCount !== appliedCount + retainedCount
    || !exactObject(retainedReasonCounts, ["factCheck", "sourceQuote", "overlap", "unchanged"])) return null;
  const reasons = Object.values(retainedReasonCounts);
  if (!reasons.every(editCount) || reasons.reduce((sum, value) => sum + value, 0) !== retainedCount) return null;
  return retainedCount ? `AI 初稿：已采用 ${appliedCount} 项改写，${retainedCount} 项改写未采用，请核实。` : `AI 初稿：已采用 ${appliedCount} 项改写。`;
}
export class ResumeOptimizerError extends Error {
  constructor(readonly code: string, readonly status: number) {
    super(resumeOptimizerMessages[code] ?? (status === 401 ? "登录已过期，请重新登录。" : status >= 500 ? "简历优化暂时不可用，请稍后重试。" : "操作未完成，请刷新后重试。"));
    this.name = "ResumeOptimizerError";
  }
}
export class BackendResumeOptimizerClient {
  constructor(private readonly baseUrl: string, private readonly fetchImpl: typeof fetch = (input, init) => globalThis.fetch(input, init)) {}
  private async response(path: string, init: RequestInit = {}, signal?: AbortSignal): Promise<Response> {
    const finishMutation = beginStateMutation(`/api/v1/resume-optimizer${path}`, init.method);
    try {
      const session = authClient.readStoredSession();
      const headers = new Headers(init.headers);
      if (session) headers.set("Authorization", `Bearer ${session.accessToken}`);
      if (typeof init.body === "string") headers.set("Content-Type", "application/json");
      headers.set("Accept", path.includes("/export?") ? "application/octet-stream" : "application/json");
      let response: Response;
      try { response = await this.fetchImpl(withBaseUrl(this.baseUrl, `/api/v1/resume-optimizer${path}`), { ...init, headers, cache: "no-store", ...(signal ? { signal } : {}) }); }
      catch (error) { if (signal?.aborted || (error instanceof DOMException && error.name === "AbortError")) throw error; throw new Error("无法连接简历优化服务，请检查网络后重试。"); }
      if (!response.ok) {
        let code = "";
        try { const payload = await response.json(); code = payload?.error?.details?.errorCode ?? payload?.error?.code ?? ""; } catch { /* No personal response content is exposed. */ }
        throw new ResumeOptimizerError(code, response.status);
      }
      return response;
    } finally {
      finishMutation();
    }
  }
  private async json<T>(path: string, init: RequestInit = {}, signal?: AbortSignal): Promise<T> {
    const payload = await (await this.response(path, init, signal)).json();
    if (payload.success === false || payload.data == null) throw new ResumeOptimizerError(payload?.error?.details?.errorCode ?? "", 500);
    return payload.data as T;
  }
  capabilities(signal?: AbortSignal) { return this.json<ResumeOptimizerCapabilities>("/capabilities", {}, signal); }
  list(signal?: AbortSignal) { return this.json<{ readonly jobs: readonly ResumeOptimizationSummary[] }>("/jobs", {}, signal); }
  get(id: string, signal?: AbortSignal) { return this.json<ResumeOptimization>(`/jobs/${encodeURIComponent(id)}`, {}, signal); }
  create(input: CreateResumeOptimization, signal?: AbortSignal) { return this.json<ResumeOptimization>("/jobs", { method: "POST", body: JSON.stringify(input) }, signal); }
  cancel(id: string, signal?: AbortSignal) { return this.json<ResumeOptimization>(`/jobs/${encodeURIComponent(id)}/cancel`, { method: "POST" }, signal); }
  remove(id: string, signal?: AbortSignal) { return this.json<{ readonly deleted: boolean }>(`/jobs/${encodeURIComponent(id)}`, { method: "DELETE" }, signal); }
  saveDraft(id: string, expectedRevision: number, markdown: string, signal?: AbortSignal) { return this.json<ResumeOptimization>(`/jobs/${encodeURIComponent(id)}/draft`, { method: "PATCH", body: JSON.stringify({ expectedRevision, markdown }) }, signal); }
  saveAs(id: string, expectedRevision: number, signal?: AbortSignal) { return this.json<{ readonly document: { readonly documentId: string; readonly documentVersionId: string } }>(`/jobs/${encodeURIComponent(id)}/save-as`, { method: "POST", body: JSON.stringify({ expectedRevision, confirmIndependentCopy: true, factsConfirmed: true }) }, signal); }
  async download(id: string, format: "docx" | "pdf", expectedRevision: number, signal?: AbortSignal) {
    const response = await this.response(`/jobs/${encodeURIComponent(id)}/export?${new URLSearchParams({ format, expectedRevision: String(expectedRevision), factsConfirmed: "true" })}`, {}, signal);
    const expectedMime = format === "pdf" ? "application/pdf" : "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
    if (response.headers.get("Content-Type")?.split(";")[0]?.trim().toLowerCase() !== expectedMime) throw new Error("未收到有效的简历文件，请重试下载。");
    const blob = await response.blob();
    const prefix = new Uint8Array(await blob.slice(0, 5).arrayBuffer());
    const validSignature = format === "pdf" ? new TextDecoder().decode(prefix) === "%PDF-" : prefix[0] === 80 && prefix[1] === 75 && prefix[2] === 3 && prefix[3] === 4;
    if (!validSignature) throw new Error("未收到有效的简历文件，请重试下载。");
    const encoded = response.headers.get("Content-Disposition")?.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
    let filename = `优化后的简历.${format}`;
    if (encoded) { try { filename = decodeURIComponent(encoded); } catch { /* Use a fixed safe fallback. */ } }
    filename = filename.replace(/[\u0000-\u001f\u007f\u202a-\u202e\u2066-\u2069\\/]/g, "-").slice(0, 180);
    if (!filename.toLowerCase().endsWith(`.${format}`)) filename = `优化后的简历.${format}`;
    return { blob, filename };
  }
}
export const resumeOptimizerClient = new BackendResumeOptimizerClient(readRuntimeConfig(import.meta.env).apiBaseUrl);
export function downloadOptimizedResume({ blob, filename }: { readonly blob: Blob; readonly filename: string }) {
  const href = URL.createObjectURL(blob); const anchor = document.createElement("a");
  try { anchor.href = href; anchor.download = filename; anchor.style.display = "none"; document.body.appendChild(anchor); anchor.click(); }
  finally { anchor.remove(); window.setTimeout(() => URL.revokeObjectURL(href), 1000); }
}
