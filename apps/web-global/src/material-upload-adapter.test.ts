import { describe, expect, it } from "vitest";

import { BackendMaterialUploadAdapter } from "./material-upload-adapter";

const envelope = (data: unknown) =>
  new Response(JSON.stringify({
    success: true,
    data,
    error: null,
    requestId: "global-material-upload-test",
    meta: { apiVersion: "v1", timestamp: new Date(0).toISOString() },
  }), { status: 200, headers: { "content-type": "application/json" } });

describe("Global material upload proxy errors", () => {
  it("reports HTTP 413 as an English file-size validation error", async () => {
    const requests: string[] = [];
    const fetchImpl: typeof fetch = async (input) => {
      const url = String(input);
      requests.push(url);
      if (url.endsWith("/upload-intents")) {
        return envelope({
          intentId: "intent-large-pdf",
          materialKind: "resume",
          objectKey: "objects/large.pdf",
          contentType: "application/pdf",
          uploadUrl: "https://storage.example/upload",
          uploadMethod: "POST",
          uploadFields: {},
          expiresAt: Date.now() + 60_000,
        });
      }
      if (url === "https://storage.example/upload") {
        return new Response(null, { status: 503 });
      }
      if (url.endsWith("/api/v1/resume/uploads/proxy")) {
        return new Response(null, { status: 413 });
      }
      throw new Error(`Unexpected request: ${url}`);
    };
    const adapter = new BackendMaterialUploadAdapter("https://api.example", fetchImpl);
    const file = new File(["synthetic pdf"], "resume.pdf", { type: "application/pdf" });

    await expect(adapter.uploadResume("user-1", file)).rejects.toMatchObject({
      code: "validation",
      message: "This file exceeds the upload limit. Choose a file no larger than 20 MB.",
    });
    expect(requests.at(-1)).toBe("https://api.example/api/v1/resume/uploads/proxy");
  });
});
