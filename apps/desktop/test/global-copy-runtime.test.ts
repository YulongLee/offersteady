import { describe, expect, it } from "vitest";

import { localizeGlobalCompanionProps } from "../src/renderer/global-copy";

describe("Global companion runtime copy", () => {
  it("translates the companion product badge", () => {
    expect(localizeGlobalCompanionProps({ children: "电脑伴随助手" })).toEqual({ children: "Desktop Companion" });
  });

  it("translates an exact current companion state without changing its meaning", () => {
    expect(localizeGlobalCompanionProps({ children: "网页笔试已绑定这台电脑，仅启用截屏回答。" })).toEqual({
      children: "The written exam is paired with this computer. Only Screenshot Answer is enabled.",
    });
  });

  it("composes dynamic status messages from translated fragments", () => {
    const translated = localizeGlobalCompanionProps({
      children: "登记失败：network unavailable。请确认后端服务已启动后重试。",
    });
    expect(translated).toEqual({
      children: "Registration failed: network unavailable. Confirm the service is available, then try again.",
    });
    expect(String(translated?.children)).not.toMatch(/[\u3400-\u9fff]/);
  });

  it("does not expose an untranslated unknown Chinese provider failure", () => {
    const translated = localizeGlobalCompanionProps({ children: "未收录的服务端中文错误" });
    expect(translated).toEqual({
      children: "The companion reported an issue. Check device permissions and the connection, then try again.",
    });
  });
});
