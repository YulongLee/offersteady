import { describe, expect, it, vi } from "vitest";

import { createAnswerStreamUpdateScheduler } from "./answer-stream-update-scheduler";

describe("answer stream update scheduler", () => {
  it("applies the first visible chunk immediately and coalesces later updates", () => {
    const applied: string[] = [];
    let scheduled: (() => void) | null = null;
    const cancel = vi.fn();
    const scheduler = createAnswerStreamUpdateScheduler<string>({
      apply: update => applied.push(update),
      isFirstVisible: update => update.startsWith("chunk:"),
      schedule: callback => {
        scheduled = callback;
        return 7;
      },
      cancel,
    });

    scheduler.push("task-started");
    expect(applied).toEqual([]);
    scheduler.push("chunk:first");
    expect(applied).toEqual(["chunk:first"]);
    expect(cancel).toHaveBeenCalledWith(7);

    scheduler.push("chunk:second");
    scheduler.push("chunk:third");
    expect(applied).toEqual(["chunk:first"]);
    expect(scheduled).not.toBeNull();
    (scheduled as () => void)();
    expect(applied).toEqual(["chunk:first", "chunk:third"]);
  });

  it("flushes terminal updates without waiting", () => {
    const applied: string[] = [];
    const scheduler = createAnswerStreamUpdateScheduler<string>({
      apply: update => applied.push(update),
      isFirstVisible: update => update.startsWith("chunk:"),
      schedule: () => 9,
      cancel: () => undefined,
    });
    scheduler.push("completed", true);
    expect(applied).toEqual(["completed"]);
  });
});
