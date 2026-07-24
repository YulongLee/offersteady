import { describe, expect, it } from "vitest";
import { syntheticState } from "./test-state";
import { DEFAULT_SPLIT_RATIO, answerPage, clampSplitRatio, initialLiveWorkspaceView, noteNewAnswer, parseStoredSplitRatio, reconcileRealtimeSpeaker, serializeSplitRatio, splitRatioBounds, splitRatioStorageKey } from "./live-workspace";

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

  it("keeps only the newest visible revision for a realtime utterance", () => {
    const current = syntheticState.speaker;
    const original = current.transcripts[0]!;
    const reconciled = reconcileRealtimeSpeaker(current, {
      ...current,
      transcripts: [
        { ...original, revision: original.revision + 1, text: "更新后的实时文本", isFinal: false },
        { ...original, revision: original.revision + 2, text: "最终实时文本", isFinal: true },
        { ...original, id: "blank-segment", text: "   ", revision: 1 },
      ],
    });
    expect(reconciled.transcripts.filter(segment => segment.id === original.id)).toEqual([
      expect.objectContaining({ revision: original.revision + 2, text: "最终实时文本", isFinal: true }),
    ]);
    expect(reconciled.transcripts.some(segment => segment.id === "blank-segment")).toBe(false);
  });

  it("does not let a stale snapshot overwrite a newer partial revision", () => {
    const current = syntheticState.speaker;
    const original = current.transcripts[0]!;
    const newer = { ...original, revision: original.revision + 3, text: "本地已收到的新版本" };
    const reconciled = reconcileRealtimeSpeaker(
      { ...current, transcripts: [newer] },
      { ...current, transcripts: [original] },
    );
    expect(reconciled.transcripts).toEqual([newer]);
  });
});
