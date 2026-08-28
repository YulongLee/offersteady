import { describe, expect, it } from "vitest";

import { nextProgressiveTranscriptText, transcriptPresentationLabel, transcriptPresentationState } from "./ConversationMonitor";

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

  it("does not infer incomplete from the client age of a partial", () => {
    expect(transcriptPresentationState({ isFinal: false })).toBe("transcribing");
    expect(transcriptPresentationState({ isFinal: true })).toBe("final");
    expect(transcriptPresentationState({ isFinal: true, terminalState: "incomplete" })).toBe("stale");
  });

  it("freezes a committing partial without turning it incomplete while final reconciles", () => {
    const committing = {
      isFinal: false,
      turnState: "committing" as const,
    };
    expect(transcriptPresentationState(committing)).toBe("confirming");
    expect(transcriptPresentationLabel("confirming")).toBe("已转写");
    expect(transcriptPresentationLabel("stale")).toBe("识别未完成");
  });
});
