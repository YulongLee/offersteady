import { describe, expect, it } from "vitest";

import { BackendMaterialUploadAdapter } from "./material-upload-adapter";

const envelope = (data: unknown) =>
  new Response(JSON.stringify({
    success: true,
    data,
    error: null,
    requestId: "material-upload-test",
    meta: { apiVersion: "v1", timestamp: new Date(0).toISOString() },
  }), { status: 200, headers: { "content-type": "application/json" } });

describe("BackendMaterialUploadAdapter knowledge billing confirmation", () => {
  it("sends explicit index-charge confirmation only for knowledge completion", async () => {
    const requests: Array<{ url: string; init: RequestInit | undefined }> = [];
    const fetchImpl: typeof fetch = async (input, init) => {
      const url = String(input);
      requests.push({ url, init });
      if (url === "https://oss.example/upload") return new Response(null, { status: 204 });
      if (url.endsWith("/upload-intents")) {
        return envelope({
          intentId: `intent-${requests.length}`,
          materialKind: url.includes("knowledge") ? "knowledge" : "resume",
          objectKey: `objects/${requests.length}.md`,
          contentType: "text/markdown",
          uploadUrl: "https://oss.example/upload",
          uploadMethod: "POST",
          uploadFields: {},
          expiresAt: Date.now() + 60_000,
        });
      }
      if (url.endsWith("/uploads/complete")) {
        return envelope({
          source: {
            sourceId: `document-${requests.length}`,
            kind: url.includes("knowledge") ? "knowledge" : "resume",
            displayName: "notes.md",
            version: "v1",
            processingState: "queued",
            updatedAtMs: Date.now(),
          },
          documentVersionId: `version-${requests.length}`,
        });
      }
      if (url.endsWith("/uploads/quote")) {
        return envelope({
          quoteId: "quote-knowledge",
          documentVersionId: "version-knowledge",
          contentFingerprint: "synthetic",
          tokenCount: 5,
          billableUnits: 1,
          pointCost: 20,
          entitlementSource: "points",
          allowanceRemaining: 0,
          catalogVersion: 5,
          tokenizerVersion: "mvp-v1",
          createdAtMs: Date.now(),
          expiresAtMs: Date.now() + 60_000,
          requiresConfirmation: true,
          projectedBalance: 180,
        });
      }
      throw new Error(`Unexpected request: ${url}`);
    };
    const adapter = new BackendMaterialUploadAdapter("https://api.example", fetchImpl);
    const file = new File(["synthetic knowledge"], "notes.md", { type: "text/markdown" });

    await adapter.uploadKnowledgeFile("user-1", "collection-1", file);
    await adapter.uploadResume("user-1", file);

    const completionBodies = requests
      .filter(({ url }) => url.endsWith("/uploads/complete"))
      .map(({ init }) => JSON.parse(String(init?.body)) as Record<string, unknown>);
    expect(completionBodies).toHaveLength(2);
    expect(completionBodies[0]).toMatchObject({ confirmIndexCharge: true, quoteId: "quote-knowledge" });
    expect(completionBodies[1]).not.toHaveProperty("confirmIndexCharge");
  });

  it("persists document availability through the owner-scoped backend endpoint", async () => {
    const requests: Array<{ url: string; init: RequestInit | undefined }> = [];
    const fetchImpl: typeof fetch = async (input, init) => {
      requests.push({ url: String(input), init });
      return envelope({ documentId: "document-1", indexState: "indexed" });
    };
    const adapter = new BackendMaterialUploadAdapter("https://api.example", fetchImpl);

    await adapter.setDocumentEnabled("user-1", "document-1", true);

    expect(requests).toHaveLength(1);
    expect(requests[0]?.url).toBe("https://api.example/api/v1/documents/document-1/availability");
    expect(requests[0]?.init?.method).toBe("PATCH");
    expect(JSON.parse(String(requests[0]?.init?.body))).toEqual({ userId: "user-1", enabled: true });
  });

  it("persists display names and downloads the authenticated original filename", async () => {
    const requests: Array<{ url: string; init: RequestInit | undefined }> = [];
    const fetchImpl: typeof fetch = async (input, init) => {
      const url = String(input);
      requests.push({ url, init });
      if (url.endsWith("/display-name")) return envelope({ documentId: "document-1", displayName: "新的名称.md" });
      return new Response("synthetic material", {
        status: 200,
        headers: {
          "content-type": "text/markdown",
          "content-disposition": "attachment; filename=material-download; filename*=UTF-8''%E5%8E%9F%E5%A7%8B%E8%B5%84%E6%96%99.md",
        },
      });
    };
    const adapter = new BackendMaterialUploadAdapter("https://api.example", fetchImpl);

    await adapter.renameDocument("user-1", "document-1", "新的名称.md");
    const downloaded = await adapter.downloadDocument("user-1", "document-1");

    expect(requests[0]?.url).toBe("https://api.example/api/v1/documents/document-1/display-name");
    expect(JSON.parse(String(requests[0]?.init?.body))).toEqual({ userId: "user-1", displayName: "新的名称.md" });
    expect(requests[1]?.url).toBe("https://api.example/api/v1/documents/document-1/download?userId=user-1");
    expect(downloaded.filename).toBe("原始资料.md");
    expect(await downloaded.blob.text()).toBe("synthetic material");
  });
});
