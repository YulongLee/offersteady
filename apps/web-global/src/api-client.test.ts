import { describe, expect, it } from "vitest";

import { createJsonClient } from "./api-client";
import { AppError } from "./domain";

describe("Global API client", () => {
  it("preserves HTTP status on envelope errors for state-aware retries", async () => {
    const client = createJsonClient({
      baseUrl: "https://offersteady.com",
      fetchImpl: async () => new Response(JSON.stringify({
        success: false,
        data: null,
        error: { code: "not_found", message: "desktop binding not found" },
        requestId: "test-request",
        meta: { apiVersion: "v1", timestamp: new Date().toISOString() },
      }), { status: 404, headers: { "content-type": "application/json" } }),
    });

    try {
      await client.request("/api/v1/realtime-speech/sessions/test/desktop-binding");
      throw new Error("expected request to fail");
    } catch (error) {
      expect(error).toBeInstanceOf(AppError);
      expect((error as AppError).status).toBe(404);
    }
  });
});
