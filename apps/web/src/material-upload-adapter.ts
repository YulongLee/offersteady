import type {
  CompleteMaterialUploadRequest,
  CreateKnowledgeCollectionRequest,
  CreateMaterialUploadIntentRequest,
  CreatePastedJobDescriptionRequest,
  CreatedKnowledgeCollection,
  MaterialUploadCompletionResult,
  MaterialUploadIntent,
} from "@offersteady/protocol";
import {
  detectMaterialUploadFormat,
} from "@offersteady/protocol";

import { createJsonClient, withBaseUrl } from "./api-client";
import { AppError } from "./domain";
import { readRuntimeConfig } from "./runtime-config";
import { authClient } from "./auth-client";

export interface MaterialUploadAdapter {
  createKnowledgeCollection(request: CreateKnowledgeCollectionRequest, signal?: AbortSignal): Promise<CreatedKnowledgeCollection>;
  uploadResume(userId: string, file: File, signal?: AbortSignal): Promise<MaterialUploadCompletionResult>;
  uploadJobDescriptionFile(userId: string, file: File, signal?: AbortSignal): Promise<MaterialUploadCompletionResult>;
  uploadKnowledgeFile(userId: string, collectionId: string, file: File, signal?: AbortSignal): Promise<MaterialUploadCompletionResult>;
  createPastedJobDescription(request: CreatePastedJobDescriptionRequest, signal?: AbortSignal): Promise<MaterialUploadCompletionResult>;
  deleteDocument(userId: string, documentId: string, signal?: AbortSignal): Promise<void>;
}

const runtimeConfig = readRuntimeConfig(import.meta.env);

const authHeaders = () => {
  const session = authClient.readStoredSession();
  return session ? { Authorization: `Bearer ${session.accessToken}` } : {};
};

const buildIntentPayload = (userId: string, materialKind: CreateMaterialUploadIntentRequest["materialKind"], file: File): CreateMaterialUploadIntentRequest => ({
  userId,
  documentKind: materialKind,
  materialKind,
  filename: file.name,
  contentType: file.type || "application/octet-stream",
  sizeBytes: file.size || 1,
});

const buildCompletePayload = (userId: string, intent: MaterialUploadIntent, file: File): CompleteMaterialUploadRequest => ({
  userId,
  intentId: intent.intentId,
  objectKey: intent.objectKey,
  contentType: intent.contentType,
  sizeBytes: file.size || 1,
  etag: `${file.name}:${file.size}`,
});

export class BackendMaterialUploadAdapter implements MaterialUploadAdapter {
  private readonly client;

  constructor(private readonly baseUrl: string, private readonly fetchImpl: typeof fetch = (input, init) => globalThis.fetch(input, init)) {
    this.client = createJsonClient({ baseUrl, fetchImpl });
  }

  async createKnowledgeCollection(request: CreateKnowledgeCollectionRequest, signal?: AbortSignal) {
    return this.client.request<CreatedKnowledgeCollection>("/api/v1/knowledge/collections", { method: "POST", headers: authHeaders(), body: JSON.stringify(request) }, signal);
  }

  async uploadResume(userId: string, file: File, signal?: AbortSignal) {
    return this.uploadFile(userId, "resume", "/api/v1/resume/upload-intents", "/api/v1/resume/uploads/complete", file, signal);
  }

  async uploadJobDescriptionFile(userId: string, file: File, signal?: AbortSignal) {
    return this.uploadFile(userId, "job_description", "/api/v1/job-descriptions/upload-intents", "/api/v1/job-descriptions/uploads/complete", file, signal);
  }

  async uploadKnowledgeFile(userId: string, collectionId: string, file: File, signal?: AbortSignal) {
    return this.uploadFile(
      userId,
      "knowledge",
      `/api/v1/knowledge/collections/${collectionId}/upload-intents`,
      `/api/v1/knowledge/collections/${collectionId}/uploads/complete`,
      file,
      signal,
    );
  }

  async createPastedJobDescription(request: CreatePastedJobDescriptionRequest, signal?: AbortSignal) {
    return this.client.request<MaterialUploadCompletionResult>("/api/v1/job-descriptions/text", { method: "POST", headers: authHeaders(), body: JSON.stringify(request) }, signal);
  }

  async deleteDocument(userId: string, documentId: string, signal?: AbortSignal) {
    await this.client.request(`/api/v1/documents/${documentId}?userId=${encodeURIComponent(userId)}`, { method: "DELETE", headers: authHeaders() }, signal);
  }

  private async uploadFile(
    userId: string,
    materialKind: CreateMaterialUploadIntentRequest["materialKind"],
    intentPath: string,
    completionPath: string,
    file: File,
    signal?: AbortSignal,
  ) {
    const fileKind = detectMaterialUploadFormat(file.name);
    if (!fileKind) throw new AppError("validation", "当前仅支持 PDF、DOCX、DOC、TXT、MD");
    const intent = await this.client.request<MaterialUploadIntent>(intentPath, { method: "POST", headers: authHeaders(), body: JSON.stringify(buildIntentPayload(userId, materialKind, file)) }, signal);
    await this.uploadToOss(intent, file, completionPath, userId, signal);
    return this.client.request<MaterialUploadCompletionResult>(completionPath, { method: "POST", headers: authHeaders(), body: JSON.stringify(buildCompletePayload(userId, intent, file)) }, signal);
  }

  private async uploadToOss(intent: MaterialUploadIntent, file: File, completionPath: string, userId: string, signal?: AbortSignal) {
    const body = new FormData();
    Object.entries(intent.uploadFields).forEach(([key, value]) => body.append(key, value));
    body.append("file", file);
    try {
      const response = await this.fetchImpl(intent.uploadUrl, { method: intent.uploadMethod, body, ...(signal ? { signal } : {}) });
      if (response.ok || response.status === 204) return;
    } catch {
      // Browsers can fail direct-to-OSS uploads before an HTTP response when CORS or endpoint settings are not ready.
    }
    await this.uploadViaBackendProxy(intent, file, completionPath, userId, signal);
  }

  private async uploadViaBackendProxy(intent: MaterialUploadIntent, file: File, completionPath: string, userId: string, signal?: AbortSignal) {
    const proxyBody = new FormData();
    proxyBody.append("userId", userId);
    proxyBody.append("intentId", intent.intentId);
    proxyBody.append("objectKey", intent.objectKey);
    proxyBody.append("contentType", intent.contentType);
    proxyBody.append("file", file);
    const proxyPath = completionPath.replace(/\/uploads\/complete$/, "/uploads/proxy");
    const response = await this.fetchImpl(withBaseUrl(this.baseUrl, proxyPath), {
      method: "POST",
      headers: authHeaders(),
      body: proxyBody,
      ...(signal ? { signal } : {}),
    });
    if (!response.ok) throw new AppError("network", "对象存储上传失败，请稍后重试");
  }
}

export const materialUploadAdapter: MaterialUploadAdapter = new BackendMaterialUploadAdapter(runtimeConfig.apiBaseUrl);
