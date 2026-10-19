import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { detectMaterialUploadFormat, materialUploadAccept, type ContextLibrarySource } from "@offersteady/protocol";
import type { WebAppState } from "./domain";
import { routes } from "./routes";
import { interviewAppAdapter } from "./app-adapter";
import { materialUploadAdapter } from "./material-upload-adapter";
import { pollLibraryDocumentUntilSettled } from "./library-processing-polling";
import { downloadOptimizedResume, resumeOptimizerClient, ResumeOptimizerError, type ResumeEvidence, type ResumeOptimization, type ResumeOptimizationSummary, type ResumeOptimizerCapabilities } from "./resume-optimizer-client";
import "./resume-optimizer.css";

interface Props { readonly state: WebAppState; readonly setState: Dispatch<SetStateAction<WebAppState>> }
const unfinished = (job: ResumeOptimizationSummary | null) => Boolean(job && (job.status === "queued" || job.status === "running"));
const ready = (source: ContextLibrarySource) => source.status === "ready" && source.syncStatus !== "missing_artifacts" && source.selectable !== false && Boolean(source.documentVersionId);
const labels: Readonly<Record<string, string>> = { completeness: "Completeness", impact: "Evidence & impact", clarity: "Clarity", structure: "Structure", roleMatch: "Role match" };
const statusLabels = { queued: "Queued", running: "Reviewing your resume", completed: "Ready", failed: "Review failed", cancelled: "Cancelled" };
const safeMessage = (error: unknown) => error instanceof Error && !/[\u3400-\u9fff]/u.test(error.message) ? error.message : "The request could not be completed. Please try again.";
const readableUtcDay = (time: number) => new Intl.DateTimeFormat("en", { dateStyle: "medium", timeZone: "UTC" }).format(time);
const readableDate = (time: number) => new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(time);
export const RESUME_OPTIMIZER_POLL_LIMIT = 120;

function Evidence({ items }: { readonly items: readonly ResumeEvidence[] }) {
  return <div className="resume-evidence">{items.map((item, i) => <blockquote key={i}><small>{item.source === "jd" ? "Parsed job description" : "Parsed resume"}</small><p>{item.quote}</p></blockquote>)}</div>;
}

export function ResumeOptimizerPage({ state, setState }: Props) {
  const [params] = useSearchParams();
  const [capabilities, setCapabilities] = useState<ResumeOptimizerCapabilities | null>(null);
  const [history, setHistory] = useState<readonly ResumeOptimizationSummary[]>([]);
  const [job, setJob] = useState<ResumeOptimization | null>(null);
  const [sourceId, setSourceId] = useState(params.get("source") ?? "");
  const [targetRole, setTargetRole] = useState("");
  const [jdMode, setJdMode] = useState<"none" | "text" | "material">("none");
  const [jdId, setJdId] = useState("");
  const [jdText, setJdText] = useState("");
  const [processingConfirmed, setProcessingConfirmed] = useState(false);
  const [factsConfirmed, setFactsConfirmed] = useState(false);
  const [copyConfirmed, setCopyConfirmed] = useState(false);
  const [draft, setDraft] = useState("");
  const [conflict, setConflict] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [operation, setOperation] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [pollPaused, setPollPaused] = useState(false);
  const lifetime = useRef<AbortController | null>(null);
  const busy = useRef(false);
  const loadGeneration = useRef(0);
  const createKey = useRef<{ fingerprint: string; key: string } | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const sources = state.librarySources.filter(item => item.ownerUserId === state.account.id && item.kind === "resume" && item.status !== "deleted");
  const jds = state.librarySources.filter(item => item.ownerUserId === state.account.id && item.kind === "jd" && item.status !== "deleted");
  const source = sources.find(item => item.id === sourceId || item.documentId === sourceId);
  const selectedJd = jds.find(item => item.id === jdId);
  const dirty = Boolean(job?.status === "completed" && draft !== job.draftMarkdown);
  const active = unfinished(job) || Boolean(capabilities?.activeJobId);
  const signal = () => lifetime.current?.signal;
  const stillHere = () => Boolean(lifetime.current && !lifetime.current.signal.aborted);
  const adopt = (next: ResumeOptimization, replaceDraft = true) => {
    setJob(next); setPollPaused(false);
    setHistory(items => [next, ...items.filter(item => item.jobId !== next.jobId)].slice(0, 30));
    if (replaceDraft) { setDraft(next.draftMarkdown ?? ""); setConflict(false); setFactsConfirmed(false); setCopyConfirmed(false); }
  };
  const refreshMetadata = async () => {
    const currentSignal = signal();
    const [caps, list] = await Promise.all([resumeOptimizerClient.capabilities(currentSignal), resumeOptimizerClient.list(currentSignal)]);
    if (currentSignal?.aborted || !stillHere()) return;
    setCapabilities(caps); setHistory(list.jobs);
    return caps;
  };
  const loadJob = async (id: string) => {
    const generation = ++loadGeneration.current;
    const next = await resumeOptimizerClient.get(id, signal());
    if (stillHere() && generation === loadGeneration.current) adopt(next);
  };
  const initialize = async () => {
    setInitialLoading(true); setError("");
    try {
      const caps = await resumeOptimizerClient.capabilities(signal());
      if (!stillHere()) return;
      setCapabilities(caps);
      if (caps.enabled) {
        const list = await resumeOptimizerClient.list(signal());
        if (!stillHere()) return;
        setHistory(list.jobs);
        if (caps.activeJobId) await loadJob(caps.activeJobId);
      }
    } catch (reason) { if (stillHere()) setError(safeMessage(reason)); }
    finally { if (stillHere()) setInitialLoading(false); }
  };
  useEffect(() => {
    const controller = new AbortController(); lifetime.current = controller;
    void initialize();
    return () => { controller.abort(); loadGeneration.current += 1; lifetime.current = null; };
  }, []);

  useEffect(() => { setProcessingConfirmed(false); }, [source?.documentVersionId, selectedJd?.documentVersionId]);

  useEffect(() => {
    if (!job || !unfinished(job) || pollPaused) return;
    const controller = new AbortController();
    const abort = () => controller.abort();
    lifetime.current?.signal.addEventListener("abort", abort, { once: true });
    const generation = loadGeneration.current;
    let timer: number | undefined; let attempts = 0;
    const poll = async () => {
      try {
        const next = await resumeOptimizerClient.get(job.jobId, controller.signal);
        if (controller.signal.aborted || generation !== loadGeneration.current) return;
        setJob(next); setHistory(items => items.map(item => item.jobId === next.jobId ? next : item));
        if (!unfinished(next)) { adopt(next); await refreshMetadata(); return; }
        attempts += 1;
        if (attempts >= RESUME_OPTIMIZER_POLL_LIMIT) { setPollPaused(true); setNotice("Your review is still processing. Automatic checks are paused; use Check status to see the latest result."); return; }
        timer = window.setTimeout(() => void poll(), 2000);
      } catch (reason) {
        if (controller.signal.aborted || generation !== loadGeneration.current) return;
        setPollPaused(true); setError(safeMessage(reason));
        if (reason instanceof ResumeOptimizerError && reason.status === 404) { setJob(null); setDraft(""); setFactsConfirmed(false); void refreshMetadata().catch(() => undefined); }
      }
    };
    timer = window.setTimeout(() => void poll(), 2000);
    return () => { controller.abort(); if (timer !== undefined) window.clearTimeout(timer); lifetime.current?.signal.removeEventListener("abort", abort); };
  }, [job?.jobId, job?.status, pollPaused]);

  useEffect(() => {
    if (!capabilities?.enabled) return;
    const delay = Math.max(1000, Math.min(capabilities.resetAtMs - Date.now() + 1000, 2_147_000_000));
    const timer = window.setTimeout(() => { void refreshMetadata().catch(reason => { if (stillHere()) setError(safeMessage(reason)); }); }, delay);
    return () => window.clearTimeout(timer);
  }, [capabilities?.resetAtMs, capabilities?.enabled]);

  const run = async (name: string, action: () => Promise<void>) => {
    if (busy.current) return;
    busy.current = true; setOperation(name); setError(""); setNotice("");
    try { await action(); }
    catch (reason) { if (stillHere()) setError(safeMessage(reason)); }
    finally { busy.current = false; if (stillHere()) setOperation(""); }
  };
  const refreshMaterials = async (requestSignal = signal()) => {
    const next = await interviewAppAdapter.loadState(requestSignal, { force: true });
    if (stillHere() && !requestSignal?.aborted) setState(next);
    return next;
  };
  const upload = (file: File) => void run("upload", async () => {
    if (!detectMaterialUploadFormat(file.name)) throw new Error("Choose a PDF, DOCX, DOC, TXT or Markdown resume.");
    if (file.size > 20 * 1024 * 1024) throw new Error("Choose a resume no larger than 20 MB.");
    const uploaded = await materialUploadAdapter.uploadResume(state.account.id, file, signal());
    if (!stillHere()) return;
    await refreshMaterials();
    if (!stillHere()) return;
    setSourceId(uploaded.source.sourceId); setProcessingConfirmed(false);
    setNotice("Your resume is uploaded and processing. It can be reviewed when processing finishes.");
    const result = await pollLibraryDocumentUntilSettled({ documentId: uploaded.source.sourceId, signal: signal()!, loadState: refreshMaterials });
    if (!stillHere()) return;
    setNotice(result.kind === "timeout" ? "Your material is still processing. Refresh materials later to check its status." : "Material processing finished. Select a ready resume to continue.");
  });
  const create = () => void run("create", async () => {
    if (!capabilities?.enabled || !capabilities.eligible || capabilities.exhausted || capabilities.dailyRemaining < 1 || !source || !ready(source) || !processingConfirmed) return;
    const input = { sourceDocumentId: source.documentId ?? source.id, sourceVersionId: source.documentVersionId!, targetRole: targetRole.trim(),
      jdDocumentId: jdMode === "material" ? selectedJd?.documentId ?? selectedJd?.id ?? null : null,
      jdVersionId: jdMode === "material" ? selectedJd?.documentVersionId ?? null : null,
      jdText: jdMode === "text" ? jdText.trim() : "", quotedQuotaDay: capabilities.quotaDay, confirmProcessing: true as const };
    if (jdMode === "material" && (!selectedJd || !ready(selectedJd))) throw new Error("Select a ready job description before continuing.");
    const fingerprint = JSON.stringify(input);
    if (createKey.current?.fingerprint !== fingerprint) createKey.current = { fingerprint, key: crypto.randomUUID() };
    try {
      const next = await resumeOptimizerClient.create({ ...input, idempotencyKey: createKey.current.key }, signal());
      if (!stillHere()) return;
      adopt(next); setProcessingConfirmed(false); await refreshMetadata();
    } catch (reason) {
      if (stillHere() && reason instanceof ResumeOptimizerError) {
        if (reason.code === "resume_optimizer_quote_changed") setProcessingConfirmed(false);
        await refreshMetadata().catch(() => undefined);
      }
      throw reason;
    }
  });
  const openHistory = (id: string) => {
    if (dirty && !window.confirm("Discard your unsaved local edits and open this review?")) return;
    void run("open", () => loadJob(id));
  };
  const revisionFailure = async (reason: unknown) => {
    if (reason instanceof ResumeOptimizerError && reason.code === "resume_optimizer_revision_conflict" && job) {
      const latest = await resumeOptimizerClient.get(job.jobId, signal());
      if (stillHere()) { adopt(latest, false); setConflict(true); setFactsConfirmed(false); }
    } else if (reason instanceof ResumeOptimizerError && reason.status === 404 && stillHere()) { setJob(null); setDraft(""); setFactsConfirmed(false); }
    throw reason;
  };
  const saveDraft = () => { if (!job) return; void run("draft", async () => {
    try { const next = await resumeOptimizerClient.saveDraft(job.jobId, job.revision, draft, signal()); if (stillHere()) { adopt(next); setNotice("Your draft is saved. The original resume and AI review are unchanged."); } }
    catch (reason) { await revisionFailure(reason); }
  }); };
  const download = (format: "docx" | "pdf") => { if (!job || !factsConfirmed || dirty || conflict) return; void run(format, async () => {
    try { const result = await resumeOptimizerClient.download(job.jobId, format, job.revision, signal()); if (stillHere()) { downloadOptimizedResume(result); setNotice(`${format === "docx" ? "Word" : "PDF"} download started from your saved draft.`); } }
    catch (reason) { await revisionFailure(reason); }
  }); };
  const saveAs = () => { if (!job || !factsConfirmed || !copyConfirmed || dirty || conflict) return; void run("copy", async () => {
    try { await resumeOptimizerClient.saveAs(job.jobId, job.revision, signal()); if (!stillHere()) return; await loadJob(job.jobId); await refreshMaterials(); if (stillHere()) setNotice("A separate resume was saved to Materials. It becomes available for interviews after processing. Your original and existing interview selections are unchanged."); }
    catch (reason) { await revisionFailure(reason); }
  }); };
  const remove = () => { if (!job || !window.confirm("Delete this review, its source snapshots, suggestions and draft? A resume explicitly saved as a separate material will remain. Deleting a completed review does not restore today's use.")) return;
    void run("delete", async () => { loadGeneration.current += 1; await resumeOptimizerClient.remove(job.jobId, signal()); if (!stillHere()) return; loadGeneration.current += 1; setJob(null); setDraft(""); setFactsConfirmed(false); await refreshMetadata(); if (stillHere()) setNotice("The review and its saved draft were deleted. Separate saved materials remain in Materials."); });
  };
  const retry = () => { if (!job) return; setSourceId(job.sourceDocumentId); setTargetRole(job.targetRole); setJdMode(job.jdDocumentId ? "material" : job.jdText ? "text" : "none"); setJdId(jds.find(item => item.documentId === job.jdDocumentId || item.id === job.jdDocumentId)?.id ?? ""); setJdText(job.jdText); setProcessingConfirmed(false); createKey.current = null; setJob(null); setDraft(""); setFactsConfirmed(false); setNotice("Review your current materials and allowance, then confirm a new attempt. No retry starts automatically."); };

  return <main className="app-page resume-optimizer-page">
    <header className="page-header"><div><span className="kicker">PREPARE WITH CONFIDENCE</span><h1>Resume Optimizer</h1><p>Evidence-based feedback. A clearer resume, built from your real experience.</p></div><Link className="button ghost" to={routes.library}>Your materials</Link></header>
    {error ? <div className="inline-error" role="alert">{error}</div> : null}
    {notice ? <div className="billing-notice" role="status">{notice}</div> : null}
    {initialLoading ? <section className="panel resume-loading" role="status">Loading your allowance and reviews…</section> : !capabilities ? <section className="panel"><p>We could not load Resume Optimizer.</p><button className="button primary" onClick={() => void initialize()}>Try again</button></section> : !capabilities.enabled ? <section className="panel resume-empty"><h2>Resume Optimizer is not available right now</h2><p>Your interviews and materials are still available. Please check back later.</p><Link to={routes.library}>Manage materials →</Link></section> : <>
      <section className="resume-benefit panel"><div><span className="kicker">INCLUDED WITH PAID TIME MEMBERSHIP</span><h2>One resume review per UTC day</h2><p>Every active paid time plan qualifies, including a one-day plan. Editing, downloads and saving a separate resume do not use another review.</p></div><div className="resume-quota"><strong>{capabilities.eligible ? `${capabilities.dailyRemaining} / ${capabilities.dailyLimit}` : "Membership required"}</strong><span>{capabilities.eligible ? "reviews available today" : "Choose a paid time plan to start"}</span><small>Resets {readableUtcDay(capabilities.resetAtMs)} at 00:00 UTC</small>{!capabilities.eligible ? <Link className="button primary" to={routes.billing}>View membership plans</Link> : capabilities.exhausted ? <small>Today's use is reserved or completed. Try again tomorrow.</small> : null}</div></section>
      <div className="resume-start-layout"><section className="panel resume-create"><div className="panel-heading"><div><h2>Start with your resume</h2><p>Your original file stays unchanged.</p></div></div>
        <label htmlFor="optimizer-resume">Resume</label><div className="resume-input-row"><select id="optimizer-resume" value={source?.id ?? sourceId} disabled={Boolean(operation) || active} onChange={e => { setSourceId(e.target.value); setProcessingConfirmed(false); }}><option value="">Select a resume</option>{sources.map(item => <option key={item.id} value={item.id} disabled={!ready(item)}>{item.displayName} · {ready(item) ? item.version : item.status === "ready" ? "Refresh version" : item.status}</option>)}</select><button className="button ghost" disabled={Boolean(operation) || active} onClick={() => fileInput.current?.click()}>{operation === "upload" ? "Processing…" : "Upload resume"}</button><input ref={fileInput} type="file" accept={materialUploadAccept} aria-label="Upload a resume" hidden onChange={event => { const file = event.target.files?.[0]; event.target.value = ""; if (file) upload(file); }} /></div>
        {!sources.length ? <p className="resume-muted">No resumes yet. Upload a PDF, Word document, TXT or Markdown file to begin.</p> : null}
        {source && !ready(source) ? <p className="resume-muted">This resume is not ready for review. Refresh materials after processing finishes.</p> : null}
        <button type="button" className="resume-text-button" disabled={Boolean(operation)} onClick={() => void run("materials", async () => { await refreshMaterials(); if (stillHere()) setNotice("Materials refreshed."); })}>Refresh materials</button>
        <label htmlFor="optimizer-role">Target role <span>(optional)</span></label><input id="optimizer-role" value={targetRole} maxLength={capabilities.limits.targetRoleCharacters} placeholder="e.g. Backend Engineer" disabled={Boolean(operation) || active} onChange={e => { setTargetRole(e.target.value); setProcessingConfirmed(false); }} />
        <label htmlFor="optimizer-jd-mode">Job description <span>(optional)</span></label><select id="optimizer-jd-mode" value={jdMode} disabled={Boolean(operation) || active} onChange={e => { setJdMode(e.target.value as typeof jdMode); setProcessingConfirmed(false); }}><option value="none">General resume review · no JD</option><option value="text">Paste a job description</option><option value="material">Choose from Materials</option></select>
        {jdMode === "text" ? <><label className="sr-only" htmlFor="optimizer-jd-text">Job description text</label><textarea id="optimizer-jd-text" rows={6} value={jdText} maxLength={capabilities.limits.jdCharacters} disabled={Boolean(operation) || active} onChange={e => { setJdText(e.target.value); setProcessingConfirmed(false); }} placeholder="Paste the role's responsibilities and requirements" /><small className="resume-muted">{jdText.length.toLocaleString()} / {capabilities.limits.jdCharacters.toLocaleString()} characters</small></> : jdMode === "material" ? <select aria-label="Saved job description" value={jdId} disabled={Boolean(operation) || active} onChange={e => { setJdId(e.target.value); setProcessingConfirmed(false); }}><option value="">Select a ready job description</option>{jds.map(item => <option key={item.id} value={item.id} disabled={!ready(item)}>{item.displayName} · {ready(item) ? item.version : item.status}</option>)}</select> : <p className="resume-muted">Without a JD, role matching is not assessed. The review focuses on your resume itself.</p>}
        <div className="resume-disclosure"><strong>Before you start</strong><p>The selected resume and JD content are sent to our configured AI service. Input snapshots, feedback and drafts are saved with the review until you delete it. Deleting a referenced material also removes linked review content.</p><p>One daily use is reserved when you start and used on successful completion. Failed or cancelled unfinished work returns its creation-day use.</p></div>
        <label className="resume-check"><input type="checkbox" checked={processingConfirmed} disabled={Boolean(operation) || active} onChange={e => setProcessingConfirmed(e.target.checked)} /><span>I agree to this processing and to reserve today's included review.</span></label>
        <button className="button primary full" disabled={Boolean(operation) || active || !capabilities.eligible || capabilities.exhausted || capabilities.dailyRemaining < 1 || !source || !ready(source) || !processingConfirmed || (jdMode === "material" && (!selectedJd || !ready(selectedJd))) || (jdMode === "text" && !jdText.trim())} onClick={create}>{operation === "create" ? "Starting review…" : active ? "A review is already in progress" : !capabilities.eligible ? "Membership required" : capabilities.exhausted || capabilities.dailyRemaining < 1 ? "Daily review used · try tomorrow" : "Review & optimize resume"}</button>
      </section><aside className="panel resume-history"><div className="panel-heading"><h2>Your reviews</h2><button className="resume-text-button" disabled={Boolean(operation)} onClick={() => void run("refresh", async () => { await refreshMetadata(); })}>Refresh</button></div>{history.length ? <ul>{history.map(item => <li key={item.jobId}><button className={job?.jobId === item.jobId ? "selected" : ""} disabled={Boolean(operation)} onClick={() => openHistory(item.jobId)}><span><strong>{item.sourceDisplayName}</strong><small>{item.targetRole || "General resume review"}</small><small>{readableDate(item.createdAtMs)}</small></span><span className={`resume-status ${item.status}`}>{statusLabels[item.status]}</span></button></li>)}</ul> : <div className="resume-empty"><span aria-hidden="true">↗</span><h3>A stronger resume starts here</h3><p>Your saved reviews will appear here. No review has been started.</p></div>}</aside></div>
      {job ? <section className="resume-result" aria-label="Selected resume review"><header className="resume-result-header"><div><span className="kicker">{statusLabels[job.status]}</span><h2>{job.sourceDisplayName}</h2><p>{job.targetRole || "General resume review"} · {job.hasJd ? "With job description" : "No JD"} · Draft revision {job.revision}</p></div><button className="button danger" disabled={Boolean(operation)} onClick={remove}>{operation === "delete" ? "Deleting…" : "Delete review"}</button></header>
        {unfinished(job) ? <div className="panel resume-progress" role="status"><div className="resume-progress-dot" aria-hidden="true" /><h3>{job.status === "queued" ? "Your review is in the queue" : "Finding improvements grounded in your resume"}</h3><p>{job.status === "queued" ? "We process one review at a time. You can leave this page and return later." : "Checking evidence, evaluating the resume and preparing a draft. It may take a little while."}</p><div className="resume-actions"><button className="button ghost" disabled={Boolean(operation)} onClick={() => void run("status", () => loadJob(job.jobId))}>Check status</button><button className="button danger" disabled={Boolean(operation)} onClick={() => void run("cancel", async () => { loadGeneration.current += 1; const next = await resumeOptimizerClient.cancel(job.jobId, signal()); if (stillHere()) { adopt(next); await refreshMetadata(); } })}>{operation === "cancel" ? "Cancelling…" : "Cancel review"}</button></div></div> : job.status === "failed" || job.status === "cancelled" ? <div className="panel resume-empty"><h3>{job.status === "cancelled" ? "This review was cancelled" : "We could not complete this review"}</h3><p>{job.status === "failed" ? (job.errorMessage && !/[\u3400-\u9fff]/u.test(job.errorMessage) ? job.errorMessage.slice(0, 600) : "No optimized resume was published. Your original is unchanged.") : "No new review will start automatically."}</p><p>{job.allowanceStatus === "released" ? "The reserved use was returned to its original UTC day." : "Refresh your allowance before starting another review."}</p><button className="button primary" disabled={Boolean(operation)} onClick={retry}>Review inputs & retry</button></div> : job.review ? <>
          <div className="resume-review-layout"><section className="panel resume-score"><span className="kicker">REFERENCE EVALUATION</span><div className="resume-score-number"><strong>{job.review.overallScore}</strong><span>/ 100</span></div><p>{job.review.disclaimer}</p><small>Equal-weight dimensions · {job.scoreVersion}</small>{!job.review.roleMatchingAssessed ? <p className="resume-muted">Role matching not assessed: no JD was supplied.</p> : null}</section><section className="panel resume-dimensions"><h3>What shapes your score</h3>{job.review.dimensions.map(dimension => <article key={dimension.key}><div><strong>{labels[dimension.key] ?? dimension.key}</strong><span>{dimension.score} / 100</span></div><meter min={0} max={100} value={dimension.score} aria-label={`${labels[dimension.key] ?? dimension.key} score`}>{dimension.score}</meter><p>{dimension.reason}</p><Evidence items={dimension.evidence} /></article>)}</section></div>
          <section className="panel resume-suggestions"><h3>Changes that matter</h3>{job.review.suggestions.map((suggestion, i) => <article key={i}><span className={`resume-priority ${suggestion.priority}`}>{suggestion.priority} priority</span><h4>{suggestion.title}</h4><p>{suggestion.explanation}</p><Evidence items={suggestion.evidence} /><p className="resume-recommendation"><strong>Try this</strong>{suggestion.recommendation}</p></article>)}{job.review.missingFacts.length ? <aside className="resume-missing"><h4>Details only you can add</h4><p>Add these only when they are true and verifiable. We have not invented them in your draft.</p><ul>{job.review.missingFacts.map((fact, i) => <li key={i}>{fact}</li>)}</ul></aside> : null}</section>
          <section className="panel resume-comparison"><div className="panel-heading"><div><h3>Compare, edit and make it yours</h3><p>The parsed source is read-only; your original file stays unchanged. Save edits before downloading or creating a separate material.</p></div></div><div className="resume-comparison-grid"><section><h4>Parsed source resume</h4><p className="resume-muted">Parsed source; table layouts simplified.</p><pre>{job.sourceText}</pre></section><section><label htmlFor="optimizer-draft">Your optimized draft</label><textarea id="optimizer-draft" rows={22} value={draft} maxLength={capabilities.limits.draftCharacters} disabled={Boolean(operation)} onChange={e => { setDraft(e.target.value); setFactsConfirmed(false); setCopyConfirmed(false); }} /><small>{draft.length.toLocaleString()} / {capabilities.limits.draftCharacters.toLocaleString()} characters · {dirty ? "Unsaved changes" : "Saved"}</small></section></div><details><summary>View the AI's original draft</summary><pre>{job.initialDraftMarkdown}</pre></details>{conflict ? <div className="inline-error" role="alert">A newer draft is saved on the server. Your local edits are kept above. Copy them if needed, then reload the saved draft.<button className="resume-text-button" onClick={() => { if (window.confirm("Replace your unsaved local edits with the latest saved draft?")) { setDraft(job.draftMarkdown ?? ""); setConflict(false); setFactsConfirmed(false); } }}>Reload saved draft</button></div> : null}<div className="resume-actions"><button className="button primary" disabled={Boolean(operation) || !dirty || conflict || !draft.trim()} onClick={saveDraft}>{operation === "draft" ? "Saving…" : "Save draft"}</button><span className="resume-muted">Use plain text or Markdown. HTML is not supported.</span></div>
            <div className="resume-export-area"><h4>Ready to use your resume?</h4><p>Exports use a clean standard template, rather than the original file's layout. Check every claim, date, skill and result before sending it.</p><label className="resume-check"><input type="checkbox" checked={factsConfirmed} disabled={Boolean(operation) || dirty || conflict} onChange={e => setFactsConfirmed(e.target.checked)} /><span>I have checked this saved draft and confirm its facts are accurate.</span></label>{dirty ? <p className="resume-muted">Save your changes before confirming and downloading.</p> : null}<div className="resume-actions">{capabilities.exports.includes("docx") ? <button className="button primary" disabled={Boolean(operation) || dirty || conflict || !factsConfirmed} onClick={() => download("docx")}>{operation === "docx" ? "Preparing Word…" : "Download Word"}</button> : null}{capabilities.exports.includes("pdf") ? <button className="button ghost" disabled={Boolean(operation) || dirty || conflict || !factsConfirmed} onClick={() => download("pdf")}>{operation === "pdf" ? "Preparing PDF…" : "Download PDF"}</button> : null}</div><label className="resume-check"><input type="checkbox" checked={copyConfirmed} disabled={Boolean(operation) || dirty || conflict} onChange={e => setCopyConfirmed(e.target.checked)} /><span>Save a separate resume in Materials. My original and existing interview selections stay unchanged. This copy remains if I delete this review.</span></label><button className="button ghost" disabled={Boolean(operation) || dirty || conflict || !factsConfirmed || !copyConfirmed} onClick={saveAs}>{operation === "copy" ? "Saving separate resume…" : job.savedDocumentId ? "View saved copy status" : "Save as new resume"}</button>{job.savedDocumentId ? <p className="resume-muted">A copy of this draft revision has been saved. <Link to={routes.library}>Open Materials →</Link></p> : null}<p className="resume-muted">Editing, downloading and saving a copy use no additional daily review. Completed results remain available after membership expiry while this review and its sources are retained.</p></div>
          </section>
        </> : <section className="panel" role="alert">This review has no available result. Refresh its status.</section>}
      </section> : null}
    </>}
  </main>;
}
