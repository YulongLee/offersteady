import { describe, expect, it } from "vitest";
import type { ContextLibrarySource } from "@offersteady/protocol";

import { displayedContextSourceStatus } from "./context-selection";

const source: ContextLibrarySource = {
  id: "source-1",
  ownerUserId: "user-1",
  kind: "resume",
  displayName: "resume.pdf",
  version: "v1",
  status: "failed",
  updatedAtMs: 1,
};

describe("Global material status labels", () => {
  it("shows an unconfirmed index quote as waiting instead of processing", () => {
    expect(displayedContextSourceStatus({
      ...source,
      kind: "knowledge",
      status: "pending",
      summary: "Index quote created.",
    })).toBe("Waiting for confirmation");
  });

  it("distinguishes upload failure from parsing failure in English", () => {
    expect(displayedContextSourceStatus({
      ...source,
      summary: "Upload failed. Please try again.",
    })).toBe("Upload failed");
    expect(displayedContextSourceStatus({
      ...source,
      summary: "Document parsing failed.",
    })).toBe("Parsing failed");
  });
});
