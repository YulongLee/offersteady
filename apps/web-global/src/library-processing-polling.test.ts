import { describe, expect, it, vi } from "vitest";
import { pollLibraryDocumentUntilSettled } from "./library-processing-polling";
import type { WebAppState } from "./domain";

const stateFor = (status: "processing" | "ready" | "failed"): WebAppState =>
  ({
    librarySources: [{ id: "document-pdf", status }],
    knowledgeDocuments: [],
  } as unknown as WebAppState);

describe("library PDF processing polling", () => {
  it("bounds polling when the material never finishes", async () => {
    const loadState = vi.fn(async () => stateFor("processing"));
    expect(await pollLibraryDocumentUntilSettled({ documentId: "document-pdf", signal: new AbortController().signal, sleep: async () => undefined, loadState })).toEqual({ kind: "timeout" });
    expect(loadState).toHaveBeenCalledTimes(45);
  });

  it("does not start a request after cancellation during the wait", async () => {
    const controller = new AbortController();
    const loadState = vi.fn(async () => stateFor("ready"));
    await expect(pollLibraryDocumentUntilSettled({ documentId: "document-pdf", signal: controller.signal, sleep: async () => controller.abort(), loadState })).rejects.toMatchObject({ name: "AbortError" });
    expect(loadState).not.toHaveBeenCalled();
  });

  it("ignores a response received after cancellation", async () => {
    const controller = new AbortController();
    await expect(pollLibraryDocumentUntilSettled({ documentId: "document-pdf", signal: controller.signal, sleep: async () => undefined, loadState: async () => { controller.abort(); return stateFor("ready"); } })).rejects.toMatchObject({ name: "AbortError" });
  });

  it("clears its real waiting timer when cancelled", async () => {
    vi.useFakeTimers();
    try {
      const controller = new AbortController();
      const loadState = vi.fn(async () => stateFor("ready"));
      const result = pollLibraryDocumentUntilSettled({ documentId: "document-pdf", signal: controller.signal, loadState });
      const rejected = expect(result).rejects.toMatchObject({ name: "AbortError" });
      controller.abort();
      await rejected;
      expect(vi.getTimerCount()).toBe(0);
      expect(loadState).not.toHaveBeenCalled();
    } finally { vi.useRealTimers(); }
  });

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
