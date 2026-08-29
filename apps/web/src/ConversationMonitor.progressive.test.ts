import { render } from "@testing-library/react";
import type { SpeakerTranscriptSegment } from "@offersteady/protocol";
import { createElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ImmediateTranscriptText,
  splitImmediateTranscriptRevision,
  transcriptPresentationLabel,
  transcriptPresentationState,
} from "./ConversationMonitor";

describe("immediate realtime transcript", () => {
  const segment = (overrides: Partial<SpeakerTranscriptSegment> = {}): SpeakerTranscriptSegment => ({
    id: "segment-1",
    sessionId: "session-1",
    revision: 1,
    sourceId: "system-loopback",
    sourceKind: "system",
    speakerId: "interviewer",
    role: "interviewer",
    text: "请介绍你的项目",
    transcriptConfidence: 0.9,
    startedAtMs: 1,
    endedAtMs: 2,
    isFinal: false,
    overlap: false,
    ...overrides,
  });

  beforeEach(() => {
    vi.stubGlobal("requestAnimationFrame", vi.fn(() => 1));
    vi.stubGlobal("cancelAnimationFrame", vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("splits a growing revision into an unchanged prefix and its new tail", () => {
    expect(splitImmediateTranscriptRevision("请介绍项目", "请介绍项目经验")).toEqual({
      stablePrefix: "请介绍项目",
      mutableTail: "经验",
    });
  });

  it("isolates only the corrected tail without retaining the old hypothesis", () => {
    expect(splitImmediateTranscriptRevision("项目负责上线", "项目复盘结果")).toEqual({
      stablePrefix: "项目",
      mutableTail: "复盘结果",
    });
  });

  it("accepts a shorter authoritative partial immediately", () => {
    expect(splitImmediateTranscriptRevision("请介绍一下你最近负责的项目", "请介绍项目")).toEqual({
      stablePrefix: "请介绍",
      mutableTail: "项目",
    });
  });

  it("compares Unicode graphemes without splitting surrogate pairs", () => {
    expect(splitImmediateTranscriptRevision("支持😀旧方案", "支持😀新方案")).toEqual({
      stablePrefix: "支持😀",
      mutableTail: "新方案",
    });
  });

  it("renders the complete first partial in the initial React render", () => {
    const view = render(createElement(ImmediateTranscriptText, { segment: segment(), active: true }));
    expect(view.container.querySelector("p")).toHaveTextContent("请介绍你的项目");
    expect(requestAnimationFrame).not.toHaveBeenCalled();
  });

  it("renders a growing revision immediately without a reservoir or animation", () => {
    const view = render(createElement(ImmediateTranscriptText, {
      segment: segment({ text: "请介绍项目" }), active: true,
    }));
    view.rerender(createElement(ImmediateTranscriptText, {
      segment: segment({ revision: 2, text: "请介绍项目经验" }), active: true,
    }));
    const paragraph = view.container.querySelector("p")!;
    expect(paragraph).toHaveTextContent("请介绍项目经验");
    expect([...paragraph.querySelectorAll(":scope > span")].slice(0, 2).map(node => node.textContent)).toEqual([
      "请介绍项目", "经验",
    ]);
    expect(requestAnimationFrame).not.toHaveBeenCalled();
  });

  it("replaces a corrected provider tail in the same render", () => {
    const view = render(createElement(ImmediateTranscriptText, {
      segment: segment({ text: "项目负责上线" }), active: true,
    }));
    view.rerender(createElement(ImmediateTranscriptText, {
      segment: segment({ revision: 2, text: "项目复盘结果" }), active: true,
    }));
    expect(view.container.querySelector("p")).toHaveTextContent("项目复盘结果");
    expect(view.container.querySelector("p")).not.toHaveTextContent("负责上线");
  });

  it("renders a shorter provider revision immediately instead of waiting for Final", () => {
    const view = render(createElement(ImmediateTranscriptText, {
      segment: segment({ text: "请介绍一下你最近负责的项目" }), active: true,
    }));
    view.rerender(createElement(ImmediateTranscriptText, {
      segment: segment({ revision: 2, text: "请介绍项目" }), active: true,
    }));
    expect(view.container.querySelector("p")).toHaveTextContent("请介绍项目");
    expect(view.container.querySelector("p")).not.toHaveTextContent("最近负责");
  });

  it("renders Final immediately with no tail animation", () => {
    const view = render(createElement(ImmediateTranscriptText, {
      segment: segment({ text: "已有部分" }), active: true,
    }));
    view.rerender(createElement(ImmediateTranscriptText, {
      segment: segment({ revision: 2, text: "已有部分以及最终尾字", isFinal: true }), active: false,
    }));
    expect(view.container.querySelector("p")).toHaveTextContent("已有部分以及最终尾字");
    expect(requestAnimationFrame).not.toHaveBeenCalled();
  });

  it("does not infer incomplete from the client age of a partial", () => {
    expect(transcriptPresentationState({ isFinal: false })).toBe("transcribing");
    expect(transcriptPresentationState({ isFinal: true })).toBe("final");
    expect(transcriptPresentationState({ isFinal: true, terminalState: "incomplete" })).toBe("stale");
  });

  it("freezes a committing partial without turning it incomplete while final reconciles", () => {
    expect(transcriptPresentationState({ isFinal: false, turnState: "committing" })).toBe("confirming");
    expect(transcriptPresentationLabel("confirming")).toBe("已转写");
    expect(transcriptPresentationLabel("stale")).toBe("识别未完成");
  });
});
