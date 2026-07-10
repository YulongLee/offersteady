import type {
  CreatedKnowledgeCollection,
  MaterialUploadCompletionResult,
  MaterialUploadKind,
} from "@offersteady/protocol";
import { detectMaterialUploadFormat, materialUploadFormatLabel } from "@offersteady/protocol";
import { vi } from "vitest";

import { AppError } from "./domain";
import { materialUploadAdapter } from "./material-upload-adapter";

const sourceId = (kind: MaterialUploadKind, name: string) => `${kind}-${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;

export const buildMaterialCompletion = (
  kind: MaterialUploadKind,
  userId: string,
  displayName: string,
  collectionId?: string,
): MaterialUploadCompletionResult => ({
  source: {
    sourceId: sourceId(kind, displayName),
    ownerUserId: userId,
    materialKind: kind,
    displayName,
    version: "v1",
    processingState: "processing",
    updatedAtMs: Date.now(),
    summary: "文件已上传，等待服务端处理。",
  },
  ...(collectionId ? { collectionId, documentVersionId: sourceId(kind, displayName) } : {}),
});

export const mockSuccessfulMaterialUploadAdapter = () => {
  vi.spyOn(materialUploadAdapter, "createKnowledgeCollection").mockImplementation(async request => {
    const now = Date.now();
    return {
      collectionId: `collection-${request.name.toLowerCase().replace(/[^a-z0-9]+/g, "-") || now}`,
      ownerUserId: request.userId,
      name: request.name,
      createdAtMs: now,
      updatedAtMs: now,
    } satisfies CreatedKnowledgeCollection;
  });
  const assertSupported = (file: File) => {
    if (!detectMaterialUploadFormat(file.name)) throw new AppError("validation", `当前仅支持 ${materialUploadFormatLabel}`);
  };
  vi.spyOn(materialUploadAdapter, "uploadResume").mockImplementation(async (userId, file) => {
    assertSupported(file);
    return buildMaterialCompletion("resume", userId, file.name);
  });
  vi.spyOn(materialUploadAdapter, "uploadJobDescriptionFile").mockImplementation(async (userId, file) => {
    assertSupported(file);
    return buildMaterialCompletion("job_description", userId, file.name);
  });
  vi.spyOn(materialUploadAdapter, "uploadKnowledgeFile").mockImplementation(async (userId, collectionId, file) => {
    assertSupported(file);
    return buildMaterialCompletion("knowledge", userId, file.name, collectionId);
  });
  vi.spyOn(materialUploadAdapter, "createPastedJobDescription").mockImplementation(async request => buildMaterialCompletion("job_description", request.userId, request.displayName ?? "粘贴 JD"));
};
