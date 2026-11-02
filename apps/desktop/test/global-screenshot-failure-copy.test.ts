import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { describe, expect, it, vi } from "vitest";
import { screenshotFailureMessage } from "../src/main/global-screenshot-failure-copy";
import { localizeGlobalCompanionProps } from "../src/renderer/global-copy";

const source = readFileSync(new URL("../src/main/index.ts", import.meta.url), "utf8");
const ts = createRequire(import.meta.url)("typescript") as typeof import("typescript");
const compile = (start: string, end: string) => {
  const from = source.indexOf(start), to = source.indexOf(end, from);
  if (from < 0 || to < 0) throw new Error("capture failure source boundary missing");
  return ts.transpileModule(source.slice(from, to), { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS,
  } }).outputText;
};
const legacyReport = compile("const reportRemoteScreenshotFailure =", "interface WrittenBinding");
const writtenPorts = compile("const writtenScreenshotProcessor =", "const enqueueWrittenScreenshot =");
const uploadFailure = "截图回传超时，请查看网页状态后重试。";

describe("Global outgoing screenshot failures", () => {
  it.each([true, false])("localizes the actual existing failure report for Global=%s", async (global) => {
    const fetch = vi.fn(async (_input: string, _init: RequestInit) => new Response(""));
    const report = new Function("fetchWithTimeout", "desktopApiUrl", "isGlobalRelease", "screenshotFailureMessage", `${legacyReport};return reportRemoteScreenshotFailure;`)(
      fetch, (x: string) => x, () => global, screenshotFailureMessage,
    );
    await report({ deviceId: "synthetic-device", manualCode: "synthetic-code" }, "synthetic-request", uploadFailure, "upload-failed");
    const payload = JSON.parse(fetch.mock.calls[0]![1]!.body as string);
    expect(payload.message).toBe(global ? "Screenshot upload timed out. Check the web status before retrying." : uploadFailure);
    expect(payload.stage).toBe("upload-failed");
    expect(payload.deviceId).toBe("synthetic-device");
  });

  it.each([true, false])("localizes the actual written processor report for Global=%s and retains terminal 409", async (global) => {
    const fetch = vi.fn(async (_input: string, _init: RequestInit) => new Response("", { status: 409 }));
    class CapturePorts { constructor(readonly ports: Record<string, (...args: unknown[]) => unknown>) {} }
    const report = new Function("WrittenScreenshotProcessor", "fetch", "desktopApiUrl", "isGlobalRelease", "screenshotFailureMessage", "isCurrentWrittenJob", `${writtenPorts};return writtenScreenshotProcessor.ports.report;`)(
      CapturePorts, fetch, (x: string) => x, () => global, screenshotFailureMessage, () => true,
    );
    await report({ requestId: "synthetic-request", identity: { deviceId: "synthetic-device", manualCode: "synthetic-code" } },
      { message: uploadFailure, stage: "upload" }, new AbortController().signal);
    const payload = JSON.parse(fetch.mock.calls[0]![1]!.body as string);
    expect(payload.message).toBe(global ? "Screenshot upload timed out. Check the web status before retrying." : uploadFailure);
    expect(payload.stage).toBe("upload-failed");
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("keeps known capture, request and timeout failures specific in English", () => {
    for (const text of ["截屏等待超时，请重试。", "截图请求较多，请稍候重试。", "截图回传结果尚未确认，请查看网页状态。", "暂时无法确认截图请求，请检查助手连接后重试。", "屏幕截取仍在恢复，请重新打开助手后重试。"]) {
      const translated = screenshotFailureMessage(true, text);
      expect(translated).not.toMatch(/[\u3400-\u9fff]/);
      expect(translated).not.toContain("Screen capture or upload failed.");
      expect(screenshotFailureMessage(false, text)).toBe(text);
    }
  });

  it("does not expose unknown Chinese provider content while retaining existing English failures", () => {
    expect(screenshotFailureMessage(true, "合成供应商错误")).toBe("Screen capture or upload failed. Check device permissions and the companion connection, then try again.");
    expect(screenshotFailureMessage(true, "network unavailable")).toBe("network unavailable");
  });

  it("keeps the actual new permission, hidden restore and stage UI copy specific", () => {
    for (const text of ["截图回传失败，请检查连接后重试。", "等待系统确认麦克风，请稍后重试。", "模拟面试收音已中断。请点击“重试麦克风”恢复。", "点击原菜单栏／托盘图标位置或按 ⌘/Ctrl + Shift + H 恢复"]) {
      const props = localizeGlobalCompanionProps({ children: text, title: text });
      expect(String(props?.children)).not.toMatch(/[\u3400-\u9fff]/);
      expect(props?.children).not.toContain("The companion reported an issue.");
      expect(props?.title).toBe(props?.children);
    }
  });
});
