import type { DocumentIndexState, MaterialArtifactSyncReference, MaterialSyncStatus } from "./document-service.js";
import type { MaterialUploadFormatId } from "./material-upload.js";

export type KnowledgeDocumentStatus = "pending" | "processing" | "ready" | "failed" | "disabled" | "deleted";
export type KnowledgeFileKind = MaterialUploadFormatId;
export type KnowledgeIndexStatus = "estimated" | "reserved" | "processing" | "settled" | "released";

export interface KnowledgeCollection {
  readonly id: string;
  readonly ownerUserId: string;
  readonly name: string;
  readonly createdAtMs: number;
  readonly updatedAtMs: number;
  readonly deletedAtMs?: number;
}

export interface KnowledgeDocumentVersion {
  readonly id: string;
  readonly collectionId: string;
  readonly ownerUserId: string;
  readonly displayName: string;
  readonly fileKind: KnowledgeFileKind;
  readonly sizeBytes: number;
  readonly pageCount?: number;
  readonly contentFingerprint: string;
  readonly version: number;
  readonly status: KnowledgeDocumentStatus;
  readonly documentId?: string;
  readonly documentVersionId?: string;
  readonly indexState?: DocumentIndexState;
  readonly objectKey?: string;
  readonly tokenCount?: number;
  readonly chunkCount?: number;
  readonly createdAtMs: number;
  readonly deletedAtMs?: number;
  readonly safeSummary?: string;
  readonly syncStatus?: MaterialSyncStatus;
  readonly artifactManifest?: readonly MaterialArtifactSyncReference[];
  readonly unavailableReason?: string;
}

export type KnowledgeIndexFundingSource = "points" | "pass_allowance";

export interface KnowledgeIndexQuote {
  readonly quoteId: string;
  readonly documentVersionId: string;
  readonly contentFingerprint: string;
  readonly tokenCount: number;
  readonly billableUnits: number;
  readonly pointCost: number;
  readonly entitlementSource: KnowledgeIndexFundingSource;
  readonly allowanceRemaining: number;
  readonly catalogVersion: number;
  readonly tokenizerVersion: string;
  readonly createdAtMs: number;
  readonly expiresAtMs: number;
  readonly requiresConfirmation: boolean;
  readonly projectedBalance: number;
}

export interface KnowledgeIndexUsage {
  readonly id: string;
  readonly userId: string;
  readonly documentVersionId: string;
  readonly points: number;
  readonly quoteId: string;
  readonly tokenCount: number;
  readonly source: KnowledgeIndexFundingSource;
  readonly catalogVersion: number;
  readonly tokenizerVersion: string;
  readonly status: KnowledgeIndexStatus;
  readonly createdAtMs: number;
}
