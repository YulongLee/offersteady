import { execFile } from "node:child_process";
import path from "node:path";
import { desktopCapturer, nativeImage, screen, systemPreferences } from "electron";

export async function captureMacPreviewSources(screenSourceId: string | null, signal?: AbortSignal) {
  if (systemPreferences.getMediaAccessStatus("screen") !== "granted") {
    throw new Error("当前尚未获得屏幕录制权限");
  }
  const sources = await desktopCapturer.getSources({
    types: ["screen"],
    thumbnailSize: { width: 0, height: 0 },
  });
  const selected = screenSourceId
    ? sources.find(source => source.id === screenSourceId)
    : sources.find(source => source.display_id === String(screen.getPrimaryDisplay().id));
  if (!selected) return [];
  if (!/^[1-9]\d*$/.test(selected.display_id)) {
    throw new Error("无法定位当前显示器，请重新选择后再试");
  }
  const helper = path.join(process.resourcesPath, "app/native/macos-capture/OfferSteadyFilteredScreenshot");
  const png = await new Promise<Buffer>((resolve, reject) => {
    execFile(helper, [selected.display_id, String(process.pid)], {
      encoding: "buffer", timeout: 7_000, maxBuffer: 12 * 1024 * 1024, ...(signal ? { signal } : {}),
    }, (error, stdout) => {
      if (error) reject(new Error("未能取得已排除助手窗口的画面，请重试"));
      else resolve(stdout);
    });
  });
  const thumbnail = nativeImage.createFromBuffer(png);
  if (thumbnail.isEmpty()) throw new Error("过滤后的截图为空，请重试");
  return [{ ...selected, thumbnail }];
}
