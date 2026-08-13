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
    expect(completionBodies[0]).toMatchObject({ confirmIndexCharge: true });
    expect(completionBodies[1]).not.toHaveProperty("confirmIndexCharge");
  });
});
