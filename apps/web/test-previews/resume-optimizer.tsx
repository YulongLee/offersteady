// Test-only entry. This file is absent from production Vite inputs and never calls production or a remote service.
import "../src/legacy-browser-polyfills";
import { createRoot } from "react-dom/client";
import { App } from "../src/App";
import { optimizerCaps, optimizerCompleted, optimizerCompletedWithSummary, optimizerPartialCompleted, optimizerFactsFailed, optimizerNoEditsFailed, optimizerQueued, optimizerState } from "../src/test/resume-optimizer-fixtures";
import { previewMockQuote, previewMockSession } from "./resume-optimizer-mock-fixtures";
import type { ResumeOptimization } from "../src/resume-optimizer-client";
import experiencedMarkdown from "./resume-template-samples/experienced.md?raw";
import campusMarkdown from "./resume-template-samples/campus.md?raw";
const scenario = new URLSearchParams(location.search).get("scenario") ?? "free";
const state = optimizerState();
// This closure is the only forwarding path: a fixed, loopback-only synthetic renderer.
// Production API requests and arbitrary URLs remain blocked by the preview below.
const renderLocally = globalThis.fetch.bind(globalThis);
const templateMarkdown = scenario === "template" ? experiencedMarkdown : scenario === "template-campus" ? campusMarkdown : null;
const initialPaid = ["points", "exhausted", "balance"].includes(scenario);
let quoteChanged = false; let conflict = false; let exportFailed = false; let copyFailed = false;
const completedResult = templateMarkdown ? { ...optimizerCompleted, sourceDisplayName: scenario === "template-campus" ? "合成校园简历.md" : "合成工作经历简历.md", sourceText: templateMarkdown, initialDraftMarkdown: templateMarkdown, draftMarkdown: templateMarkdown, targetRole: scenario === "template-campus" ? "前端开发工程师" : "后端开发工程师", review: { ...optimizerCompleted.review!, dimensions: [], suggestions: [], missingFacts: [], disclaimer: "合成模板预览，评分仅作界面占位，不代表真实评估。未调用 AI。" } } : scenario === "partial" ? optimizerPartialCompleted : scenario === "legacy" ? optimizerCompleted : optimizerCompletedWithSummary;
let job: ResumeOptimization | null = ["completed", "partial", "legacy", "conflict", "export-error", "copy-error", "source-gone", "template", "template-campus"].includes(scenario) ? { ...completedResult }
  : scenario === "failed-known" ? { ...optimizerFactsFailed } : scenario === "no-effective" ? { ...optimizerNoEditsFailed }
  : scenario === "queued" ? { ...optimizerQueued, billingClass: "points", pointsCharged: 100 } : scenario === "failed" ? { ...optimizerQueued, status: "failed", billingClass: "points", pointsCharged: 100, allowanceStatus: "released", billingStatus: "released", errorCode: "resume_optimizer_provider_unavailable", errorMessage: "DO_NOT_EXPOSE_PRIVATE_PROVIDER" } : null;
let jobs: ResumeOptimization[] = job ? [job] : [];
const usage = new Map(jobs.map(item => [item.jobId, item]));
let sequence = jobs.length; let pollReads = 0;
const syncJob = () => { if (job) { jobs = [job, ...jobs.filter(item => item.jobId !== job!.jobId)]; usage.set(job.jobId, job); } };
const requests: { path: string; method: string; quote?: unknown }[] = [];
const receipt = () => { syncJob(); document.getElementById("qa-receipt")!.textContent = JSON.stringify({ syntheticOnly: true, scenario, providerCalls: 0, requests, status: job?.status, billingStatus: job?.billingStatus, dailyRemaining: caps().dailyRemaining }); };
const caps = () => {
  syncJob();
  const member = scenario !== "points" && scenario !== "balance";
  const freeUsed = [...usage.values()].filter(item => item.billingClass === "daily_pass_free" && item.billingStatus !== "released").length;
  const remaining = member && !initialPaid && !quoteChanged ? Math.max(0, 3 - freeUsed) : 0;
  const paid = !member || remaining === 0;
  const activeJob = jobs.find(item => ["queued", "running"].includes(item.status));
  const availablePoints = scenario === "balance" ? 99 : 250 - [...usage.values()].reduce((spent, item) => spent + (item.billingClass === "points" && item.billingStatus !== "released" ? item.pointsCharged : 0), 0);
  return optimizerCaps({ activeTimeMember: member, dailyRemaining: remaining, billingClass: paid ? "points" : "daily_pass_free", entryPoints: paid ? 100 : 0, availablePoints, exhausted: member && remaining === 0, canStart: (!paid || availablePoints >= 100) && !activeJob, activeJobId: activeJob?.jobId ?? null, enabled: scenario !== "disabled" });
};
const response = (data: unknown, status = 200, message = "private synthetic detail") => new Response(JSON.stringify({ requestId: "synthetic-local-preview", meta: { apiVersion: "v1", timestamp: "2026-10-18T00:00:00+08:00" }, success: status < 400, ...(status < 400 ? { data } : { error: { message, details: { errorCode: data } } }) }), { status, headers: { "Content-Type": "application/json", "Cache-Control": "private, no-store" } });
globalThis.fetch = async (input, init) => {
  const url = new URL(String(input), location.origin);
  // Development API clients default to loopback:8000. Synthesize that request too;
  // never forward either same-origin or loopback calls to an actual server.
  const localApi = ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname) && url.pathname.startsWith("/api/v1/");
  if (url.origin !== location.origin && !localApi) throw new Error("External network is disabled in synthetic preview.");
  const method = init?.method ?? "GET"; const body = init?.body ? JSON.parse(String(init.body)) : {};
  requests.push({ path: url.pathname, method, ...(url.pathname.endsWith("/jobs") && method === "POST" ? { quote: { quotedQuotaDay: body.quotedQuotaDay, quotedBillingClass: body.quotedBillingClass, quotedPoints: body.quotedPoints, confirmPointsCharge: body.confirmPointsCharge, confirmProcessing: body.confirmProcessing } } : {}) }); receipt();
  // Explicit existing capability comes before the generic disabled fallback.
  if (url.pathname === "/api/v1/mock-interviews/capabilities") return response({ enabled: true });
  if (url.pathname === "/api/v1/mock-interviews") {
    if (method === "GET") return response({ sessions: [previewMockSession], quote: previewMockQuote });
    return response("synthetic_preview_no_live_interview", 422, "本地合成预览不创建真实面试；请在正式服务中体验出题和收音。");
  }
  if (url.pathname === `/api/v1/mock-interviews/${previewMockSession.sessionId}` && method === "GET") return response(previewMockSession);
  if (url.pathname === "/api/v1/resume-optimizer/capabilities") return response(caps());
  if (url.pathname === "/api/v1/resume-optimizer/jobs") {
    if (method === "POST") {
      if (scenario === "quote-changed" && !quoteChanged) { quoteChanged = true; return response("resume_optimizer_quote_changed", 409); }
      const current = caps();
      if (body.quotedBillingClass !== current.billingClass || body.quotedPoints !== current.entryPoints) return response("resume_optimizer_quote_changed", 409);
      if (!body.confirmProcessing || (current.billingClass === "points" && !body.confirmPointsCharge)) return response("resume_optimizer_points_confirmation_required", 422);
      if (!current.canStart) return response("resume_optimizer_insufficient_balance", 402);
      job = { ...optimizerQueued, jobId: `${optimizerQueued.jobId}-${++sequence}`, sourceDocumentId: body.sourceDocumentId, sourceVersionId: body.sourceVersionId, targetRole: body.targetRole ?? "", hasJd: Boolean(body.jdText || body.jdDocumentId), jdText: body.jdText ?? "", jdDocumentId: body.jdDocumentId ?? null, jdVersionId: body.jdVersionId ?? null, billingClass: body.quotedBillingClass, pointsCharged: body.quotedPoints }; pollReads = 0; receipt(); return response(job);
    } syncJob(); return response({ jobs });
  }
  if (url.pathname.endsWith("/cancel")) { job = { ...job!, status: "cancelled", allowanceStatus: "released", billingStatus: "released" }; receipt(); return response(job); }
  if (url.pathname.endsWith("/draft")) {
    if (scenario === "conflict" && !conflict) { conflict = true; job = { ...job!, revision: 2, draftMarkdown: "# 已在另一页面保存的合成稿" }; return response("resume_optimizer_revision_conflict", 409); }
    job = { ...job!, revision: job!.revision + 1, draftMarkdown: body.markdown }; receipt(); return response(job);
  }
  if (url.pathname.endsWith("/save-as")) {
    if (scenario === "copy-error" && !copyFailed) { copyFailed = true; return response("resume_optimizer_storage_unavailable", 503); }
    job = { ...job!, savedDocumentId: "synthetic-independent", savedVersionId: "synthetic-independent-v1" }; return response({ document: { documentId: "synthetic-independent", documentVersionId: "synthetic-independent-v1" } });
  }
  if (/^\/api\/v1\/resume-optimizer\/jobs\/[^/]+\/export$/.test(url.pathname)) {
    if (scenario === "source-gone") return response("resume_optimizer_not_found", 404);
    const exportId = url.pathname.split("/").at(-2);
    const saved = jobs.find(item => item.jobId === exportId);
    if (!saved) return response("resume_optimizer_not_found", 404);
    if (method !== "GET" || url.searchParams.get("factsConfirmed") !== "true") return response("resume_optimizer_invalid_draft", 422);
    if (url.searchParams.get("expectedRevision") !== String(saved.revision)) return response("resume_optimizer_revision_conflict", 409);
    if (saved.status !== "completed" || !saved.draftMarkdown?.trim()) return response("resume_optimizer_not_completed", 409);
    if (scenario === "export-error" && !exportFailed) { exportFailed = true; return response("resume_optimizer_export_unavailable", 422); }
    const format = url.searchParams.get("format");
    if (format !== "pdf" && format !== "docx") return response("resume_optimizer_export_unavailable", 422);
    try {
      return await renderLocally("http://127.0.0.1:5192/render", {
        method: "POST", headers: { "Content-Type": "application/json", "X-OfferSteady-Synthetic-Preview": "resume-template-20261018" },
        body: JSON.stringify({ markdown: saved.draftMarkdown, format }), credentials: "omit", cache: "no-store", redirect: "error",
      });
    } catch { return response("resume_optimizer_export_unavailable", 422, "请启动本地合成文件渲染服务后重试下载。"); }
  }
  if (url.pathname.startsWith("/api/v1/resume-optimizer/jobs/")) {
    const id = url.pathname.split("/").at(-1); const found = jobs.find(item => item.jobId === id);
    if (!found) return response("resume_optimizer_not_found", 404);
    if (method === "DELETE") { if (["queued", "running"].includes(found.status)) usage.set(found.jobId, { ...found, status: "cancelled", allowanceStatus: "released", billingStatus: "released" }); jobs = jobs.filter(item => item.jobId !== id); if (job?.jobId === id) job = null; receipt(); return response({ deleted: true }); }
    job = found;
    if (scenario !== "queued" && job.status === "queued" && ++pollReads >= 2) { job = { ...completedResult, ...job, status: "completed", allowanceStatus: "settled", billingStatus: "settled", review: completedResult.review ? { ...completedResult.review, roleMatchingAssessed: job.hasJd } : null, sourceText: completedResult.sourceText, initialDraftMarkdown: completedResult.initialDraftMarkdown, draftMarkdown: completedResult.draftMarkdown, errorCode: null, errorMessage: null, completedAtMs: Date.now() }; receipt(); }
    return response(job);
  }
  if (url.pathname === "/api/v1/billing/state") return response({ ...state.billing, balance: caps().availablePoints });
  if (url.pathname === "/api/v1/web/state") return response(state);
  if (url.pathname.endsWith("/capabilities")) return response({ enabled: false });
  if (url.pathname.includes("partner-program") || url.pathname.includes("referral")) return response({ enabled: false });
  return response("synthetic_route_not_supported", 404);
};
window.history.replaceState({}, "", `/app/resume-optimizer?source=synthetic-resume&syntheticScenario=${encodeURIComponent(scenario)}`);
receipt(); createRoot(document.getElementById("root")!).render(<App initialAuthenticated initialState={state} />);
