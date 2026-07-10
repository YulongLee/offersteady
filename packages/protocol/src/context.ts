import type { DocumentIndexState, DocumentKind, MaterialArtifactSyncReference, MaterialSyncStatus } from "./document-service.js";
import type { MaterialProcessingState } from "./material-upload.js";

export type ContextSourceKind = "resume" | "jd" | "knowledge";
export type ContextSourceStatus = "processing" | "ready" | "failed" | "disabled" | "deleted";
export type SelectionIntegrity = "unconfirmed" | "valid" | "attention-required";
export type ContextLevel = "none" | "resume-only" | "jd-only" | "knowledge-only" | "partial" | "personalized";

export interface ContextLibrarySource {
  readonly id: string;
  readonly ownerUserId: string;
  readonly kind: ContextSourceKind;
  readonly displayName: string;
  readonly version: string;
  readonly status: ContextSourceStatus;
  readonly documentId?: string;
  readonly documentVersionId?: string;
  readonly indexState?: DocumentIndexState;
  readonly selectable?: boolean;
  readonly deletedAtMs?: number;
  readonly processingState?: MaterialProcessingState;
  readonly updatedAtMs: number;
  readonly summary?: string;
  readonly syncStatus?: MaterialSyncStatus;
  readonly artifactManifest?: readonly MaterialArtifactSyncReference[];
  readonly unavailableReason?: string;
}

export interface SessionMaterialSnapshotSource {
  readonly sourceId: string;
  readonly ownerUserId: string;
  readonly kind: ContextSourceKind;
  readonly documentKind: DocumentKind;
  readonly documentId: string;
  readonly documentVersionId: string;
  readonly displayName: string;
  readonly sourceVersion: string;
  readonly indexState: DocumentIndexState;
  readonly deleted?: boolean;
  readonly disabled?: boolean;
  readonly safeSummary?: string;
}

export interface SessionContextSelection {
  readonly sessionId: string;
  readonly resumeSourceId: string | null;
  readonly jobDescriptionSourceId: string | null;
  readonly knowledgeSourceIds: readonly string[];
  readonly materialSnapshots?: readonly SessionMaterialSnapshotSource[];
  readonly revision: number;
  readonly confirmedAtMs: number | null;
}

export interface AnswerSourceReference {
  readonly sourceId: string;
  readonly sourceVersion: string;
  readonly displayName: string;
  readonly kind: ContextSourceKind;
  readonly documentId?: string;
  readonly documentVersionId?: string;
  readonly contextRole?: "fixed" | "retrieved";
  readonly evidenceSummary?: string;
  readonly retrievalCount?: number;
  readonly truncated?: boolean;
  readonly unavailable?: boolean;
  readonly unavailableReason?: string;
  readonly deleted?: boolean;
}

export interface AnswerProvenance {
  readonly selectionRevision: number;
  readonly usedSources: readonly AnswerSourceReference[];
  readonly unavailableSources?: readonly AnswerSourceReference[];
  readonly fixedSourceCount?: number;
  readonly retrievedSourceCount?: number;
  readonly noPersonalMaterialUsed?: boolean;
  readonly retrievalTraceId?: string;
}

export interface ConfirmContextSelectionRequest {
  readonly userId: string;
  readonly sessionId: string;
  readonly expectedRevision: number;
  readonly resumeSourceId: string | null;
  readonly jobDescriptionSourceId: string | null;
  readonly knowledgeSourceIds: readonly string[];
}

export interface RagContextItem {
  readonly source: AnswerSourceReference;
  readonly chunkId: string;
  readonly text: string;
  readonly score?: number;
  readonly rerankScore?: number;
  readonly truncated: boolean;
}

export interface RagContextResult {
  readonly traceId: string;
  readonly userId: string;
  readonly sessionId: string;
  readonly selectionRevision: number;
  readonly items: readonly RagContextItem[];
  readonly excludedSourceIds: readonly string[];
  readonly createdAtMs: number;
}
