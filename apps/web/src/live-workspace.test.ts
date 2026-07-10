import { describe, expect, it } from "vitest";
import { syntheticState } from "./test-state";
import { DEFAULT_SPLIT_RATIO, answerPage, clampSplitRatio, initialLiveWorkspaceView, noteNewAnswer, parseStoredSplitRatio, serializeSplitRatio, splitRatioBounds, splitRatioStorageKey } from "./live-workspace";

describe("live workspace answer pagination", () => {
  const answers = syntheticState.questions;

  it("moves through stable answer ids and disables boundary directions", () => {
    const latest = answerPage(answers, null)!;
    expect(latest.answer.id).toBe("q-current");
    expect(latest.nextId).toBeNull();
    expect(latest.previousId).toBe("q-old");

    const oldest = answerPage(answers, "q-old")!;
    expect(oldest.answer.id).toBe("q-old");
    expect(oldest.previousId).toBeNull();
    expect(oldest.nextId).toBe("q-current");
  });

  it("keeps the selected historical id when a new answer arrives", () => {
    const browsing = { ...initialLiveWorkspaceView(), viewingAnswerId: "q-old" };
    const updated = noteNewAnswer(browsing, "q-current", "q-new");
    expect(updated.viewingAnswerId).toBe("q-old");
    expect(updated.newAnswerAvailable).toBe(true);
  });

  it("validates, clamps and versions session-scoped split ratios", () => {
    expect(splitRatioStorageKey("session-a")).not.toBe(splitRatioStorageKey("session-b"));
    expect(parseStoredSplitRatio(serializeSplitRatio(57))).toBe(57);
    expect(parseStoredSplitRatio('{"version":0,"ratio":57}')).toBe(DEFAULT_SPLIT_RATIO);
    expect(parseStoredSplitRatio('{"version":1,"ratio":999}')).toBe(DEFAULT_SPLIT_RATIO);
    expect(parseStoredSplitRatio("broken")).toBe(DEFAULT_SPLIT_RATIO);
    expect(clampSplitRatio(10)).toBe(25);
    expect(clampSplitRatio(90)).toBe(75);
  });

  it("derives minimum-width bounds from the available desktop width", () => {
    const bounds = splitRatioBounds(1200);
    expect(bounds.min).toBeGreaterThanOrEqual(25);
    expect(bounds.max).toBeLessThanOrEqual(75);
    expect(clampSplitRatio(5, bounds)).toBe(bounds.min);
    expect(clampSplitRatio(95, bounds)).toBe(bounds.max);
  });
});
