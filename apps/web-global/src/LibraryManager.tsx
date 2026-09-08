import {
  useRef,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from "react";
import {
  detectMaterialUploadFormat,
  materialUploadAccept,
  materialUploadFormatLabel,
  type ContextLibrarySource,
  type KnowledgeCollection,
  type KnowledgeDocumentVersion,
  type KnowledgeFileKind,
} from "@offersteady/protocol";
import type { WebAppState } from "./domain";
import { routes } from "./routes";
import { Link } from "react-router-dom";
import {
  displayedContextSourceStatus,
  managedLibrarySources,
} from "./context-selection";
import { runAdapterOperation } from "./api-client";
import { materialUploadAdapter, saveMaterialDownload } from "./material-upload-adapter";
import type { PreparedKnowledgeUpload } from "./material-upload-adapter";
import { interviewAppAdapter } from "./app-adapter";
import { globalEditionMetadata } from "./product-edition";

interface Props {
  readonly state: WebAppState;
  readonly setState: Dispatch<SetStateAction<WebAppState>>;
}
type MaterialTab = "resume" | "jd" | "knowledge";
type Dialog = "create-collection" | "upload-knowledge" | "add-source" | null;
type LibraryOperation =
  | "create-collection"
  | "upload-knowledge"
  | "add-source"
  | "rename-collection"
  | "delete-collection"
  | `document:${string}`
  | null;

const supportedFormatsLabel = `Upload ${materialUploadFormatLabel}`;
const documentStatus: Record<KnowledgeDocumentVersion["status"], string> = {
  pending: "Waiting for confirmation",
  processing: "Indexing",
  ready: "Ready",
  failed: "Processing failed",
  disabled: "Disabled",
  deleted: "Deleted",
};
const displayedDocumentStatus = (document: KnowledgeDocumentVersion) =>
  document.status === "failed" && document.safeSummary?.startsWith("Upload failed")
    ? "Upload failed"
    : documentStatus[document.status];
const syncStatusLabel = {
  synced: "Storage synced",
  processing: "Syncing",
  missing_artifacts: "File missing",
  failed: "Sync failed",
  deleted: "Deleted",
  unknown: "Pending verification",
} as const;
const tabCopy: Record<
  MaterialTab,
  {
    title: string;
    detail: string;
    action: string;
    emptyTitle: string;
    emptyDetail: string;
    emptyAction: string;
  }
> = {
  resume: {
    title: "Resume",
    detail: `Keep reusable resumes here, then select one during interview preparation. ${supportedFormatsLabel}.`,
    action: "+ Add Resume",
    emptyTitle: "No resumes yet",
    emptyDetail: `Add reusable material and select it for the interviews that need it. ${supportedFormatsLabel}.`,
    emptyAction: "Add Resume",
  },
  jd: {
    title: "Job Description",
    detail: `Save target roles from pasted text or a file. Nothing is selected automatically. ${supportedFormatsLabel}, or paste the job description.`,
    action: "+ Add JD",
    emptyTitle: "No job descriptions yet",
    emptyDetail: `${supportedFormatsLabel}, or paste the job description directly.`,
    emptyAction: "Add JD",
  },
  knowledge: {
    title: "Knowledge Base",
    detail: `Organize reference material by topic, then select what each interview needs. ${supportedFormatsLabel}.`,
    action: "+ New Library",
    emptyTitle: "Create your first knowledge base",
    emptyDetail: `Organize by role, technical area, or project. ${supportedFormatsLabel}.`,
    emptyAction: "New Library",
  },
};

const nextVersion = (version: string) =>
  `v${Math.max(1, Number.parseInt(version.replace(/\D/g, ""), 10) || 1) + 1}`;

export function LibraryManager({ state, setState }: Props) {
  const [tab, setTab] = useState<MaterialTab>("knowledge");
  const [selectedId, setSelectedId] = useState(
    state.knowledgeCollections[0]?.id ?? "",
  );
  const [dialog, setDialog] = useState<Dialog>(null);
  const [name, setName] = useState("");
  const [jdText, setJdText] = useState("");
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [preparedKnowledgeUpload, setPreparedKnowledgeUpload] =
    useState<PreparedKnowledgeUpload | null>(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [operation, setOperation] = useState<LibraryOperation>(null);
  const [submittingUpload, setSubmittingUpload] = useState(false);
  const refreshGenerationRef = useRef(0);
  const selected =
    state.knowledgeCollections.find((item) => item.id === selectedId) ?? null;
  const documents = state.knowledgeDocuments.filter(
    (item) => item.collectionId === selectedId && item.status !== "deleted",
  );
  const tabSources = managedLibrarySources(
    state.librarySources,
    state.account.id,
  ).filter((source) => source.kind === tab);
  const serviceQuote = preparedKnowledgeUpload?.quote ?? null;
  const tokenCount = serviceQuote?.tokenCount ?? 0;
  const knowledgeIndexPointsPer5000Tokens =
    state.billing.rates.knowledgeIndexPointsPer1000Tokens * 5;
  const quotedPoints = serviceQuote?.pointCost ?? 0;
  const quoteSource = serviceQuote?.entitlementSource ?? "points";
  const refreshFromBackend = async () => {
    const generation = ++refreshGenerationRef.current;
    const next = await runAdapterOperation((signal) =>
      interviewAppAdapter.loadState(signal),
    );
    if (generation === refreshGenerationRef.current) setState(next);
    return next;
  };
  const invalidatePendingRefreshes = () => {
    refreshGenerationRef.current += 1;
  };
  const pollDocumentUntilSettled = (documentId: string) => {
    void (async () => {
      for (let attempt = 0; attempt < 12; attempt += 1) {
        await new Promise((resolve) =>
          window.setTimeout(resolve, attempt === 0 ? 800 : 1500),
        );
        const next = await refreshFromBackend();
        const source = next.librarySources.find(
          (item) => item.id === documentId,
        );
        const document = next.knowledgeDocuments.find(
          (item) => item.id === documentId,
        );
        const status = source?.status ?? document?.status;
        if (
          status === "ready" ||
          status === "failed" ||
          status === "deleted" ||
          status === "disabled"
        )
          return;
      }
    })().catch((error) =>
      setError(
        error instanceof Error
          ? error.message
          : "资料状态刷新失败，请手动刷新页面",
      ),
    );
  };

  const retryDocument = async (documentId: string) => {
    const op = `document:${documentId}` as const;
    setOperation(op);
    setError("");
    try {
      await runAdapterOperation((signal) =>
        materialUploadAdapter.retryDocument(
          state.account.id,
          documentId,
          signal,
        ),
      );
      setState((current) => ({
        ...current,
        knowledgeDocuments: current.knowledgeDocuments.map((item) =>
          item.id === documentId || item.documentId === documentId
            ? {
                ...item,
                status: "processing",
                safeSummary: "已重新提交处理任务，完成前不会用于新面试。",
              }
            : item,
        ),
        librarySources: current.librarySources.map((item) =>
          item.id === documentId || item.documentId === documentId
            ? {
                ...item,
                status: "processing",
                processingState: "processing",
                summary: "已重新提交处理任务，完成前不会用于新面试。",
              }
            : item,
        ),
      }));
      setNotice("已重新提交资料处理任务，系统会自动刷新结果");
      pollDocumentUntilSettled(documentId);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? `${reason.message}. Upload the file again or contact support through the user guide.`
          : "重新处理失败，请重新上传文件或联系客服。",
      );
    } finally {
      setOperation(null);
    }
  };

  const openPrimary = () => {
    setName("");
    setJdText("");
    setPendingFile(null);
    setPreparedKnowledgeUpload(null);
    setDialog(tab === "knowledge" ? "create-collection" : "add-source");
  };
  const createCollection = async () => {
    const clean = name.trim();
    if (!clean) return;
    setOperation("create-collection");
    setError("");
    try {
      const created = await runAdapterOperation((signal) =>
        materialUploadAdapter.createKnowledgeCollection(
          { userId: state.account.id, name: clean },
          signal,
        ),
      );
      const collection: KnowledgeCollection = {
        id: created.collectionId,
        ownerUserId: created.ownerUserId,
        name: created.name,
        createdAtMs: created.createdAtMs,
        updatedAtMs: created.updatedAtMs,
      };
      setState((current) => ({
        ...current,
        knowledgeCollections: [...current.knowledgeCollections, collection],
      }));
      setSelectedId(collection.id);
      setName("");
      setDialog(null);
      setNotice("资料库已创建，空资料库不扣点");
    } catch (error) {
      setError(
        error instanceof Error ? error.message : "创建资料库失败，请稍后重试",
      );
    } finally {
      setOperation(null);
    }
  };
  const uploadKnowledge = async () => {
    if (!pendingFile || !selected || !preparedKnowledgeUpload) return;
    const fileKind = detectMaterialUploadFormat(
      pendingFile.name,
    ) as KnowledgeFileKind | null;
    if (!fileKind) {
      setNotice(`Supported formats: ${materialUploadFormatLabel}`);
      return;
    }
    if (Date.now() >= preparedKnowledgeUpload.quote.expiresAtMs) {
      setNotice("报价已过期，请刷新后重新确认");
      return;
    }
    const points = quoteSource === "points" ? quotedPoints : 0;
    const projected = state.billing.balance - points;
    if (projected < 0) {
      setNotice("积分不足，文件未建立索引，可充值后继续");
      return;
    }
    const uploadFile = pendingFile;
    const selectedCollection = selected;
    setSubmittingUpload(true);
    setError("");
    setPendingFile(null);
    setDialog(null);
    setNotice("资料正在后台上传并建立索引，你可以继续使用其他功能");
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
    setState((current) => ({
      ...current,
      knowledgeDocuments: [...current.knowledgeDocuments, optimisticDocument],
      librarySources: [...current.librarySources, optimisticSource],
    }));
    try {
      const completed = await runAdapterOperation((signal) =>
        materialUploadAdapter.confirmKnowledgeFile(
          state.account.id,
          selectedCollection.id,
          uploadFile,
          preparedKnowledgeUpload,
          signal,
        ),
      );
      const now = completed.source.updatedAtMs;
      const document: KnowledgeDocumentVersion = {
        id: completed.source.sourceId,
        collectionId: selectedCollection.id,
        ownerUserId: state.account.id,
        displayName: completed.source.displayName,
        fileKind,
        sizeBytes: uploadFile.size || 1024,
        contentFingerprint: `prototype:${uploadFile.name}:${uploadFile.size}`,
        version: 1,
        status: "processing",
        syncStatus: "processing",
        createdAtMs: now,
        safeSummary: completed.source.summary ?? "文件已上传，等待建立索引。",
      };
      const source: ContextLibrarySource = {
        id: document.id,
        ownerUserId: state.account.id,
        kind: "knowledge",
        displayName: document.displayName,
        version: "v1",
        status: "processing",
        processingState: completed.source.processingState,
        syncStatus: "processing",
        updatedAtMs: now,
        ...(document.safeSummary ? { summary: document.safeSummary } : {}),
      };
      setState((current) => ({
        ...current,
        knowledgeDocuments: current.knowledgeDocuments.map((item) =>
          item.id === optimisticId ? document : item,
        ),
        librarySources: current.librarySources.map((item) =>
          item.id === optimisticId ? source : item,
        ),
      }));
      pollDocumentUntilSettled(document.id);
      setNotice("报价已由服务端确认并预留；索引成功后自动结算，失败则自动释放");
    } catch (error) {
      setState((current) => ({
        ...current,
        knowledgeDocuments: current.knowledgeDocuments.map((item) =>
          item.id === optimisticId
            ? {
                ...item,
                status: "failed",
                syncStatus: "failed",
                safeSummary: "Upload failed. Please try again.",
              }
            : item,
        ),
        librarySources: current.librarySources.map((item) =>
          item.id === optimisticId
            ? {
                ...item,
                status: "failed",
                syncStatus: "failed",
                summary: "Upload failed. Please try again.",
              }
            : item,
        ),
      }));
      setError(
        error instanceof Error
          ? error.message
          : "The knowledge file could not be uploaded. Please try again.",
      );
    } finally {
      setSubmittingUpload(false);
    }
  };

  const prepareKnowledgeQuote = async (file: File | null) => {
    setPendingFile(file);
    setPreparedKnowledgeUpload(null);
    setError("");
    if (!file || !selected) return;
    setQuoteLoading(true);
    try {
      const prepared = await runAdapterOperation((signal) =>
        materialUploadAdapter.prepareKnowledgeFile(
          state.account.id,
          selected.id,
          file,
          signal,
        ),
      );
      setPreparedKnowledgeUpload(prepared);
      setNotice("服务端已按解析后的正文生成最终报价，请确认后建立索引");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "文件解析或报价失败，请重新选择文件");
    } finally {
      setQuoteLoading(false);
    }
  };
  const addSource = async () => {
    if (tab !== "resume" && tab !== "jd") return;
    const displayName =
      name.trim() ||
      pendingFile?.name ||
      (tab === "jd" && jdText.trim() ? jdText.trim().slice(0, 24) : "");
    if (
      !displayName ||
      (tab === "resume" && !pendingFile) ||
      (tab === "jd" && !pendingFile && !jdText.trim())
    )
      return;
    const uploadFile = pendingFile;
    const pastedJdText = jdText;
    const materialTab = tab;
    setSubmittingUpload(true);
    setError("");
    setDialog(null);
    setName("");
    setJdText("");
    setPendingFile(null);
    setNotice(
      `${materialTab === "resume" ? "Resume" : "Job description"} is uploading and processing in the background. You can continue using other features.`,
    );
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
      summary:
        materialTab === "resume"
          ? "正在上传简历到 OSS，完成后会自动解析。"
          : "正在上传 JD 到 OSS，完成后会自动解析。",
    };
    setState((current) => ({
      ...current,
      librarySources: [...current.librarySources, optimisticSource],
    }));
    try {
      const completed = uploadFile
        ? await runAdapterOperation((signal) =>
            materialTab === "resume"
              ? materialUploadAdapter.uploadResume(
                  state.account.id,
                  uploadFile,
                  signal,
                )
              : materialUploadAdapter.uploadJobDescriptionFile(
                  state.account.id,
                  uploadFile,
                  signal,
                ),
          )
        : await runAdapterOperation((signal) =>
            materialUploadAdapter.createPastedJobDescription(
              { userId: state.account.id, text: pastedJdText, displayName },
              signal,
            ),
          );
      const now = completed.source.updatedAtMs;
      const source: ContextLibrarySource = {
        id: completed.source.sourceId,
        ownerUserId: state.account.id,
        kind: materialTab,
        displayName: completed.source.displayName,
        version: "v1",
        status: "processing",
        processingState: completed.source.processingState,
        syncStatus: "processing",
        updatedAtMs: now,
        summary:
          completed.source.summary ??
          (materialTab === "resume"
            ? "等待解析简历结构。"
            : "等待提取岗位职责与技能要求。"),
      };
      setState((current) => ({
        ...current,
        librarySources: current.librarySources.map((item) =>
          item.id === optimisticId ? source : item,
        ),
      }));
      pollDocumentUntilSettled(source.id);
      setNotice(
        `${materialTab === "resume" ? "Resume" : "Job description"} uploaded and waiting for processing. It is not selected for any interview yet.`,
      );
    } catch (error) {
      setState((current) => ({
        ...current,
        librarySources: current.librarySources.map((item) =>
          item.id === optimisticId
            ? {
                ...item,
                status: "failed",
                syncStatus: "failed",
                summary: "Upload failed. Please try again.",
              }
            : item,
        ),
      }));
      setError(
        error instanceof Error
          ? error.message
          : `${tab === "resume" ? "Resume" : "Job description"} upload failed. Please try again.`,
      );
    } finally {
      setSubmittingUpload(false);
    }
  };
  const updateSource = (
    sourceId: string,
    action: "ready" | "replace" | "delete",
  ) =>
    setState((current) => ({
      ...current,
      librarySources: current.librarySources.map((source) =>
        source.id !== sourceId
          ? source
          : action === "ready"
            ? {
                ...source,
                status: "ready",
                updatedAtMs: Date.now(),
                summary:
                  source.kind === "resume"
                    ? "已解析经历、技能与项目摘要。"
                    : "已提取岗位职责、技能与业务背景。",
              }
            : action === "replace"
              ? {
                  ...source,
                  version: nextVersion(source.version),
                  status: "processing",
                  updatedAtMs: Date.now(),
                  summary: "新版本正在解析，旧版本不再用于新选择。",
                }
              : { ...source, status: "deleted", updatedAtMs: Date.now() },
      ),
    }));
  const removeSource = (source: ContextLibrarySource) => {
    if (
      !window.confirm(`Delete “${source.displayName}”? It will no longer be used for future answers.`)
    )
      return;
    const op = `document:${source.id}` as const;
    setOperation(op);
    setError("");
    setNotice("");
    invalidatePendingRefreshes();
    void runAdapterOperation((signal) =>
      materialUploadAdapter.deleteDocument(
        state.account.id,
        source.documentId ?? source.id,
        signal,
      ),
    )
      .then(() => refreshFromBackend())
      .catch((error) =>
        setError(
          error instanceof Error ? error.message : "删除资料失败，请稍后重试",
        ),
      )
      .finally(() => setOperation(null));
  };
  const downloadDocument = (documentId: string) => {
    const op = `document:${documentId}` as const;
    setOperation(op);
    setError("");
    void runAdapterOperation(signal => materialUploadAdapter.downloadDocument(state.account.id, documentId, signal))
      .then(result => { saveMaterialDownload(result); setNotice("原始资料已开始下载"); })
      .catch(error => setError(error instanceof Error ? error.message : "资料下载失败，请稍后重试"))
      .finally(() => setOperation(null));
  };
  const renameSource = (source: ContextLibrarySource) => {
    const nextName = window.prompt("New material name", source.displayName)?.trim();
    if (!nextName) return;
    const documentId = source.documentId ?? source.id;
    const op = `document:${documentId}` as const;
    setOperation(op);
    setError("");
    invalidatePendingRefreshes();
    void runAdapterOperation(signal => materialUploadAdapter.renameDocument(state.account.id, documentId, nextName, signal))
      .then(() => refreshFromBackend())
      .then(() => setNotice("资料已重命名并保存"))
      .catch(error => setError(error instanceof Error ? error.message : "重命名资料失败，请稍后重试"))
      .finally(() => setOperation(null));
  };
  const removeDocument = (document: KnowledgeDocumentVersion) => {
    if (
      !window.confirm(
        `Delete “${document.displayName}”? It will stop contributing to future answers. Existing answers will retain only its name and version.`,
      )
    )
      return;
    const op = `document:${document.id}` as const;
    setOperation(op);
    setError("");
    setNotice("");
    invalidatePendingRefreshes();
    void runAdapterOperation((signal) =>
      materialUploadAdapter.deleteDocument(
        state.account.id,
        document.documentId ?? document.id,
        signal,
      ),
    )
      .then(() => refreshFromBackend())
      .catch((error) =>
        setError(
          error instanceof Error ? error.message : "删除资料失败，请稍后重试",
        ),
      )
      .finally(() => setOperation(null));
  };
  const removeCollection = () => {
    if (
      !selected ||
      !window.confirm(
        `Delete the “${selected.name}” collection and its ${documents.length} materials?`,
      )
    )
      return;
    setOperation("delete-collection");
    invalidatePendingRefreshes();
    const deletingCollectionId = selected.id;
    void runAdapterOperation((signal) =>
      materialUploadAdapter.deleteKnowledgeCollection(
        state.account.id,
        deletingCollectionId,
        signal,
      ),
    )
      .then(() => refreshFromBackend())
      .then((nextState) => {
        const next = nextState.knowledgeCollections.find(
          (item) => item.id !== deletingCollectionId,
        );
        setSelectedId(next?.id ?? "");
        setNotice("资料库已删除，其中资料不会再参与未来面试");
      })
      .catch((error) =>
        setError(
          error instanceof Error
            ? error.message
            : "删除资料库失败，请稍后重试",
        ),
      )
      .finally(() => setOperation(null));
  };
  const rename = () => {
    if (!selected) return;
    const next = window.prompt("New collection name", selected.name)?.trim();
    if (!next) return;
    setOperation("rename-collection");
    setError("");
    invalidatePendingRefreshes();
    void runAdapterOperation((signal) =>
      materialUploadAdapter.renameKnowledgeCollection(
        state.account.id,
        selected.id,
        next,
        signal,
      ),
    )
      .then(() => refreshFromBackend())
      .then(() => setNotice("资料库已重命名并保存"))
      .catch((error) =>
        setError(
          error instanceof Error ? error.message : "重命名资料库失败，请稍后重试",
        ),
      )
      .finally(() => setOperation(null));
  };
  const updateDocument = (
    document: KnowledgeDocumentVersion,
    action: "ready" | "retry" | "replace" | "rename" | "disable" | "enable",
  ) => {
    const op = `document:${document.id}` as const;
    setOperation(op);
    setError("");
    if (action === "disable" || action === "enable") {
      invalidatePendingRefreshes();
      void runAdapterOperation((signal) =>
        materialUploadAdapter.setDocumentEnabled(
          state.account.id,
          document.documentId ?? document.id,
          action === "enable",
          signal,
        ),
      )
        .then(() => refreshFromBackend())
        .then(() => setNotice(action === "enable" ? "资料已启用，可在面试准备中选择" : "资料已停用，不参与后续面试"))
        .catch((error) => setError(error instanceof Error ? error.message : `Unable to ${action === "enable" ? "enable" : "disable"} the material. Please try again.`))
        .finally(() => setOperation(null));
      return;
    }
    const now = Date.now();
    const nextName =
      action === "rename"
        ? window.prompt("New material name", document.displayName)?.trim()
        : "";
    if (action === "rename" && !nextName) {
      setOperation(null);
      return;
    }
    if (action === "rename") {
      invalidatePendingRefreshes();
      void runAdapterOperation(signal => materialUploadAdapter.renameDocument(
        state.account.id,
        document.documentId ?? document.id,
        nextName!,
        signal,
      ))
        .then(() => refreshFromBackend())
        .then(() => setNotice("资料已重命名并保存"))
        .catch(error => setError(error instanceof Error ? error.message : "重命名资料失败，请稍后重试"))
        .finally(() => setOperation(null));
      return;
    }
    setState((current) => ({
      ...current,
      knowledgeDocuments: current.knowledgeDocuments.map((item) =>
        item.id !== document.id
          ? item
          : action === "ready"
            ? {
                ...item,
                status: "ready",
                safeSummary:
                  item.safeSummary &&
                  item.safeSummary !== "文件已上传，等待建立索引。"
                    ? item.safeSummary
                    : "已建立可检索索引，可在面试准备中选择。",
                createdAtMs: item.createdAtMs,
              }
            : action === "retry"
              ? {
                  ...item,
                  status: "processing",
                  safeSummary: "正在重新建立索引，成功前不会用于新面试。",
                }
              : action === "replace"
                ? {
                    ...item,
                    version: item.version + 1,
                    status: "processing",
                    createdAtMs: now,
                    contentFingerprint: `${item.contentFingerprint}:v${item.version + 1}`,
                    safeSummary: "新版本正在解析，旧版本不再用于新选择。",
                  }
                : action === "rename"
                  ? { ...item, displayName: nextName || item.displayName }
                  : {
                      ...item,
                      status: "disabled",
                      safeSummary: "已停用，不参与当前面试。",
                    },
      ),
      librarySources: current.librarySources.map((source) =>
        source.id !== document.id
          ? source
          : action === "ready"
            ? {
                ...source,
                status: "ready",
                updatedAtMs: now,
                summary: "已建立可检索索引，可在面试准备中选择。",
              }
            : action === "retry" || action === "replace"
              ? {
                  ...source,
                  version:
                    action === "replace"
                      ? nextVersion(source.version)
                      : source.version,
                  status: "processing",
                  updatedAtMs: now,
                  summary:
                    action === "replace"
                      ? "新版本正在解析，旧版本不再用于新选择。"
                      : "正在重新建立索引，成功前不会用于新面试。",
                }
              : action === "rename"
                ? {
                    ...source,
                    displayName: nextName || source.displayName,
                    updatedAtMs: now,
                  }
                : {
                    ...source,
                    status: "disabled",
                    updatedAtMs: now,
                    summary: "已停用，不参与当前面试。",
                  },
      ),
    }));
    setNotice(
      action === "ready"
        ? "资料已标记为可用于面试"
        : action === "retry"
          ? "已重新提交索引任务"
          : action === "replace"
            ? "已创建新版本并进入解析"
            : action === "rename"
              ? "资料已重命名"
              : "资料已停用",
    );
    setOperation(null);
  };

  return (
    <main className="app-page">
      <header className="page-header">
        <div>
          <span className="kicker">INTERVIEW MATERIALS</span>
          <h1>面试资料</h1>
          <p>{tabCopy[tab].detail}</p>
        </div>
        <button className="button primary" onClick={openPrimary}>
          {tabCopy[tab].action}
        </button>
      </header>
      <nav className="material-tabs" aria-label="资料类型">
        {(["resume", "jd", "knowledge"] as const).map((item) => (
          <button
            key={item}
            className={tab === item ? "active" : ""}
            aria-current={tab === item ? "page" : undefined}
            onClick={() => setTab(item)}
          >
            <span>{item === "resume" ? "R" : item === "jd" ? "J" : "K"}</span>
            <strong>{tabCopy[item].title}</strong>
            <small>
              {item === "knowledge"
                ? `${state.knowledgeDocuments.filter((doc) => doc.status !== "deleted").length} files`
                : `${state.librarySources.filter((source) => source.kind === item && source.status !== "deleted").length} files`}
            </small>
          </button>
        ))}
      </nav>
      {notice ? (
        <div className="billing-notice" role="status">
          {notice}
        </div>
      ) : null}
      {error ? (
        <div className="inline-error" role="alert">
          {error}
        </div>
      ) : null}
      {tab === "knowledge" ? (
        <div className="library-layout">
          <aside className="panel collection-list">
            <div className="panel-heading">
              <h2>我的知识库</h2>
              <span>
                {operation === "create-collection"
                  ? "创建中"
                  : `${state.knowledgeCollections.length} collections`}
              </span>
            </div>
            {state.knowledgeCollections.length ? (
              state.knowledgeCollections.map((item) => (
                <button
                  className={item.id === selectedId ? "active" : ""}
                  key={item.id}
                  disabled={operation !== null}
                  onClick={() => setSelectedId(item.id)}
                >
                  <span>◇</span>
                  <div>
                    <strong>{item.name}</strong>
                    <small>
                      {
                        state.knowledgeDocuments.filter(
                          (doc) =>
                            doc.collectionId === item.id &&
                            doc.status !== "deleted",
                        ).length
                      }{" "}
                      份资料
                    </small>
                  </div>
                </button>
              ))
            ) : (
              <div className="collection-empty">
                <strong>还没有知识库</strong>
                <small>先创建集合，再添加文件建立索引。</small>
                <button
                  className="button ghost"
                  onClick={() => setDialog("create-collection")}
                >
                  新建资料库
                </button>
              </div>
            )}
          </aside>
          <section className="panel collection-detail">
            {selected ? (
              <>
                <div className="collection-head">
                  <div>
                    <h2>{selected.name}</h2>
                    <p>
                      空资料库免费；知识材料{" "}
                      {state.billing.rates.knowledgeIndexMinimumPoints} 点起，每
                      5,000 Token {knowledgeIndexPointsPer5000Tokens} 点。15/30
                      天会员含 2 份额度。{supportedFormatsLabel}。
                    </p>
                  </div>
                  <div>
                    <button
                      className="button ghost"
                      disabled={operation !== null}
                      onClick={rename}
                    >
                      重命名
                    </button>
                    <button
                      className="button danger"
                      disabled={operation !== null}
                      onClick={removeCollection}
                    >
                      {operation === "delete-collection"
                        ? "删除中…"
                        : "删除资料库"}
                    </button>
                    <button
                      className="button primary"
                      disabled={operation !== null}
                      onClick={() => setDialog("upload-knowledge")}
                    >
                      ＋ 添加资料
                    </button>
                  </div>
                </div>
                {documents.length ? (
                  <div className="document-list">
                    {documents.map((document) => (
                      <article key={document.id}>
                        <span className="resource-icon">
                          {document.fileKind.toUpperCase()}
                        </span>
                        <div>
                          <strong>{document.displayName}</strong>
                          <small>
                            v{document.version} ·{" "}
                            {Math.max(1, Math.round(document.sizeBytes / 1024))}{" "}
                            KB · {displayedDocumentStatus(document)} ·{" "}
                            {syncStatusLabel[document.syncStatus ?? "unknown"]}
                          </small>
                          <p>
                            {document.status === "pending"
                              ? "Indexing has not started and no credits have been charged. Select the file again to review and confirm the quote."
                              : document.safeSummary ??
                                document.unavailableReason ??
                                "Processing is in progress. This material cannot be used until it is ready."}
                          </p>
                        </div>
                        <div>
                          <span
                            className={`state-mark ${document.status === "ready" && document.syncStatus !== "missing_artifacts" ? "ready" : document.status === "processing" || document.status === "pending" ? "processing" : "error"}`}
                          >
                            {document.syncStatus === "missing_artifacts"
                              ? "File missing"
                              : displayedDocumentStatus(document)}
                          </span>
                          {document.status === "failed" ||
                          document.syncStatus === "missing_artifacts" ? (
                            <button
                              disabled={operation !== null}
                              onClick={() =>
                                void retryDocument(
                                  document.documentId ?? document.id,
                                )
                              }
                            >
                              {operation ===
                              `document:${document.documentId ?? document.id}`
                                ? "提交中…"
                                : "重新处理"}
                            </button>
                          ) : null}
                          {document.status === "ready" ? (
                            <button
                              disabled={operation !== null}
                              onClick={() =>
                                updateDocument(document, "disable")
                              }
                            >
                              停用
                            </button>
                          ) : null}
                          {document.status === "disabled" ? (
                            <button
                              disabled={operation !== null}
                              onClick={() => updateDocument(document, "enable")}
                            >
                              {operation === `document:${document.id}` ? "启用中…" : "启用"}
                            </button>
                          ) : null}
                          <button
                            disabled={operation !== null}
                            onClick={() => updateDocument(document, "rename")}
                          >
                            重命名
                          </button>
                          <button
                            disabled={operation !== null}
                            onClick={() => downloadDocument(document.documentId ?? document.id)}
                          >
                            下载原文件
                          </button>
                          <button
                            disabled={operation !== null}
                            onClick={() => removeDocument(document)}
                          >
                            {operation === `document:${document.id}`
                              ? "删除中…"
                              : "删除"}
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                ) : (
                  <EmptyMaterial
                    title="这个知识库还是空的"
                    detail={`Credits are charged only after a file is indexed successfully. Membership allowances apply to indexed material, not empty collections. ${supportedFormatsLabel}.`}
                    action="添加第一份资料"
                    onAction={() => setDialog("upload-knowledge")}
                  />
                )}
              </>
            ) : (
              <EmptyMaterial
                title="创建你的第一个知识库"
                detail={`Organize by role, technical area, or project. ${supportedFormatsLabel}.`}
                action="新建资料库"
                onAction={() => setDialog("create-collection")}
              />
            )}
          </section>
        </div>
      ) : (
        <section className="panel typed-material-panel">
          <div className="panel-heading">
            <div>
              <h2>{tabCopy[tab].title}</h2>
              <p>
                这里只维护可复用资料；请在真正进入面试准备时选择，本页新增不会自动授权。
              </p>
              <small>
                {tab === "jd"
                  ? `${supportedFormatsLabel}, or paste the job description directly.`
                  : `${supportedFormatsLabel}.`}
              </small>
            </div>
            <Link to={routes.app}>前往面试准备 →</Link>
          </div>
          {tabSources.length ? (
            <div className="typed-material-list">
              {tabSources.map((source) => (
                <article key={source.id}>
                  <span className="resource-icon">
                    {source.kind === "resume" ? "R" : "J"}
                  </span>
                  <div>
                    <strong>{source.displayName}</strong>
                    <small>
                      {source.version} ·{" "}
                      {displayedContextSourceStatus(source)} ·{" "}
                      {syncStatusLabel[source.syncStatus ?? "unknown"]} ·{" "}
                      {new Date(source.updatedAtMs).toLocaleDateString(globalEditionMetadata().locale)}
                    </small>
                    <p>
                      {source.status === "ready"
                        ? source.kind === "resume"
                          ? "简历已处理完成，可在面试准备中选择。"
                          : "职位 JD 已处理完成，可在面试准备中选择。"
                        : source.status === "pending"
                          ? "Indexing has not started and no credits have been charged. Select the file again to review and confirm the quote."
                        : source.status === "processing"
                          ? "正在后台解析，完成后可在面试准备中选择。"
                          : (source.unavailableReason ??
                            "资料暂不可用，请刷新状态。")}
                    </p>
                  </div>
                  <div>
                    <span
                      className={`state-mark ${source.status === "ready" && source.syncStatus !== "missing_artifacts" ? "ready" : source.status === "processing" || source.status === "pending" ? "processing" : "error"}`}
                    >
                      {source.syncStatus === "missing_artifacts"
                        ? "File missing"
                        : displayedContextSourceStatus(source)}
                    </span>
                    {source.status === "pending" ? (
                      <small>Indexing has not started</small>
                    ) : source.status === "processing" ? (
                      <small>正在构建中</small>
                    ) : source.status === "failed" ||
                      source.syncStatus === "missing_artifacts" ? (
                      <button
                        disabled={operation !== null}
                        onClick={() =>
                          void retryDocument(source.documentId ?? source.id)
                        }
                      >
                        {operation ===
                        `document:${source.documentId ?? source.id}`
                          ? "提交中…"
                          : "重新处理"}
                      </button>
                    ) : null}
                    <button
                      disabled={operation !== null}
                      onClick={() => renameSource(source)}
                    >
                      重命名
                    </button>
                    <button
                      disabled={operation !== null}
                      onClick={() => downloadDocument(source.documentId ?? source.id)}
                    >
                      下载原文件
                    </button>
                    <button
                      className="danger-link"
                      disabled={operation !== null}
                      onClick={() => removeSource(source)}
                    >
                      {operation === `document:${source.id}`
                        ? "删除中…"
                        : "删除"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyMaterial
              title={tabCopy[tab].emptyTitle}
              detail={tabCopy[tab].emptyDetail}
              action={tabCopy[tab].emptyAction}
              onAction={openPrimary}
            />
          )}
        </section>
      )}
      {dialog === "create-collection" ? (
        <DialogShell title="新建知识库" onClose={() => setDialog(null)}>
          <p>创建集合免费，只有文件成功解析并建立索引后才扣点。</p>
          <label className="checkout-field">
            资料库名称
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="例如：前端架构面试"
            />
          </label>
          <div className="sheet-actions">
            <button
              className="button ghost"
              disabled={operation !== null}
              onClick={() => setDialog(null)}
            >
              取消
            </button>
            <button
              className="button primary"
              disabled={!name.trim() || operation !== null}
              onClick={createCollection}
            >
              {operation === "create-collection" ? "创建中…" : "确认创建"}
            </button>
          </div>
        </DialogShell>
      ) : null}
      {dialog === "upload-knowledge" ? (
        <DialogShell title="添加并建立索引" onClose={() => setDialog(null)}>
          <p>
            {supportedFormatsLabel}。选择后由服务端提取可索引正文并计算最终报价，不会把 PDF 图片、字体或压缩数据计入 Token。
          </p>
          <label className="checkout-field">
            Choose file
            <input
              aria-label="选择资料文件"
              type="file"
              accept={materialUploadAccept}
              disabled={submittingUpload}
              onChange={(event) => {
                const file = event.target.files?.[0] ?? null;
                void prepareKnowledgeQuote(file);
              }}
            />
          </label>
          <div className="index-estimate">
            <span>
              {quoteLoading
                ? "正在解析并计算报价"
                : serviceQuote
                  ? "服务端最终报价"
                  : pendingFile
                    ? "等待服务端报价"
                    : "等待选择文件"}
            </span>
            <strong>
              {quoteLoading
                ? "解析正文中…"
                : serviceQuote
                ? quoteSource === "pass_allowance"
                  ? "使用 1 份会员额度"
                  : `${quotedPoints} credits`
                : "选择文件后自动计算"}
            </strong>
            {serviceQuote ? (
              <>
                <small>
                  {tokenCount.toLocaleString(globalEditionMetadata().locale)} Token · {serviceQuote.billableUnits}{" "}
                  个计费单位 · 目录 v{serviceQuote.catalogVersion}
                </small>
                <small>
                  {quoteSource === "pass_allowance"
                    ? `${serviceQuote.allowanceRemaining} remaining; ${Math.max(0, serviceQuote.allowanceRemaining - 1)} after indexing`
                    : `${state.billing.balance} credits → ${serviceQuote.projectedBalance} after indexing`}
                </small>
                <button
                  type="button"
                  disabled={submittingUpload || quoteLoading || !pendingFile}
                  onClick={() => void prepareKnowledgeQuote(pendingFile)}
                >
                  刷新报价
                </button>
              </>
            ) : null}
            <small>
              每 5,000 Token {knowledgeIndexPointsPer5000Tokens} 点，最低{" "}
              {state.billing.rates.knowledgeIndexMinimumPoints}{" "}
              点；最终以服务端确认为准，失败或取消会释放预留或额度。
            </small>
          </div>
          <div className="sheet-actions">
            <button
              className="button ghost"
              disabled={submittingUpload}
              onClick={() => {
                setPendingFile(null);
                setPreparedKnowledgeUpload(null);
                setDialog(null);
              }}
            >
              取消
            </button>
            {serviceQuote &&
            quoteSource === "points" &&
            state.billing.balance < quotedPoints ? (
              <Link className="button primary" to={routes.billing}>
                积分不足，去充值
              </Link>
            ) : (
              <button
                className="button primary"
                disabled={!pendingFile || !preparedKnowledgeUpload || submittingUpload || quoteLoading}
                onClick={uploadKnowledge}
              >
                {quoteLoading
                  ? "正在计算报价…"
                  : submittingUpload
                    ? "提交中…"
                    : serviceQuote
                      ? "确认报价并建立索引"
                      : "请等待服务端报价"}
              </button>
            )}
          </div>
        </DialogShell>
      ) : null}
      {dialog === "add-source" && tab !== "knowledge" ? (
        <DialogShell
          title={tab === "resume" ? "Add Resume" : "Add Job Description"}
          onClose={() => setDialog(null)}
        >
          <p>
            {tab === "resume"
              ? `${supportedFormatsLabel}. New material is added to your library and is never selected automatically.`
              : `${supportedFormatsLabel}, or paste the job description. New material is never selected automatically.`}
          </p>
          <label className="checkout-field">
            Display name (optional)
            <input
              value={name}
              disabled={submittingUpload}
              onChange={(event) => setName(event.target.value)}
              placeholder={
                tab === "resume"
                  ? "e.g. Senior frontend resume"
                  : "e.g. Frontend engineer at Example Co."
              }
            />
          </label>
          <label className="checkout-field">
            Choose file
            <input
              aria-label={tab === "resume" ? "Select resume file" : "Select job description file"}
              type="file"
              accept={materialUploadAccept}
              disabled={submittingUpload}
              onChange={(event) =>
                setPendingFile(event.target.files?.[0] ?? null)
              }
            />
          </label>
          {tab === "jd" ? (
            <label className="checkout-field">
              Or paste the job description
              <textarea
                aria-label="Job description text"
                value={jdText}
                disabled={submittingUpload}
                onChange={(event) => setJdText(event.target.value)}
                placeholder="Paste responsibilities, required skills, and preferred qualifications"
              />
            </label>
          ) : null}
          <div className="sheet-actions">
            <button
              className="button ghost"
              disabled={submittingUpload}
              onClick={() => setDialog(null)}
            >
              取消
            </button>
            <button
              className="button primary"
              disabled={
                (tab === "resume"
                  ? !pendingFile
                  : !pendingFile && !jdText.trim()) || submittingUpload
              }
              onClick={addSource}
            >
              {submittingUpload ? "Submitting…" : "Add and process"}
            </button>
          </div>
        </DialogShell>
      ) : null}
    </main>
  );
}

function EmptyMaterial({
  title,
  detail,
  action,
  onAction,
}: {
  readonly title: string;
  readonly detail: string;
  readonly action: string;
  readonly onAction: () => void;
}) {
  return (
    <section className="empty-state">
      <span>◇</span>
      <h2>{title}</h2>
      <p>{detail}</p>
      <button className="button primary" onClick={onAction}>
        {action}
      </button>
    </section>
  );
}
function DialogShell({
  title,
  onClose,
  children,
}: {
  readonly title: string;
  readonly onClose: () => void;
  readonly children: ReactNode;
}) {
  return (
    <div
      className="sheet-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="material-dialog-title"
    >
      <section className="sheet">
        <button className="sheet-close" aria-label="关闭" onClick={onClose}>
          ×
        </button>
        <h2 id="material-dialog-title">{title}</h2>
        {children}
      </section>
    </div>
  );
}
