import { describe, expect, it } from "vitest";

import { formatTranscriptTimestamp } from "./ConversationMonitor";

describe("conversation transcript timestamp", () => {
  it("formats epoch timestamps as local clock time", () => {
    const timestamp = new Date(2026, 6, 25, 9, 8, 7).getTime();
    expect(formatTranscriptTimestamp(timestamp)).toBe("[09:08:07]");
  });

  it("keeps legacy elapsed timestamps readable", () => {
    expect(formatTranscriptTimestamp(78_000)).toBe("[01:18]");
  });
});
