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

  it("keeps preview wording stable while a screenshot is processing", () => {
    const source = readFileSync(new URL("../src/renderer/CompanionApp.tsx", import.meta.url), "utf8");

    expect(source).toContain("disabled={screenshotCaptureLocked}");
    expect(source).toContain(">\n                预览\n              </button>");
    expect(source).not.toContain("取消当前截屏");
    expect(source).not.toContain("cancelScreenshotCapture");
  });

  it("shows screen imagery only in an on-demand preview dialog", () => {
    const source = readFileSync(new URL("../src/renderer/CompanionApp.tsx", import.meta.url), "utf8");

    expect(source).not.toContain('className="preview-row"');
    expect(source).toContain('aria-labelledby="screen-preview-title"');
    expect(source).toContain('aria-label="关闭屏幕预览"');
    expect(source).not.toContain('<button type="button" className="primary-button" onClick={closeScreenPreview}>完成</button>');
    expect(source).toContain("正在获取最新屏幕画面");
    expect(source).toContain("setShowScreenPreviewDialog(true)");
    expect(source).toContain("previewRequestIdRef.current += 1");
  });
});
