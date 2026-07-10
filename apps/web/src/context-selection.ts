import type { ContextLevel, ContextLibrarySource, SelectionIntegrity, SessionContextSelection } from "@offersteady/protocol";

export type ContextSelectionValidity = SelectionIntegrity;

export const contextSourceStatusLabel: Record<ContextLibrarySource["status"], string> = { processing: "解析中", ready: "可用于面试", failed: "解析失败", disabled: "已停用", deleted: "已删除" };

export const managedLibrarySources = (sources: readonly ContextLibrarySource[], ownerUserId: string) => sources.filter(source => source.ownerUserId === ownerUserId && source.status !== "deleted");

export const eligibleSource = (source: ContextLibrarySource) => source.status === "ready" && source.selectable !== false;

export const selectionSources = (sources: readonly ContextLibrarySource[], selection: SessionContextSelection) => {
  const ids = new Set([selection.resumeSourceId, selection.jobDescriptionSourceId, ...selection.knowledgeSourceIds].filter(Boolean));
  return sources.filter(source => ids.has(source.id));
};

export const selectionIntegrity = (sources: readonly ContextLibrarySource[], selection: SessionContextSelection): SelectionIntegrity => {
  if (selection.confirmedAtMs === null) return "unconfirmed";
  const byId = new Map(sources.map(source => [source.id, source]));
  const selected = [
    selection.resumeSourceId ? { id: selection.resumeSourceId, kind: "resume" as const } : null,
    selection.jobDescriptionSourceId ? { id: selection.jobDescriptionSourceId, kind: "jd" as const } : null,
    ...selection.knowledgeSourceIds.map(id => ({ id, kind: "knowledge" as const })),
  ].filter((item): item is { id: string; kind: ContextLibrarySource["kind"] } => Boolean(item));
  return selected.every(item => {
    const source = byId.get(item.id);
    return source?.kind === item.kind && eligibleSource(source);
  }) ? "valid" : "attention-required";
};

export const selectionValidity = selectionIntegrity;

export const contextLevel = (selection: SessionContextSelection): ContextLevel => {
  const resume = Boolean(selection.resumeSourceId);
  const jd = Boolean(selection.jobDescriptionSourceId);
  const knowledge = selection.knowledgeSourceIds.length > 0;
  if (!resume && !jd && !knowledge) return "none";
  if (resume && jd) return "personalized";
  if (resume && !knowledge) return "resume-only";
  if (jd && !knowledge) return "jd-only";
  if (knowledge && !resume && !jd) return "knowledge-only";
  return "partial";
};

export const reviseSelection = (current: SessionContextSelection, draft: Pick<SessionContextSelection, "resumeSourceId" | "jobDescriptionSourceId" | "knowledgeSourceIds">, nowMs = Date.now()): SessionContextSelection => ({
  ...current,
  ...draft,
  knowledgeSourceIds: [...new Set(draft.knowledgeSourceIds)],
  revision: current.revision + 1,
  confirmedAtMs: nowMs,
});
