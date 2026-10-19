import { authClient } from "./auth-client";
import { withBaseUrl } from "./api-client";
import { readRuntimeConfig } from "./runtime-config";

export interface ResumeOptimizerCapabilities {
  readonly enabled: boolean; readonly eligible: boolean; readonly dailyLimit: number; readonly dailyRemaining: number;
  readonly quotaDay: string; readonly timezone: "UTC"; readonly resetAtMs: number; readonly memberRequired: boolean;
  readonly exhausted: boolean; readonly activeJobId: string | null;
  readonly limits: { readonly resumeCharacters: number; readonly jdCharacters: number; readonly targetRoleCharacters: number; readonly draftCharacters: number };
  readonly exports: readonly ("docx" | "pdf")[];
}
export interface ResumeEvidence { readonly source: "resume" | "jd"; readonly quote: string }
export interface ResumeReview {
  readonly overallScore: number; readonly roleMatchingAssessed: boolean;
  readonly dimensions: readonly { readonly key: string; readonly score: number; readonly reason: string; readonly evidence: readonly ResumeEvidence[] }[];
  readonly suggestions: readonly { readonly priority: "high" | "medium" | "low"; readonly title: string; readonly explanation: string; readonly recommendation: string; readonly evidence: readonly ResumeEvidence[] }[];
  readonly missingFacts: readonly string[]; readonly disclaimer: string;
}
export interface ResumeOptimizationSummary {
  readonly jobId: string; readonly status: "queued" | "running" | "completed" | "failed" | "cancelled"; readonly revision: number;
  readonly sourceDocumentId: string; readonly sourceVersionId: string; readonly sourceDisplayName: string; readonly targetRole: string;
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
  readonly quotedQuotaDay: string; readonly confirmProcessing: true;
}
const messages: Readonly<Record<string, string>> = {
  resume_optimizer_disabled: "Resume Optimizer is temporarily unavailable. Your existing tools are unaffected.",
  resume_optimizer_membership_required: "An active paid time membership is required, including a one-day plan. Upgrade to start a review.",
  resume_optimizer_daily_limit: "Today's optimization is already used or reserved. Try again after 00:00 UTC.",
  resume_optimizer_busy: "The optimizer is busy. Please try again shortly.",
  resume_optimizer_not_found: "This optimization is no longer available. Its source may have been deleted.",
  resume_optimizer_source_unavailable: "The selected material changed or is not ready. Refresh your materials and select its current version.",
  resume_optimizer_source_markup_unsupported: "This resume or job description has unsupported formatting. Upload a plain-text or Markdown version without HTML markup, then try again. Your daily review has not been used.",
  resume_optimizer_idempotency_conflict: "The submission changed. Review the inputs and submit again.",
  resume_optimizer_revision_conflict: "A newer draft was saved elsewhere. Your local edits are kept. Reload the saved draft before continuing.",
  resume_optimizer_not_completed: "Wait for the review to finish before editing or downloading.",
  resume_optimizer_invalid_draft: "Use nonempty plain text or Markdown within the character limit. HTML and scripts are not supported.",
  resume_optimizer_provider_unconfigured: "Resume Optimizer is temporarily unavailable. Please try again later.",
  resume_optimizer_export_unavailable: "We couldn’t prepare this format. Try Word, or remove unsupported characters and retry. Your saved draft is unchanged.",
  resume_optimizer_quote_changed: "The UTC day changed. Review your refreshed allowance and confirm again.",
};
export class ResumeOptimizerError extends Error {
  constructor(readonly code: string, readonly status: number) {
    super(messages[code] ?? (status === 401 ? "Your session has expired. Sign in again." : status >= 500 ? "The optimizer is temporarily unavailable. Please try again." : "The request could not be completed. Refresh and try again."));
    this.name = "ResumeOptimizerError";
  }
}
export class BackendResumeOptimizerClient {
  constructor(private readonly baseUrl: string, private readonly fetchImpl: typeof fetch = (input, init) => globalThis.fetch(input, init)) {}
  private async response(path: string, init: RequestInit = {}, signal?: AbortSignal): Promise<Response> {
    const session = authClient.readStoredSession();
    const headers = new Headers(init.headers);
    if (session) headers.set("Authorization", `Bearer ${session.accessToken}`);
    if (typeof init.body === "string") headers.set("Content-Type", "application/json");
    headers.set("Accept", path.includes("/export?") ? "application/octet-stream" : "application/json");
    let response: Response;
    try { response = await this.fetchImpl(withBaseUrl(this.baseUrl, `/api/v1/resume-optimizer${path}`), { ...init, headers, cache: "no-store", ...(signal ? { signal } : {}) }); }
    catch (error) { if (signal?.aborted || (error instanceof DOMException && error.name === "AbortError")) throw error; throw new Error("Unable to connect to the optimizer. Check your connection and try again."); }
    if (!response.ok) {
      let code = "";
      try { const payload = await response.json(); code = payload?.error?.details?.errorCode ?? payload?.error?.code ?? ""; } catch { /* No personal response content is exposed. */ }
      throw new ResumeOptimizerError(code, response.status);
    }
    return response;
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
    if (response.headers.get("Content-Type")?.split(";")[0]?.trim().toLowerCase() !== expectedMime) throw new Error("The download was not a valid resume file. Please try again.");
    const blob = await response.blob();
    const prefix = new Uint8Array(await blob.slice(0, 5).arrayBuffer());
    const validSignature = format === "pdf" ? new TextDecoder().decode(prefix) === "%PDF-" : prefix[0] === 80 && prefix[1] === 75 && prefix[2] === 3 && prefix[3] === 4;
    if (!validSignature) throw new Error("The download was not a valid resume file. Please try again.");
    const encoded = response.headers.get("Content-Disposition")?.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
    let filename = `Optimized resume.${format}`;
    if (encoded) { try { filename = decodeURIComponent(encoded); } catch { /* Use a fixed safe fallback. */ } }
    filename = filename.replace(/[\u0000-\u001f\u007f\u202a-\u202e\u2066-\u2069\\/]/g, "-").slice(0, 180);
    if (!filename.toLowerCase().endsWith(`.${format}`)) filename = `Optimized resume.${format}`;
    return { blob, filename };
  }
}
export const resumeOptimizerClient = new BackendResumeOptimizerClient(readRuntimeConfig(import.meta.env).apiBaseUrl);
export function downloadOptimizedResume({ blob, filename }: { readonly blob: Blob; readonly filename: string }) {
  const href = URL.createObjectURL(blob); const anchor = document.createElement("a");
  try { anchor.href = href; anchor.download = filename; anchor.style.display = "none"; document.body.appendChild(anchor); anchor.click(); }
  finally { anchor.remove(); window.setTimeout(() => URL.revokeObjectURL(href), 1000); }
}
