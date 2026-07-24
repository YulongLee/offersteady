import { describe, expect, it } from "vitest";

import { nextProgressiveTranscriptText } from "./ConversationMonitor";

describe("progressive realtime transcript", () => {
  it("reveals appended partial text without replacing the whole sentence", () => {
    expect(nextProgressiveTranscriptText("你好", "你好，请介绍项目")).toBe("你好，请");
  });

  it("recovers from an ASR correction at the first changed character", () => {
    expect(nextProgressiveTranscriptText("项目负责", "项目复盘")).toBe("项目复盘");
  });
});
