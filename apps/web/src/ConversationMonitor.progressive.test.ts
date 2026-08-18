import { describe, expect, it } from "vitest";

import { nextProgressiveTranscriptText, STALE_TRANSCRIPT_MS, transcriptPresentationState } from "./ConversationMonitor";

describe("progressive realtime transcript", () => {
  it("reveals appended partial text without replacing the whole sentence", () => {
    expect(nextProgressiveTranscriptText("你好", "你好，请介绍项目")).toBe("你好，请");
  });

  it("catches up a 100-character partial transcript within 250ms", () => {
    const target = "面".repeat(100);
    let visible = "";
    for (let elapsed = 32; elapsed <= 224; elapsed += 32) {
      visible = nextProgressiveTranscriptText(visible, target);
    }
    expect(visible).toBe(target);
  });

  it("recovers from an ASR correction at the first changed character", () => {
    expect(nextProgressiveTranscriptText("项目负责", "项目复盘")).toBe("项目复盘");
  });

  it("stops claiming an abandoned partial is actively transcribing", () => {
    const publishedAtMs = 1_800_000_000_000;
    expect(transcriptPresentationState({ isFinal: false, publishedAtMs, endedAtMs: publishedAtMs }, publishedAtMs + STALE_TRANSCRIPT_MS - 1)).toBe("transcribing");
    expect(transcriptPresentationState({ isFinal: false, publishedAtMs, endedAtMs: publishedAtMs }, publishedAtMs + STALE_TRANSCRIPT_MS)).toBe("stale");
    expect(transcriptPresentationState({ isFinal: true, publishedAtMs, endedAtMs: publishedAtMs }, publishedAtMs + STALE_TRANSCRIPT_MS)).toBe("final");
  });
});
