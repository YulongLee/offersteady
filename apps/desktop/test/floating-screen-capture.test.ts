import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { captureMacPreviewSources } from "../src/main/floating-screen-capture";

const mocks = vi.hoisted(() => ({
  sources: vi.fn(),
  primary: vi.fn(),
  permission: vi.fn(),
  decode: vi.fn(),
  screenshot: vi.fn(),
}));

vi.mock("node:child_process", () => ({ execFile: mocks.screenshot }));
vi.mock("electron", () => ({
  desktopCapturer: { getSources: mocks.sources },
  screen: { getPrimaryDisplay: mocks.primary },
  systemPreferences: { getMediaAccessStatus: mocks.permission },
  nativeImage: { createFromBuffer: mocks.decode },
}));

const screen = { id: "screen:0:0", display_id: "18", name: "Screen 1", thumbnail: "unfiltered" };
const originalResourcesPath = Object.getOwnPropertyDescriptor(process, "resourcesPath");

beforeEach(() => {
  Object.defineProperty(process, "resourcesPath", { configurable: true, value: "/test/resources" });
  vi.resetAllMocks();
  mocks.sources.mockResolvedValue([screen]);
  mocks.primary.mockReturnValue({ id: 18 });
  mocks.permission.mockReturnValue("granted");
});

afterEach(() => {
  if (originalResourcesPath) Object.defineProperty(process, "resourcesPath", originalResourcesPath);
  else Reflect.deleteProperty(process, "resourcesPath");
});

it("filters the entire companion on the selected display", async () => {
  const png = Buffer.from("filtered");
  const image = { isEmpty: () => false };
  mocks.screenshot.mockImplementation((_path, _args, _options, callback) => callback(null, png));
  mocks.decode.mockReturnValue(image);
  const signal = new AbortController().signal;

  await expect(captureMacPreviewSources(screen.id, signal)).resolves.toEqual([{ ...screen, thumbnail: image }]);
  expect(mocks.sources).toHaveBeenCalledExactlyOnceWith({ types: ["screen"], thumbnailSize: { width: 0, height: 0 } });
  expect(mocks.screenshot).toHaveBeenCalledExactlyOnceWith(
    expect.stringContaining("OfferSteadyFilteredScreenshot"),
    ["18", String(process.pid)],
    expect.objectContaining({ signal }),
    expect.any(Function),
  );
});

it("defaults to the primary display even when Electron lists another display first", async () => {
  mocks.sources.mockResolvedValue([{ ...screen, id: "screen:1:0", display_id: "28" }, screen]);
  mocks.screenshot.mockImplementation((_path, _args, _options, callback) => callback(null, Buffer.from("filtered")));
  const image = { isEmpty: () => false };
  mocks.decode.mockReturnValue(image);

  await expect(captureMacPreviewSources(null)).resolves.toEqual([{ ...screen, thumbnail: image }]);
});

it("does not return the raw thumbnail when native exclusion fails", async () => {
  mocks.screenshot.mockImplementation((_path, _args, _options, callback) => callback(new Error("unavailable")));

  await expect(captureMacPreviewSources(screen.id)).rejects.toThrow("未能取得已排除助手窗口的画面");
  expect(mocks.sources).toHaveBeenCalledOnce();
  expect(mocks.decode).not.toHaveBeenCalled();
});

it("does not request a screen capture when recording permission is unavailable", async () => {
  mocks.permission.mockReturnValue("denied");

  await expect(captureMacPreviewSources(null)).rejects.toThrow("当前尚未获得屏幕录制权限");
  expect(mocks.sources).not.toHaveBeenCalled();
  expect(mocks.screenshot).not.toHaveBeenCalled();
});

it("does not capture a different screen if the selected display is gone", async () => {
  await expect(captureMacPreviewSources("screen:2:0")).resolves.toEqual([]);
  expect(mocks.screenshot).not.toHaveBeenCalled();
});
