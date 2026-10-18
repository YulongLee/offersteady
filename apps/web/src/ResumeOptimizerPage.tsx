import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { detectMaterialUploadFormat, materialUploadAccept, type ContextLibrarySource } from "@offersteady/protocol";
import type { WebAppState } from "./domain";
import { routes } from "./routes";
import { interviewAppAdapter } from "./app-adapter";
import { materialUploadAdapter } from "./material-upload-adapter";
import { pollLibraryDocumentUntilSettled } from "./library-processing-polling";
import { downloadOptimizedResume, resumeOptimizerClient, resumeOptimizationFailureMessage, resumeInitialDraftSummary, ResumeOptimizerError, type ResumeEvidence, type ResumeOptimization, type ResumeOptimizationSummary, type ResumeOptimizerCapabilities } from "./resume-optimizer-client";
import "./resume-optimizer.css";

interface Props { readonly state: WebAppState; readonly setState: Dispatch<SetStateAction<WebAppState>> }
const unfinished = (job: ResumeOptimizationSummary | null) => Boolean(job && (job.status === "queued" || job.status === "running"));
const ready = (source: ContextLibrarySource) => source.status === "ready" && source.syncStatus !== "missing_artifacts" && source.selectable !== false && Boolean(source.documentVersionId);
const labels: Readonly<Record<string, string>> = { completeness: "信息完整度", impact: "经历与成果依据", clarity: "表达清晰度", structure: "结构与可读性", roleMatch: "岗位匹配度" };
const sourceLabels: Readonly<Record<string, string>> = { ready: "已就绪", processing: "解析中", processing_requested: "待解析", uploaded: "待解析", failed: "解析失败", disabled: "已停用" };
const statusLabels = { queued: "排队中", running: "正在优化", completed: "已完成", failed: "优化失败", cancelled: "已取消" };
const safeMessage = (error: unknown) => error instanceof Error ? error.message : "操作未完成，请稍后重试。";
const readableDate = (time: number) => new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Shanghai" }).format(time);
export const RESUME_OPTIMIZER_POLL_LIMIT = 120;

function Evidence({ items }: { readonly items: readonly ResumeEvidence[] }) {
  return <div className="resume-evidence">{items.map((item, i) => <blockquote key={i}><small>{item.source === "jd" ? "解析后的岗位描述" : "解析后的简历"}</small><p>{item.quote}</p></blockquote>)}</div>;
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
  const [paymentQuote, setPaymentQuote] = useState<string | null>(null);
  const [section, setSection] = useState<"create" | "history">("create");
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
  const billingSync = useRef(new Set<string>());
  const billingGeneration = useRef(0);
  const createKey = useRef<{ fingerprint: string; key: string } | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const paymentDialog = useRef<HTMLDialogElement>(null);
  const paymentCancel = useRef<HTMLButtonElement>(null);
  const startButton = useRef<HTMLButtonElement>(null);
  const returnPaymentFocus = useRef(false);
  const sources = state.librarySources.filter(item => item.ownerUserId === state.account.id && item.kind === "resume" && item.status !== "deleted");
  const jds = state.librarySources.filter(item => item.ownerUserId === state.account.id && item.kind === "jd" && item.status !== "deleted");
  const source = sources.find(item => item.id === sourceId || item.documentId === sourceId);
  const selectedJd = jds.find(item => item.id === jdId);
  const dirty = Boolean(job?.status === "completed" && draft !== job.draftMarkdown);
  const initialDraftSummary = job ? resumeInitialDraftSummary(job) : null;
  const active = unfinished(job) || Boolean(capabilities?.activeJobId);
  const paid = capabilities?.billingClass === "points";
  const quotedBilling = useRef<string | null>(null);
  const acceptCapabilities = (caps: ResumeOptimizerCapabilities) => {
    const identity = JSON.stringify([caps.quotaDay, caps.billingClass, caps.entryPoints]);
    if (quotedBilling.current !== identity) { setProcessingConfirmed(false); setPaymentQuote(null); }
    quotedBilling.current = identity; setCapabilities(caps);
  };
  useEffect(() => {
    if (!paymentQuote || !paymentDialog.current) return;
    const dialog = paymentDialog.current;
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
    paymentCancel.current?.focus();
    return () => { if (dialog.open && typeof dialog.close === "function") dialog.close(); returnPaymentFocus.current = true; };
  }, [paymentQuote]);
  useEffect(() => {
    if (paymentQuote || operation || !returnPaymentFocus.current) return;
    returnPaymentFocus.current = false;
    const button = startButton.current;
    if (button && !button.disabled && !button.closest("[hidden]")) button.focus();
  }, [paymentQuote, operation]);
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
    acceptCapabilities(caps); setHistory(list.jobs);
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
      acceptCapabilities(caps);
      if (caps.enabled) {
        const list = await resumeOptimizerClient.list(signal());
        if (!stillHere()) return;
        setHistory(list.jobs);
        if (caps.activeJobId) { await loadJob(caps.activeJobId); if (stillHere()) setSection("history"); }
      }
    } catch (reason) { if (stillHere()) setError(safeMessage(reason)); }
    finally { if (stillHere()) setInitialLoading(false); }
  };
  useEffect(() => {
    const controller = new AbortController(); lifetime.current = controller;
    void initialize();
    return () => { controller.abort(); loadGeneration.current += 1; lifetime.current = null; };
  }, []);

  useEffect(() => {
    if (!job || job.billingClass !== "points") return;
    const key = `${job.jobId}:${job.billingStatus === "released" ? "refunded" : "charged"}`;
    if (billingSync.current.has(key)) return;
    billingSync.current.add(key);
    const generation = ++billingGeneration.current;
    const requestSignal = signal();
    void interviewAppAdapter.getBillingState(requestSignal).then(billing => {
      if (!stillHere() || requestSignal?.aborted || generation !== billingGeneration.current) return;
      setState(current => current.account.id === state.account.id ? { ...current, billing } : current);
    }).catch(() => {
      billingSync.current.delete(key);
      if (stillHere() && generation === billingGeneration.current) setNotice("优化状态已更新，积分明细暂未同步；本页可用积分以最新报价为准，可到积分与会员页刷新。");
    });
  }, [job?.jobId, job?.billingClass, job?.billingStatus]);

  useEffect(() => { setProcessingConfirmed(false); setPaymentQuote(null); }, [source?.documentVersionId, selectedJd?.documentVersionId, targetRole, jdMode, jdText]);

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
        if (attempts >= RESUME_OPTIMIZER_POLL_LIMIT) { setPollPaused(true); setNotice("任务仍在处理中，已暂停自动查询。可点击“刷新进度”查看最新结果。"); return; }
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
    // Use the quoted server clock so a wrong device clock cannot delay midnight refresh.
    const delay = Math.max(100, Math.min(capabilities.resetAtMs - capabilities.nowMs + 100, 2_147_000_000));
    const refresh = () => { void refreshMetadata().catch(reason => { if (stillHere()) setError(safeMessage(reason)); }); };
    const recover = () => { if (document.visibilityState === "visible") refresh(); };
    const timer = window.setTimeout(refresh, delay);
    window.addEventListener("focus", refresh); document.addEventListener("visibilitychange", recover);
    return () => { window.clearTimeout(timer); window.removeEventListener("focus", refresh); document.removeEventListener("visibilitychange", recover); };
  }, [capabilities?.resetAtMs, capabilities?.nowMs, capabilities?.enabled]);

  const run = async (name: string, action: () => Promise<void>) => {
    if (busy.current) return;
    busy.current = true; setOperation(name); setError(""); setNotice("");
    try { await action(); }
    catch (reason) { if (stillHere()) setError(safeMessage(reason)); }
    finally { busy.current = false; if (stillHere()) setOperation(""); }
  };
  const refreshMaterials = async (requestSignal = signal()) => {
    const next = await interviewAppAdapter.loadState(requestSignal);
    if (stillHere() && !requestSignal?.aborted) setState(next);
    return next;
  };
  const upload = (file: File) => void run("upload", async () => {
    if (!detectMaterialUploadFormat(file.name)) throw new Error("请选择 PDF、DOCX、DOC、TXT 或 Markdown 简历。");
    if (file.size > 20 * 1024 * 1024) throw new Error("请选择不超过 20 MB 的简历。");
    const uploaded = await materialUploadAdapter.uploadResume(state.account.id, file, signal());
    if (!stillHere()) return;
    await refreshMaterials();
    if (!stillHere()) return;
    setSourceId(uploaded.source.sourceId); setProcessingConfirmed(false);
    setNotice("简历已上传，正在解析，完成后即可优化。");
    const result = await pollLibraryDocumentUntilSettled({ documentId: uploaded.source.sourceId, signal: signal()!, loadState: refreshMaterials });
    if (!stillHere()) return;
    setNotice(result.kind === "timeout" ? "资料仍在解析中，稍后刷新资料即可查看状态。" : "资料处理已结束，请选择解析完成的简历继续。");
  });
  const create = (confirmPointsCharge = false) => void run("create", async () => {
    const currentQuote = capabilities ? JSON.stringify([capabilities.quotaDay, capabilities.billingClass, capabilities.entryPoints]) : null;
    if (!capabilities?.enabled || !capabilities.canStart || active || !source || !ready(source) || !processingConfirmed || (paid && (!confirmPointsCharge || paymentQuote !== currentQuote))) return;
    const input = { sourceDocumentId: source.documentId ?? source.id, sourceVersionId: source.documentVersionId!, targetRole: targetRole.trim(),
      jdDocumentId: jdMode === "material" ? selectedJd?.documentId ?? selectedJd?.id ?? null : null,
      jdVersionId: jdMode === "material" ? selectedJd?.documentVersionId ?? null : null,
      jdText: jdMode === "text" ? jdText.trim() : "", quotedQuotaDay: capabilities.quotaDay, quotedBillingClass: capabilities.billingClass, quotedPoints: capabilities.entryPoints, confirmPointsCharge: paid && confirmPointsCharge, confirmProcessing: true as const };
    if (jdMode === "material" && (!selectedJd || !ready(selectedJd))) throw new Error("请选择已解析完成的岗位描述后继续。");
    const { quotedQuotaDay: _day, quotedBillingClass: _class, quotedPoints: _points, confirmPointsCharge: _charge, confirmProcessing: _processing, ...logicalInput } = input;
    const fingerprint = JSON.stringify(logicalInput);
    if (createKey.current?.fingerprint !== fingerprint) createKey.current = { fingerprint, key: crypto.randomUUID() };
    try {
      const next = await resumeOptimizerClient.create({ ...input, idempotencyKey: createKey.current.key }, signal());
      if (!stillHere()) return;
      adopt(next); setSection("history"); createKey.current = null; setProcessingConfirmed(false); setPaymentQuote(null); await refreshMetadata();
    } catch (reason) {
      // A native modal makes the page alert inert; expose every failure before retry.
      if (stillHere()) setPaymentQuote(null);
      if (stillHere() && reason instanceof ResumeOptimizerError) {
        if (reason.code === "resume_optimizer_quote_changed" || reason.code === "resume_optimizer_insufficient_balance") { setProcessingConfirmed(false); setPaymentQuote(null); createKey.current = null; }
        await refreshMetadata().catch(() => undefined);
      }
      throw reason;
    }
  });
  const begin = () => {
    if (paid && capabilities) setPaymentQuote(JSON.stringify([capabilities.quotaDay, capabilities.billingClass, capabilities.entryPoints]));
    else create();
  };
  const openHistory = (id: string) => {
    if (dirty && !window.confirm("放弃尚未保存的本地修改，并打开这次优化？")) return;
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
    try { const next = await resumeOptimizerClient.saveDraft(job.jobId, job.revision, draft, signal()); if (stillHere()) { adopt(next); setNotice("草稿已保存，原简历和 AI 初稿保留。"); } }
    catch (reason) { await revisionFailure(reason); }
  }); };
  const download = (format: "docx" | "pdf") => { if (!job || !factsConfirmed || dirty || conflict) return; void run(format, async () => {
    try { const result = await resumeOptimizerClient.download(job.jobId, format, job.revision, signal()); if (stillHere()) { downloadOptimizedResume(result); setNotice(`${format === "docx" ? "Word" : "PDF"}已开始下载，内容来自已保存稿。`); } }
    catch (reason) { await revisionFailure(reason); }
  }); };
  const saveAs = () => { if (!job || !factsConfirmed || !copyConfirmed || dirty || conflict) return; void run("copy", async () => {
    try { await resumeOptimizerClient.saveAs(job.jobId, job.revision, signal()); if (!stillHere()) return; await loadJob(job.jobId); await refreshMaterials(); if (stillHere()) setNotice("已在资料库另存一份新简历，解析完成后可用于面试。原简历和既有面试选择保留。"); }
    catch (reason) { await revisionFailure(reason); }
  }); };
  const remove = () => { if (!job || !window.confirm("删除本次优化及其输入快照、建议和草稿？已经另存的新简历将保留。已完成的优化不会退还积分或恢复免费次数。")) return;
    void run("delete", async () => { loadGeneration.current += 1; await resumeOptimizerClient.remove(job.jobId, signal()); if (!stillHere()) return; loadGeneration.current += 1; setJob(null); setDraft(""); setFactsConfirmed(false); await refreshMetadata(); if (stillHere()) setNotice("本次优化及草稿已删除，已另存的新简历仍保留在资料库。"); });
  };
  const retry = () => { if (!job) return; setSourceId(job.sourceDocumentId); setTargetRole(job.targetRole); setJdMode(job.jdDocumentId ? "material" : job.jdText ? "text" : "none"); setJdId(jds.find(item => item.documentId === job.jdDocumentId || item.id === job.jdDocumentId)?.id ?? ""); setJdText(job.jdText); setProcessingConfirmed(false); setPaymentQuote(null); createKey.current = null; setJob(null); setSection("create"); setDraft(""); setFactsConfirmed(false); setNotice("请核对资料，重新确认后再开始。系统不会自动重试或收费。"); };

  return <main className="app-page resume-optimizer-page">
    <header className="page-header"><div><h1>简历优化</h1><p>让你的经历，表达得更清楚。</p></div><Link className="button ghost" to={routes.library}>我的资料</Link></header>
    {error ? <div className="inline-error" role="alert">{error}</div> : null}
    {notice ? <div className="billing-notice" role="status">{notice}</div> : null}
    {initialLoading ? <section className="panel resume-loading" role="status">正在加载…</section> : !capabilities ? <section className="panel"><p>暂时无法读取简历优化。</p><button className="button primary" onClick={() => void initialize()}>重试</button></section> : !capabilities.enabled ? <section className="panel resume-empty"><h2>简历优化暂时不可用</h2><p>请稍后再试，也可继续使用面试和资料。</p><Link to={routes.library}>管理资料 →</Link></section> : <>
      <div className="resume-tabs" role="tablist" aria-label="简历优化工作区" onKeyDown={event => {
        if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
        event.preventDefault(); const next = event.key === "Home" ? "create" : event.key === "End" ? "history" : section === "create" ? "history" : "create";
        setSection(next); event.currentTarget.querySelector<HTMLButtonElement>(`#resume-${next}-tab`)?.focus();
      }}>
        <button id="resume-create-tab" role="tab" tabIndex={section === "create" ? 0 : -1} aria-selected={section === "create"} aria-controls="resume-create-panel" onClick={() => setSection("create")}>新建优化</button>
        <button id="resume-history-tab" role="tab" tabIndex={section === "history" ? 0 : -1} aria-selected={section === "history"} aria-controls="resume-history-panel" onClick={() => setSection("history")}>我的优化记录{history.length ? <span aria-hidden="true">{history.length}</span> : null}</button>
      </div>
      <section id="resume-create-panel" role="tabpanel" aria-labelledby="resume-create-tab" hidden={section !== "create"} className="panel resume-create">
        <div className="resume-form-heading"><h2>从一份简历开始</h2><p>获取评分、修改建议与可下载的优化稿。原文件会保留。</p></div>
        <div className="resume-field"><div className="resume-field-heading"><label htmlFor="optimizer-resume">选择简历</label><button type="button" className="resume-text-button" disabled={Boolean(operation)} onClick={() => void run("materials", async () => { await refreshMaterials(); if (stillHere()) setNotice("资料已刷新。"); })}>刷新资料</button></div><div className="resume-input-row"><select id="optimizer-resume" value={source?.id ?? sourceId} disabled={Boolean(operation) || active} onChange={e => { setSourceId(e.target.value); setProcessingConfirmed(false); setPaymentQuote(null); }}><option value="">请选择简历</option>{sources.map(item => <option key={item.id} value={item.id} disabled={!ready(item)}>{item.displayName} · {ready(item) ? item.version : item.status === "ready" ? "请刷新版本" : (sourceLabels[item.status] ?? "暂不可用")}</option>)}</select><button className="button ghost" disabled={Boolean(operation) || active} onClick={() => fileInput.current?.click()}>{operation === "upload" ? "正在处理…" : "上传简历"}</button><input ref={fileInput} type="file" accept={materialUploadAccept} aria-label="上传简历文件" hidden onChange={event => { const file = event.target.files?.[0]; event.target.value = ""; if (file) upload(file); }} /></div>
        {!sources.length ? <p className="resume-muted">支持 PDF、Word、TXT 和 Markdown。</p> : null}
        {source && !ready(source) ? <p className="resume-muted">这份简历尚未就绪，请解析完成后刷新资料。</p> : null}</div>
        <div className="resume-field"><label htmlFor="optimizer-role">目标岗位 <span>选填</span></label><input id="optimizer-role" value={targetRole} maxLength={capabilities.limits.targetRoleCharacters} placeholder="例如：后端工程师" disabled={Boolean(operation) || active} onChange={e => { setTargetRole(e.target.value); setProcessingConfirmed(false); }} /></div>
        <details className="resume-jd"><summary>添加岗位描述 <span>可选，让建议更有针对性</span></summary><div className="resume-jd-content"><label className="sr-only" htmlFor="optimizer-jd-mode">岗位描述</label><select id="optimizer-jd-mode" value={jdMode} disabled={Boolean(operation) || active} onChange={e => { setJdMode(e.target.value as typeof jdMode); setProcessingConfirmed(false); }}><option value="none">通用简历诊断，不提供 JD</option><option value="text">粘贴岗位描述</option><option value="material">选择资料库中的 JD</option></select>
        {jdMode === "text" ? <><label className="sr-only" htmlFor="optimizer-jd-text">岗位描述正文</label><textarea id="optimizer-jd-text" rows={6} value={jdText} maxLength={capabilities.limits.jdCharacters} disabled={Boolean(operation) || active} onChange={e => { setJdText(e.target.value); setProcessingConfirmed(false); }} placeholder="粘贴岗位职责和要求" /><small className="resume-muted">{jdText.length.toLocaleString()} / {capabilities.limits.jdCharacters.toLocaleString()} 字</small></> : jdMode === "material" ? <select aria-label="资料库中的 JD" value={jdId} disabled={Boolean(operation) || active} onChange={e => { setJdId(e.target.value); setProcessingConfirmed(false); setPaymentQuote(null); }}><option value="">请选择已解析完成的岗位描述</option>{jds.map(item => <option key={item.id} value={item.id} disabled={!ready(item)}>{item.displayName} · {ready(item) ? item.version : (sourceLabels[item.status] ?? "暂不可用")}</option>)}</select> : <p className="resume-muted">未提供 JD 时进行通用简历诊断，不评估岗位匹配度。</p>}</div></details>
        <div className="resume-start-footer"><label className="resume-check"><input type="checkbox" checked={processingConfirmed} disabled={Boolean(operation) || active} onChange={e => setProcessingConfirmed(e.target.checked)} /><span>我同意使用 AI 处理所选资料并保存优化结果。</span></label>
        <details className="resume-disclosure"><summary>处理与使用说明</summary><p>所选简历和岗位描述将发送至配置的 AI 服务。输入快照、建议和草稿随任务保存，直到你删除任务；删除引用的源资料也会清理对应优化内容。</p><p>有效时间会员每日免费 3 次，与模拟面试次数独立。编辑、下载和另存不再收费。未完成任务失败或取消时，退还原创建日次数或原扣积分一次；已完成后删除不退还。</p></details>
        <button ref={startButton} className="button primary full" disabled={Boolean(operation) || active || (!paid && !capabilities.canStart) || !source || !ready(source) || !processingConfirmed || (jdMode === "material" && (!selectedJd || !ready(selectedJd))) || (jdMode === "text" && !jdText.trim())} onClick={begin}>{operation === "create" ? "正在开始优化…" : active ? "已有优化任务处理中" : "开始优化"}</button></div>
      </section>
      <section id="resume-history-panel" role="tabpanel" aria-labelledby="resume-history-tab" hidden={section !== "history"} className="resume-history"><div className="resume-history-heading"><h2>优化记录</h2><button className="resume-text-button" disabled={Boolean(operation)} onClick={() => void run("refresh", async () => { await refreshMetadata(); })}>刷新</button></div>{history.length ? <ul>{history.map(item => <li key={item.jobId}><button className={job?.jobId === item.jobId ? "selected" : ""} disabled={Boolean(operation)} onClick={() => openHistory(item.jobId)}><span><strong>{item.sourceDisplayName}</strong><small>{item.targetRole || "通用简历诊断"} · {readableDate(item.createdAtMs)}</small></span><span className={`resume-status ${item.status}`}>{statusLabels[item.status]}</span></button></li>)}</ul> : <div className="resume-empty"><h3>还没有优化记录</h3><p>完成第一次优化后，在这里查看。</p><button className="resume-text-button" onClick={() => setSection("create")}>选择一份简历开始</button></div>}</section>
      {paymentQuote ? <dialog ref={paymentDialog} className="resume-payment-dialog" aria-labelledby="resume-payment-title" aria-describedby="resume-payment-description" onCancel={event => { event.preventDefault(); if (!operation) setPaymentQuote(null); }}>
        <h2 id="resume-payment-title">确认本次优化</h2><p id="resume-payment-description">本次开始优化将扣除 <strong>100 积分</strong>。</p><p className="resume-payment-balance">可用积分 <strong>{capabilities.availablePoints}</strong></p><p className="resume-muted">未完成任务失败或取消，积分将原路退还。编辑和下载不再收费。</p>
        {capabilities.availablePoints < 100 ? <div className="resume-payment-insufficient" role="status"><p>积分不足 100，请充值或开通会员后重试。</p><Link to={routes.billing}>充值 / 开通会员</Link></div> : null}
        <div className="resume-actions"><button ref={paymentCancel} className="button ghost" disabled={Boolean(operation)} onClick={() => setPaymentQuote(null)}>取消</button><button className="button primary" disabled={Boolean(operation) || !capabilities.canStart || capabilities.availablePoints < 100} onClick={() => create(true)}>{operation === "create" ? "正在开始…" : "确认并开始"}</button></div>
      </dialog> : null}
      {job ? <section className="resume-result" aria-label="当前简历优化"><header className="resume-result-header"><div><span className="kicker">{statusLabels[job.status]}</span><h2>{job.sourceDisplayName}</h2><p>{job.targetRole || "通用简历诊断"} · {job.hasJd ? "已提供岗位描述" : "未提供 JD"} · 稿件版本 {job.revision}</p><p>{job.billingClass === "points" ? `本次 ${job.pointsCharged} 积分` : "本次会员免费"} · {job.billingStatus === "reserved" ? job.billingClass === "points" ? "已扣积分，等待结果" : "免费次数已占用" : job.billingStatus === "released" ? "已原路退还" : "已完成结算"}</p></div><button className="button danger" disabled={Boolean(operation)} onClick={remove}>{operation === "delete" ? "正在删除…" : "删除优化"}</button></header>
        {unfinished(job) ? <div className="panel resume-progress" role="status"><div className="resume-progress-dot" aria-hidden="true" /><h3>{job.status === "queued" ? "优化任务正在排队" : "正在根据原文整理改进建议"}</h3><p>{job.status === "queued" ? "任务按顺序处理，你可以离开页面，稍后回来查看。" : "正在核对依据、诊断简历并生成优化稿，请稍候。"}</p><div className="resume-actions"><button className="button ghost" disabled={Boolean(operation)} onClick={() => void run("status", () => loadJob(job.jobId))}>刷新进度</button><button className="button danger" disabled={Boolean(operation)} onClick={() => void run("cancel", async () => { loadGeneration.current += 1; const next = await resumeOptimizerClient.cancel(job.jobId, signal()); if (stillHere()) { adopt(next); await refreshMetadata(); } })}>{operation === "cancel" ? "正在取消…" : "取消优化"}</button></div></div> : job.status === "failed" || job.status === "cancelled" ? <div className="panel resume-empty"><h3>{job.status === "cancelled" ? "本次优化已取消" : "本次优化未完成"}</h3><p>{job.status === "failed" ? resumeOptimizationFailureMessage(job) : "系统不会自动开始新的优化。"}</p><p>{job.allowanceStatus === "released" ? job.billingClass === "points" ? "本次扣除的 100 积分已原路退还。" : "已退还原创建日的免费次数，跨日不会增加今日额度。" : "请刷新最新次数和费用后重新开始。"}</p><button className="button primary" disabled={Boolean(operation)} onClick={retry}>核对输入并重试</button></div> : job.review ? <>
          <div className="resume-review-layout"><section className="panel resume-score"><span className="kicker">参考评分</span><div className="resume-score-number"><strong>{job.review.overallScore}</strong><span>/ 100</span></div><p>{job.review.disclaimer}</p><small>各维度等权计算</small>{!job.review.roleMatchingAssessed ? <p className="resume-muted">未提供岗位描述，岗位匹配度未评估。</p> : null}</section><section className="panel resume-dimensions"><h3>评分维度与依据</h3>{job.review.dimensions.map(dimension => <article key={dimension.key}><div><strong>{labels[dimension.key] ?? dimension.key}</strong><span>{dimension.score} / 100</span></div><meter min={0} max={100} value={dimension.score} aria-label={`${labels[dimension.key] ?? dimension.key}评分`}>{dimension.score}</meter><p>{dimension.reason}</p><Evidence items={dimension.evidence} /></article>)}</section></div>
          <section className="panel resume-suggestions"><h3>修改建议</h3>{job.review.suggestions.map((suggestion, i) => <article key={i}><span className={`resume-priority ${suggestion.priority}`}>{{high: "优先修改", medium: "建议修改", low: "可选完善"}[suggestion.priority]}</span><h4>{suggestion.title}</h4><p>{suggestion.explanation}</p><Evidence items={suggestion.evidence} /><p className="resume-recommendation"><strong>建议修改方式</strong>{suggestion.recommendation}</p></article>)}{job.review.missingFacts.length ? <aside className="resume-missing"><h4>需要你补充的信息</h4><p>仅补充真实且可核实的信息，这些内容未被虚构到优化稿中。</p><ul>{job.review.missingFacts.map((fact, i) => <li key={i}>{fact}</li>)}</ul></aside> : null}</section>
          <section className="panel resume-comparison"><div className="panel-heading"><div><h3>对照原文，编辑优化稿</h3><p>解析原文只读，原文件保留。修改后请先保存，再下载或另存新简历。</p>{initialDraftSummary ? <p className="resume-muted" aria-label="AI 初稿改写摘要">{initialDraftSummary}</p> : null}</div></div><div className="resume-comparison-grid"><section><h4>解析后的原简历</h4><p className="resume-muted">展示解析文本，表格已转为简化文本。</p><pre>{job.sourceText}</pre></section><section><label htmlFor="optimizer-draft">可编辑优化稿</label><textarea id="optimizer-draft" rows={22} value={draft} maxLength={capabilities.limits.draftCharacters} disabled={Boolean(operation)} onChange={e => { setDraft(e.target.value); setFactsConfirmed(false); setCopyConfirmed(false); }} /><small>{draft.length.toLocaleString()} / {capabilities.limits.draftCharacters.toLocaleString()} 字 · {dirty ? "尚未保存" : "已保存"}</small></section></div><details><summary>查看 AI 初稿</summary><pre>{job.initialDraftMarkdown}</pre></details>{conflict ? <div className="inline-error" role="alert">服务端已有更新版本，已保留上方的本地编辑。请先复制需要保留的内容，再载入已保存稿。<button className="resume-text-button" onClick={() => { if (window.confirm("用最新已保存稿替换尚未保存的本地修改？")) { setDraft(job.draftMarkdown ?? ""); setConflict(false); setFactsConfirmed(false); } }}>载入已保存稿</button></div> : null}<div className="resume-actions"><button className="button primary" disabled={Boolean(operation) || !dirty || conflict || !draft.trim()} onClick={saveDraft}>{operation === "draft" ? "正在保存…" : "保存草稿"}</button><span className="resume-muted">支持纯文本或 Markdown，不支持 HTML。</span></div>
            <div className="resume-export-area"><h4>下载或另存简历</h4><p>导出使用统一简洁模板，不保留原文件排版。使用前请核对每项经历、日期、技能和成果。</p><label className="resume-check"><input type="checkbox" checked={factsConfirmed} disabled={Boolean(operation) || dirty || conflict} onChange={e => setFactsConfirmed(e.target.checked)} /><span>我已核对这份已保存稿，确认事实准确。</span></label>{dirty ? <p className="resume-muted">请先保存修改，再确认事实并下载。</p> : null}<div className="resume-actions">{capabilities.exports.includes("docx") ? <button className="button primary" disabled={Boolean(operation) || dirty || conflict || !factsConfirmed} onClick={() => download("docx")}>{operation === "docx" ? "正在生成 Word…" : "下载 Word"}</button> : null}{capabilities.exports.includes("pdf") ? <button className="button ghost" disabled={Boolean(operation) || dirty || conflict || !factsConfirmed} onClick={() => download("pdf")}>{operation === "pdf" ? "正在生成 PDF…" : "下载 PDF"}</button> : null}</div><label className="resume-check"><input type="checkbox" checked={copyConfirmed} disabled={Boolean(operation) || dirty || conflict} onChange={e => setCopyConfirmed(e.target.checked)} /><span>在资料库另存一份独立新简历。原简历和既有面试选择保留，删除本次优化时新简历仍保留。</span></label><button className="button ghost" disabled={Boolean(operation) || dirty || conflict || !factsConfirmed || !copyConfirmed} onClick={saveAs}>{operation === "copy" ? "正在另存简历…" : job.savedDocumentId ? "刷新已另存状态" : "另存为新简历"}</button>{job.savedDocumentId ? <p className="resume-muted">此稿件版本已另存为新简历。 <Link to={routes.library}>打开资料库 →</Link></p> : null}<p className="resume-muted">编辑、下载和另存不会再次收费或占用次数。任务及源资料保留时，会员到期后仍可使用已完成结果。</p></div>
          </section>
        </> : <section className="panel" role="alert">本次优化尚无可用结果，请刷新进度。</section>}
      </section> : null}
    </>}
  </main>;
}
