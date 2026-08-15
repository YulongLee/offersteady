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
  ...(collectionId ? {
    collectionId,
    documentVersionId: sourceId(kind, displayName),
    indexBilling: { status: "reserved" as const, settlesAfter: "indexed" as const },
  } : {}),
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
  vi.spyOn(materialUploadAdapter, "renameKnowledgeCollection").mockImplementation(async (userId, collectionId, name) => ({
    collectionId,
    ownerUserId: userId,
    name,
    createdAtMs: Date.now() - 1,
    updatedAtMs: Date.now(),
  }));
  vi.spyOn(materialUploadAdapter, "deleteKnowledgeCollection").mockResolvedValue();
  vi.spyOn(materialUploadAdapter, "setDocumentEnabled").mockResolvedValue();
  vi.spyOn(materialUploadAdapter, "renameDocument").mockResolvedValue();
  vi.spyOn(materialUploadAdapter, "downloadDocument").mockResolvedValue({ blob: new Blob(["synthetic material"]), filename: "synthetic.md" });
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
  vi.spyOn(materialUploadAdapter, "prepareKnowledgeFile").mockImplementation(async (userId, _collectionId, file) => {
    assertSupported(file);
    const now = Date.now();
    return {
      intent: {
        intentId: `intent-${file.name}`,
        userId,
        documentKind: "knowledge" as const,
        materialKind: "knowledge" as const,
        filename: file.name,
        fileKind: detectMaterialUploadFormat(file.name)!,
        contentType: file.type || "application/octet-stream",
        objectKey: `test/${file.name}`,
        uploadMethod: "POST" as const,
        uploadUrl: "https://upload.example.test",
        uploadFields: {},
        issuedAtMs: now,
        expiresAtMs: now + 60_000,
      },
      quote: {
        quoteId: `quote-${file.name}`,
        documentVersionId: `version-${file.name}`,
        contentFingerprint: `synthetic:${file.name}`,
        tokenCount: 3,
        billableUnits: 1,
        pointCost: 20,
        entitlementSource: file.name.includes("会员") ? ("pass_allowance" as const) : ("points" as const),
        allowanceRemaining: file.name.includes("会员") ? 2 : 0,
        catalogVersion: 5,
        tokenizerVersion: "mvp-v1",
        createdAtMs: now,
        expiresAtMs: now + 15 * 60_000,
        requiresConfirmation: true,
        projectedBalance: 180,
      },
    };
  });
  vi.spyOn(materialUploadAdapter, "confirmKnowledgeFile").mockImplementation(async (userId, collectionId, file) => {
    assertSupported(file);
    return buildMaterialCompletion("knowledge", userId, file.name, collectionId);
  });
  vi.spyOn(materialUploadAdapter, "createPastedJobDescription").mockImplementation(async request => buildMaterialCompletion("job_description", request.userId, request.displayName ?? "粘贴 JD"));
};
