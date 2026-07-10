import { useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import { detectMaterialUploadFormat, materialUploadAccept, materialUploadFormatLabel, type ContextLibrarySource, type KnowledgeCollection, type KnowledgeDocumentVersion, type KnowledgeFileKind } from "@offersteady/protocol";
import type { WebAppState } from "./domain";
import { routes } from "./routes";
import { Link } from "react-router-dom";
import { contextSourceStatusLabel, managedLibrarySources } from "./context-selection";
import { runAdapterOperation } from "./api-client";
import { materialUploadAdapter } from "./material-upload-adapter";
import { interviewAppAdapter } from "./app-adapter";

interface Props { readonly state: WebAppState; readonly setState: Dispatch<SetStateAction<WebAppState>> }
type MaterialTab = "resume" | "jd" | "knowledge";
type Dialog = "create-collection" | "upload-knowledge" | "add-source" | null;
type LibraryOperation = "create-collection" | "upload-knowledge" | "add-source" | "rename-collection" | "delete-collection" | `document:${string}` | null;

const supportedFormatsLabel = `支持上传 ${materialUploadFormatLabel}`;
const documentStatus: Record<KnowledgeDocumentVersion["status"], string> = { pending: "待确认", processing: "建立索引中", ready: "可用于面试", failed: "处理失败", disabled: "已停用", deleted: "已删除" };
const syncStatusLabel = { synced: "OSS已同步", processing: "同步中", missing_artifacts: "OSS缺失", failed: "同步失败", deleted: "已删除", unknown: "待校验" } as const;
const tabCopy: Record<MaterialTab, { title: string; detail: string; action: string }> = {
  resume: { title: "简历", detail: `维护可复用简历；具体使用哪一份，在每场面试准备时选择。${supportedFormatsLabel}。`, action: "＋ 添加简历" },
  jd: { title: "职位 JD", detail: `通过粘贴文本或文件保存目标岗位；不会自动加入任何面试。${supportedFormatsLabel}，也支持直接粘贴 JD 文本。`, action: "＋ 添加 JD" },
  knowledge: { title: "知识库", detail: `按主题管理知识材料，每场面试再选择需要的内容。${supportedFormatsLabel}。`, action: "＋ 新建资料库" },
};

const nextVersion = (version: string) => `v${Math.max(1, Number.parseInt(version.replace(/\D/g, ""), 10) || 1) + 1}`;

export function LibraryManager({ state, setState }: Props) {
  const [tab, setTab] = useState<MaterialTab>("knowledge");
  const [selectedId, setSelectedId] = useState(state.knowledgeCollections[0]?.id ?? "");
  const [dialog, setDialog] = useState<Dialog>(null);
  const [name, setName] = useState("");
  const [jdText, setJdText] = useState("");
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [quoteIssuedAt, setQuoteIssuedAt] = useState(0);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [operation, setOperation] = useState<LibraryOperation>(null);
  const [submittingUpload, setSubmittingUpload] = useState(false);
  const selected = state.knowledgeCollections.find(item => item.id === selectedId) ?? null;
  const documents = state.knowledgeDocuments.filter(item => item.collectionId === selectedId && item.status !== "deleted");
  const tabSources = managedLibrarySources(state.librarySources, state.account.id).filter(source => source.kind === tab);
  const allowanceRemaining = state.billing.activePass ? Math.max(0, state.billing.activePass.knowledgeAllowanceGranted - state.billing.activePass.knowledgeAllowanceUsed - state.billing.activePass.knowledgeAllowanceLocked) : 0;
  const tokenCount = pendingFile ? Math.max(1, Math.ceil((pendingFile.size || 12_000) / 4)) : 0;
  const knowledgeIndexPointsPer5000Tokens = state.billing.rates.knowledgeIndexPointsPer1000Tokens * 5;
  const billableUnits = tokenCount ? Math.ceil(tokenCount / 5000) : 0;
  const quotedPoints = tokenCount ? Math.max(state.billing.rates.knowledgeIndexMinimumPoints, billableUnits * knowledgeIndexPointsPer5000Tokens) : 0;
  const quoteSource = allowanceRemaining > 0 ? "pass_allowance" as const : "points" as const;
  const refreshFromBackend = async () => {
    const next = await runAdapterOperation(signal => interviewAppAdapter.loadState(signal));
    setState(next);
    return next;
  };
  const pollDocumentUntilSettled = (documentId: string) => {
    void (async () => {
      for (let attempt = 0; attempt < 12; attempt += 1) {
        await new Promise(resolve => window.setTimeout(resolve, attempt === 0 ? 800 : 1500));
        const next = await refreshFromBackend();
        const source = next.librarySources.find(item => item.id === documentId);
        const document = next.knowledgeDocuments.find(item => item.id === documentId);
        const status = source?.status ?? document?.status;
        if (status === "ready" || status === "failed" || status === "deleted" || status === "disabled") return;
      }
    })().catch(error => setError(error instanceof Error ? error.message : "资料状态刷新失败，请手动刷新页面"));
  };

  const openPrimary = () => { setName(""); setJdText(""); setPendingFile(null); setDialog(tab === "knowledge" ? "create-collection" : "add-source"); };
  const createCollection = async () => {
    const clean = name.trim(); if (!clean) return;
    setOperation("create-collection"); setError("");
    try {
      const created = await runAdapterOperation(signal => materialUploadAdapter.createKnowledgeCollection({ userId: state.account.id, name: clean }, signal));
      const collection: KnowledgeCollection = { id: created.collectionId, ownerUserId: created.ownerUserId, name: created.name, createdAtMs: created.createdAtMs, updatedAtMs: created.updatedAtMs };
      setState(current => ({ ...current, knowledgeCollections: [...current.knowledgeCollections, collection] }));
      setSelectedId(collection.id); setName(""); setDialog(null); setNotice("资料库已创建，空资料库不扣点");
    } catch (error) {
      setError(error instanceof Error ? error.message : "创建资料库失败，请稍后重试");
    } finally {
      setOperation(null);
    }
  };
  const uploadKnowledge = async () => {
    if (!pendingFile || !selected) return; const fileKind = detectMaterialUploadFormat(pendingFile.name) as KnowledgeFileKind | null; if (!fileKind) { setNotice(`仅支持 ${materialUploadFormatLabel}`); return; }
    if (!quoteIssuedAt || Date.now() - quoteIssuedAt >= 15 * 60_000) { setNotice("报价已过期，请刷新后重新确认"); return; }
    const points = quoteSource === "points" ? quotedPoints : 0; const projected = state.billing.balance - points; if (projected < 0) { setNotice("积分不足，文件未建立索引，可充值后继续"); return; }
    const uploadFile = pendingFile;
    const selectedCollection = selected;
    setSubmittingUpload(true); setError("");
    setPendingFile(null); setDialog(null); setNotice("资料正在后台上传并建立索引，你可以继续使用其他功能");
    const optimisticId = `uploading-${crypto.randomUUID()}`;
    const optimisticNow = Date.now();
    const optimisticDocument: KnowledgeDocumentVersion = {
      id: optimisticId,
      collectionId: selectedCollection.id,
      ownerUserId: state.account.id,
      displayName: uploadFile.name,
      fileKind,
      sizeBytes: uploadFile.size || 1024,
      contentFingerprint: `uploading:${uploadFile.name}:${optimisticNow}`,
      version: 1,
      status: "processing",
      syncStatus: "processing",
      createdAtMs: optimisticNow,
      safeSummary: "正在上传到 OSS，上传完成后会自动解析并建立索引。",
    };
    const optimisticSource: ContextLibrarySource = {
      id: optimisticId,
      ownerUserId: state.account.id,
      kind: "knowledge",
      displayName: uploadFile.name,
      version: "v1",
      status: "processing",
      processingState: "processing",
      syncStatus: "processing",
      updatedAtMs: optimisticNow,
      summary: "正在上传到 OSS，上传完成后会自动解析并建立索引。",
    };
    setState(current => ({
      ...current,
      knowledgeDocuments: [...current.knowledgeDocuments, optimisticDocument],
      librarySources: [...current.librarySources, optimisticSource],
    }));
    try {
      const completed = await runAdapterOperation(signal => materialUploadAdapter.uploadKnowledgeFile(state.account.id, selectedCollection.id, uploadFile, signal));
      const now = completed.source.updatedAtMs;
      const document: KnowledgeDocumentVersion = { id: completed.source.sourceId, collectionId: selectedCollection.id, ownerUserId: state.account.id, displayName: uploadFile.name, fileKind, sizeBytes: uploadFile.size || 1024, contentFingerprint: `prototype:${uploadFile.name}:${uploadFile.size}`, version: 1, status: "processing", syncStatus: "processing", createdAtMs: now, safeSummary: completed.source.summary ?? "文件已上传，等待建立索引。" };
      const source: ContextLibrarySource = { id: document.id, ownerUserId: state.account.id, kind: "knowledge", displayName: document.displayName, version: "v1", status: "processing", processingState: completed.source.processingState, syncStatus: "processing", updatedAtMs: now, ...(document.safeSummary ? { summary: document.safeSummary } : {}) };
      setState(current => ({
        ...current,
        knowledgeDocuments: current.knowledgeDocuments.map(item => item.id === optimisticId ? document : item),
        librarySources: current.librarySources.map(item => item.id === optimisticId ? source : item),
      }));
      pollDocumentUntilSettled(document.id);
      setNotice("资料已上传，等待服务端建立索引；索引成功后才会正式结算");
    } catch (error) {
      setState(current => ({
        ...current,
        knowledgeDocuments: current.knowledgeDocuments.map(item => item.id === optimisticId ? { ...item, status: "failed", syncStatus: "failed", safeSummary: "上传失败，请稍后重试。" } : item),
        librarySources: current.librarySources.map(item => item.id === optimisticId ? { ...item, status: "failed", syncStatus: "failed", summary: "上传失败，请稍后重试。" } : item),
      }));
      setError(error instanceof Error ? error.message : "上传知识资料失败，请稍后重试");
    } finally {
      setSubmittingUpload(false);
    }
  };
  const addSource = async () => {
    if (tab !== "resume" && tab !== "jd") return;
    const displayName = name.trim() || pendingFile?.name || (tab === "jd" && jdText.trim() ? jdText.trim().slice(0, 24) : "");
    if (!displayName || (tab === "resume" && !pendingFile) || (tab === "jd" && !pendingFile && !jdText.trim())) return;
    const uploadFile = pendingFile;
    const pastedJdText = jdText;
    const materialTab = tab;
    setSubmittingUpload(true); setError("");
    setDialog(null); setName(""); setJdText(""); setPendingFile(null); setNotice(`${materialTab === "resume" ? "简历" : "JD"}正在后台上传并解析，你可以继续使用其他功能`);
    const optimisticId = `uploading-${crypto.randomUUID()}`;
    const optimisticNow = Date.now();
    const optimisticSource: ContextLibrarySource = {
      id: optimisticId,
      ownerUserId: state.account.id,
      kind: materialTab,
      displayName,
      version: "v1",
      status: "processing",
      processingState: "processing",
      syncStatus: "processing",
      updatedAtMs: optimisticNow,
      summary: materialTab === "resume" ? "正在上传简历到 OSS，完成后会自动解析。" : "正在上传 JD 到 OSS，完成后会自动解析。",
    };
    setState(current => ({ ...current, librarySources: [...current.librarySources, optimisticSource] }));
    try {
      const completed = uploadFile
        ? await runAdapterOperation(signal => materialTab === "resume" ? materialUploadAdapter.uploadResume(state.account.id, uploadFile, signal) : materialUploadAdapter.uploadJobDescriptionFile(state.account.id, uploadFile, signal))
        : await runAdapterOperation(signal => materialUploadAdapter.createPastedJobDescription({ userId: state.account.id, text: pastedJdText, displayName }, signal));
      const now = completed.source.updatedAtMs; const source: ContextLibrarySource = { id: completed.source.sourceId, ownerUserId: state.account.id, kind: materialTab, displayName, version: "v1", status: "processing", processingState: completed.source.processingState, syncStatus: "processing", updatedAtMs: now, summary: completed.source.summary ?? (materialTab === "resume" ? "等待解析简历结构。" : "等待提取岗位职责与技能要求。") };
      setState(current => ({ ...current, librarySources: current.librarySources.map(item => item.id === optimisticId ? source : item) }));
      pollDocumentUntilSettled(source.id);
      setNotice(`${materialTab === "resume" ? "简历" : "JD"}已上传，等待服务端处理；尚未授权给任何面试`);
    } catch (error) {
      setState(current => ({
        ...current,
        librarySources: current.librarySources.map(item => item.id === optimisticId ? { ...item, status: "failed", syncStatus: "failed", summary: "上传失败，请稍后重试。" } : item),
      }));
      setError(error instanceof Error ? error.message : `${tab === "resume" ? "简历" : "JD"}上传失败，请稍后重试`);
    } finally {
      setSubmittingUpload(false);
    }
  };
  const updateSource = (sourceId: string, action: "ready" | "replace" | "delete") => setState(current => ({
    ...current,
    librarySources: current.librarySources.map(source => source.id !== sourceId ? source : action === "ready"
      ? { ...source, status: "ready", updatedAtMs: Date.now(), summary: source.kind === "resume" ? "已解析经历、技能与项目摘要。" : "已提取岗位职责、技能与业务背景。" }
      : action === "replace"
        ? { ...source, version: nextVersion(source.version), status: "processing", updatedAtMs: Date.now(), summary: "新版本正在解析，旧版本不再用于新选择。" }
        : { ...source, status: "deleted", updatedAtMs: Date.now() }),
  }));
  const removeSource = (source: ContextLibrarySource) => {
    if (!window.confirm(`删除“${source.displayName}”？它将立即停止参与后续回答。`)) return;
    const op = `document:${source.id}` as const;
    setOperation(op); setError("");
    void runAdapterOperation(signal => materialUploadAdapter.deleteDocument(state.account.id, source.documentId ?? source.id, signal))
      .then(() => refreshFromBackend())
      .then(() => setNotice("资料已删除，后端会继续清理 OSS 与向量产物"))
      .catch(error => setError(error instanceof Error ? error.message : "删除资料失败，请稍后重试"))
      .finally(() => setOperation(null));
  };
  const removeDocument = (document: KnowledgeDocumentVersion) => {
    if (!window.confirm(`删除“${document.displayName}”？它将立即停止参与后续回答，历史回答仅保留名称和版本。`)) return;
    const op = `document:${document.id}` as const;
    setOperation(op); setError("");
    void runAdapterOperation(signal => materialUploadAdapter.deleteDocument(state.account.id, document.documentId ?? document.id, signal))
      .then(() => refreshFromBackend())
      .then(() => setNotice("资料已删除，后端会继续清理 OSS 与向量产物"))
      .catch(error => setError(error instanceof Error ? error.message : "删除资料失败，请稍后重试"))
      .finally(() => setOperation(null));
  };
  const removeCollection = () => {
    if (!selected || !window.confirm(`删除资料库“${selected.name}”及其中 ${documents.length} 份资料？`)) return;
    setOperation("delete-collection");
    const ids = new Set(documents.map(item => item.id));
    void Promise.all(documents.map(document => runAdapterOperation(signal => materialUploadAdapter.deleteDocument(state.account.id, document.documentId ?? document.id, signal))))
      .then(() => refreshFromBackend())
      .then(nextState => {
        const next = nextState.knowledgeCollections.find(item => item.id !== selected.id);
        setSelectedId(next?.id ?? "");
        setNotice("资料库内资料已删除，未来面试不会再检索其中资料");
      })
      .catch(error => setError(error instanceof Error ? error.message : "删除资料库资料失败，请稍后重试"))
      .finally(() => setOperation(null));
  };
  const rename = () => {
    if (!selected) return; const next = window.prompt("新的资料库名称", selected.name)?.trim(); if (!next) return;
    setOperation("rename-collection");
    setState(current => ({ ...current, knowledgeCollections: current.knowledgeCollections.map(item => item.id === selected.id ? { ...item, name: next, updatedAtMs: Date.now() } : item) }));
    setNotice("资料库已重命名"); setOperation(null);
  };
  const updateDocument = (document: KnowledgeDocumentVersion, action: "ready" | "retry" | "replace" | "rename" | "disable") => {
    const op = `document:${document.id}` as const; setOperation(op);
    const now = Date.now();
    const nextName = action === "rename" ? window.prompt("新的资料名称", document.displayName)?.trim() : "";
    if (action === "rename" && !nextName) { setOperation(null); return; }
    setState(current => ({
      ...current,
      knowledgeDocuments: current.knowledgeDocuments.map(item => item.id !== document.id ? item : action === "ready"
        ? { ...item, status: "ready", safeSummary: item.safeSummary && item.safeSummary !== "文件已上传，等待建立索引。" ? item.safeSummary : "已建立可检索索引，可在面试准备中选择。", createdAtMs: item.createdAtMs }
        : action === "retry"
          ? { ...item, status: "processing", safeSummary: "正在重新建立索引，成功前不会用于新面试。" }
          : action === "replace"
            ? { ...item, version: item.version + 1, status: "processing", createdAtMs: now, contentFingerprint: `${item.contentFingerprint}:v${item.version + 1}`, safeSummary: "新版本正在解析，旧版本不再用于新选择。" }
            : action === "rename"
              ? { ...item, displayName: nextName || item.displayName }
              : { ...item, status: "disabled", safeSummary: "已停用，不参与当前面试。" }),
      librarySources: current.librarySources.map(source => source.id !== document.id ? source : action === "ready"
        ? { ...source, status: "ready", updatedAtMs: now, summary: "已建立可检索索引，可在面试准备中选择。" }
        : action === "retry" || action === "replace"
          ? { ...source, version: action === "replace" ? nextVersion(source.version) : source.version, status: "processing", updatedAtMs: now, summary: action === "replace" ? "新版本正在解析，旧版本不再用于新选择。" : "正在重新建立索引，成功前不会用于新面试。" }
          : action === "rename"
            ? { ...source, displayName: nextName || source.displayName, updatedAtMs: now }
            : { ...source, status: "disabled", updatedAtMs: now, summary: "已停用，不参与当前面试。" }),
    }));
    setNotice(action === "ready" ? "资料已标记为可用于面试" : action === "retry" ? "已重新提交索引任务" : action === "replace" ? "已创建新版本并进入解析" : action === "rename" ? "资料已重命名" : "资料已停用");
    setOperation(null);
  };

  return <main className="app-page"><header className="page-header"><div><span className="kicker">INTERVIEW MATERIALS</span><h1>面试资料</h1><p>{tabCopy[tab].detail}</p></div><button className="button primary" onClick={openPrimary}>{tabCopy[tab].action}</button></header>
    <nav className="material-tabs" aria-label="资料类型">{(["resume", "jd", "knowledge"] as const).map(item => <button key={item} className={tab === item ? "active" : ""} aria-current={tab === item ? "page" : undefined} onClick={() => setTab(item)}><span>{item === "resume" ? "R" : item === "jd" ? "J" : "K"}</span><strong>{tabCopy[item].title}</strong><small>{item === "knowledge" ? `${state.knowledgeDocuments.filter(doc => doc.status !== "deleted").length} 份` : `${state.librarySources.filter(source => source.kind === item && source.status !== "deleted").length} 份`}</small></button>)}</nav>
    {notice ? <div className="billing-notice" role="status">{notice}</div> : null}
    {error ? <div className="inline-error" role="alert">{error}</div> : null}
    {tab === "knowledge" ? <div className="library-layout"><aside className="panel collection-list"><div className="panel-heading"><h2>我的知识库</h2><span>{operation === "create-collection" ? "创建中" : `${state.knowledgeCollections.length} 个`}</span></div>{state.knowledgeCollections.length ? state.knowledgeCollections.map(item => <button className={item.id === selectedId ? "active" : ""} key={item.id} disabled={operation !== null} onClick={() => setSelectedId(item.id)}><span>◇</span><div><strong>{item.name}</strong><small>{state.knowledgeDocuments.filter(doc => doc.collectionId === item.id && doc.status !== "deleted").length} 份资料</small></div></button>) : <div className="collection-empty"><strong>还没有知识库</strong><small>先创建集合，再添加文件建立索引。</small><button className="button ghost" onClick={() => setDialog("create-collection")}>新建资料库</button></div>}</aside><section className="panel collection-detail">{selected ? <><div className="collection-head"><div><h2>{selected.name}</h2><p>空资料库免费；知识材料 {state.billing.rates.knowledgeIndexMinimumPoints} 点起，每 5,000 Token {knowledgeIndexPointsPer5000Tokens} 点。15/30 天会员含 2 份额度。{supportedFormatsLabel}。</p></div><div><button className="button ghost" disabled={operation !== null} onClick={rename}>重命名</button><button className="button danger" disabled={operation !== null} onClick={removeCollection}>{operation === "delete-collection" ? "删除中…" : "删除资料库"}</button><button className="button primary" disabled={operation !== null} onClick={() => setDialog("upload-knowledge")}>＋ 添加资料</button></div></div>{documents.length ? <div className="document-list">{documents.map(document => <article key={document.id}><span className="resource-icon">{document.fileKind.toUpperCase()}</span><div><strong>{document.displayName}</strong><small>v{document.version} · {Math.max(1, Math.round(document.sizeBytes / 1024))} KB · {documentStatus[document.status]} · {syncStatusLabel[document.syncStatus ?? "unknown"]}</small><p>{document.safeSummary ?? document.unavailableReason ?? "正在构建中，完成前不能用于面试。"}</p></div><div><span className={`state-mark ${document.status === "ready" && document.syncStatus !== "missing_artifacts" ? "ready" : document.status === "processing" || document.status === "pending" ? "processing" : "error"}`}>{document.syncStatus === "missing_artifacts" ? "OSS缺失" : documentStatus[document.status]}</span>{document.status === "failed" || document.syncStatus === "missing_artifacts" ? <button disabled={operation !== null} onClick={() => pollDocumentUntilSettled(document.id)}>刷新状态</button> : null}{document.status === "ready" ? <button disabled={operation !== null} onClick={() => updateDocument(document, "disable")}>停用</button> : null}<button disabled={operation !== null} onClick={() => updateDocument(document, "rename")}>重命名</button><button disabled={operation !== null} onClick={() => removeDocument(document)}>{operation === `document:${document.id}` ? "删除中…" : "删除"}</button></div></article>)}</div> : <EmptyMaterial title="这个知识库还是空的" detail={`添加并成功索引文件后才结算；会员额度适用于知识材料，不是空集合。${supportedFormatsLabel}。`} action="添加第一份资料" onAction={() => setDialog("upload-knowledge")} />}</> : <EmptyMaterial title="创建你的第一个知识库" detail={`可按岗位、技术方向或项目经历分类。${supportedFormatsLabel}。`} action="新建资料库" onAction={() => setDialog("create-collection")} />}</section></div> : <section className="panel typed-material-panel"><div className="panel-heading"><div><h2>{tabCopy[tab].title}</h2><p>这里只维护可复用资料；请在真正进入面试准备时选择，本页新增不会自动授权。</p><small>{tab === "jd" ? `${supportedFormatsLabel}，也支持直接粘贴 JD 文本。` : `${supportedFormatsLabel}。`}</small></div><Link to={routes.app}>前往面试准备 →</Link></div>{tabSources.length ? <div className="typed-material-list">{tabSources.map(source => <article key={source.id}><span className="resource-icon">{source.kind === "resume" ? "R" : "J"}</span><div><strong>{source.displayName}</strong><small>{source.version} · {contextSourceStatusLabel[source.status]} · {syncStatusLabel[source.syncStatus ?? "unknown"]} · {new Date(source.updatedAtMs).toLocaleDateString("zh-CN")}</small><p>{source.status === "ready" ? source.kind === "resume" ? "简历已处理完成，可在面试准备中选择。" : "职位 JD 已处理完成，可在面试准备中选择。" : source.status === "processing" ? "正在后台解析，完成后可在面试准备中选择。" : source.unavailableReason ?? "资料暂不可用，请刷新状态。"}</p></div><div><span className={`state-mark ${source.status === "ready" && source.syncStatus !== "missing_artifacts" ? "ready" : source.status === "processing" ? "processing" : "error"}`}>{source.syncStatus === "missing_artifacts" ? "OSS缺失" : contextSourceStatusLabel[source.status]}</span>{source.status === "processing" ? <small>正在构建中</small> : source.status === "failed" || source.syncStatus === "missing_artifacts" ? <button onClick={() => pollDocumentUntilSettled(source.id)}>刷新状态</button> : null}<button className="danger-link" disabled={operation !== null} onClick={() => removeSource(source)}>{operation === `document:${source.id}` ? "删除中…" : "删除"}</button></div></article>)}</div> : <EmptyMaterial title={`还没有${tabCopy[tab].title}`} detail={tab === "resume" ? `添加后可在不同面试中选择使用。${supportedFormatsLabel}。` : `支持上传 ${supportedFormatsLabel.replace("支持上传 ", "")}，也支持粘贴 JD 文本。`} action={tabCopy[tab].action.replace("＋ ", "")} onAction={openPrimary} />}</section>}
    {dialog === "create-collection" ? <DialogShell title="新建知识库" onClose={() => setDialog(null)}><p>创建集合免费，只有文件成功解析并建立索引后才扣点。</p><label className="checkout-field">资料库名称<input value={name} onChange={event => setName(event.target.value)} placeholder="例如：前端架构面试" /></label><div className="sheet-actions"><button className="button ghost" disabled={operation !== null} onClick={() => setDialog(null)}>取消</button><button className="button primary" disabled={!name.trim() || operation !== null} onClick={createCollection}>{operation === "create-collection" ? "创建中…" : "确认创建"}</button></div></DialogShell> : null}
    {dialog === "upload-knowledge" ? <DialogShell title="添加并建立索引" onClose={() => setDialog(null)}><p>{supportedFormatsLabel}。选择后由服务端计算 Token 并生成短期报价。</p><label className="checkout-field">选择文件<input aria-label="选择资料文件" type="file" accept={materialUploadAccept} disabled={submittingUpload} onChange={event => { const file = event.target.files?.[0] ?? null; setPendingFile(file); setQuoteIssuedAt(file ? Date.now() : 0); }} /></label><div className="index-estimate"><span>{pendingFile ? "服务端预估报价" : "等待选择文件"}</span><strong>{pendingFile ? quoteSource === "pass_allowance" ? "使用 1 份会员额度" : `${quotedPoints} 点` : `${state.billing.rates.knowledgeIndexMinimumPoints} 点起`}</strong>{pendingFile ? <><small>{tokenCount.toLocaleString("zh-CN")} Token · {billableUnits} 个计费单位 · 目录 v{state.billing.rates.catalogVersion}</small><small>{quoteSource === "pass_allowance" ? `当前剩余 ${allowanceRemaining} 份，成功后剩余 ${allowanceRemaining - 1} 份` : `当前 ${state.billing.balance} 点 → 成功后 ${state.billing.balance - quotedPoints} 点`}</small><button type="button" disabled={submittingUpload} onClick={() => setQuoteIssuedAt(Date.now())}>刷新报价</button></> : null}<small>每 5,000 Token {knowledgeIndexPointsPer5000Tokens} 点，最低 {state.billing.rates.knowledgeIndexMinimumPoints} 点；失败或取消会释放预留或额度。</small></div><div className="sheet-actions"><button className="button ghost" disabled={submittingUpload} onClick={() => { setPendingFile(null); setQuoteIssuedAt(0); setDialog(null); }}>取消</button>{pendingFile && quoteSource === "points" && state.billing.balance < quotedPoints ? <Link className="button primary" to={routes.billing}>积分不足，去充值</Link> : <button className="button primary" disabled={!pendingFile || submittingUpload} onClick={uploadKnowledge}>{submittingUpload ? "提交中…" : "确认报价并建立索引"}</button>}</div></DialogShell> : null}
    {dialog === "add-source" && tab !== "knowledge" ? <DialogShell title={tab === "resume" ? "添加简历" : "添加职位 JD"} onClose={() => setDialog(null)}><p>{tab === "resume" ? `${supportedFormatsLabel}。资料只加入可选列表，不会自动用于任何面试。` : `${supportedFormatsLabel}，也支持直接粘贴 JD 文本。资料只加入可选列表，不会自动用于任何面试。`}</p><label className="checkout-field">显示名称（可选）<input value={name} disabled={submittingUpload} onChange={event => setName(event.target.value)} placeholder={tab === "resume" ? "例如：高级前端简历" : "例如：示例公司前端 JD"} /></label><label className="checkout-field">选择文件<input aria-label={tab === "resume" ? "选择简历文件" : "选择 JD 文件"} type="file" accept={materialUploadAccept} disabled={submittingUpload} onChange={event => setPendingFile(event.target.files?.[0] ?? null)} /></label>{tab === "jd" ? <label className="checkout-field">或者粘贴 JD 文本<textarea aria-label="JD 内容" value={jdText} disabled={submittingUpload} onChange={event => setJdText(event.target.value)} placeholder="粘贴岗位职责、必备技能和加分项" /></label> : null}<div className="sheet-actions"><button className="button ghost" disabled={submittingUpload} onClick={() => setDialog(null)}>取消</button><button className="button primary" disabled={(tab === "resume" ? !pendingFile : !pendingFile && !jdText.trim()) || submittingUpload} onClick={addSource}>{submittingUpload ? "提交中…" : "添加并解析"}</button></div></DialogShell> : null}
  </main>;
}

function EmptyMaterial({ title, detail, action, onAction }: { readonly title: string; readonly detail: string; readonly action: string; readonly onAction: () => void }) { return <section className="empty-state"><span>◇</span><h2>{title}</h2><p>{detail}</p><button className="button primary" onClick={onAction}>{action}</button></section>; }
function DialogShell({ title, onClose, children }: { readonly title: string; readonly onClose: () => void; readonly children: ReactNode }) { return <div className="sheet-backdrop" role="dialog" aria-modal="true" aria-labelledby="material-dialog-title"><section className="sheet"><button className="sheet-close" aria-label="关闭" onClick={onClose}>×</button><h2 id="material-dialog-title">{title}</h2>{children}</section></div>; }
