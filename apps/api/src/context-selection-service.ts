import type { AnswerProvenance, AnswerSourceReference, ConfirmContextSelectionRequest, ContextLibrarySource, ContextSourceStatus, SessionContextSelection } from "@offersteady/protocol";

export class ContextSelectionError extends Error {
  constructor(readonly code: "unauthorized" | "not-found" | "invalid-source" | "stale-revision", message: string) { super(message); }
}

export class ContextSelectionService {
  private sources = new Map<string, ContextLibrarySource>();
  private sessionOwners = new Map<string, string>();
  private selections = new Map<string, SessionContextSelection>();

  constructor(sources: readonly ContextLibrarySource[]) { sources.forEach(source => this.sources.set(source.id, source)); }

  registerSession(sessionId: string, ownerUserId: string) {
    this.sessionOwners.set(sessionId, ownerUserId);
    if (!this.selections.has(sessionId)) this.selections.set(sessionId, { sessionId, resumeSourceId: null, jobDescriptionSourceId: null, knowledgeSourceIds: [], revision: 0, confirmedAtMs: null });
  }

  listSources(userId: string) { return [...this.sources.values()].filter(source => source.ownerUserId === userId); }

  getSelection(userId: string, sessionId: string) {
    this.assertSessionOwner(userId, sessionId);
    return this.selections.get(sessionId)!;
  }

  confirm(request: ConfirmContextSelectionRequest, nowMs = Date.now()): SessionContextSelection {
    this.assertSessionOwner(request.userId, request.sessionId);
    const current = this.selections.get(request.sessionId)!;
    if (current.revision !== request.expectedRevision) throw new ContextSelectionError("stale-revision", "资料选择已经更新，请刷新后重试");
    this.assertSource(request.userId, request.resumeSourceId, "resume");
    this.assertSource(request.userId, request.jobDescriptionSourceId, "jd");
    const knowledgeSourceIds = [...new Set(request.knowledgeSourceIds)];
    knowledgeSourceIds.forEach(id => this.assertSource(request.userId, id, "knowledge"));
    const next: SessionContextSelection = { sessionId: request.sessionId, resumeSourceId: request.resumeSourceId, jobDescriptionSourceId: request.jobDescriptionSourceId, knowledgeSourceIds, revision: current.revision + 1, confirmedAtMs: nowMs };
    this.selections.set(request.sessionId, next);
    return next;
  }

  allowedSources(userId: string, sessionId: string, revision: number, requestedIds?: readonly string[]) {
    const selection = this.getSelection(userId, sessionId);
    if (selection.revision !== revision) throw new ContextSelectionError("stale-revision", "资料选择版本不匹配");
    if (selection.confirmedAtMs === null) throw new ContextSelectionError("invalid-source", "资料清单尚未确认");
    const selected = [selection.resumeSourceId, selection.jobDescriptionSourceId, ...selection.knowledgeSourceIds].filter((id): id is string => Boolean(id));
    const requested = requestedIds ?? selected;
    return requested.map(id => {
      if (!selected.includes(id)) throw new ContextSelectionError("unauthorized", "请求包含未选择的资料");
      const source = this.sources.get(id);
      if (!source || source.ownerUserId !== userId || source.status !== "ready") throw new ContextSelectionError("invalid-source", "资料当前不可用于检索");
      return source;
    });
  }

  provenance(userId: string, sessionId: string, revision: number, actuallyUsedIds: readonly string[]): AnswerProvenance {
    const allowed = this.allowedSources(userId, sessionId, revision);
    const allowedById = new Map(allowed.map(source => [source.id, source]));
    const usedSources: AnswerSourceReference[] = [...new Set(actuallyUsedIds)].flatMap(id => {
      const source = allowedById.get(id);
      return source ? [{ sourceId: source.id, sourceVersion: source.version, displayName: source.displayName, kind: source.kind }] : [];
    });
    return { selectionRevision: revision, usedSources };
  }

  setSourceStatus(sourceId: string, status: ContextSourceStatus) {
    const source = this.sources.get(sourceId);
    if (!source) throw new ContextSelectionError("not-found", "资料不存在");
    this.sources.set(sourceId, { ...source, status });
  }

  private assertSessionOwner(userId: string, sessionId: string) {
    if (!this.sessionOwners.has(sessionId)) throw new ContextSelectionError("not-found", "面试不存在");
    if (this.sessionOwners.get(sessionId) !== userId) throw new ContextSelectionError("unauthorized", "无权访问该面试");
  }

  private assertSource(userId: string, sourceId: string | null, kind: ContextLibrarySource["kind"]) {
    if (!sourceId) return;
    const source = this.sources.get(sourceId);
    if (!source || source.ownerUserId !== userId || source.kind !== kind || source.status !== "ready") throw new ContextSelectionError("invalid-source", `所选${kind}不可用`);
  }
}
