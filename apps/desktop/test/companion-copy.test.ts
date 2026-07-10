import { describe, expect, it } from "vitest";
import { companionPrimaryAction, companionStatusCopy } from "../src/renderer/CompanionApp";

describe("companion interview wording", () => {
  it("uses concise pairing-terminal wording", () => {
    expect(companionPrimaryAction("ready")).toBe("复制连接码");
    expect(companionStatusCopy.ready.detail).toContain("输入后，会绑定这台收音电脑");
    expect(companionStatusCopy["permission-required"].detail).toContain("选择麦克风、系统音频和屏幕捕捉");
    expect(companionPrimaryAction("permission-required")).toBe("复制连接码");
    expect(companionPrimaryAction("capturing")).toBe("已连接");
  });
});
