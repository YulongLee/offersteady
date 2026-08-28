import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SpeakerTranscriptSegment } from "@offersteady/protocol";
import { createElement } from "react";

import {
  firstAdaptiveTranscriptText,
  nextAdaptiveTranscriptText,
  nextProgressiveTranscriptText,
  ProgressiveTranscriptText,
  transcriptPresentationLabel,
  transcriptPresentationState,
} from "./ConversationMonitor";

describe("progressive realtime transcript", () => {
  let frameId = 0;
  let frameCallbacks: Map<number, FrameRequestCallback>;
  let now = 1_000;

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

  const runFrame = (advanceMs: number) => {
    now = Math.max(now, window.performance.now()) + advanceMs;
    const callbacks = [...frameCallbacks.values()];
    frameCallbacks.clear();
    act(() => callbacks.forEach(callback => callback(now)));
  };

  beforeEach(() => {
    frameId = 0;
    frameCallbacks = new Map();
    now = window.performance.now();
    vi.stubGlobal("requestAnimationFrame", vi.fn((callback: FrameRequestCallback) => {
      const id = ++frameId;
      frameCallbacks.set(id, callback);
      return id;
    }));
    vi.stubGlobal("cancelAnimationFrame", vi.fn((id: number) => { frameCallbacks.delete(id); }));
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reveals the first received character immediately", () => {
    expect(firstAdaptiveTranscriptText("", "你好，请介绍项目")).toBe("你");
    expect(firstAdaptiveTranscriptText("你好", "你好，请介绍项目")).toBe("你好，");
  });

  it("dynamically increases its step and always catches up within 300ms", () => {
    const target = "面".repeat(100);
    const first = firstAdaptiveTranscriptText("", target);
    const progressing = nextAdaptiveTranscriptText(first, target, 32);
    expect(progressing.length).toBeGreaterThan(first.length);
    expect(nextAdaptiveTranscriptText(progressing, target, 300)).toBe(target);
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

  it("smooths a received partial with one shared frame loop and catches up", () => {
    const view = render(createElement(ProgressiveTranscriptText, { segment: segment(), active: true }));
    const paragraph = view.container.querySelector("p")!;
    expect(paragraph).toHaveTextContent("请");
    expect(requestAnimationFrame).toHaveBeenCalledTimes(1);

    runFrame(40);
    expect(paragraph.textContent!.length).toBeGreaterThan(1);
    runFrame(300);
    expect(paragraph).toHaveTextContent("请介绍你的项目");
  });

  it("flushes an authoritative Final immediately and cancels pending smoothing", () => {
    const view = render(createElement(ProgressiveTranscriptText, { segment: segment(), active: true }));
    expect(view.container.querySelector("p")).toHaveTextContent("请");
    view.rerender(createElement(ProgressiveTranscriptText, { segment: segment({ revision: 2, text: "最终文本", isFinal: true }), active: false }));
    expect(view.container.querySelector("p")).toHaveTextContent("最终文本");
    expect(cancelAnimationFrame).toHaveBeenCalled();
  });

  it("renders immediately for reduced motion and does not schedule smoothing", () => {
    vi.mocked(window.matchMedia).mockReturnValue({ matches: true } as MediaQueryList);
    const view = render(createElement(ProgressiveTranscriptText, { segment: segment(), active: true }));
    expect(view.container.querySelector("p")).toHaveTextContent("请介绍你的项目");
    expect(requestAnimationFrame).not.toHaveBeenCalled();
  });

  it("cancels its shared frame job when the session row unmounts", () => {
    const view = render(createElement(ProgressiveTranscriptText, { segment: segment(), active: true }));
    expect(requestAnimationFrame).toHaveBeenCalledTimes(1);
    view.unmount();
    expect(cancelAnimationFrame).toHaveBeenCalledTimes(1);
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
