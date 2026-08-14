import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { companionPrimaryAction, companionStatusCopy, liveInterviewUrl } from "../src/renderer/CompanionApp";

describe("companion interview wording", () => {
  it("uses concise pairing-terminal wording", () => {
    expect(companionPrimaryAction("ready")).toBe("复制连接码");
    expect(companionStatusCopy.ready.detail).toContain("输入固定机器码即可连接面试");
    expect(companionStatusCopy["permission-required"].detail).toContain("完成麦克风与屏幕录制授权");
    expect(companionPrimaryAction("permission-required")).toBe("复制连接码");
    expect(companionPrimaryAction("capturing")).toBe("已连接");
  });

  it("opens the authoritative live interview instead of the workspace home", () => {
    expect(liveInterviewUrl("https://mianshiwen.cn/app", "session-current")).toBe(
      "https://mianshiwen.cn/app/interviews/session-current/live",
    );
  });

  it("keeps the screen thumbnail visible without an unnecessary close-preview action", () => {
    const source = readFileSync(new URL("../src/renderer/CompanionApp.tsx", import.meta.url), "utf8");

    expect(source).toContain('aria-label="屏幕捕捉预览"');
    expect(source).not.toContain(">关闭预览</button>");
  });
});
