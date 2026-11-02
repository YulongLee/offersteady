import { describe, expect, it } from "vitest";
import { writtenScreenshotFailureMessage } from "./written-screenshot-feedback";

describe("written screenshot failure feedback", () => {
  it("distinguishes the current backend heartbeat rejection from invalid binding", () => {
    expect(writtenScreenshotFailureMessage("电脑伴随程序心跳已过期，请保持伴随程序打开。")).toContain("本地助手已离线");
    for (const message of [
      "这台电脑尚未登记或机器码不匹配。", "网页端尚未输入该机器码绑定面试。",
      "网页端绑定已失效，请重新绑定机器码。", "伴随程序已重新登记，请在面试页重新绑定机器码。",
    ]) expect(writtenScreenshotFailureMessage(message)).toBe("本地助手连接已失效，请重新连接后截屏。");
  });

  it.each(["capture-failed", "upload-failed"])("uses existing %s stages even if legacy text is ambiguous", stage => {
    const expected = stage === "capture-failed" ? "截屏失败，请检查本地助手的共享屏幕或录制权限后重试。" : "截图上传失败，请检查网络后重新截屏。";
    expect(writtenScreenshotFailureMessage("request timed out", stage)).toBe(expected);
    expect(writtenScreenshotFailureMessage(`截图阶段 ${stage} 失败：request timed out`)).toBe(expected);
  });

  it.each(["当前面试已结束，不能继续截图回答。", "截图已过期，请重新截屏。", "余额不足", "无法连接后端基础服务", "404", "截屏回答失败，请稍后重试。"])("preserves other errors without claiming the assistant is offline: %s", message => {
    expect(writtenScreenshotFailureMessage(message)).toBe(message);
  });
});
