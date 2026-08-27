import { describe, expect, it } from "vitest";

import { nextProgressiveTranscriptText, STALE_TRANSCRIPT_MS, transcriptPresentationState } from "./ConversationMonitor";

describe("progressive realtime transcript", () => {
  it("shows the complete latest partial revision immediately", () => {
    expect(nextProgressiveTranscriptText("你好", "你好，请介绍项目")).toBe("你好，请介绍项目");
  });

  it("does not add a synthetic reveal delay to long partials", () => {
    const target = "面".repeat(100);
    expect(nextProgressiveTranscriptText("", target)).toBe(target);
  });

  it("recovers from an ASR correction at the first changed character", () => {
    expect(nextProgressiveTranscriptText("项目负责", "项目复盘")).toBe("项目复盘");
  });

  it("keeps the last longer visible partial during a temporary provider retraction", () => {
    expect(nextProgressiveTranscriptText("请介绍一下你最近负责的项目", "请介绍项目")).toBe("请介绍一下你最近负责的项目");
  });

  it("ignores punctuation when deciding whether a partial retracted", () => {
    expect(nextProgressiveTranscriptText("请介绍项目。", "请介绍项目")).toBe("请介绍项目");
  });

  it("lets an authoritative final replace a longer visible partial", () => {
    expect(nextProgressiveTranscriptText("请介绍一下你最近负责的项目", "请介绍项目", true)).toBe("请介绍项目");
  });

  it("stops claiming an abandoned partial is actively transcribing", () => {
    expect(STALE_TRANSCRIPT_MS).toBe(4_000);
    const publishedAtMs = 1_800_000_000_000;
    expect(transcriptPresentationState({ isFinal: false, publishedAtMs, endedAtMs: publishedAtMs }, publishedAtMs + STALE_TRANSCRIPT_MS - 1)).toBe("transcribing");
    expect(transcriptPresentationState({ isFinal: false, publishedAtMs, endedAtMs: publishedAtMs }, publishedAtMs + STALE_TRANSCRIPT_MS)).toBe("stale");
    expect(transcriptPresentationState({ isFinal: true, publishedAtMs, endedAtMs: publishedAtMs }, publishedAtMs + STALE_TRANSCRIPT_MS)).toBe("final");
    expect(transcriptPresentationState({ isFinal: true, terminalState: "incomplete", publishedAtMs, endedAtMs: publishedAtMs }, publishedAtMs + 1)).toBe("stale");
  });

  it("shows a bounded confirming state after terminal admission", () => {
    expect(transcriptPresentationState({
      isFinal: false,
      turnState: "committing",
      publishedAtMs: 1_800_000_000_000,
      endedAtMs: 1_800_000_000_000,
    })).toBe("confirming");
  });
});
