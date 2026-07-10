import { materialUploadFormats } from "./material-upload-formats.js";

export type DocumentKind = "resume" | "job_description" | "knowledge";
export type DocumentFileKind = "pdf" | "docx" | "doc" | "txt" | "md";
export type DocumentIndexState = "not_indexed" | "queued" | "processing" | "indexed" | "failed" | "disabled" | "deleted";
export type DocumentProcessingStage = "queued" | "parsing" | "normalizing" | "chunking" | "embedding" | "indexing" | "indexed" | "failed" | "cancelled";
export type DocumentProcessingJobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled" | "timed_out";
export type DocumentArtifactKind = "original" | "normalized_markdown" | "chunk_manifest" | "deletion_marker" | "temporary_upload" | "export";
export type MaterialSyncStatus = "synced" | "processing" | "missing_artifacts" | "failed" | "deleted" | "unknown";
export type MaterialArtifactRecordStatus = "synced" | "processing" | "missing" | "failed" | "deleted";
export type CommercialJobKind = "processing" | "deletion" | "reconcile";
export type CommercialJobStatus = "queued" | "running" | "retrying" | "succeeded" | "failed" | "cancelled";
export type AiOperationKind = "parser" | "vision" | "embedding" | "rerank" | "chat";
export type DocumentLifecycleStatus =
  | "pending_upload"
  | "uploaded"
  | "processing_requested"
  | "processing"
  | "ready"
  | "failed"
  | "deleting"
  | "deleted";

export interface DocumentValidationPolicy {
  readonly maxFileSizeBytes: number;
  readonly acceptedExtensions: readonly string[];
  readonly acceptedMimeTypes: readonly string[];
  readonly label: string;
}

export interface DocumentUploadIntent {
  readonly intentId: string;
  readonly userId: string;
  readonly documentKind: DocumentKind;
  readonly filename: string;
  readonly fileKind: DocumentFileKind;
  readonly contentType: string;
  readonly objectKey: string;
  readonly uploadMethod: "POST";
  readonly uploadUrl: string;
  readonly uploadFields: Readonly<Record<string, string>>;
  readonly issuedAtMs: number;
  readonly expiresAtMs: number;
  readonly uploadObjectId?: string;
  readonly documentId?: string;
  readonly documentVersionId?: string;
}

export interface CreateDocumentUploadIntentRequest {
  readonly userId: string;
  readonly documentKind: DocumentKind;
  readonly filename: string;
  readonly contentType: string;
  readonly sizeBytes: number;
  readonly knowledgeCollectionId?: string;
}

export interface CompleteDocumentUploadRequest {
  readonly userId: string;
  readonly intentId: string;
  readonly objectKey: string;
  readonly contentType: string;
  readonly sizeBytes: number;
  readonly etag?: string;
  readonly contentSha256?: string;
  readonly knowledgeCollectionId?: string;
}

export interface DocumentRecord {
  readonly documentId: string;
  readonly ownerUserId: string;
  readonly documentKind: DocumentKind;
  readonly displayName: string;
  readonly fileKind: DocumentFileKind;
  readonly contentType: string;
  readonly sizeBytes: number;
  readonly objectKey: string;
  readonly objectId?: string;
  readonly documentVersionId?: string;
  readonly version?: number;
  readonly contentFingerprint?: string;
  readonly originalFilename?: string;
  readonly indexState?: DocumentIndexState;
  readonly status: DocumentLifecycleStatus;
  readonly knowledgeCollectionId?: string;
  readonly processingRequestedAtMs?: number;
  readonly deletedAtMs?: number;
  readonly createdAtMs: number;
  readonly updatedAtMs: number;
  readonly summary?: string;
  readonly syncStatus?: MaterialSyncStatus;
  readonly artifactManifest?: readonly MaterialArtifactSyncReference[];
  readonly unavailableReason?: string;
}

export interface PersistedMaterialDocument {
  readonly documentId: string;
  readonly ownerUserId: string;
  readonly documentKind: DocumentKind;
  readonly displayName: string;
  readonly currentVersionId: string | null;
  readonly status: DocumentLifecycleStatus;
  readonly knowledgeCollectionId?: string;
  readonly createdAtMs: number;
  readonly updatedAtMs: number;
  readonly deletedAtMs?: number;
}

export interface PersistedMaterialVersion {
  readonly documentVersionId: string;
  readonly documentId: string;
  readonly ownerUserId: string;
  readonly documentKind: DocumentKind;
  readonly displayName: string;
  readonly originalFilename: string;
  readonly fileKind: DocumentFileKind;
  readonly contentType: string;
  readonly sizeBytes: number;
  readonly objectKey: string;
  readonly objectId: string;
  readonly contentFingerprint: string;
  readonly version: number;
  readonly lifecycleStatus: DocumentLifecycleStatus;
  readonly indexState: DocumentIndexState;
  readonly pageCount?: number;
  readonly tokenCount?: number;
  readonly chunkCount?: number;
  readonly safeSummary?: string;
  readonly knowledgeCollectionId?: string;
  readonly createdAtMs: number;
  readonly updatedAtMs: number;
  readonly deletedAtMs?: number;
}

export interface MaterialArtifactReference {
  readonly artifactKind: DocumentArtifactKind;
  readonly objectKey: string;
  readonly contentType?: string;
  readonly sizeBytes?: number;
  readonly sha256?: string;
  readonly createdAtMs: number;
}

export interface MaterialArtifactSyncReference {
  readonly artifactKind: DocumentArtifactKind | "inline_source";
  readonly objectKey: string;
  readonly exists: boolean;
  readonly required: boolean;
  readonly syncStatus?: MaterialArtifactRecordStatus;
  readonly verifiedAtMs?: number;
  readonly safeErrorCode?: string;
}

export interface MaterialArtifactRecord {
  readonly artifactId: string;
  readonly ownerUserId: string;
  readonly documentId: string;
  readonly documentVersionId: string;
  readonly documentKind: DocumentKind;
  readonly artifactKind: DocumentArtifactKind | "inline_source";
  readonly objectKey: string;
  readonly syncStatus: MaterialArtifactRecordStatus;
  readonly required: boolean;
  readonly contentType?: string;
  readonly sizeBytes?: number;
  readonly sha256?: string;
  readonly verifiedAtMs?: number;
  readonly createdAtMs: number;
  readonly updatedAtMs: number;
  readonly safeErrorCode?: string;
}

export interface CommercialMaterialJob {
  readonly jobId: string;
  readonly ownerUserId: string;
  readonly jobKind: CommercialJobKind;
  readonly status: CommercialJobStatus;
  readonly stage: string;
  readonly documentId?: string;
  readonly documentVersionId?: string;
  readonly relatedTaskId?: string;
  readonly retryCount: number;
  readonly maxRetries: number;
  readonly safeErrorCode?: string;
  readonly createdAtMs: number;
  readonly updatedAtMs: number;
  readonly scheduledAfterMs: number;
  readonly startedAtMs?: number;
  readonly completedAtMs?: number;
}

export interface AiUsageRecord {
  readonly usageId: string;
  readonly ownerUserId: string;
  readonly operationKind: AiOperationKind;
  readonly provider: string;
  readonly model: string;
  readonly status: "succeeded" | "failed";
  readonly relatedJobId?: string;
  readonly relatedTaskId?: string;
  readonly sessionId?: string;
  readonly documentId?: string;
  readonly documentVersionId?: string;
  readonly traceId?: string;
  readonly inputUnits?: number;
  readonly outputUnits?: number;
  readonly totalUnits?: number;
  readonly pointCost?: number;
  readonly durationMs?: number;
  readonly safeErrorCode?: string;
  readonly createdAtMs: number;
}

export interface RagRetrievalTrace {
  readonly traceId: string;
  readonly ownerUserId: string;
  readonly sessionId?: string;
  readonly queryHash: string;
  readonly strategy: string;
  readonly filterDocumentIds: readonly string[];
  readonly filterDocumentVersionIds: readonly string[];
  readonly candidateCount: number;
  readonly rerankedCount: number;
  readonly returnedCount: number;
  readonly returnedSourceIds: readonly string[];
  readonly safeErrorCode?: string;
  readonly createdAtMs: number;
}

export interface CompleteDocumentUploadResult {
  readonly document: DocumentRecord;
}

export interface ListDocumentsRequest {
  readonly userId: string;
  readonly documentKind?: DocumentKind;
  readonly knowledgeCollectionId?: string;
  readonly includeDeleted?: boolean;
}

export interface DeleteDocumentRequest {
  readonly userId: string;
  readonly documentId: string;
}

export interface DocumentProcessingHandoff {
  readonly documentId: string;
  readonly ownerUserId: string;
  readonly documentKind: DocumentKind;
  readonly objectKey: string;
  readonly status: "processing_requested" | "processing" | "ready" | "failed";
  readonly requestedAtMs?: number;
  readonly documentVersionId?: string;
  readonly indexState?: DocumentIndexState;
}

export interface MaterialProcessingJob {
  readonly jobId: string;
  readonly ownerUserId: string;
  readonly documentId: string;
  readonly documentVersionId: string;
  readonly idempotencyKey: string;
  readonly contentFingerprint: string;
  readonly stage: DocumentProcessingStage;
  readonly status: DocumentProcessingJobStatus;
  readonly retryCount: number;
  readonly parserVersion?: string;
  readonly embeddingModel?: string;
  readonly tokenizerVersion?: string;
  readonly safeErrorCode?: string;
  readonly createdAtMs: number;
  readonly updatedAtMs: number;
  readonly startedAtMs?: number;
  readonly completedAtMs?: number;
}

export type MaterialIndexJobStatus = "estimated" | "reserved" | "processing" | "indexed" | "settled" | "released" | "failed" | "cancelled";
export type MaterialIndexFundingSource = "points" | "pass_allowance";

export interface MaterialIndexJob {
  readonly indexJobId: string;
  readonly ownerUserId: string;
  readonly documentId: string;
  readonly documentVersionId: string;
  readonly processingJobId?: string;
  readonly quoteId?: string;
  readonly usageId?: string;
  readonly status: MaterialIndexJobStatus;
  readonly fundingSource?: MaterialIndexFundingSource;
  readonly pointCost?: number;
  readonly tokenCount?: number;
  readonly chunkCount?: number;
  readonly embeddingModel?: string;
  readonly embeddingDimension?: number;
  readonly catalogVersion?: number;
  readonly safeErrorCode?: string;
  readonly createdAtMs: number;
  readonly updatedAtMs: number;
}

export interface VectorSourceMetadata {
  readonly ownerUserId: string;
  readonly documentId: string;
  readonly documentVersionId: string;
  readonly documentKind: DocumentKind;
  readonly collectionId?: string;
  readonly chunkId: string;
  readonly contentHash: string;
  readonly embeddingModel: string;
  readonly embeddingDimension: number;
  readonly safeSummary?: string;
  readonly createdAtMs: number;
}

export const documentValidationPolicy: DocumentValidationPolicy = {
  maxFileSizeBytes: 20 * 1024 * 1024,
  acceptedExtensions: materialUploadFormats.flatMap((item) => item.extensions),
  acceptedMimeTypes: materialUploadFormats.flatMap((item) => item.mimeTypes),
  label: materialUploadFormats.map((item) => item.label).join("、"),
};

export const documentUploadAccept = documentValidationPolicy.acceptedExtensions.join(",");

export const detectDocumentFileKind = (filename: string): DocumentFileKind | null => {
  const lowered = filename.toLowerCase();
  const match = materialUploadFormats.find((format) => format.extensions.some((extension) => lowered.endsWith(extension)));
  return (match?.id as DocumentFileKind | undefined) ?? null;
};

export const isDocumentMimeAllowed = (fileKind: DocumentFileKind, contentType: string) => {
  if (!contentType.trim()) return true;
  const format = materialUploadFormats.find((item) => item.id === fileKind);
  return format ? format.mimeTypes.some((mimeType) => mimeType === contentType.toLowerCase()) : false;
};
