import { cleanup, render, screen } from "@testing-library/react";
import { createElement } from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { SubtitleDiagnosticsOverlay } from "./SubtitleDiagnosticsOverlay";
import {
  getSubtitleDiagnosticsSnapshot,
  recordSubtitleBackendStages,
  recordSubtitleRevisionStage,
  subtitleRevisionIdentity,
} from "./realtime-subtitle-diagnostics";

describe("realtime subtitle revision diagnostics", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/app/interviews/synthetic?subtitleDiagnostics=1");
  });
  afterEach(cleanup);

  it("correlates one revision without retaining transcript content", () => {
    const payload = {
      segmentId: "segment-safe-1",
      revision: 2,
      text: "仅用于计算长度的合成文本",
      performance: {
        traceId: "trace-safe-1",
        utteranceId: "utterance-safe-1",
        qwenPartialReceivedAtMs: 100,
        transcriptEventCreatedAtMs: 101,
        redisEventXaddCompleteAtMs: 102,
        redisEventXreadAtMs: 103,
        sseGeneratorYieldAtMs: 104,
      },
    };
    const identity = subtitleRevisionIdentity("session-safe-1", "event-safe-1", payload);
    expect(identity).toMatchObject({ revision: 2, textLength: payload.text.length });
    expect(JSON.stringify(identity)).not.toContain(payload.text);
    recordSubtitleBackendStages(identity!, payload.performance);
    recordSubtitleRevisionStage(identity!, "browser-parse", 105);
    const snapshot = getSubtitleDiagnosticsSnapshot();
    expect(snapshot.stageCounts).toMatchObject({ qwen: 1, event: 1, "redis-xadd": 1, "redis-xread": 1, "sse-yield": 1, "browser-parse": 1 });
  });

  it("keeps the overlay isolated from normal pages", () => {
    window.history.replaceState({}, "", "/app/interviews/synthetic");
    const { rerender } = render(createElement(SubtitleDiagnosticsOverlay));
    expect(screen.queryByLabelText("实时字幕诊断")).toBeNull();
    window.history.replaceState({}, "", "/app/interviews/synthetic?subtitleDiagnostics=1");
    rerender(createElement(SubtitleDiagnosticsOverlay));
    expect(screen.getByLabelText("实时字幕诊断")).toBeInTheDocument();
  });
});
