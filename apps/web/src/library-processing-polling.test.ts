import { describe, expect, it } from "vitest";
import { pollLibraryDocumentUntilSettled } from "./library-processing-polling";
import type { WebAppState } from "./domain";

const stateFor = (status: "processing" | "ready" | "failed"): WebAppState =>
  ({
    librarySources: [{ id: "document-pdf", status }],
    knowledgeDocuments: [],
  } as unknown as WebAppState);

describe("library PDF processing polling", () => {
  it("keeps polling beyond the previous twelve attempts for a slow PDF", async () => {
    let calls = 0;
    const result = await pollLibraryDocumentUntilSettled({
      documentId: "document-pdf",
      signal: new AbortController().signal,
      maxAttempts: 13,
      sleep: async () => undefined,
      loadState: async () => {
        calls += 1;
        return stateFor(calls === 13 ? "ready" : "processing");
      },
    });

    expect(calls).toBe(13);
    expect(result.kind).toBe("settled");
  });

  it("stops as soon as the backend reports a terminal failure", async () => {
    let calls = 0;
    const result = await pollLibraryDocumentUntilSettled({
      documentId: "document-pdf",
      signal: new AbortController().signal,
      sleep: async () => undefined,
      loadState: async () => {
        calls += 1;
        return stateFor(calls === 2 ? "failed" : "processing");
      },
    });

    expect(calls).toBe(2);
    expect(result.kind).toBe("settled");
  });
});
