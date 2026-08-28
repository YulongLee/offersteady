import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { companionPrimaryAction, companionStatusCopy, workspaceEntryUrl } from "../src/renderer/CompanionApp";

describe("companion interview wording", () => {
  it("uses concise pairing-terminal wording", () => {
    expect(companionPrimaryAction("ready")).toBe("复制连接码");
    expect(companionStatusCopy.ready.detail).toContain("输入固定机器码即可连接面试");
    expect(companionStatusCopy["permission-required"].detail).toContain("完成麦克风与屏幕录制授权");
    expect(companionPrimaryAction("permission-required")).toBe("复制连接码");
    expect(companionPrimaryAction("capturing")).toBe("已连接");
  });

  it("opens the configured workspace without deriving a live interview route", () => {
    expect(workspaceEntryUrl("https://mianshiwen.cn/app/interviews/session-current/live?from=desktop#active")).toBe(
      "https://mianshiwen.cn/app",
    );
    expect(workspaceEntryUrl(undefined)).toBe("http://localhost:5173/app");
    expect(workspaceEntryUrl("not-a-url")).toBe("http://localhost:5173/app");

    const source = readFileSync(new URL("../src/renderer/CompanionApp.tsx", import.meta.url), "utf8");
    expect(source).toContain('openResolvedUrl("workspace")');
    expect(source).toContain("打开面试稳网站");
    expect(source).not.toContain("进入当前面试");
    expect(source).not.toContain("/live`");
  });

  it("keeps preview wording stable while a screenshot is processing", () => {
    const source = readFileSync(new URL("../src/renderer/CompanionApp.tsx", import.meta.url), "utf8");

    expect(source).toContain("disabled={screenshotCaptureLocked}");
    expect(source).toContain(">\n                预览\n              </button>");
    expect(source).not.toContain("取消当前截屏");
    expect(source).not.toContain("cancelScreenshotCapture");
  });

  it("keeps the accepted audio-row layout independent from permission state", () => {
    const source = readFileSync(new URL("../src/renderer/CompanionApp.tsx", import.meta.url), "utf8");

    expect(source).toContain('subtitle="识别你的声音"');
    expect(source).toContain('statusLabel="我的声音"');
    expect(source).toContain('subtitle="识别你能听到的面试官声音"');
    expect(source).toContain('statusLabel="面试官声音"');
    expect(source).not.toContain("开启电脑音频权限");
    expect(source).not.toContain("等待声音检查");
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
