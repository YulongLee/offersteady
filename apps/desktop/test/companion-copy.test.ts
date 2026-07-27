import { describe, expect, it } from "vitest";
import { companionPrimaryAction, companionStatusCopy } from "../src/renderer/CompanionApp";

describe("companion interview wording", () => {
  it("uses concise pairing-terminal wording", () => {
    expect(companionPrimaryAction("ready")).toBe("复制连接码");
    expect(companionStatusCopy.ready.detail).toContain("输入固定机器码即可连接面试");
    expect(companionStatusCopy["permission-required"].detail).toContain("完成麦克风与屏幕录制授权");
    expect(companionPrimaryAction("permission-required")).toBe("复制连接码");
    expect(companionPrimaryAction("capturing")).toBe("已连接");
  });
});
