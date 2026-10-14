import { describe, expect, it } from "vitest";
import { mockMicrophoneHealth, mockMicrophoneMeterCopy } from "../src/renderer/audio/mock-microphone-presentation";

describe("mock microphone presentation uses actual capture evidence", () => {
  it("does not claim sound was detected just because capture opened", () => {
    expect(mockMicrophoneHealth("capturing", null, "synthetic").state).toBe("unknown");
    expect(mockMicrophoneMeterCopy("capturing", null)).toBe("麦克风已就绪，等待声音");
    expect(mockMicrophoneHealth("capturing", 0, "synthetic").state).toBe("silent");
    expect(mockMicrophoneMeterCopy("capturing", 0)).toBe("麦克风已就绪，等待声音");
  });

  it("shows receiving only after PCM level is above the existing microphone threshold", () => {
    expect(mockMicrophoneHealth("capturing", 0.1, "synthetic")).toMatchObject({ state: "receiving", level: 0.1 });
    expect(mockMicrophoneMeterCopy("capturing", 0.1)).toBe("正在采集你的回答");
  });

  it("discards old level while paused or failed and retains the correct failure state", () => {
    expect(mockMicrophoneHealth("paused", 0.1, "synthetic")).toMatchObject({ state: "unknown", level: 0 });
    expect(mockMicrophoneHealth("error", 0.1, "synthetic")).toMatchObject({ state: "error", level: 0 });
    expect(mockMicrophoneMeterCopy("error", 0.1)).toBe("麦克风启动失败");
  });
});
