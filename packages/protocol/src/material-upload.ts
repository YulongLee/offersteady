import type {
  CompleteDocumentUploadRequest,
  CompleteDocumentUploadResult,
  CreateDocumentUploadIntentRequest,
  DocumentFileKind,
  DocumentKind,
  DocumentLifecycleStatus,
  DocumentUploadIntent,
} from "./document-service.js";
import {
  detectDocumentFileKind,
  documentUploadAccept,
  documentValidationPolicy,
  isDocumentMimeAllowed,
} from "./document-service.js";
import { materialUploadFormats as rawFormats } from "./material-upload-formats.js";

export type MaterialUploadFormatId = DocumentFileKind;
export type MaterialUploadKind = DocumentKind;
export type MaterialUploadMethod = "file" | "pasted_text";
export type MaterialProcessingState = Exclude<DocumentLifecycleStatus, "processing_requested" | "deleting">;

export interface MaterialUploadFormatDefinition {
  readonly id: MaterialUploadFormatId;
  readonly label: string;
  readonly extensions: readonly string[];
  readonly mimeTypes: readonly string[];
}

export type MaterialUploadIntent = DocumentUploadIntent & { readonly materialKind: MaterialUploadKind };

export type CreateMaterialUploadIntentRequest = CreateDocumentUploadIntentRequest & { readonly materialKind: MaterialUploadKind };

export type CompleteMaterialUploadRequest = CompleteDocumentUploadRequest;

export interface MaterialUploadSourceRecord {
  readonly sourceId: string;
  readonly ownerUserId: string;
  readonly materialKind: MaterialUploadKind;
  readonly displayName: string;
  readonly version: string;
  readonly processingState: MaterialProcessingState;
  readonly updatedAtMs: number;
  readonly summary?: string;
}

export interface MaterialUploadCompletionResult {
  readonly source: MaterialUploadSourceRecord;
  readonly documentVersionId?: string;
  readonly collectionId?: string;
}

export interface CreateKnowledgeCollectionRequest {
  readonly userId: string;
  readonly name: string;
}

export interface CreatedKnowledgeCollection {
  readonly collectionId: string;
  readonly ownerUserId: string;
  readonly name: string;
  readonly createdAtMs: number;
  readonly updatedAtMs: number;
}

export interface CreatePastedJobDescriptionRequest {
  readonly userId: string;
  readonly displayName?: string;
  readonly text: string;
}

export const materialUploadFormats = rawFormats as readonly MaterialUploadFormatDefinition[];
export const materialUploadAccept = documentUploadAccept;
export const materialUploadFormatLabel = documentValidationPolicy.label;
export const materialUploadMaxFileSizeBytes = documentValidationPolicy.maxFileSizeBytes;

export const detectMaterialUploadFormat = detectDocumentFileKind;

export const isMaterialUploadMimeAllowed = isDocumentMimeAllowed;
export type MaterialUploadCompletionEnvelope = CompleteDocumentUploadResult;
