export interface ScreenCaptureResult {
  readonly name: string;
  readonly width?: number;
  readonly height?: number;
  readonly source: "desktop-bridge" | "browser-display" | "synthetic";
  readonly file?: File;
}

export interface ScreenCaptureAdapter {
  captureCurrentScreen(signal?: AbortSignal): Promise<ScreenCaptureResult>;
}

declare global {
  interface Window {
    offersteadyDesktop?: {
      captureCurrentScreen?: () => Promise<{
        readonly name?: string;
        readonly width?: number;
        readonly height?: number;
        readonly dataUrl?: string;
      }>;
    };
  }
}

const abortError = () => new DOMException("Aborted", "AbortError");

const delay = (milliseconds: number, signal?: AbortSignal) => new Promise<void>((resolve, reject) => {
  if (signal?.aborted) {
    reject(abortError());
    return;
  }
  const timeoutId = window.setTimeout(resolve, milliseconds);
  signal?.addEventListener("abort", () => {
    window.clearTimeout(timeoutId);
    reject(abortError());
  }, { once: true });
});

const stopTracks = (stream: MediaStream) => {
  stream.getTracks().forEach(track => track.stop());
};

const blobToFile = (blob: Blob, filename: string) => new File([blob], filename, {
  type: blob.type || "image/png",
  lastModified: Date.now(),
});

const sanitizeCaptureName = (name: string) => {
  const base = name.replace(/[\\/:*?"<>|]+/g, "-").trim() || "current-screen";
  return base.endsWith(".png") ? base : `${base}.png`;
};

const dataUrlToFile = (dataUrl: string, name: string) => {
  const [meta, payload] = dataUrl.split(",", 2);
  if (!meta || !payload) throw new Error("桌面端未返回有效截图数据");
  const mimeMatch = meta.match(/^data:(.*?);base64$/);
  const mimeType = mimeMatch?.[1] || "image/png";
  const binary = window.atob(payload);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return new File([bytes], sanitizeCaptureName(name), { type: mimeType, lastModified: Date.now() });
};

const canvasBlob = (canvas: HTMLCanvasElement, type = "image/png") => new Promise<Blob>((resolve, reject) => {
  canvas.toBlob(blob => {
    if (!blob) {
      reject(new Error("当前屏幕截取失败，请重试。"));
      return;
    }
    resolve(blob);
  }, type);
});

const scaleDimensions = (width: number, height: number, maxEdge = 1600) => {
  const longest = Math.max(width, height);
  if (longest <= maxEdge) return { width, height };
  const ratio = maxEdge / longest;
  return {
    width: Math.max(1, Math.round(width * ratio)),
    height: Math.max(1, Math.round(height * ratio)),
  };
};

export const screenCaptureAdapter: ScreenCaptureAdapter = {
  async captureCurrentScreen(signal) {
    if (window.offersteadyDesktop?.captureCurrentScreen) {
      const captured = await window.offersteadyDesktop.captureCurrentScreen();
      if (signal?.aborted) throw abortError();
      if (!captured.dataUrl) throw new Error("桌面端暂未返回截图图像");
      return {
        name: captured.name?.trim() || "当前屏幕截取",
        ...(typeof captured.width === "number" ? { width: captured.width } : {}),
        ...(typeof captured.height === "number" ? { height: captured.height } : {}),
        source: "desktop-bridge",
        file: dataUrlToFile(captured.dataUrl, captured.name?.trim() || "当前屏幕截取"),
      };
    }

    if (typeof navigator !== "undefined" && navigator.mediaDevices?.getDisplayMedia) {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
      try {
        if (signal?.aborted) throw abortError();
        const [videoTrack] = stream.getVideoTracks();
        const settings = videoTrack?.getSettings?.() ?? {};
        const video = document.createElement("video");
        video.srcObject = stream;
        video.muted = true;
        video.playsInline = true;
        await video.play();
        await delay(90, signal);
        const rawWidth = typeof settings.width === "number" ? settings.width : (video.videoWidth || 1280);
        const rawHeight = typeof settings.height === "number" ? settings.height : (video.videoHeight || 720);
        const { width, height } = scaleDimensions(rawWidth, rawHeight);
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const context = canvas.getContext("2d");
        if (!context) throw new Error("当前浏览器不支持截图渲染");
        context.drawImage(video, 0, 0, width, height);
        const blob = await canvasBlob(canvas, "image/png");
        const name = videoTrack?.label?.trim() || "当前屏幕截取";
        return {
          name,
          width,
          height,
          source: "browser-display",
          file: blobToFile(blob, sanitizeCaptureName(name)),
        };
      } finally {
        stopTracks(stream);
      }
    }

    // Prototype fallback so the live screenshot flow remains testable without platform capture.
    await delay(120, signal);
    return {
      name: "当前屏幕截取",
      source: "synthetic",
      file: blobToFile(new Blob(["synthetic-screenshot"], { type: "image/png" }), "当前屏幕截取.png"),
    };
  },
};
